import re
import unicodedata
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.policies import IMAGE

Name = Annotated[str, Field(min_length=1, max_length=160)]
Sex = Literal["female", "male", "other", "unspecified"]


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFKD", value.casefold())
    return " ".join("".join(c for c in value if not unicodedata.combining(c)).split())


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, allow_inf_nan=False)


class ImageInput(StrictModel):
    image_base64: Annotated[str, Field(min_length=4, max_length=IMAGE.max_encoded_characters)]


def validate_tenant(value: str) -> str:
    if not re.fullmatch(r"[a-zA-Z0-9_-]{1,64}", value):
        raise ValueError("invalid_tenant")
    return value
