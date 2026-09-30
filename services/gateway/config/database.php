<?php

return ['redis' => ['client' => 'phpredis', 'options' => ['prefix' => 'heyface_'],
    'default' => ['host' => env('REDIS_HOST', 'redis'), 'password' => env('REDIS_PASSWORD'), 'port' => 6379, 'database' => 0, 'timeout' => 2, 'read_timeout' => 2],
    'cache' => ['host' => env('REDIS_HOST', 'redis'), 'password' => env('REDIS_PASSWORD'), 'port' => 6379, 'database' => 1, 'timeout' => 2, 'read_timeout' => 2]]];
