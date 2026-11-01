# Consolidated validation

Three independent Skill packages are evaluated, installed and invoked separately.
The two original runtime implementations are unchanged apart from active repository
metadata/provenance URLs; all original files and histories are mapped in migration.

## Static package checks

Plugin Eval (unaltered rules): anydoc-markdown **95/A**, obsidian-llm-wiki **91/B**,
knowledge-pipeline **95/A**. All three official Agent Skills checks pass. Full source
inventories, original reports, briefs, and the coordinator's routing review are in
[evaluation/merge](evaluation/merge/README.md). These are static quality measures,
not model accuracy, source fidelity, or observed token metrics.

## Actual runtime and task checks

- The existing parser has 22 Rust regressions and the Wiki has 29 Python regressions.
- A new repository integration test executes the real Rust converter over three
  public inputs and passes its actual batch into the independently installed Wiki
  helper. It checks assets, originals, diagnostic isolation, pending semantics,
  prepare-only isolation, review hashes, publication, idempotency and read-only search.
- Native CI builds/tests Rust on macOS ARM/Intel and Windows x64, then runs both
  Python 3.10 and 3.13 regression/integration checks on each platform.
- A separate independent Agent exercise uses the top-level Skill on actual source
  documents, compiles source summaries and knowledge pages and answers a cited query.
  Its record distinguishes helper execution from actual source reading and synthesis.

Execution identities and final native outcomes are recorded in
[verification/native-ci.json](verification/native-ci.json). The Agent exercise lives
under [verification/coordinator-forward](verification/coordinator-forward/).
Original component reports retain their historical scores and source identity under
docs/components; original CI assets and logs are preserved in the portable backup.
No Obsidian GUI automation or broad model-accuracy benchmark is claimed.

## Migration checks

Both standalone Git bundles restore their original heads and original tag objects.
All four former Release assets, five CI logs and seven build artifacts were backed
up with SHA-256/CRC checks. The new combined package and portable backup are downloaded
and verified before either old remote repository can be deleted. Local old repositories,
mirrors and the author's original Karpathy source remain intact. See [migration](migration/README.md).
