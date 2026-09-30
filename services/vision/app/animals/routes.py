from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request

from app.animals.contracts import AnimalEnrollment, AnimalSearch
from app.media.requests import ImageRequest, image_request


def router(tenant_dependency):
    routes = APIRouter(prefix="/v1/animals", dependencies=[Depends(tenant_dependency)])

    @routes.post("", status_code=201)
    def enroll(
        request: Request,
        payload: Annotated[
            ImageRequest[AnimalEnrollment], Depends(image_request(AnimalEnrollment))
        ],
    ):
        body = payload.parameters
        tenant = request.headers["x-tenant-id"]
        vector, local, metadata = request.app.state.animals.extract(payload.image)
        return {
            "animal": request.app.state.animal_store.enroll_animal(
                tenant, body, vector, local, metadata
            )
        }

    @routes.post("/search")
    def search(
        request: Request,
        payload: Annotated[ImageRequest[AnimalSearch], Depends(image_request(AnimalSearch))],
    ):
        body = payload.parameters
        tenant = request.headers["x-tenant-id"]
        vector, local, _ = request.app.state.animals.extract(payload.image)
        return {
            "matches": request.app.state.animal_store.query_animals(tenant, body, vector, local),
            "method": body.method,
            "calibrated": body.method == "wildfusion",
        }

    @routes.delete("/{animal_id}", status_code=204)
    def delete(animal_id: UUID, request: Request):
        request.app.state.animal_store.delete_animal(request.headers["x-tenant-id"], animal_id)

    return routes
