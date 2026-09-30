<?php

return [
    'server_error' => 'The request could not be completed. Use the request ID to report the failure.',
    'unauthorized' => 'Enter a valid access key.', 'forbidden' => 'This key cannot perform this operation.',
    'not_found' => 'Resource not found.', 'person_not_found' => 'Record not found.',
    'invalid_request' => 'Check the submitted fields and try again.',
    'invalid_base64' => 'The base64 image is invalid.',
    'invalid_image' => 'The image could not be read. Send a valid JPEG or PNG.',
    'unsupported_image' => 'Use a JPEG or PNG image.',
    'unsupported_media_type' => 'Send the image using multipart/form-data or JSON.',
    'image_too_large' => 'Use an image up to 5 MB and 16 million pixels.',
    'no_face' => 'No face found. Use a well-lit, front-facing photo.',
    'multiple_faces' => 'More than one face found. Crop the image to one person.',
    'face_too_small' => 'The face is too small. Use a closer photo.',
    'low_face_confidence' => 'The face is not clear enough. Try another photo.',
    'vision_busy' => 'Processing is busy. Try again shortly.',
    'vision_unavailable' => 'Image processing is temporarily unavailable.',
    'storage_unavailable' => 'Search is temporarily unavailable.',
    'invalid_embedding' => 'This image could not be represented. Try another photo.',
    'rate_limited' => 'Request limit reached. Please wait before trying again.',
    'calibration_required' => 'This method requires calibration for the selected species.',
];
