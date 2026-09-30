<?php

declare(strict_types=1);

namespace App\People\UseCases;

use App\Access\RequireCapability;
use App\Http\ResponsePresenter;
use App\Vision\Ports\VisionGateway;
use Illuminate\Http\Request;

final readonly class GetPerson
{
    public function __construct(private VisionGateway $vision) {}

    public function __invoke(Request $request, string $id)
    {
        $principal = RequireCapability::for($request, 'read');

        return ResponsePresenter::present($this->vision->send($principal, 'GET', '/v1/people/'.$id, []));
    }
}
