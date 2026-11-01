"""Read-only Unicode retrieval; an explicit optional SQLite cache is disposable."""

from __future__ import annotations
from pathlib import Path
from contextlib import closing
import sqlite3

from .paths import CONTROL, digest, ensure_ready, file_hash, json_bytes, now, safe


def _documents(vault: Path) -> list[tuple[str, str]]:
    ensure_ready(vault)
    result = []
    for path in sorted(safe(vault, "wiki").rglob("*.md")):
        if path.is_symlink():
            raise ValueError("Symlink in wiki search scope")
        result.append(
            (path.relative_to(vault).as_posix(), path.read_text(encoding="utf-8"))
        )
    return result


def _fingerprint(documents: list[tuple[str, str]]) -> str:
    return digest(
        json_bytes([(path, digest(text.encode())) for path, text in documents])
    )


def build_index(vault: Path) -> dict:
    documents = _documents(vault)
    destination = safe(vault, f"{CONTROL}/search.sqlite")
    temporary = destination.with_name("search-building.sqlite")
    if temporary.exists():
        raise ValueError(
            "Search build file exists; finish or remove the stopped build before retrying"
        )
    try:
        with closing(sqlite3.connect(temporary)) as connection:
            connection.execute(
                "CREATE VIRTUAL TABLE notes USING fts5(path UNINDEXED, body)"
            )
            connection.execute(
                "CREATE TABLE metadata (fingerprint TEXT, built_at TEXT)"
            )
            connection.executemany(
                "INSERT INTO notes(path,body) VALUES (?,?)", documents
            )
            connection.execute(
                "INSERT INTO metadata VALUES (?,?)", (_fingerprint(documents), now())
            )
            connection.commit()
        if _fingerprint(_documents(vault)) != _fingerprint(documents):
            raise ValueError("Wiki changed during search indexing; retry")
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)
    return {"indexed": len(documents), "fingerprint": _fingerprint(documents)}


def search(vault: Path, query: str, limit: int = 20, bm25: bool = False) -> dict:
    if not query.strip() or not 1 <= limit <= 200:
        raise ValueError("Search requires text and a limit between 1 and 200")
    documents = _documents(vault)
    warning = None
    if bm25:
        try:
            index = safe(vault, f"{CONTROL}/search.sqlite")
            if index.is_file():
                with closing(
                    sqlite3.connect(index.as_uri() + "?mode=ro", uri=True)
                ) as connection:
                    saved = connection.execute(
                        "SELECT fingerprint FROM metadata"
                    ).fetchone()
                    if saved and saved[0] == _fingerprint(documents):
                        try:
                            rows = connection.execute(
                                "SELECT path, snippet(notes,1,'[',']','…',28), bm25(notes) "
                                "FROM notes WHERE notes MATCH ? ORDER BY bm25(notes) LIMIT ?",
                                ('"' + query.replace('"', '""') + '"', limit),
                            ).fetchall()
                        except sqlite3.OperationalError:
                            rows = []
                        if rows:
                            return {
                                "mode": "bm25",
                                "hits": [
                                    {"path": row[0], "snippet": row[1], "score": row[2]}
                                    for row in rows
                                ],
                                "warning": None,
                            }
                        warning = (
                            "No lexical BM25 match; using Unicode substring search"
                        )
                    else:
                        warning = "Search index is stale (changed, added, or deleted notes); using text search"
            else:
                warning = (
                    "No index; using text search. Build explicitly with index-search"
                )
        except sqlite3.Error as error:
            warning = f"Search cache unavailable ({error}); using Unicode text search"
    hits = []
    for path, body in documents:
        if query.casefold() in body.casefold():
            for number, line in enumerate(body.splitlines(), 1):
                if query.casefold() in line.casefold():
                    hits.append({"path": path, "line": number, "snippet": line[:500]})
                    break
        if len(hits) >= limit:
            break
    return {"mode": "text", "hits": hits, "warning": warning}
