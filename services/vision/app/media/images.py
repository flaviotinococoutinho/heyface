import base64
import binascii
import io
import warnings

from PIL import Image, ImageOps, UnidentifiedImageError

from app.config import Settings
from app.errors import DomainError


def decode_image(encoded: str, settings: Settings) -> Image.Image:
    if encoded.startswith("data:"):
        prefix, sep, encoded = encoded.partition(",")
        if not sep or prefix not in {"data:image/jpeg;base64", "data:image/png;base64"}:
            raise DomainError("invalid_image")
    if len(encoded) > ((settings.max_image_bytes + 2) // 3) * 4:
        raise DomainError("image_too_large", 413)
    try:
        data = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error):
        raise DomainError("invalid_base64") from None
    if not data or len(data) > settings.max_image_bytes:
        raise DomainError("image_too_large", 413)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as image:
                if image.format not in {"JPEG", "PNG"}:
                    raise DomainError("unsupported_image", 415)
                if image.width * image.height > settings.max_pixels:
                    raise DomainError("image_too_large", 413)
                image.load()
                return ImageOps.exif_transpose(image).convert("RGB")
    except DomainError:
        raise
    except (UnidentifiedImageError, OSError, ValueError):
        raise DomainError("invalid_image") from None
    except (Image.DecompressionBombWarning, Image.DecompressionBombError):
        raise DomainError("image_too_large", 413) from None
