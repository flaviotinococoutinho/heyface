<?php

declare(strict_types=1);

namespace App\Providers;

use App\Vision\Ports\VisionGateway;
use App\Vision\VisionClient;
use Illuminate\Cache\RateLimiting\Limit;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\RateLimiter;
use Illuminate\Support\ServiceProvider;

final class AppServiceProvider extends ServiceProvider
{
    public function register(): void
    {
        $this->app->bind(VisionGateway::class, VisionClient::class);
    }

    public function boot(): void
    {
        RateLimiter::for('api', fn (Request $request) => Limit::perMinute(config('heyface.requests_per_minute'))
            ->by($request->attributes->get('credential_id')));
    }
}
