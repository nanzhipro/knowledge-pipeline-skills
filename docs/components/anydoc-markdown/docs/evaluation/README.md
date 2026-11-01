# Plugin Eval and Agent Skills evidence

Evaluated with the user's installed Plugin Eval plugin (installation package 0.1.2; result tool.version reports 0.1.0). The evaluator was not modified.

| Stage | Static score | Interpretation |
| --- | --- | --- |
| [Initial](before/plugin-eval.json) | 95/A | Description lacked an explicit use-when trigger; Rust helper was still being built |
| [Development tree](after/plugin-eval.json) | 91/B | Cargo target artifacts inflated deferred size; retained as actual intermediate result |
| [Clean source](after-clean-source/plugin-eval.json) | 95/A | All source/tests/fixtures retained; only generated build/cache content excluded |
| [Pre-native source](final-result/plugin-eval.json) | 95/A | After trigger clarification and source-relative-link warning |
| [Native-fix source](release-final/plugin-eval.json) | 95/A | After the native Windows no-replace correction |
| [Published checkout](published-source/plugin-eval.json) | **95/A** | Final 60-file source with fixture byte-preservation rules; core.autocrlf=true checkout tested |

Final [official Agent Skills validation](published-source/agent-skills-validation.json) passed. [Before/after comparison](final-compare.md) and [final source fingerprints](published-source/source-inventory.json) retain the conditions. The final 60-file inventory is tied to commit 71121dc708d0c886d246f41232b85d21c6eb969c; all 18 original fixture hashes also match after a core.autocrlf=true checkout. Earlier 59-file inventories predate the fixture-level .gitattributes addition.

The remaining warning flags `tests/fixtures/README.md`; it is intentionally retained because it explains licensing and how to select actual document inputs. No coverage artifact was supplied; no synthetic coverage or usage measurements were fabricated. Static token figures are estimates.

This Plugin Eval version does not analyze Rust helper code. Its score is not conversion accuracy, semantic fidelity, test coverage, native-platform assurance, or measured token savings. Cargo fmt/clippy/tests, corpus checks, independent forward execution, and native CI provide separate evidence.

Reproduce with an installed Plugin Eval CLI on a clean checkout:

```text
plugin-eval start anydoc-markdown --request "Evaluate this skill." --format markdown
plugin-eval analyze anydoc-markdown --format json --output result.json
skills-ref validate anydoc-markdown
```

Some raw reports retain local evaluation paths to identify their original run conditions. They contain no user's document content or private corpus paths.
