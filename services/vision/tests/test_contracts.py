import base64
import io
from datetime import date, timedelta

import pytest
from PIL import Image
from pydantic import ValidationError

from app.config import Settings
from app.domain.representations import Embedding, VectorSpace
from app.errors import DomainError
from app.media.images import decode_image
from app.people.contracts import Filters, Person, Search
from app.people.repository import build_filter, point_id


def encoded_image(fmt="PNG", size=(20, 20)):
    output = io.BytesIO()
    Image.new("RGB", size, "white").save(output, format=fmt)
    return base64.b64encode(output.getvalue()).decode()


def test_metadata_filters_precede_similarity_and_preserve_tenant():
    result = build_filter(
        "tenant-a",
        Filters(
            name="João da Silva",
            city="Vitória",
            state="ES",
            sex="male",
            birth_date_from=date(1980, 1, 1),
            birth_date_to=date(1990, 1, 1),
        ),
    )
    clauses = result["must"]
    assert clauses[0] == {"key": "tenant_id", "match": {"value": "tenant-a"}}
    assert {"key": "city_normalized", "match": {"value": "vitoria"}} in clauses
    assert {"key": "name_tokens", "match": {"value": "joao"}} in clauses
    assert clauses[-1]["range"] == {
        "gte": date(1980, 1, 1).toordinal(),
        "lte": date(1990, 1, 1).toordinal(),
    }


def test_external_identifiers_cannot_overwrite_another_tenant():
    assert point_id("a", "same-id") != point_id("b", "same-id")
    assert point_id("a", "same-id") == point_id("a", "same-id")


@pytest.mark.parametrize(
    "changes",
    [
        {"consent": False},
        {"birth_date": date.today() + timedelta(days=1)},
        {"sex": "inferred"},
        {"unknown": "field"},
        {"name": "  "},
    ],
)
def test_invalid_registration_is_rejected(changes):
    values = {
        "name": "Example",
        "sex": "unspecified",
        "birth_date": "1990-01-01",
        "state": "ES",
        "city": "Vitória",
        "consent": True,
    } | changes
    with pytest.raises(ValidationError):
        Person(**values)


@pytest.mark.parametrize(
    "changes",
    [
        {"limit": 51},
        {"hnsw_ef": 99999},
        {"method": "unknown"},
        {"min_score": float("nan")},
        {"tenant_id": "attacker"},
    ],
)
def test_search_rejects_unbounded_and_unrecognized_parameters(changes):
    with pytest.raises(ValidationError):
        Search(image_base64="abcd", **changes)


def test_date_interval_is_validated():
    with pytest.raises(ValidationError):
        Filters(birth_date_from="2001-01-01", birth_date_to="1990-01-01")


@pytest.mark.parametrize("fmt", ["JPEG", "PNG"])
def test_image_decode_uses_actual_content(fmt):
    assert decode_image(encoded_image(fmt), Settings()).mode == "RGB"


@pytest.mark.parametrize(
    "value,code",
    [
        ("not base64!", "invalid_base64"),
        (base64.b64encode(b"not an image").decode(), "invalid_image"),
        (encoded_image("GIF"), "unsupported_image"),
    ],
)
def test_bad_image_errors_are_specific(value, code):
    with pytest.raises(DomainError) as error:
        decode_image(value, Settings())
    assert error.value.code == code


def test_pixel_limit_is_checked_before_decode():
    with pytest.raises(DomainError) as error:
        decode_image(encoded_image(size=(100, 100)), Settings(max_pixels=9000))
    assert error.value.status == 413


def test_data_uri_support_and_size_limit():
    value = "data:image/png;base64," + encoded_image()
    assert decode_image(value, Settings()).size == (20, 20)
    with pytest.raises(DomainError):
        decode_image(value, Settings(max_image_bytes=8))


def test_embedding_normalization_and_immutability():
    space = VectorSpace("test", 2, "v1")
    vector = space.normalize([3, 4])
    assert vector.values == (0.6, 0.8)
    with pytest.raises(AttributeError):
        vector.values = (1, 0)


@pytest.mark.parametrize("values", [[0, 0], [1], [float("nan"), 0], [float("inf"), 0]])
def test_invalid_vectors_do_not_enter_storage(values):
    with pytest.raises(ValueError):
        VectorSpace("test", 2, "v1").normalize(values)


def test_embedding_constructor_cannot_bypass_normalization():
    with pytest.raises(ValueError):
        Embedding(VectorSpace("test", 2, "v1"), (3, 4))
