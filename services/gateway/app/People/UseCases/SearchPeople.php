<?php

declare(strict_types=1);

namespace App\People\UseCases;

use App\Access\RequireCapability;
use App\Http\ImagePayload;
use App\Http\ResponsePresenter;
use App\Vision\Ports\VisionGateway;
use Illuminate\Http\Request;

final readonly class SearchPeople
{
    public function __construct(private VisionGateway $vision, private ImagePayload $images) {}

    public function __invoke(Request $request)
    {
        $principal = RequireCapability::for($request, 'read');
        $data = $this->images->decode($request);

        return ResponsePresenter::present($this->vision->send($principal, 'POST', '/v1/search', $data));
    }
}
