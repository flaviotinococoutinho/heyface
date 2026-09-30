<?php

return ['default' => env('CACHE_STORE', 'redis'), 'prefix' => 'heyface_cache_',
    'stores' => ['redis' => ['driver' => 'redis', 'connection' => 'cache', 'lock_connection' => 'default'],
        'array' => ['driver' => 'array', 'serialize' => false]]];
