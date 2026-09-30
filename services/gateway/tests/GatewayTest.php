<?php

declare(strict_types=1);

namespace Tests;

use Illuminate\Contracts\Console\Kernel;
use Illuminate\Foundation\Testing\TestCase;
use Illuminate\Http\UploadedFile;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Str;

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

    public function test_plain_text_overload_keeps_a_retryable_status(): void
    {
        Http::fake(['vision:8000/*' => Http::response('Service Unavailable', 503)]);
        $this->withToken('reader-a')->postJson('/api/v1/search', ['image_base64' => 'abcd'])
            ->assertStatus(503)->assertHeader('Retry-After', '2')
            ->assertJsonPath('error.code', 'vision_unavailable');
    }

    public function test_binary_image_is_forwarded_as_multipart_with_original_bytes(): void
    {
        $captured = [];
        Http::fake(function ($request) use (&$captured) {
            $captured = ['body' => $request->body(), 'headers' => $request->headers()];

            return Http::response(['matches' => []]);
        });
        $bytes = base64_decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+cP1sAAAAASUVORK5CYII=');
        $image = UploadedFile::fake()->createWithContent('photo.png', $bytes);
        $response = $this->withToken('reader-a')->post('/api/v1/search', [
            'image' => $image, 'metadata' => '{"method":"sface","filters":{}}',
        ])->assertOk();
        self::assertStringContainsString('multipart/form-data', $captured['headers']['Content-Type'][0]);
        self::assertStringContainsString($bytes, $captured['body']);
        self::assertStringContainsString('"filters":{}', $captured['body']);
        self::assertStringNotContainsString('image_base64', $captured['body']);
        self::assertSame($response->headers->get('X-Request-Id'), $captured['headers']['X-Request-Id'][0]);
    }

    public function test_metadata_envelope_cannot_mix_sources(): void
    {
        $this->withToken('reader-a')->post('/api/v1/search', [
            'metadata' => '{}', 'image_base64' => 'abcd',
        ])->assertUnprocessable();
        Http::assertNothingSent();
    }

    public function test_problem_details_are_negotiated_and_localized_for_authentication_errors(): void
    {
        $response = $this->withHeader('Accept', 'application/problem+json, application/json')
            ->withHeader('Accept-Language', 'en')->post('/api/v1/search')
            ->assertUnauthorized()->assertHeader('Content-Type', 'application/problem+json')
            ->assertJsonPath('code', 'unauthorized')->assertJsonPath('status', 401)
            ->assertJsonPath('detail', 'Enter a valid access key.');
        self::assertSame($response->headers->get('X-Request-Id'), $response->json('request_id'));
        $this->withHeader('Accept', 'application/json')->post('/api/v1/search')
            ->assertUnauthorized()->assertJsonPath('error.code', 'unauthorized');
    }

    public function test_capabilities_describe_this_credential_without_exposing_secrets(): void
    {
        $this->withToken('reader-a')->getJson('/api/v1/capabilities')->assertOk()
            ->assertJsonPath('permissions', ['read'])->assertJsonPath('max_image_bytes', 5242880);
        Http::assertNothingSent();
    }

    public function test_public_contract_preserves_json_objects_without_authentication(): void
    {
        $response = $this->get('/api/v1/openapi.json')->assertOk();
        $contract = json_decode($response->getContent(), false, 512, JSON_THROW_ON_ERROR);
        self::assertInstanceOf(\stdClass::class, $contract->components->schemas->StrictModel->properties);
        Http::assertNothingSent();
    }

    public function test_unsupported_transport_does_not_reach_the_image_service(): void
    {
        $this->withToken('reader-a')->call('POST', '/api/v1/search', [], [], [], [
            'CONTENT_TYPE' => 'application/protobuf', 'HTTP_ACCEPT' => 'application/problem+json',
            'HTTP_AUTHORIZATION' => 'Bearer reader-a',
        ], 'binary')->assertStatus(415)->assertJsonPath('code', 'unsupported_media_type');
        Http::assertNothingSent();
    }

    public function test_enrollment_preserves_the_supplied_identifier_and_previous_default(): void
    {
        Http::fake(['vision:8000/*' => Http::response(['person' => []], 201)]);
        $identity = '1d4fa779-962e-4b5b-b88e-8a8f8d6093b5';
        $this->withToken('writer-b')->postJson('/api/v1/people', [
            'person_id' => $identity, 'image_base64' => 'abcd',
        ])->assertCreated();
        $this->withToken('writer-b')->postJson('/api/v1/animals', ['image_base64' => 'abcd'])->assertCreated();
        $sent = Http::recorded();
        self::assertSame($identity, $sent[0][0]['person_id']);
        self::assertTrue(Str::isUuid($sent[1][0]['animal_id']));
    }
}
