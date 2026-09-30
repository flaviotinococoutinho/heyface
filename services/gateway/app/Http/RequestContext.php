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
        $request->attributes->set('request_id', (string) Str::uuid());
        abort_if((int) $request->header('Content-Length', '0') > config('heyface.max_body_bytes'), 413);

        return ResponsePresenter::finalize($next($request), $request);
    }
}
