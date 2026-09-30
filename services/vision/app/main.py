import secrets
import time
from contextlib import asynccontextmanager
from typing import Annotated
from uuid import UUID

from fastapi import Depends, FastAPI, Header, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.animals.recognition import AnimalRecognition
from app.animals.repository import AnimalRepository
from app.animals.routes import router as animal_router
from app.config import settings
from app.domain.contracts import ImageInput, validate_tenant
from app.errors import DomainError
from app.people.contracts import Enrollment, ListPeople, Search
from app.people.recognition import HumanRecognition
from app.people.repository import PersonRepository
from app.retrieval.collection import ANIMAL_COLLECTION
from app.retrieval.qdrant import Qdrant


@asynccontextmanager
async def lifespan(app: FastAPI):
    if len(settings.service_token) < 32 or len(settings.qdrant_key) < 32:
        raise RuntimeError("Run the bootstrap command to configure service credentials.")
    transport = Qdrant(settings)
    store = PersonRepository(transport, settings.collection)
    for attempt in range(30):
        try:
            store.initialize()
            break
        except DomainError:
            if attempt == 29:
                raise
            time.sleep(1)
    app.state.store = store
    app.state.engine = HumanRecognition(settings)
    app.state.animal_store = AnimalRepository(transport, ANIMAL_COLLECTION)
    app.state.animal_store.initialize()
    app.state.animals = AnimalRecognition(settings)
    yield
    transport.close()


app = FastAPI(
    title="Heyface internal vision API",
    version="0.1.0",
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)


@app.exception_handler(DomainError)
async def domain_error(request, error):
    headers = {"Retry-After": "2"} if error.status == 503 else {}
    return JSONResponse({"error": {"code": error.code}}, status_code=error.status, headers=headers)


@app.exception_handler(RequestValidationError)
async def validation_error(request, error):
    # Pydantic's default includes the input (potentially a biometric image).
    return JSONResponse({"error": {"code": "invalid_request"}}, status_code=422)


def tenant(
    authorization: Annotated[str | None, Header()] = None,
    x_tenant_id: Annotated[str | None, Header()] = None,
):
    if not authorization or not secrets.compare_digest(
        authorization, "Bearer " + settings.service_token
    ):
        raise DomainError("unauthorized", 401)
    try:
        return validate_tenant(x_tenant_id or "")
    except ValueError:
        raise DomainError("unauthorized", 401) from None


Tenant = Annotated[str, Depends(tenant)]
app.include_router(animal_router(tenant))


@app.get("/health/live")
def live():
    return {"status": "ok"}


@app.get("/health/ready")
def ready(request: Request):
    request.app.state.store.healthy()
    request.app.state.animal_store.healthy()
    return {"status": "ok", "model": settings.model_version}


@app.post("/v1/faces/analyze")
def analyze(body: ImageInput, tenant: Tenant, request: Request):
    _, face = request.app.state.engine.query(body.image_base64, "facenet")
    return {"face": face}


@app.post("/v1/people", status_code=201)
def enroll(body: Enrollment, tenant: Tenant, request: Request):
    vector, face = request.app.state.engine.enroll(body.image_base64)
    result = request.app.state.store.enroll(tenant, str(body.person_id), body.person, vector, face)
    return {"person": result}


@app.post("/v1/people/query")
def people(body: ListPeople, tenant: Tenant, request: Request):
    return request.app.state.store.list(tenant, body)


@app.post("/v1/search")
def search(body: Search, tenant: Tenant, request: Request):
    start = time.perf_counter()
    vector, face = request.app.state.engine.query(body.image_base64, body.method)
    inference_ms = (time.perf_counter() - start) * 1000
    query_start = time.perf_counter()
    result = request.app.state.store.search(tenant, vector, body)
    return {
        "matches": result,
        "face": face,
        "metric": "cosine",
        "mode": "exact" if body.exact else "approximate",
        "timing_ms": {
            "inference": round(inference_ms, 2),
            "search": round((time.perf_counter() - query_start) * 1000, 2),
        },
    }


@app.get("/v1/people/{person_id}")
def person(person_id: UUID, tenant: Tenant, request: Request):
    return {"person": request.app.state.store.get(tenant, str(person_id))}


@app.delete("/v1/people/{person_id}", status_code=204)
def delete(person_id: UUID, tenant: Tenant, request: Request):
    request.app.state.store.delete(tenant, str(person_id))


@app.get("/v1/methods")
def methods(tenant: Tenant):
    return {
        "methods": [
            {"id": "facenet", "domain": "person", "dimensions": 512, "available": True},
            {"id": "sface", "domain": "person", "dimensions": 128, "available": True},
            {"id": "dinov2", "domain": "animal", "dimensions": 384, "available": True},
            {
                "id": "wildfusion",
                "domain": "animal",
                "dimensions": 384,
                "available": True,
                "requires": "species_calibration",
                "variant": "dinov2-sift",
            },
        ]
    }
