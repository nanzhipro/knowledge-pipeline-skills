# Changelog

## 0.2.0 - 2026-11-01

### Distribution

- Consolidate both original repositories under `skills/` while preserving complete
  commit history and namespaced original v0.1.0 tags.
- Keep anydoc-markdown and obsidian-llm-wiki independently callable and installable.
- Add knowledge-pipeline as an independent top-level task coordinator with explicit
  child discovery, stage routing, preparation-only boundaries and cited read-only queries.
- Update active repository URLs, retain MIT notices and preserve historical reports.

### Validation and migration

- Evaluate all three complete packages with Plugin Eval and official Agent Skills checks.
- Run native Rust, Python 3.10/3.13 and real conversion-to-Wiki handoff checks.
- Preserve portable Git bundles, original Release assets and CI logs/artifacts before
  activating this repository and deleting the two former repositories.

Component/CLI versions and the anydoc-markdown/1 protocol remain unchanged. The new
installation paths are skills/anydoc-markdown, skills/obsidian-llm-wiki and
skills/knowledge-pipeline. Root 0.2.0 identifies the combined distribution.
