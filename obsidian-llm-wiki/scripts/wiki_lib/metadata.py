"""Real YAML parsing; generated note properties stay flat for Obsidian."""

from __future__ import annotations
from datetime import date, datetime
import re
import yaml


class UniqueLoader(yaml.SafeLoader):
    pass


def _mapping(loader, node, deep=False):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if not isinstance(key, str) or key in result:
            raise ValueError(f"Invalid or duplicate YAML property: {key!r}")
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _mapping)


def split_page(text: str) -> tuple[dict, str]:
    text = text.replace("\r\n", "\n")
    if not text.startswith("---\n"):
        raise ValueError("Knowledge note requires YAML frontmatter")
    match = re.search(r"^---\s*$", text[4:], flags=re.M)
    if not match:
        raise ValueError("Unclosed YAML frontmatter")
    try:
        data = yaml.load(text[4 : 4 + match.start()], Loader=UniqueLoader)
    except yaml.YAMLError as error:
        raise ValueError(f"Invalid note YAML: {error}") from error
    if not isinstance(data, dict):
        raise ValueError("Frontmatter must be an object")
    return data, text[4 + match.end() :].lstrip("\n")


def page(data: dict, body: str) -> bytes:
    return (
        "---\n"
        + yaml.safe_dump(data, allow_unicode=True, sort_keys=False)
        + "---\n\n"
        + body.replace("\r\n", "\n").rstrip()
        + "\n"
    ).encode()


def note_issues(data: dict, body: str) -> list[str]:
    issues = []
    for name in ("title", "type", "description"):
        if not isinstance(data.get(name), str) or not data[name].strip():
            issues.append(f"{name} requires a nonempty string")
    if not isinstance(data.get("updated"), (str, date, datetime)):
        issues.append("updated requires a date or timestamp")
    sources = data.get("sources")
    if not isinstance(sources, list) or any(not isinstance(s, str) for s in sources):
        issues.append("sources requires a list of source-ID strings")
    for name, value in data.items():
        if isinstance(value, dict) or (
            isinstance(value, list) and any(isinstance(v, (dict, list)) for v in value)
        ):
            issues.append(f"{name} must be flat metadata for the generated notes")
    if not body.strip():
        issues.append("Empty note body")
    return issues
