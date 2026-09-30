"""Validate real HTTP responses against the published contract and compare wire sizes."""

import base64
import json
import re
from collections import Counter

import httpx
from build_contract import CONTRACT, ROOT
from jsonschema import Draft202012Validator, FormatChecker
from tools import API_URL, smoke


def main():
    contract = json.loads(CONTRACT.read_text())
    downloaded = httpx.get(API_URL + "/openapi.json").raise_for_status().json()
    if downloaded != contract:
        raise AssertionError("The running gateway does not serve the current public contract.")
    checked = Counter()

    def validate(response):
        response.read()
        path = response.request.url.path.removeprefix("/api/v1")
        path = re.sub(r"/[0-9a-f-]{36}$", "/{id}", path)
        operation = contract["paths"][path][response.request.method.lower()]
        result = operation["responses"].get(
            str(response.status_code), operation["responses"]["default"]
        )
        if response.status_code == 204:
            assert not response.content
            checked[operation["operationId"]] += 1
            return
        media_type = response.headers["content-type"].split(";", 1)[0]
        if media_type not in result["content"]:
            raise AssertionError(
                f"Unexpected HTTP {response.status_code} {media_type} "
                f"from {operation['operationId']}"
            )
        schema = result["content"][media_type]["schema"] | {"components": contract["components"]}
        errors = list(
            Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(
                response.json()
            )
        )
        if errors:
            # Do not emit response values or identities into test logs.
            locations = [
                {"path": "/".join(map(str, error.absolute_path)), "rule": error.validator}
                for error in errors
            ]
            raise AssertionError(
                f"Contract mismatch: {operation['operationId']} "
                f"HTTP {response.status_code} at {locations}"
            )
        assert response.headers.get("x-request-id")
        checked[operation["operationId"]] += 1

    smoke(response_hooks=[validate])
    expected = {
        value["operationId"]
        for path, methods in contract["paths"].items()
        for value in methods.values()
        if path != "/health/live"
    }
    if missing := expected - checked.keys():
        raise AssertionError(f"Missing exercised operations: {sorted(missing)}")
    sizes = []
    for name in ("heyface.png", "animal.png"):
        content = (ROOT / "web/public/brand" / name).read_bytes()
        metadata = {"method": "sface", "limit": 10}
        legacy = httpx.Request(
            "POST",
            "http://localhost/search",
            json=metadata | {"image_base64": base64.b64encode(content).decode()},
        ).read()
        binary = httpx.Request(
            "POST",
            "http://localhost/search",
            data={"metadata": json.dumps(metadata)},
            files={"image": ("image.png", content, "image/png")},
        ).read()
        sizes.append(
            {
                "sample": name,
                "image_bytes": len(content),
                "json_base64_bytes": len(legacy),
                "multipart_bytes": len(binary),
                "reduction_percent": round((1 - len(binary) / len(legacy)) * 100, 2),
            }
        )
    report = {
        "validated_responses": sum(checked.values()),
        "operations": dict(checked),
        "wire_sizes": sizes,
    }
    (ROOT / ".local/contract-report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
