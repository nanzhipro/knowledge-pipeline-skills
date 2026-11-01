"""Contained paths, exact snapshots, and no-replace publication."""

from __future__ import annotations

import ctypes
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import sys
import tempfile
from datetime import datetime, timezone

CONTROL = ".llm-wiki"
STATE = f"{CONTROL}/state.json"
PREFS = ".llm-wiki-bootstrap/EXTEND.md"
FIXED = ("SCHEMA.md", "AGENTS.md", PREFS, STATE)


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_hash(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def safe(root: Path, relative: str) -> Path:
    if (
        not isinstance(relative, str)
        or not relative
        or "\\" in relative
        or ":" in relative
    ):
        raise ValueError(f"Invalid managed path: {relative!r}")
    parts = relative.split("/")
    if any(p in {"", ".", ".."} or "\x00" in p for p in parts):
        raise ValueError(f"Path escapes managed root: {relative}")
    result = root
    for part in parts:
        result = result / part
        if result.is_symlink():
            raise ValueError(f"Symlink is not a managed artifact: {relative}")
    return result


def json_bytes(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode()


def read_json(path: Path) -> dict:
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"Duplicate JSON key: {key}")
            result[key] = value
        return result

    value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique)
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path.name}")
    return value


def publish_new(source: Path, target: Path) -> None:
    """An existing file/directory must survive even a competing publication."""
    if "\x00" in str(source) or "\x00" in str(target):
        raise ValueError("NUL in path")
    if sys.platform == "win32":
        api = ctypes.WinDLL("kernel32", use_last_error=True).MoveFileExW
        api.argtypes = (ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint32)
        api.restype = ctypes.c_int
        if not api(str(source), str(target), 0):
            raise ctypes.WinError(ctypes.get_last_error())
        return
    libc = ctypes.CDLL(None, use_errno=True)
    if sys.platform == "darwin":
        api = libc.renamex_np
        api.argtypes = (ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint)
        args = (os.fsencode(source), os.fsencode(target), 4)  # RENAME_EXCL
    elif sys.platform.startswith("linux"):
        api = libc.renameat2
        api.argtypes = (
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_uint,
        )
        args = (-100, os.fsencode(source), -100, os.fsencode(target), 1)  # NOREPLACE
    else:
        raise ValueError("Native publication supports Windows, macOS, and Linux")
    api.restype = ctypes.c_int
    if api(*args) != 0:
        code = ctypes.get_errno()
        raise OSError(code, os.strerror(code), str(target))


def atomic_write(path: Path, data: bytes, expected: str | None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink() or (file_hash(path) if path.is_file() else None) != expected:
        raise ValueError(f"File changed before write: {path.name}")
    fd, name = tempfile.mkstemp(prefix=".wiki-", dir=path.parent)
    staging = Path(name)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        if expected is None:
            publish_new(staging, path)
        else:
            if not path.is_file() or file_hash(path) != expected:
                raise ValueError(f"File changed before replace: {path.name}")
            os.replace(staging, path)
    finally:
        staging.unlink(missing_ok=True)


def managed_files(root: Path) -> dict[str, str]:
    result = {}
    for prefix in ("raw", "wiki", f"{CONTROL}/batches"):
        folder = safe(root, prefix)
        if folder.exists():
            for path in sorted(folder.rglob("*")):
                if path.is_symlink():
                    raise ValueError(f"Managed symlink: {path.relative_to(root)}")
                if path.is_file() and path.name not in {".DS_Store", "Thumbs.db"}:
                    relative = path.relative_to(root).as_posix()
                    result[relative] = file_hash(safe(root, relative))
    for relative in FIXED:
        path = safe(root, relative)
        if path.is_file():
            result[relative] = file_hash(path)
    return result


def read_state(root: Path) -> dict:
    state = read_json(safe(root, STATE))
    if state.get("format") != "obsidian-llm-wiki/1":
        raise ValueError(
            "Not a supported managed library; do not initialize over existing notes"
        )
    return state


def ensure_ready(root: Path) -> None:
    read_state(root)
    if safe(root, f"{CONTROL}/active.json").exists():
        raise ValueError(
            "An interrupted publication requires recover before further operations"
        )
