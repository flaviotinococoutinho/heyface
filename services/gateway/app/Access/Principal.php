<?php

declare(strict_types=1);

namespace App\Access;

final readonly class Principal
{
    public function __construct(public string $tenant, public string $credentialId, private array $scopes)
    {
        if (! preg_match('/^[a-zA-Z0-9_-]{1,64}$/', $tenant)) {
            throw new \InvalidArgumentException('Invalid tenant identifier');
        }
        if (array_diff($scopes, ['read', 'write', 'delete'])) {
            throw new \InvalidArgumentException('Unknown access capability');
        }
    }

    public function permits(string $scope): bool
    {
        return in_array($scope, $this->scopes, true);
    }
}
