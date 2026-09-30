<?php

declare(strict_types=1);

namespace App\Access;

use Closure;
use Illuminate\Http\Request;

final class Authenticate
{
    public function handle(Request $request, Closure $next)
    {
        if ($request->is('api/v1/health/live', 'api/v1/openapi.json')) {
            return $next($request);
        }
        $token = $request->bearerToken();
        abort_if(! $token || strlen($token) > 256, 401);
        $registry = json_decode(file_get_contents(config('heyface.access_file')), true, 32, JSON_THROW_ON_ERROR);
        $hash = hash('sha256', $token);
        $credential = $registry[$hash] ?? null;
        abort_if(! $credential || ! empty($credential['revoked']), 401);
        $request->attributes->set('tenant_id', $credential['tenant']);
        $request->attributes->set('credential_id', $hash);
        $request->attributes->set('scopes', $credential['scopes']);
        $request->attributes->set(Principal::class, new Principal($credential['tenant'], $hash, $credential['scopes']));

        return $next($request);
    }
}
