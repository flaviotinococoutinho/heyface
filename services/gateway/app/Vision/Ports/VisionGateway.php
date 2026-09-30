<?php

declare(strict_types=1);

namespace App\Vision\Ports;

use App\Access\Principal;
use App\Vision\RemoteResponse;
use App\Vision\VisionPayload;

interface VisionGateway
{
    public function send(Principal $principal, string $method, string $path, array|VisionPayload $data = []): RemoteResponse;
}
