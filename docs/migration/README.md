# Repository consolidation

Scope: replace `nanzhipro/anydoc-markdown-skill` and
`nanzhipro/obsidian-llm-wiki-skill` with `nanzhipro/knowledge-pipeline-skills`.
The author's original Karpathy repository and all local source/backup directories
are excluded from deletion. User authorization explicitly conditions old-repository
deletion on successful merge/evaluation; no additional task approval is inferred.

## Preserved material

- Both original commit graphs are reachable from main through full-history subtree
  merges; the active skill folders moved to `skills/`. No squash/rewrite was used.
- Original tags survive as `legacy/anydoc-markdown/v0.1.0` and
  `legacy/obsidian-llm-wiki/v0.1.0`, pointing to the exact original tag objects.
  The first original was lightweight; the second was annotated.
- [Relocation inventory](component-relocation.json) lists all 60/97 original Skill
  files and the three intended repository-link/provenance changes. Runtime source
  behavior was unchanged; the third coordinator was added separately.
- [Git inventory](git-inventory.json), [standalone restoration tests](backup-restoration.json)
  and [asset inventory](assets-inventory.json) record verified portable backups.
- Four original Release assets, five CI log ZIPs and seven native build artifacts
  were downloaded before deletion, with remote digests, ZIP CRC and checksums verified.
- No issues, pull requests, milestones, deployments, environments, webhooks, secrets,
  variables or repository rules were present. Linked ProjectsV2 could not be queried
  with the existing OAuth scope; the default Projects feature switch alone does not
  establish linked project content. See [preflight audit](preflight-audit.json).

The new Release includes `legacy-repositories-backup-2026-11-01.zip` alongside the
three-Skill install ZIP and SHA256SUMS. It contains portable bundles and the assets
above, without mirror configs, credential stores or local private test corpora.
A separate local mirror/backup remains under the project's `repository-backups/`.

To recover an original Git repository, extract the backup and use a new destination:

```text
git clone anydoc-markdown-skill.bundle restored-anydoc
git clone obsidian-llm-wiki-skill.bundle restored-wiki
```

Original CI/Release URLs in historical reports are retained as observed evidence;
after old-repository deletion, use the backed-up run IDs/assets and new repository
CI rather than treating those URLs as active endpoints. Current installation,
maintenance, reports and releases use this repository.

## Activation gate

Delete only after all three static evaluations exceed 90, official specification
checks pass, native matrix/integration checks pass, top-level Agent forward evidence
is reviewed, both bundles restore, remote release assets match their checksums, and
the named old repository IDs/heads still match the backup. Record the actual action
or any GitHub authorization error honestly; archiving is not reported as deletion.
