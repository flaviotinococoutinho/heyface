<?php

declare(strict_types=1);

namespace App\Http;

use Closure;
use Illuminate\Http\Request;
use Illuminate\Support\Str;

final class RequestContext
{
    public function handle(Request $request, Closure $next)
    {
        app()->setLocale($request->getPreferredLanguage(['pt-BR', 'en']) === 'en' ? 'en' : 'pt_BR');
        abort_if((int) $request->header('Content-Length', '0') > config('heyface.max_body_bytes'), 413);
        $request->attributes->set('request_id', (string) Str::uuid());
        $response = $next($request);
        $response->headers->set('X-Request-Id', $request->attributes->get('request_id'));
        $response->headers->set('Cache-Control', 'no-store');
        $response->headers->set('Content-Language', app()->getLocale() === 'en' ? 'en' : 'pt-BR');

        return $response;
    }
}
