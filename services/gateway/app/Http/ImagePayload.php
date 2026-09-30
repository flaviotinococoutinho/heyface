<?php

declare(strict_types=1);

namespace App\Http;

use App\Vision\VisionPayload;
use Illuminate\Http\Request;
use Illuminate\Validation\ValidationException;

final class ImagePayload
{
    public function decode(Request $request): VisionPayload
    {
        $mediaType = strtolower(explode(';', $request->header('Content-Type', ''))[0]);
        abort_unless(in_array($mediaType, ['', 'application/json', 'multipart/form-data', 'application/x-www-form-urlencoded'], true), 415);
        $data = $request->except('image');
        $canonical = $request->exists('metadata');
        if ($canonical) {
            if (array_diff(array_keys($request->all()), ['metadata', 'image'])) {
                throw ValidationException::withMessages(['metadata' => 'Choose one envelope.']);
            }
            $data = $this->object($request->input('metadata'));
            $request->validate(['image' => 'required|file']);
        }
        $image = null;
        if ($request->hasFile('image')) {
            if (array_key_exists('image_base64', $data)) {
                throw ValidationException::withMessages(['image' => 'Choose one image source.']);
            }
            $request->validate(['image' => 'required|file|max:'.config('heyface.max_image_kib').'|mimetypes:image/jpeg,image/png']);
            $image = $request->file('image');
        }
        foreach (['person', 'filters', 'animal'] as $field) {
            if (! $canonical && isset($data[$field]) && is_string($data[$field])) {
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
            if (! $canonical && array_key_exists($field, $data) && $data[$field] === []) {
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

        return new VisionPayload($data, $image?->getRealPath(), $image?->getMimeType());
    }

    private function object(mixed $value): array
    {
        if (! is_string($value) || strlen($value) > config('heyface.max_metadata_bytes')) {
            throw ValidationException::withMessages(['metadata' => 'Invalid metadata.']);
        }
        try {
            $object = json_decode($value, false, 32, JSON_THROW_ON_ERROR);
            if (! $object instanceof \stdClass) {
                throw new \JsonException;
            }

            return get_object_vars($object);
        } catch (\JsonException) {
            throw ValidationException::withMessages(['metadata' => 'Invalid JSON object.']);
        }
    }
}
