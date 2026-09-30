<?php

return [
    'access_file' => env('ACCESS_FILE', '/run/heyface/keys.json'),
    'vision_url' => env('VISION_URL', 'http://vision:8000'),
    'service_token' => env('VISION_SERVICE_TOKEN'),
    'requests_per_minute' => (int) env('REQUESTS_PER_MINUTE', 120),
    'connect_timeout_seconds' => 2,
    'vision_timeout_seconds' => 45,
    'max_body_bytes' => 8 * 1024 * 1024,
];
