"""Prepare this workspace without replacing existing credentials or data."""

import base64
import hashlib
import json
import os
import secrets
from pathlib import Path

root = Path(__file__).resolve().parents[1]
private = root / ".secrets"
private.mkdir(mode=0o700, exist_ok=True)
(private / "access").mkdir(mode=0o755, exist_ok=True)
(root / ".local/calibrations").mkdir(parents=True, exist_ok=True)
(root / ".local/backups").mkdir(parents=True, exist_ok=True)


def create(path, content):
    try:
        with path.open("x") as stream:
            stream.write(content)
        path.chmod(0o600)
    except FileExistsError:
        pass


token_file = private / "demo-token.txt"
create(token_file, secrets.token_urlsafe(32) + "\n")
token = token_file.read_text().strip()
registry = {
    hashlib.sha256(token.encode()).hexdigest(): {
        "tenant": "local",
        "name": "Local development",
        "scopes": ["read", "write", "delete"],
    }
}
create(private / "access/keys.json", json.dumps(registry, indent=2) + "\n")
# Read access for the unprivileged PHP container; tokens remain owner-only.
(private / "access/keys.json").chmod(0o644)
create(
    root / ".env",
    "\n".join(
        [
            "COMPOSE_PROJECT_NAME=heyface",
            "HTTP_PORT=8088",
            f"LOCAL_UID={os.getuid()}",
            f"LOCAL_GID={os.getgid()}",
            "APP_KEY=base64:" + base64.b64encode(secrets.token_bytes(32)).decode(),
            "VISION_SERVICE_TOKEN=" + secrets.token_urlsafe(40),
            "QDRANT_API_KEY=" + secrets.token_urlsafe(40),
            "REDIS_PASSWORD=" + secrets.token_urlsafe(40),
            "OCTANE_WORKERS=2",
            "REQUESTS_PER_MINUTE=120",
            "",
        ]
    ),
)
print("Configuration ready. Existing files preserved. Access key: .secrets/demo-token.txt")
