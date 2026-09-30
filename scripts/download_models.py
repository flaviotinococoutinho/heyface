"""Download pinned public model artifacts; verify before atomic publication."""

import hashlib
import json
import sys
import urllib.request
from pathlib import Path

manifest = json.loads(Path(sys.argv[1]).read_text())
destination = Path(sys.argv[2])
destination.mkdir(parents=True, exist_ok=True)

for artifact in manifest["files"]:
    target = destination / artifact["name"]
    if target.is_file() and hashlib.sha256(target.read_bytes()).hexdigest() == artifact["sha256"]:
        print("Verified", artifact["name"], flush=True)
        continue
    temporary = target.with_suffix(target.suffix + ".download")
    print("Downloading", artifact["name"], flush=True)
    request = urllib.request.Request(
        artifact["url"], headers={"User-Agent": "heyface-model-setup/1"}
    )
    with (
        urllib.request.urlopen(request, timeout=120) as response,
        temporary.open("wb") as output,
    ):
        while chunk := response.read(1024 * 1024):
            output.write(chunk)
    if hashlib.sha256(temporary.read_bytes()).hexdigest() != artifact["sha256"]:
        raise SystemExit("Checksum mismatch for " + artifact["name"])
    temporary.replace(target)
    target.chmod(0o644)
print("All model checksums verified.", flush=True)
