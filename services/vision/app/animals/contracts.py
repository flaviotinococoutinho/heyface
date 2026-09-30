from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field

from app.domain.contracts import Sex, StrictModel
from app.policies import SEARCH

Species = Annotated[str, Field(pattern=r"^[a-z][a-z0-9-]{1,63}$")]


class Animal(StrictModel):
    name: Annotated[str, Field(min_length=1, max_length=160)]
    species: Species
    sex: Sex = "unspecified"
    breed: Annotated[str, Field(max_length=100)] = ""
    color: Annotated[str, Field(max_length=100)] = ""
    pattern: Annotated[str, Field(max_length=100)] = ""
    consent: Literal[True]


class AnimalEnrollment(StrictModel):
    animal: Animal
    animal_id: UUID
    single_subject_confirmed: Literal[True]


class AnimalSearch(StrictModel):
    species: Species
    single_subject_confirmed: Literal[True]
    method: Literal["dinov2", "wildfusion"] = "dinov2"
    limit: Annotated[int, Field(ge=1, le=SEARCH.animal_limit)] = SEARCH.default_limit
    candidate_limit: Annotated[int, Field(ge=SEARCH.animal_limit, le=SEARCH.candidate_limit)] = (
        SEARCH.default_candidates
    )
    exact: bool = False
    hnsw_ef: Annotated[int, Field(ge=SEARCH.hnsw_ef_min, le=SEARCH.hnsw_ef_max)] = SEARCH.hnsw_ef
