<?php

declare(strict_types=1);

namespace App\Access;

use Illuminate\Http\Request;

final class RequireCapability
{
    public static function for(Request $request, string $scope): Principal
    {
        $principal = $request->attributes->get(Principal::class);
        abort_unless($principal instanceof Principal && $principal->permits($scope), 403);

        return $principal;
    }
}
