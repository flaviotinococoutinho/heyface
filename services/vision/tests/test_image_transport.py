import base64
import json
from typing import Annotated

import pytest
from fastapi import Depends, FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from app.errors import DomainError
from app.media.requests import MAX_METADATA_BYTES, ImageRequest, image_request
from app.people.contracts import Search

app = FastAPI()


@app.exception_handler(DomainError)
async def domain_error(request, error):
    return JSONResponse({"code": error.code}, status_code=error.status)


@app.post("/search")
def inspect_image(payload: Annotated[ImageRequest[Search], Depends(image_request(Search))]):
    return {"bytes": list(payload.image), "parameters": payload.parameters.model_dump()}


client = TestClient(app)
IMAGE_BYTES = b"\x00\xff\x01\x80binary-image"


def test_binary_transport_preserves_bytes_and_metadata_without_base64():
    response = client.post(
        "/search",
        data={"metadata": json.dumps({"method": "sface", "filters": {"city": "Vitória"}})},
        files={"image": ("photo.png", IMAGE_BYTES, "image/png")},
    )
    assert response.status_code == 200
    assert bytes(response.json()["bytes"]) == IMAGE_BYTES
    assert response.json()["parameters"]["filters"]["city"] == "Vitória"


def test_json_compatibility_reaches_the_same_bytes():
    response = client.post("/search", json={"image_base64": base64.b64encode(IMAGE_BYTES).decode()})
    assert response.status_code == 200
    assert bytes(response.json()["bytes"]) == IMAGE_BYTES


@pytest.mark.parametrize(
    "metadata",
    [
        "[]",
        "null",
        "bad-json",
        '{"limit":51}',
        '{"image_base64":"abcd"}',
        " " * (MAX_METADATA_BYTES + 1),
    ],
)
def test_invalid_metadata_does_not_reach_recognition(metadata):
    response = client.post(
        "/search", data={"metadata": metadata}, files={"image": ("x.png", IMAGE_BYTES)}
    )
    assert response.status_code in {400, 422}
    assert "binary-image" not in response.text


def test_duplicate_or_conflicting_parts_are_rejected():
    response = client.post(
        "/search",
        files=[
            ("image", ("x.png", IMAGE_BYTES)),
            ("metadata", (None, "{}")),
            ("metadata", (None, '{"limit":1}')),
        ],
    )
    assert response.status_code == 422


def test_unknown_content_type_is_explicit():
    response = client.post(
        "/search", content=IMAGE_BYTES, headers={"Content-Type": "application/protobuf"}
    )
    assert response.status_code == 415
