<?php

declare(strict_types=1);

namespace App\Http;

use Illuminate\Http\Request;
use Illuminate\Validation\ValidationException;

final class ImagePayload
{
    public function decode(Request $request): array
    {
        $data = $request->except('image');
        if ($request->hasFile('image')) {
            if ($request->exists('image_base64')) {
                throw ValidationException::withMessages(['image' => 'Choose one image source.']);
            }
            $request->validate(['image' => 'required|file|max:5120|mimetypes:image/jpeg,image/png']);
            $data['image_base64'] = base64_encode($request->file('image')->getContent());
        }
        foreach (['person', 'filters', 'animal'] as $field) {
            if (isset($data[$field]) && is_string($data[$field])) {
                try {
                    $value = json_decode($data[$field], true, 32, JSON_THROW_ON_ERROR);
                    if (! is_array($value) || array_is_list($value) && $value !== []) {
                        throw new \JsonException;
                    }
                    $data[$field] = $value ?: (object) [];
                } catch (\JsonException) {
                    throw ValidationException::withMessages([$field => 'Invalid JSON object.']);
                }
            }
            if (array_key_exists($field, $data) && $data[$field] === []) {
                $data[$field] = (object) [];
            }
        }
        foreach (['limit', 'hnsw_ef', 'candidate_limit'] as $field) {
            if (isset($data[$field]) && is_string($data[$field]) && ctype_digit($data[$field])) {
                $data[$field] = (int) $data[$field];
            }
        }
        foreach (['exact', 'single_subject_confirmed'] as $field) {
            if (isset($data[$field]) && is_string($data[$field])) {
                $data[$field] = filter_var($data[$field], FILTER_VALIDATE_BOOLEAN, FILTER_NULL_ON_FAILURE);
            }
        }

        return $data;
    }
}
