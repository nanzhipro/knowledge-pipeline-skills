"""Read-only local Markdown link checks; code examples are not navigation."""

from __future__ import annotations

import html
from pathlib import Path
import re
import stat
from urllib.parse import unquote, urlsplit

DEFINITION = re.compile(r"(?m)^ {0,3}\[([^\]^][^\]\n]*)\]:[ \t]*(.+)$")
INLINE = re.compile(r"(?<![\\\[])!?\[((?:\\.|[^\]\\\n])*)\]\(")
REFERENCE = re.compile(r"(?<![\\\[])!?\[((?:\\.|[^\]\\\n])*)\][ \t]*\[([^\]\n]*)\]")
SHORTCUT = re.compile(r"(?<![\\\[])!?\[([^\]\n]+)\](?![\[(])")
WIKILINK = re.compile(r"(?<!\\)!?\[\[([^\]\n]+)\]\]")


def masked(text: str) -> str:
    """Remove comments and fenced/inline code while retaining line boundaries."""
    lines, fence, size = [], "", 0
    for line in text.splitlines(keepends=True):
        if fence:
            if re.match(
                rf"^ {{0,3}}{re.escape(fence)}{{{size},}}[ \t]*$", line.rstrip("\r\n")
            ):
                fence = ""
            lines.append("\n" if line.endswith("\n") else "")
            continue
        opening = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", line.rstrip("\r\n"))
        if opening and not (opening[1][0] == "`" and "`" in opening[2]):
            fence, size = opening[1][0], len(opening[1])
            lines.append("\n" if line.endswith("\n") else "")
        else:
            lines.append(line)
    content = re.sub(r"<!--.*?(?:-->|\Z)", "", "".join(lines), flags=re.S)
    return re.sub(r"(?<!`)(`+)(?!`)(.*?)\1(?!`)", "", content, flags=re.S)


def _label(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().casefold()


def _destination(value: str) -> str:
    value = value.lstrip()
    if value.startswith("<"):
        match = re.search(r"(?<!\\)>", value[1:])
        return value[1 : match.start() + 1] if match else value[1:]
    output, depth, escaped = [], 0, False
    for char in value:
        if escaped:
            output.extend(("\\", char))
            escaped = False
        elif char == "\\":
            escaped = True
        elif char.isspace() and depth == 0:
            break
        else:
            depth += (char == "(") - (char == ")")
            output.append(char)
    if escaped:
        output.append("\\")
    return re.sub(r"\\([!\"#$%&'()*+,\-./:;<=>?@\[\]^_`{|}~])", r"\1", "".join(output))


def _inline_destination(content: str, start: int) -> str | None:
    depth, escaped, angle, quote = 1, False, False, ""
    for position in range(start, len(content)):
        char = content[position]
        if escaped:
            escaped = False
        elif char == "\\":
            escaped = True
        elif quote:
            if char == quote:
                quote = ""
        elif angle:
            if char == ">":
                angle = False
        elif char == "<" and not content[start:position].strip():
            angle = True
        elif (
            char in {'"', "'"} and position > start and content[position - 1].isspace()
        ):
            quote = char
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return _destination(content[start:position])
    return None


def _local(root: Path, page: str, destination: str, wiki: bool) -> str | None:
    raw = html.unescape(destination.strip())
    if "\\" in raw or re.match(r"^[A-Za-z]:", raw):
        raise ValueError("Windows drive/backslash paths are not vault links")
    parsed = urlsplit(raw)
    if parsed.scheme.casefold() == "file":
        raise ValueError("file URLs are not contained vault links")
    if parsed.scheme or parsed.netloc:
        return None
    path = unquote(parsed.path, errors="strict")
    if (
        path.startswith("/")
        or "\\" in path
        or ":" in path
        or any(ord(char) < 32 for char in path)
    ):
        raise ValueError("absolute, drive, backslash or control-character path refused")
    if not path:
        relative = page
    else:
        base = (
            []
            if wiki and path.startswith(("wiki/", "raw/"))
            else list(Path(page).parent.parts)
        )
        for part in path.split("/"):
            if part in {"", "."}:
                continue
            if part == "..":
                if not base:
                    raise ValueError("local link escapes the vault")
                base.pop()
            else:
                base.append(part)
        relative = "/".join(base)
        if wiki and not Path(relative).suffix:
            relative += ".md"
    current = root
    for part in relative.split("/"):
        current = current / part
        mode = current.lstat().st_mode
        if stat.S_ISLNK(mode):
            raise ValueError(f"symlink target refused: {relative}")
    if not stat.S_ISREG(mode):
        raise ValueError(f"local target is not a regular file: {relative}")
    return relative


def targets(root: Path, relative_page: str, body: str) -> tuple[set[str], list[str]]:
    """Return existing contained local targets and errors, never fetching URLs.

    Markdown links are page-relative. Wikilinks with ``wiki/`` or ``raw/`` are
    vault-root-relative; other wikilinks are sibling-relative. Heading anchors
    are not checked, and ambiguous basename lookup is deliberately not used.
    """
    found, errors, links = set(), [], []
    if (
        not isinstance(relative_page, str)
        or relative_page.startswith("/")
        or "\\" in relative_page
        or ":" in relative_page
        or any(part in {"", ".", ".."} for part in relative_page.split("/"))
    ):
        return found, [f"{relative_page}: invalid relative page path"]
    content = masked(body)
    definitions = {}
    for match in DEFINITION.finditer(content):
        label, destination = _label(match[1]), _destination(match[2])
        if label in definitions and definitions[label] != destination:
            errors.append(f"{relative_page}: conflicting link definition [{label}]")
        definitions.setdefault(label, destination)
        links.append((destination, False))
    content = DEFINITION.sub("", content)
    for match in WIKILINK.finditer(content):
        links.append((match[1].split("|", 1)[0], True))
    content = WIKILINK.sub("", content)
    for match in INLINE.finditer(content):
        destination = _inline_destination(content, match.end())
        if destination is not None:
            links.append((destination, False))
    for match in REFERENCE.finditer(content):
        label = _label(match[2] or match[1])
        if label.startswith("^"):
            continue
        if label not in definitions:
            errors.append(
                f"{relative_page}: undefined Markdown link reference [{label}]"
            )
    for match in SHORTCUT.finditer(content):
        if _label(match[1]) in definitions:
            links.append((definitions[_label(match[1])], False))
    for destination, wiki in links:
        try:
            target = _local(Path(root), relative_page, destination, wiki)
            if target is not None:
                found.add(target)
        except (OSError, RuntimeError, ValueError) as exc:
            errors.append(f"{relative_page}: invalid local link {destination!r}: {exc}")
    return found, list(dict.fromkeys(errors))
