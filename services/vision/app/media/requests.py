"""HTTP image envelopes end here. Recognition receives bytes and typed parameters."""

import json
from dataclasses import dataclass
from typing import TypeVar

from fastapi import Request
from pydantic import BaseModel, ValidationError
from starlette.datastructures import UploadFile

from app.errors import DomainError
from app.media.images import decode_base64
from app.policies import IMAGE

MAX_BODY_BYTES = 8 * 1024 * 1024
MAX_METADATA_BYTES = 64 * 1024
MAX_FORM_FIELDS = 20
Parameters = TypeVar("Parameters", bound=BaseModel)


@dataclass(frozen=True)
class ImageRequest[Parameters: BaseModel]:
    parameters: Parameters
    image: bytes


def image_request[Parameters: BaseModel](model: type[Parameters]):
    async def parse(request: Request) -> ImageRequest[Parameters]:
        content_type = request.headers.get("content-type", "").split(";", 1)[0].lower()
        if content_type == "multipart/form-data":
            return await multipart_request(request, model)
        if content_type != "application/json":
            raise DomainError("unsupported_media_type", 415)
        raw = await bounded_body(request)
        data = json_object(raw)
        encoded = data.pop("image_base64", None)
        if not isinstance(encoded, str):
            raise DomainError("invalid_request")
        return ImageRequest(validate(model, data), decode_base64(encoded, IMAGE.max_bytes))

    return parse


async def bounded_body(request: Request) -> bytes:
    parts = bytearray()
    async for chunk in request.stream():
        parts.extend(chunk)
        if len(parts) > MAX_BODY_BYTES:
            raise DomainError("image_too_large", 413)
    return bytes(parts)


async def multipart_request[Parameters: BaseModel](
    request: Request, model: type[Parameters]
) -> ImageRequest[Parameters]:
    # Gateway already streams a bounded file. Bound the internal boundary too.
    async with bounded_form_request(request).form(
        max_files=1, max_fields=MAX_FORM_FIELDS, max_part_size=MAX_METADATA_BYTES
    ) as form:
        if set(form) != {"metadata", "image"} or len(form.multi_items()) != 2:
            raise DomainError("invalid_request")
        upload = form["image"]
        metadata = form["metadata"]
        if not isinstance(upload, UploadFile) or not isinstance(metadata, str):
            raise DomainError("invalid_request")
        if len(metadata.encode()) > MAX_METADATA_BYTES:
            raise DomainError("invalid_request")
        parameters = validate(model, json_object(metadata))
        image = await upload.read(IMAGE.max_bytes + 1)
        if not image or len(image) > IMAGE.max_bytes:
            raise DomainError("image_too_large", 413)
        return ImageRequest(parameters, image)


def bounded_form_request(request: Request) -> Request:
    received = 0

    async def receive():
        nonlocal received
        message = await request.receive()
        received += len(message.get("body", b""))
        if received > MAX_BODY_BYTES:
            raise DomainError("image_too_large", 413)
        return message

    return Request(request.scope, receive=receive)


def json_object(raw: str | bytes) -> dict:
    try:
        value = json.loads(raw)
        if isinstance(value, dict):
            return value
    except (ValueError, UnicodeError, RecursionError):
        pass
    raise DomainError("invalid_request")


def validate[Parameters: BaseModel](model: type[Parameters], data: dict) -> Parameters:
    try:
        return model.model_validate(data)
    except (ValidationError, ValueError):
        raise DomainError("invalid_request") from None
