"""Inspect tracked objects without printing potential credential values."""

import argparse
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_PARTS = {
    ".local",
    ".secrets",
    ".env",
    "node_modules",
    "vendor",
    "__pycache__",
}
FORBIDDEN_SUFFIXES = {".zip", ".pt", ".onnx", ".safetensors", ".snapshot", ".log"}
SECRET_PATTERNS = (
    rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
    rb"gh[pousr]_[A-Za-z0-9]{30,}",
    rb"github_pat_[A-Za-z0-9_]{40,}",
    rb"AKIA[A-Z0-9]{16}",
    rb"sk-[A-Za-z0-9_-]{32,}",
    rb"/" + rb"Users/[^/\s]+/",
)
MAX_PUBLIC_FILE_BYTES = 10 * 1024 * 1024


def git(*arguments):
    return subprocess.check_output(["git", *arguments], cwd=ROOT)


def local_secrets():
    values = []
    environment = ROOT / ".env"
    if environment.exists():
        for line in environment.read_text().splitlines():
            key, separator, value = line.partition("=")
            if (
                separator
                and any(word in key for word in ("KEY", "TOKEN", "PASSWORD"))
                and len(value) >= 16
            ):
                values.append(value.encode())
    token = ROOT / ".secrets/demo-token.txt"
    if token.exists():
        values.append(token.read_bytes().strip())
    return values


def inspect(path, data, secrets):
    parts = Path(path).parts
    if any(part in FORBIDDEN_PARTS for part in parts) or Path(path).suffix in FORBIDDEN_SUFFIXES:
        return "private/generated path"
    if len(data) > MAX_PUBLIC_FILE_BYTES:
        return "oversized artifact"
    if any(re.search(pattern, data) for pattern in SECRET_PATTERNS):
        return "credential or local path pattern"
    if any(value and value in data for value in secrets):
        return "local credential content"
    if data.startswith(b"\x89PNG"):
        offset = 8
        while offset < len(data):
            size = int.from_bytes(data[offset : offset + 4], "big")
            if data[offset + 4 : offset + 8] in {
                b"caBX",
                b"iTXt",
                b"tEXt",
                b"zTXt",
                b"eXIf",
            }:
                return "image metadata"
            offset += size + 12
    return None


def main():
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--staged", action="store_true")
    mode.add_argument("--history", action="store_true")
    args = parser.parse_args()
    objects = []
    if args.staged:
        for line in git("ls-files", "-s").decode().splitlines():
            metadata, path = line.split("\t", 1)
            permissions, oid, _ = metadata.split()
            if permissions == "120000":
                raise SystemExit("Publication check refused a tracked symlink: " + path)
            objects.append((oid, path))
    else:
        for line in git("rev-list", "--objects", "--all").decode().splitlines():
            oid, separator, path = line.partition(" ")
            if separator and git("cat-file", "-t", oid).strip() == b"blob":
                objects.append((oid, path))
    failures = []
    secrets = local_secrets()
    for oid, path in objects:
        reason = inspect(path, git("cat-file", "blob", oid), secrets)
        if reason:
            failures.append(f"{path}: {reason}")
    if failures:
        raise SystemExit("Publication check failed:\n" + "\n".join(failures))
    print(f"Publication check passed: {len(objects)} tracked objects inspected.")


if __name__ == "__main__":
    main()
