<?php

declare(strict_types=1);

namespace App\Vision;

final readonly class VisionPayload
{
    public function __construct(
        public array $metadata,
        public ?string $imagePath = null,
        public ?string $imageType = null,
    ) {}

    public function withDefaultIdentifier(string $field, string $identifier): self
    {
        return new self(
            [...$this->metadata, $field => $this->metadata[$field] ?? $identifier],
            $this->imagePath,
            $this->imageType,
        );
    }
}
