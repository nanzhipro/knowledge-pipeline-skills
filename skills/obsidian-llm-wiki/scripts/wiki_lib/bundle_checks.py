"""Strict, read-only checks for the anydoc-markdown/1 wire contract."""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import unicodedata
from pathlib import Path
from typing import Any

import yaml

SCHEMA = "anydoc-markdown/1"
STATUSES = {"converted", "partial", "needs_ocr", "unsupported", "error"}
READABLE = {"converted", "partial"}
SHA256 = re.compile(r"[0-9a-f]{64}\Z")


def fail(where: str, message: str) -> None:
    raise ValueError(f"{where}: {message}")


def string(value: Any, where: str, *, empty: bool = False) -> str:
    if not isinstance(value, str) or (not empty and not value):
        fail(where, "expected a string" + ("" if empty else " that is not empty"))
    try:
        value.encode("utf-8")
    except UnicodeError:
        fail(where, "string contains an invalid Unicode surrogate")
    return value


def digest(value: Any, where: str, *, empty: bool = False) -> str:
    value = string(value, where, empty=empty)
    if not ((empty and value == "") or SHA256.fullmatch(value)):
        fail(where, "expected a lowercase SHA-256 hex digest")
    return value


def integer(value: Any, where: str, *, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        fail(where, f"expected an integer >= {minimum}")
    return value


def mapping(
    value: Any, where: str, required: set[str], optional: set[str] | None = None
) -> dict:
    if type(value) is not dict:
        fail(where, "expected an object")
    if any(type(key) is not str for key in value):
        fail(where, "all object field names must be strings")
    missing = required - value.keys()
    unknown = value.keys() - required - (optional or set())
    if missing or unknown:
        fail(
            where, f"missing fields {sorted(missing)}; unknown fields {sorted(unknown)}"
        )
    return value


def array(value: Any, where: str) -> list:
    if type(value) is not list:
        fail(where, "expected an array")
    return value


def strings(value: Any, where: str) -> list[str]:
    for index, item in enumerate(array(value, where)):
        string(item, f"{where}[{index}]", empty=True)
    return value


def relative(value: Any, where: str) -> str:
    value = string(value, where)
    if (
        "\\" in value
        or ":" in value
        or value.startswith("/")
        or any(ord(char) < 32 or ord(char) == 127 for char in value)
        or any(part in {"", ".", ".."} for part in value.split("/"))
    ):
        fail(
            where,
            "expected a contained relative path without drive, backslash, or dot components",
        )
    return value


def portable_key(value: str) -> str:
    return unicodedata.normalize("NFC", value).casefold()


def checked_file(root: Path, relative_path: str, where: str) -> Path:
    relative(relative_path, where)
    current = root
    try:
        for part in relative_path.split("/"):
            current = current / part
            mode = current.lstat().st_mode
            if stat.S_ISLNK(mode):
                fail(where, f"symlink refused: {current}")
        if not stat.S_ISREG(mode):
            fail(where, f"not a regular file: {current}")
    except OSError as exc:
        fail(where, f"cannot access {current}: {exc}")
    return current


def file_hash(path: Path) -> tuple[str, int]:
    """Hash artifact bytes in bounded chunks; return (sha256, byte_count)."""
    hasher, length = hashlib.sha256(), 0
    try:
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
        with os.fdopen(os.open(path, flags), "rb") as stream:
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                fail(str(path), "not a regular file")
            while block := stream.read(1024 * 1024):
                hasher.update(block)
                length += len(block)
    except OSError as exc:
        fail(str(path), f"cannot hash file: {exc}")
    return hasher.hexdigest(), length


def json_bytes(path: Path) -> tuple[dict, bytes]:
    def unique(pairs: list[tuple[str, Any]]) -> dict:
        result = {}
        for key, value in pairs:
            if key in result:
                fail(str(path), f"duplicate JSON field {key!r}")
            result[key] = value
        return result

    def invalid_constant(value: str) -> None:
        fail(str(path), f"invalid JSON number {value}")

    try:
        raw = path.read_bytes()
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=unique,
            parse_constant=invalid_constant,
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        fail(str(path), f"cannot read UTF-8 JSON: {exc}")
    if type(value) is not dict:
        fail(str(path), "expected a JSON object")
    return value, raw


class UniqueSafeLoader(yaml.SafeLoader):
    """Safe YAML with duplicate mapping keys rejected, including merges."""

    def construct_mapping(self, node, deep=False):
        self.flatten_mapping(node)
        result = {}
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            try:
                if key in result:
                    raise ValueError(f"duplicate YAML field {key!r}")
                result[key] = self.construct_object(value_node, deep=deep)
            except TypeError as exc:
                raise ValueError("YAML mapping key is not scalar") from exc
        return result


def readable_frontmatter(path: Path, report: dict, source_path: str) -> None:
    where = str(path)
    try:
        with path.open("r", encoding="utf-8", newline="") as stream:
            if stream.readline() != "---\n":
                fail(
                    where,
                    "readable extraction requires YAML frontmatter with LF line endings",
                )
            lines, size = [], 0
            for line in stream:
                size += len(line.encode("utf-8"))
                if size > 1024 * 1024:
                    fail(where, "frontmatter exceeds 1 MiB")
                if line == "---\n":
                    break
                lines.append(line)
            else:
                fail(where, "frontmatter closing delimiter is missing")
            if not any(line.strip() for line in stream):
                fail(where, "readable extraction has an empty Markdown body")
        frontmatter = yaml.load("".join(lines), Loader=UniqueSafeLoader)
    except (OSError, UnicodeError, yaml.YAMLError, ValueError) as exc:
        fail(where, f"invalid readable Markdown/frontmatter: {exc}")
    fields = {
        "title",
        "source",
        "source_relative_path",
        "source_sha256",
        "format",
        "conversion_status",
        "converter",
    }
    mapping(frontmatter, where, fields)
    for name in fields:
        string(frontmatter[name], f"{where} frontmatter.{name}")
    relative(frontmatter["source"], f"{where} frontmatter.source")
    relative(
        frontmatter["source_relative_path"], f"{where} frontmatter.source_relative_path"
    )
    expected = {
        "source": source_path,
        "source_relative_path": report["source_relative_path"],
        "source_sha256": report["source_sha256"],
        "format": report["format"],
        "conversion_status": report["status"],
        "converter": report["engine"],
    }
    for key, value in expected.items():
        if frontmatter[key] != value:
            fail(where, f"frontmatter.{key} does not match the verified report")
