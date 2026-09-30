<?php

declare(strict_types=1);

namespace App\Http;

use App\Vision\RemoteResponse;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Symfony\Component\HttpFoundation\Response;

final class ResponsePresenter
{
    public static function finalize(Response $response, Request $request): Response
    {
        $identity = $request->attributes->get('request_id');
        $response->headers->set('X-Request-Id', (string) $identity);
        $response->headers->set('Cache-Control', 'no-store');
        $response->headers->set('Content-Language', app()->getLocale() === 'en' ? 'en' : 'pt-BR');
        $response->setVary(['Accept', 'Accept-Language'], false);
        if (! $response instanceof JsonResponse || $response->getStatusCode() < 400) {
            return $response;
        }
        $body = $response->getData(true);
        if (! isset($body['error']['code'])) {
            return $response;
        }
        if (! in_array('application/problem+json', $request->getAcceptableContentTypes(), true)
            || $request->prefers(['application/problem+json', 'application/json']) !== 'application/problem+json') {
            return $response;
        }
        $code = $body['error']['code'];
        $status = $response->getStatusCode();
        $response->setData([
            'type' => 'urn:heyface:problem:'.$code,
            'title' => Response::$statusTexts[$status] ?? 'Request failed',
            'status' => $status,
            'detail' => $body['error']['message'] ?? __('errors.invalid_request'),
            'instance' => 'urn:uuid:'.$identity,
            'code' => $code,
            'request_id' => $identity,
        ]);
        $response->headers->set('Content-Type', 'application/problem+json');

        return $response;
    }

    public static function present(RemoteResponse $result)
    {
        if ($result->status === 204) {
            return response('', 204);
        }
        $body = $result->body;
        if (isset($body['error']['code'])) {
            $key = 'errors.'.$body['error']['code'];
            $body['error']['message'] = trans()->has($key) ? __($key) : __('errors.invalid_request');
        }

        return response()->json($body, $result->status, $result->headers);
    }
}
