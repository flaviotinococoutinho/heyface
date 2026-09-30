<?php

declare(strict_types=1);

namespace App\Http;

use App\Vision\RemoteResponse;

final class ResponsePresenter
{
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
