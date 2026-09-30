<?php

declare(strict_types=1);

namespace App\Vision;

use App\Access\Principal;
use App\Vision\Ports\VisionGateway;
use Illuminate\Http\Client\ConnectionException;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Str;

final class VisionClient implements VisionGateway
{
    public function send(Principal $principal, string $method, string $path, array $data = []): RemoteResponse
    {
        try {
            $result = Http::baseUrl(config('heyface.vision_url'))
                ->withToken(config('heyface.service_token'))
                ->withHeaders(['X-Tenant-Id' => $principal->tenant,
                    'X-Request-Id' => (string) Str::uuid()])
                ->connectTimeout(config('heyface.connect_timeout_seconds'))
                ->timeout(config('heyface.vision_timeout_seconds'))->acceptJson()
                ->send($method, $path, $data ? ['json' => $data] : []);
        } catch (ConnectionException) {
            return new RemoteResponse(503, ['error' => ['code' => 'vision_unavailable']], ['Retry-After' => '2']);
        }
        if ($result->status() === 204) {
            return new RemoteResponse(204);
        }
        $body = $result->json();
        if (! is_array($body)) {
            $status = $result->status() === 503 ? 503 : 502;
            $headers = $status === 503 ? ['Retry-After' => '2'] : [];

            return new RemoteResponse($status, ['error' => ['code' => 'vision_unavailable']], $headers);
        }
        $headers = $result->status() === 503 ? ['Retry-After' => '2'] : [];

        return new RemoteResponse($result->status(), $body, $headers);
    }
}
