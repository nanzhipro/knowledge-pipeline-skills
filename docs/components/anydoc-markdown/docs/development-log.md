# Development and verification log

## 2026-11-01 — Requirements and source verification

- Scope: one document conversion skill, Rust anydoc, Windows/macOS, file/directory input, auditable per-file Markdown bundles. Wiki synthesis and OKF compliance are outside this skill.
- Latest stable verified: anydoc 0.2.4; release tag commit `42bf1c5ecdde9eb0d96d6bd75a9e6698cf93b14c`, published 2026-08-27; crate checksum `cf0d78e4cfe3654eb3ea04422ec5a94352000ee56e97902125e68e51f7527062`.
- Critical API gap: public `to_document` exposes assets but public `to_markdown_bytes` does not render a modified Document. Vendor only the matching MIT Markdown serializer, then replace embedded image references with safe local asset paths before rendering. No parser fork.
- Independent probe compiled the serializer against the published crate and matched official RTF output byte for byte.
- Downloads inventory found real DOCX/CSV/PDF/EPUB inputs. Missing parser families are supplemented with official MIT fixtures. Originals, extracted content, and private paths stay outside tracked files.
- Evaluation plan: Plugin Eval static analysis and recommendations, official Agent Skills validator, Rust tests, independent forward task, real corpus checks, and native Windows/macOS CI. Static scores do not establish conversion accuracy.

## Implementation and observed iteration

- Implemented per-file bundles, original snapshots, UTF-8/LF Markdown, flat provenance, local assets, manifests, failure pages and read-only artifact verification. Unknown/corrupt inputs do not prevent remaining files from being processed.
- Public regression corpus: 18 MIT fixtures covering 14 extensions plus scanned/corrupt/embedded-image examples. Mac development checks passed 22 tests, formatting and Clippy with warnings denied.
- Independent review reproduced and corrected three concrete defects: OS hidden attributes were not excluded, plain directory rename could replace a concurrently created empty destination, and failed misnamed files reported the suffix rather than detected format. Added regressions; atomic NOREPLACE/RENAME_EXCL now protects publication on Unix, and Windows publication was queued for native verification.
- Independent forward execution found retained source-relative links with unresolved targets. Added a visible warning rather than expanding filesystem scope or claiming those targets were copied. Clarified that verify exit 0 confirms artifact integrity while partial/failed statuses remain.
- Plugin Eval: 95 initial, 91 development tree including build caches, 95 final clean source. Applied the trigger advice; retained useful fixture attribution despite the generic extra-document warning. Official Agent Skills validation passed. No scoring rules were altered.
- Corpus checks distinguish readable extraction from fidelity: PDFs showed differences against pypdf and PDFKit, so they remain partial. This is recorded rather than hidden as a successful lossless conversion.

- The three original review probes were rerun after the fixes: macOS UF_HIDDEN exclusion/explicit inclusion, misnamed scanned-PDF detection, and an injected competing empty destination at the actual rename syscall. All behaved as intended; existing destination permissions/content remained unchanged.

- Final corpus rerun after the fixes retained all 175 Markdown bodies, original copies and extracted asset payloads. Existing authored source-relative links are now explicitly warned; generated source/asset links remain intact.
- Created the public MIT repository via gh and pushed implementation commit 53962172a87369f88ff254f490d9ff552ba29cb1; native Windows/macOS workflow started. No private document content was committed.

## Native Windows correction

- First native run passed formatting/Clippy and 19 unit tests, but the no-replace publication regression failed: Rust std::fs::rename also replaced an existing empty destination directory on that Windows runner. This disproved the earlier source-only assumption.
- Replaced that Windows branch with MoveFileExW flags=0 (no REPLACE_EXISTING), with checked NUL-terminated UTF-16 buffers and a narrowly documented FFI call. The same existing-empty-directory regression is retained. A new native run must pass before release.

- Second native Windows run passed all 20 unit tests, including the corrected no-replace behavior, then caught a fixture SHA mismatch in the 18-document integration test. Recreating Git's LF-to-CRLF conversion produced the exact observed mismatch. Added .gitattributes to keep source-document fixture bytes binary and repository text LF; this fixes checkout behavior without weakening the original-byte assertion or changing upstream fixture hashes.

- Reproduced the final source from Git with core.autocrlf=true: all 18 fixture SHA-256 values still matched. Re-evaluated that complete 60-file source checkout: Plugin Eval 95/A and official Agent Skills validation passed; no test/resource was removed.

## Release verification

- Native run 41267043173 passed on Windows x64, macOS ARM64 and macOS Intel: 22 tests per runner, fmt, Clippy -D warnings, release build and CLI formats execution. Tested implementation commit: 71121dc708d0c886d246f41232b85d21c6eb969c.
- Final 60-file source distribution scores 95/A in Plugin Eval and passes official Agent Skills validation. Package is assembled from tracked source files, excludes build/Finder/private artifacts, and is checked byte-for-byte before upload.
- v0.1.0 release contains the self-contained source Skill ZIP plus SHA256SUMS under MIT. Public evidence records actual failures and fixes, aggregate corpus metrics, independent forward execution, and native job results.
