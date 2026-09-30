"""Build the public HTTP contract from the same parameter schemas used by recognition."""

import argparse
import json
from pathlib import Path

from app.animals.contracts import AnimalEnrollment, AnimalSearch
from app.domain.contracts import StrictModel
from app.people.contracts import Enrollment, Filters, Search
from app.policies import IMAGE, SEARCH

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "services/gateway/resources/contracts/openapi.json"
CONTRACT_VERSION = "1.1.0"


def reference(name):
    return {"$ref": f"#/components/schemas/{name}"}


def object_schema(properties, required=None, *, extra=False):
    return {
        "type": "object",
        "properties": properties,
        "required": required or list(properties),
        "additionalProperties": extra,
    }


def array_schema(items, **constraints):
    return {"type": "array", "items": items, **constraints}


def build_schemas():
    schemas = {}
    for model in [Enrollment, Search, AnimalEnrollment, AnimalSearch, Filters, StrictModel]:
        schema = model.model_json_schema(ref_template="#/components/schemas/{model}")
        schemas.update(schema.pop("$defs", {}))
        for field in ("person_id", "animal_id"):
            if field in schema.get("required", []):
                schema["required"].remove(field)
                schema["properties"][field]["description"] = (
                    "Prefira UUID criado pelo cliente para repetição estável. "
                    "Na ausência, o gateway gera um UUID novo."
                )
        schemas[model.__name__] = schema
    text = {"type": "string"}
    number = {"type": "number"}
    integer = {"type": "integer"}
    uuid = {"type": "string", "format": "uuid"}
    timestamp = {"type": "string", "format": "date-time"}
    boolean = {"type": "boolean"}
    nullable_text = {"type": ["string", "null"]}
    schemas["FaceObservation"] = object_schema(
        {
            "model": text,
            "dimensions": integer,
            "detection_confidence": number,
            "box": array_schema(number, minItems=4, maxItems=4),
            "landmarks": array_schema(
                array_schema(number, minItems=2, maxItems=2), minItems=5, maxItems=5
            ),
            "landmark_order": array_schema(text, minItems=5, maxItems=5),
            "image_size": array_schema(integer, minItems=2, maxItems=2),
            "sharpness": number,
            "methods": {"type": "object"},
        },
        ["model", "dimensions", "detection_confidence"],
        extra=True,
    )
    person = {k: v for k, v in schemas["Person"]["properties"].items() if k != "consent"}
    schemas["PersonRecord"] = object_schema(
        person
        | {
            "id": uuid,
            "face": reference("FaceObservation"),
            "consent_recorded_at": timestamp,
            "updated_at": timestamp,
        }
    )
    animal = {k: v for k, v in schemas["Animal"]["properties"].items() if k != "consent"}
    schemas["AnimalRecord"] = object_schema(
        animal
        | {
            "id": uuid,
            "updated_at": timestamp,
            "representation": object_schema(
                {
                    "model": text,
                    "dimensions": integer,
                    "local_features": integer,
                    "subject_detection": {"const": "user_confirmed_crop"},
                }
            ),
        }
    )
    schemas["PersonResult"] = object_schema({"person": reference("PersonRecord")})
    schemas["AnimalResult"] = object_schema({"animal": reference("AnimalRecord")})
    schemas["FaceResult"] = object_schema({"face": reference("FaceObservation")})
    schemas["PeoplePage"] = object_schema(
        {"items": array_schema(reference("PersonRecord")), "next_cursor": nullable_text}
    )
    schemas["PeopleSearchResult"] = object_schema(
        {
            "matches": array_schema(
                object_schema(
                    {"person": reference("PersonRecord"), "score": number, "distance": number}
                )
            ),
            "face": reference("FaceObservation"),
            "metric": {"const": "cosine"},
            "mode": {"enum": ["exact", "approximate"]},
            "timing_ms": object_schema({"inference": number, "search": number}),
        }
    )
    schemas["AnimalSearchResult"] = object_schema(
        {
            "matches": array_schema(
                object_schema(
                    {
                        "animal": reference("AnimalRecord"),
                        "score": number,
                        "components": object_schema(
                            {
                                "global_cosine": number,
                                "local_matches": {"type": ["integer", "null"]},
                            }
                        ),
                    }
                )
            ),
            "method": {"enum": ["dinov2", "wildfusion"]},
            "calibrated": boolean,
        }
    )
    schemas["Problem"] = object_schema(
        {
            "type": {"type": "string", "format": "uri"},
            "title": text,
            "status": {"type": "integer", "minimum": 400, "maximum": 599},
            "detail": text,
            "instance": {"type": "string", "format": "uri"},
            "code": text,
            "request_id": uuid,
        },
        extra=True,
    )
    schemas["LegacyError"] = object_schema(
        {"error": object_schema({"code": text, "message": text})}
    )
    schemas["Health"] = object_schema({"status": {"const": "ok"}, "model": text}, ["status"])
    schemas["Methods"] = object_schema(
        {
            "methods": array_schema(
                object_schema(
                    {
                        "id": text,
                        "domain": {"enum": ["person", "animal"]},
                        "dimensions": integer,
                        "available": boolean,
                        "requires": text,
                        "variant": text,
                    },
                    ["id", "domain", "dimensions", "available"],
                )
            )
        }
    )
    schemas["Capabilities"] = object_schema(
        {
            "api_version": {"const": "1"},
            "contract_version": text,
            "preferred_upload": {"const": "multipart/form-data"},
            "image_field": {"const": "image"},
            "metadata_field": {"const": "metadata"},
            "accepted_image_types": array_schema(text),
            "max_image_bytes": integer,
            "max_metadata_bytes": integer,
            "permissions": array_schema({"enum": ["read", "write", "delete"]}),
            "request_timeout_seconds": integer,
            "openapi": text,
        }
    )
    return schemas


def upload_body(model, schemas):
    metadata = reference(model)
    image = {
        "type": "string",
        "format": "binary",
        "description": f"JPEG ou PNG; até {IMAGE.max_bytes} bytes e {IMAGE.max_pixels} pixels.",
    }
    base64_image = {
        "type": "string",
        "minLength": 4,
        "maxLength": IMAGE.max_encoded_characters,
        "description": "Base64 ou data URI JPEG/PNG. Prefira image binária em multipart.",
    }
    properties = schemas[model]["properties"]
    required = schemas[model].get("required", [])
    canonical = object_schema(
        {
            "image": image,
            "metadata": {
                "type": "string",
                "maxLength": 65536,
                "contentMediaType": "application/json",
                "contentSchema": metadata,
                "description": "JSON serializado em campo textual UTF-8, até 64 KiB.",
            },
        }
    )
    # Legacy flat fields remain documented for existing integrations.
    flat = {
        k: (
            {"type": "string", "contentMediaType": "application/json", "contentSchema": v}
            if k in {"person", "animal", "filters"}
            else v
        )
        for k, v in properties.items()
    }
    return {
        "required": True,
        "content": {
            "multipart/form-data": {
                "schema": {
                    "oneOf": [
                        canonical,
                        object_schema(flat | {"image": image}, required + ["image"]),
                        object_schema(
                            flat | {"image_base64": base64_image}, required + ["image_base64"]
                        ),
                    ]
                }
            },
            "application/json": {
                "schema": object_schema(
                    properties | {"image_base64": base64_image}, required + ["image_base64"]
                )
            },
        },
    }


def build_contract():
    schemas = build_schemas()
    success_headers = {
        "X-Request-Id": {
            "description": "Identificador criado pelo gateway; use ao relatar uma falha.",
            "schema": {"type": "string", "format": "uuid"},
        },
        "Content-Language": {"schema": {"enum": ["pt-BR", "en"]}},
    }
    problem = {
        "description": (
            "Erro estável. Prefira Accept: application/problem+json, application/json. "
            "Falhas anteriores ao gateway podem ter outro corpo; verifique o status HTTP."
        ),
        "headers": success_headers
        | {
            "Retry-After": {
                "description": "Espera mínima em segundos para 429/503, quando presente.",
                "schema": {"type": "string"},
            }
        },
        "content": {
            "application/problem+json": {"schema": reference("Problem")},
            "application/json": {"schema": reference("LegacyError")},
        },
    }
    paths = {}

    def operation(
        path,
        method,
        identity,
        summary,
        response=None,
        *,
        model=None,
        scope="read",
        status="200",
        parameters=None,
    ):
        value = {
            "operationId": identity,
            "summary": summary,
            "tags": [path.split("/")[1]],
            "parameters": [
                {
                    "name": "Accept-Language",
                    "in": "header",
                    "schema": {"enum": ["pt-BR", "en"], "default": "pt-BR"},
                }
            ]
            + (parameters or []),
            "responses": {
                status: {"description": "Operação concluída.", "headers": success_headers},
                "default": problem,
            },
        }
        if response:
            value["responses"][status]["content"] = {
                "application/json": {"schema": reference(response)}
            }
        if model:
            value["requestBody"] = upload_body(model, schemas)
        if scope is None:
            value["security"] = []
        else:
            value["x-required-capability"] = scope
        paths.setdefault(path, {})[method] = value

    identity = [
        {
            "name": "id",
            "in": "path",
            "required": True,
            "schema": {"type": "string", "format": "uuid"},
        }
    ]
    filters = [
        {"name": name, "in": "query", "schema": schema}
        for name, schema in schemas["Filters"]["properties"].items()
    ]
    filters += [
        {
            "name": "limit",
            "in": "query",
            "schema": {
                "type": "integer",
                "minimum": 1,
                "maximum": SEARCH.page_limit,
                "default": SEARCH.default_page_size,
            },
        },
        {"name": "cursor", "in": "query", "schema": {"type": "string", "format": "uuid"}},
    ]
    operation(
        "/health/live",
        "get",
        "checkLiveness",
        "Consultar processo do gateway",
        "Health",
        scope=None,
    )
    operation(
        "/health/ready", "get", "checkReadiness", "Consultar serviços de imagem e busca", "Health"
    )
    operation(
        "/capabilities",
        "get",
        "getCapabilities",
        "Consultar limites e permissões desta chave",
        "Capabilities",
    )
    operation("/methods", "get", "listMethods", "Consultar métodos de comparação", "Methods")
    operation(
        "/people",
        "post",
        "enrollPerson",
        "Cadastrar ou substituir pessoa pelo UUID",
        "PersonResult",
        model="Enrollment",
        scope="write",
        status="201",
    )
    operation(
        "/people",
        "get",
        "listPeople",
        "Consultar pessoas com filtros e cursor",
        "PeoplePage",
        parameters=filters,
    )
    operation(
        "/people/{id}",
        "get",
        "getPerson",
        "Consultar um cadastro de pessoa",
        "PersonResult",
        parameters=identity,
    )
    operation(
        "/people/{id}",
        "delete",
        "removePerson",
        "Excluir pessoa e representações",
        scope="delete",
        status="204",
        parameters=identity,
    )
    operation(
        "/search",
        "post",
        "searchPeople",
        "Ordenar candidatos humanos por similaridade",
        "PeopleSearchResult",
        model="Search",
    )
    operation(
        "/faces/analyze",
        "post",
        "analyzeFace",
        "Examinar observação do rosto",
        "FaceResult",
        model="StrictModel",
    )
    operation(
        "/animals",
        "post",
        "enrollAnimal",
        "Cadastrar ou substituir animal pelo UUID",
        "AnimalResult",
        model="AnimalEnrollment",
        scope="write",
        status="201",
    )
    operation(
        "/animals/search",
        "post",
        "searchAnimals",
        "Ordenar animais da mesma espécie",
        "AnimalSearchResult",
        model="AnimalSearch",
    )
    operation(
        "/animals/{id}",
        "delete",
        "removeAnimal",
        "Excluir animal e representações",
        scope="delete",
        status="204",
        parameters=identity,
    )
    return {
        "openapi": "3.1.2",
        "info": {
            "title": "Heyface API",
            "version": CONTRACT_VERSION,
            "description": (
                "Busca visual de pessoas e animais cadastrados. Scores ordenam candidatos; "
                "não confirmam identidade. UUIDs de cadastro pertencem ao cliente e são "
                "isolados por espaço de trabalho. Repetir o UUID substitui o registro. "
                "A API não armazena a imagem enviada."
            ),
        },
        "servers": [{"url": "/api/v1"}],
        "security": [{"accessKey": []}],
        "paths": paths,
        "components": {
            "schemas": schemas,
            "securitySchemes": {
                "accessKey": {
                    "type": "http",
                    "scheme": "bearer",
                    "description": "Chave com permissões read, write e/ou delete.",
                }
            },
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    serialized = json.dumps(build_contract(), ensure_ascii=False, indent=2) + "\n"
    if args.check:
        if CONTRACT.read_text() != serialized:
            raise SystemExit(
                "Contract drift: run ./heyface contract-build and commit the generated contract."
            )
        from openapi_spec_validator import validate

        validate(json.loads(serialized))
        print("Public OpenAPI contract is valid and matches parameter schemas.")
        return
    CONTRACT.parent.mkdir(parents=True, exist_ok=True)
    CONTRACT.write_text(serialized)
    print("Updated services/gateway/resources/contracts/openapi.json")


if __name__ == "__main__":
    main()
