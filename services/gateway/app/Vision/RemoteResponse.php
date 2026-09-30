<?php

declare(strict_types=1);

namespace App\Vision;

final readonly class RemoteResponse
{
    public function __construct(public int $status, public array $body = [], public array $headers = []) {}
}
