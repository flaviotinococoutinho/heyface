<?php

declare(strict_types=1);

namespace App\People\UseCases;

use App\Access\RequireCapability;
use App\Http\ImagePayload;
use App\Http\ResponsePresenter;
use App\Vision\Ports\VisionGateway;
use Illuminate\Http\Request;
use Illuminate\Support\Str;

final readonly class EnrollPerson
{
    public function __construct(private VisionGateway $vision, private ImagePayload $images) {}

    public function __invoke(Request $request)
    {
        $principal = RequireCapability::for($request, 'write');
        $data = $this->images->decode($request);
        $data['person_id'] ??= (string) Str::uuid();

        return ResponsePresenter::present($this->vision->send($principal, 'POST', '/v1/people', $data));
    }
}
