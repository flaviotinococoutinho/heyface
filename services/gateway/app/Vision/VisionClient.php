<?php

declare(strict_types=1);

namespace App\Vision;

use App\Access\Principal;
use App\Vision\Ports\VisionGateway;
use Illuminate\Http\Client\ConnectionException;
use Illuminate\Support\Facades\Http;

final class VisionClient implements VisionGateway
{
    public function send(Principal $principal, string $method, string $path, array|VisionPayload $data = []): RemoteResponse
    {
        $payload = $data instanceof VisionPayload ? $data : new VisionPayload($data);
        $stream = null;
        try {
            $client = Http::baseUrl(config('heyface.vision_url'))
                ->withToken(config('heyface.service_token'))
                ->withHeaders(['X-Tenant-Id' => $principal->tenant,
                    'X-Request-Id' => request()->attributes->get('request_id')])
                ->connectTimeout(config('heyface.connect_timeout_seconds'))
                ->timeout(config('heyface.vision_timeout_seconds'))->acceptJson();
            $options = $payload->metadata ? ['json' => $payload->metadata] : [];
            if ($payload->imagePath !== null) {
                $stream = fopen($payload->imagePath, 'rb');
                $client->attach('image', $stream, 'image', ['Content-Type' => $payload->imageType]);
                $options = ['multipart' => [['name' => 'metadata', 'contents' => json_encode(
                    (object) $payload->metadata, JSON_THROW_ON_ERROR
                )]]];
            }
            $result = $client->send($method, $path, $options);
        } catch (ConnectionException) {
            return new RemoteResponse(503, ['error' => ['code' => 'vision_unavailable']], ['Retry-After' => '2']);
        } finally {
            if (is_resource($stream)) {
                fclose($stream);
            }
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
