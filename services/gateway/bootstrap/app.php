<?php

declare(strict_types=1);

use App\Access\Authenticate;
use App\Http\RequestContext;
use Illuminate\Foundation\Application;
use Illuminate\Foundation\Configuration\Exceptions;
use Illuminate\Foundation\Configuration\Middleware;
use Illuminate\Http\Request;
use Illuminate\Validation\ValidationException;
use Symfony\Component\HttpKernel\Exception\HttpException;

return Application::configure(basePath: dirname(__DIR__))
    ->withRouting(api: __DIR__.'/../routes/api.php', apiPrefix: 'api/v1')
    ->withMiddleware(function (Middleware $middleware): void {
        $middleware->use([RequestContext::class]);
        $middleware->api(prepend: [Authenticate::class]);
    })
    ->withExceptions(function (Exceptions $exceptions): void {
        $exceptions->shouldRenderJsonWhen(fn (Request $request, Throwable $e) => true);
        $exceptions->render(function (ValidationException $e) {
            return response()->json(['error' => ['code' => 'invalid_request', 'message' => __('errors.invalid_request')]], 422);
        });
        $exceptions->render(function (HttpException $e) {
            $code = match ($e->getStatusCode()) {
                401 => 'unauthorized', 403 => 'forbidden', 404 => 'not_found', 413 => 'image_too_large', 429 => 'rate_limited', default => 'invalid_request'
            };

            return response()->json(['error' => ['code' => $code, 'message' => __('errors.'.$code)]], $e->getStatusCode(), $e->getHeaders());
        });
    })->create();
