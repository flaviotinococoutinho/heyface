<?php

declare(strict_types=1);

namespace App\Vision\Ports;

use App\Access\Principal;
use App\Vision\RemoteResponse;

interface VisionGateway
{
    public function send(Principal $principal, string $method, string $path, array $data = []): RemoteResponse;
}
