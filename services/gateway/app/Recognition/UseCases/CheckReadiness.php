<?php

declare(strict_types=1);

namespace App\Recognition\UseCases;

use App\Access\RequireCapability;
use App\Http\ResponsePresenter;
use App\Vision\Ports\VisionGateway;
use Illuminate\Http\Request;

final readonly class CheckReadiness
{
    public function __construct(private VisionGateway $vision) {}

    public function __invoke(Request $request)
    {
        $principal = RequireCapability::for($request, 'read');

        return ResponsePresenter::present($this->vision->send($principal, 'GET', '/health/ready', []));
    }
}
