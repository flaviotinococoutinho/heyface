<?php

declare(strict_types=1);

namespace Tests;

use Illuminate\Contracts\Console\Kernel;
use Illuminate\Foundation\Testing\TestCase;
use Illuminate\Support\Facades\Http;

final class GatewayTest extends TestCase
{
    private string $keys;

    public function createApplication()
    {
        $application = require __DIR__.'/../bootstrap/app.php';
        $application->make(Kernel::class)->bootstrap();

        return $application;
    }

    protected function setUp(): void
    {
        parent::setUp();
        $this->keys = tempnam(sys_get_temp_dir(), 'heyface-keys-');
        file_put_contents($this->keys, json_encode([
            hash('sha256', 'reader-a') => ['tenant' => 'a', 'scopes' => ['read']],
            hash('sha256', 'writer-b') => ['tenant' => 'b', 'scopes' => ['read', 'write', 'delete']],
        ]));
        config(['heyface.access_file' => $this->keys, 'heyface.service_token' => 'internal-service-secret']);
        Http::preventStrayRequests();
    }

    protected function tearDown(): void
    {
        unlink($this->keys);
        parent::tearDown();
    }

    public function test_health_is_public_but_search_requires_authentication(): void
    {
        $this->getJson('/api/v1/health/live')->assertOk();
        $this->postJson('/api/v1/search', [])->assertUnauthorized();
        Http::assertNothingSent();
    }

    public function test_read_only_key_cannot_register(): void
    {
        $this->withToken('reader-a')->postJson('/api/v1/people', [])->assertForbidden();
        Http::assertNothingSent();
    }

    public function test_tenant_and_locale_do_not_leak_between_requests(): void
    {
        Http::fake(['vision:8000/*' => Http::response(['error' => ['code' => 'no_face']], 422)]);
        $this->withToken('reader-a')->withHeader('X-Tenant-Id', 'b')->withHeader('Accept-Language', 'en')
            ->postJson('/api/v1/search', ['image_base64' => 'abcd'])->assertUnprocessable()
            ->assertJsonPath('error.message', 'No face found. Use a well-lit, front-facing photo.');
        $this->withToken('writer-b')->withHeader('Accept-Language', 'pt-BR')
            ->postJson('/api/v1/search', ['image_base64' => 'abcd'])->assertUnprocessable()
            ->assertJsonPath('error.message', 'Nenhum rosto foi encontrado. Use uma foto frontal e bem iluminada.');
        $sent = Http::recorded();
        self::assertSame('a', $sent[0][0]->header('X-Tenant-Id')[0]);
        self::assertSame('b', $sent[1][0]->header('X-Tenant-Id')[0]);
        self::assertSame('Bearer internal-service-secret', $sent[0][0]->header('Authorization')[0]);
    }

    public function test_upstream_failure_preserves_status_and_retry_header(): void
    {
        Http::fake(['vision:8000/*' => Http::response(['error' => ['code' => 'storage_unavailable']], 503)]);
        $this->withToken('reader-a')->postJson('/api/v1/search', ['image_base64' => 'abcd'])
            ->assertStatus(503)->assertHeader('Retry-After', '2')->assertJsonPath('error.code', 'storage_unavailable');
    }

    public function test_invalid_id_is_rejected_before_forwarding(): void
    {
        $this->withToken('reader-a')->getJson('/api/v1/people/not-a-uuid')->assertNotFound();
        Http::assertNothingSent();
    }

    public function test_multipart_json_is_parsed_and_excess_image_sources_are_rejected(): void
    {
        Http::fake(['vision:8000/*' => Http::response(['matches' => []])]);
        $this->withToken('reader-a')->post('/api/v1/search', ['image_base64' => 'abcd',
            'filters' => '{"city":"Vitória"}', 'exact' => 'false'])->assertOk();
        Http::assertSent(fn ($request) => $request['filters']['city'] === 'Vitória' && $request['exact'] === false);
    }

    public function test_empty_filter_object_is_preserved_for_the_python_contract(): void
    {
        Http::fake(['vision:8000/*' => Http::response(['matches' => []])]);
        $this->withToken('reader-a')->postJson('/api/v1/search', [
            'image_base64' => 'abcd', 'filters' => (object) [],
        ])->assertOk();
        Http::assertSent(fn ($request) => str_contains($request->body(), '"filters":{}'));
    }
}
