<?php

declare(strict_types=1);

namespace App\People\UseCases;

use App\Access\RequireCapability;
use App\Http\ResponsePresenter;
use App\Vision\Ports\VisionGateway;
use Illuminate\Http\Request;

final readonly class ListPeople
{
    public function __construct(private VisionGateway $vision) {}

    public function __invoke(Request $request)
    {
        $principal = RequireCapability::for($request, 'read');
        $data = $request->only('limit', 'cursor');
        $data['filters'] = (object) $request->except('limit', 'cursor');

        return ResponsePresenter::present($this->vision->send($principal, 'POST', '/v1/people/query', $data));
    }
}
