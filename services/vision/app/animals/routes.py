from uuid import UUID

from fastapi import APIRouter, Request

from app.animals.contracts import AnimalEnrollment, AnimalSearch


def router(tenant_dependency):
    from fastapi import Depends

    routes = APIRouter(prefix="/v1/animals", dependencies=[Depends(tenant_dependency)])

    @routes.post("", status_code=201)
    def enroll(body: AnimalEnrollment, request: Request):
        tenant = request.headers["x-tenant-id"]
        vector, local, metadata = request.app.state.animals.extract(body.image_base64)
        return {
            "animal": request.app.state.animal_store.enroll_animal(
                tenant, body, vector, local, metadata
            )
        }

    @routes.post("/search")
    def search(body: AnimalSearch, request: Request):
        tenant = request.headers["x-tenant-id"]
        vector, local, _ = request.app.state.animals.extract(body.image_base64)
        return {
            "matches": request.app.state.animal_store.query_animals(tenant, body, vector, local),
            "method": body.method,
            "calibrated": body.method == "wildfusion",
        }

    @routes.delete("/{animal_id}", status_code=204)
    def delete(animal_id: UUID, request: Request):
        request.app.state.animal_store.delete_animal(request.headers["x-tenant-id"], animal_id)

    return routes
