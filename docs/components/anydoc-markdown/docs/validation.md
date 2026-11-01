# Validation record

Date: 2026-11-01. Results below distinguish static skill checks, deterministic Rust behavior, document extraction, and native platform execution.

## Static Skill evaluation

Plugin Eval initial static score: **95/100 (A)**. The official Agent Skills validator passed. The initial report recommended an explicit “Use when” trigger in the description; that recommendation was applied. Initial evaluation occurred before the Rust helper was complete, illustrating why its score cannot establish runtime behavior. Final clean-source evaluation: **95/100 (A)**, above the requested 90 threshold. The remaining warning flags a nested fixture README that is retained because it documents corpus licensing and correct test inputs. Development-tree evaluation was 91 because it included Cargo build artifacts. Both original reports and the source-only packaging condition are retained in [evaluation](evaluation/README.md).

The installed Plugin Eval only analyzes Python/TypeScript helpers. This project's Rust code is checked by Cargo tests and Clippy, not by that static code evaluator. Token figures in those reports are estimates, not measured agent usage.

## Public corpus

An expanded local upstream corpus contains 78 documents across 14 extensions: DOC, DOCX, PPT, PPTX, XLS, XLSX, XLSB, ODT, ODS, ODP, RTF, EPUB, CSV and PDF. Of these, 64 expected readable cases yielded readable Markdown, 12 malformed/resource-abuse cases failed in a controlled way, and 2 scanned-PDF cases returned needs_ocr. Preserved originals matched all 78 input hashes. Twenty extracted asset payloads (100,026 bytes) had no missing generated source/asset links or mismatched ZIP payload bytes. Eight authored source-relative links target files not copied into the bundles; seven documents now explicitly report that limitation.

Sixty readable cases had upstream Markdown snapshots: 59 had complete normalized line coverage. The PDF case differed in a heading/line grouping and bidirectional-script ordering; its independent character 4-gram recall was 97.1%. These are diagnostic comparisons, not a general semantic accuracy score. The lockfile resolves pdf-inspector 1.25.2, while the upstream release's historical lockfile used 1.14.2; both satisfy anydoc 0.2.4's declared dependency range.

The committed redistributable subset contains 18 attributed MIT fixtures covering the 14 extensions, embedded assets, scanned PDF and a truncated PDF. Rust integration tests exercise these fixtures natively.

## Private real documents

The user authorized local Downloads testing. Names, source paths, individual source hashes, extracted text and originals are not committed. A separate, deduplicated corpus contains 97 documents from files and ZIP members (DOCX, CSV, PDF, EPUB); 95 generated readable Markdown (93 partial, 2 converted), while 2 truncated/corrupt PDFs failed in a controlled way. All 97 retained originals matched their input bytes, 271 extracted assets matched their source payloads, and 291 relative links resolved. The 82 original direct Downloads files were rehashed with no changes. A final rerun of all 175 public/private inputs after the runtime fixes preserved every body byte (excluding frontmatter status), original copy and extracted asset; previously recorded semantic diagnostics therefore apply to the unchanged bodies.

Independent checks retained all CSV cell values and all DOCX alphanumeric character multisets in this corpus. EPUB character-multiset recall ranged from 99.49% to 100%. For 23 readable PDFs, 10 had recall below 99% against independent extractors: minimum 89.0% versus pypdf, 91.6% versus PDFKit, with median 99.93%. These lexical differences require review and do not establish visual or semantic significance. PDF outputs remain partial. See [machine-readable aggregate evidence](corpus-validation.json).

## Native platform evidence

Native validation **passed on all three runners**: Windows x64, macOS ARM64, and macOS Intel. Formatting, Clippy with warnings denied, all 22 native regression/integration tests, release compilation, and CLI execution passed. [Successful native run](https://github.com/nanzhipro/anydoc-markdown-skill/actions/runs/41267043173) validates implementation commit `71121dc708d0c886d246f41232b85d21c6eb969c`; [machine-readable jobs](native-ci.json) and [native build artifacts](native-artifacts.json) preserve results.

Earlier native runs exposed Windows replacement behavior and Git line-ending conversion. The no-replace API and fixture checkout rules were fixed, retaining the original regression and SHA assertions. The final source was also checked out with core.autocrlf=true; all 18 fixture hashes matched. Final documentation-only updates leave the tested skill and CI source unchanged.


## Limits

Structural verification checks recorded artifact bytes and safe paths. It does not prove arbitrary source fidelity, validate all Markdown syntax, reproduce original page geometry, perform OCR, or independently confirm facts. General format-wide warnings conservatively produce partial status even when text extraction succeeds. Known parser limitations remain visible rather than being hidden to improve a score.
