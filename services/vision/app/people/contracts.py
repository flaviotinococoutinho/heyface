from datetime import date
from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from app.domain.contracts import ImageInput, Name, Sex, StrictModel
from app.policies import SEARCH

EARLIEST_BIRTH_YEAR = 1900


class Person(StrictModel):
    name: Name
    sex: Sex = "unspecified"
    birth_date: date
    state: Annotated[str, Field(min_length=2, max_length=80)]
    city: Annotated[str, Field(min_length=1, max_length=120)]
    consent: Literal[True]

    @field_validator("birth_date")
    @classmethod
    def valid_birth_date(cls, value):
        if value > date.today() or value.year < EARLIEST_BIRTH_YEAR:
            raise ValueError("invalid_birth_date")
        return value


class Filters(StrictModel):
    name: Name | None = None
    sex: Sex | None = None
    birth_date: date | None = None
    birth_date_from: date | None = None
    birth_date_to: date | None = None
    state: Annotated[str, Field(min_length=2, max_length=80)] | None = None
    city: Annotated[str, Field(min_length=1, max_length=120)] | None = None

    @model_validator(mode="after")
    def valid_interval(self):
        if self.birth_date_from and self.birth_date_to:
            if self.birth_date_from > self.birth_date_to:
                raise ValueError("invalid_date_interval")
        return self


class Enrollment(ImageInput):
    person: Person
    person_id: UUID


class Search(ImageInput):
    method: Literal["facenet", "sface"] = "facenet"
    filters: Filters = Field(default_factory=Filters)
    limit: Annotated[int, Field(ge=1, le=SEARCH.human_limit)] = SEARCH.default_limit
    min_score: Annotated[float, Field(ge=-1, le=1)] | None = None
    exact: bool = False
    hnsw_ef: Annotated[int, Field(ge=SEARCH.hnsw_ef_min, le=SEARCH.hnsw_ef_max)] = SEARCH.hnsw_ef


class ListPeople(StrictModel):
    filters: Filters = Field(default_factory=Filters)
    limit: Annotated[int, Field(ge=1, le=SEARCH.page_limit)] = SEARCH.default_page_size
    cursor: UUID | None = None
