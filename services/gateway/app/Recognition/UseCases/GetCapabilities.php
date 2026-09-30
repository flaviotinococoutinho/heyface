<?php

declare(strict_types=1);

namespace App\Recognition\UseCases;

use App\Access\RequireCapability;
use Illuminate\Http\Request;

final class GetCapabilities
{
    public function __invoke(Request $request): array
    {
        $principal = RequireCapability::for($request, 'read');

        return [
            'api_version' => '1',
            'contract_version' => '1.1.0',
            'preferred_upload' => 'multipart/form-data',
            'image_field' => 'image',
            'metadata_field' => 'metadata',
            'accepted_image_types' => ['image/jpeg', 'image/png'],
            'max_image_bytes' => config('heyface.max_image_kib') * 1024,
            'max_metadata_bytes' => config('heyface.max_metadata_bytes'),
            'permissions' => array_values(array_filter(['read', 'write', 'delete'], $principal->permits(...))),
            'request_timeout_seconds' => config('heyface.vision_timeout_seconds'),
            'openapi' => '/api/v1/openapi.json',
        ];
    }
}
