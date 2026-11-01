# Formats and limits

Backend: `anydoc = 0.2.4`, latest stable checked against GitHub releases and the crates.io index on 2026-11-01. The lockfile makes builds reproducible. Upgrades require checking a newer release, updating Cargo.toml/lockfile, and rerunning tests; do not silently switch parser versions mid-batch.

Supported Rust parser families: DOC, DOCX/DOCM, PPT/PPS/POT, PPTX/PPTM/PPSX/PPSM, XLS/XLSX/XLSM/XLSB, ODT, ODS, ODP, RTF, EPUB, CSV, PDF. Content signatures take precedence over filename extensions; CSV needs its extension because it has no signature. HTML, images, archives and unknown binary files are reported unsupported. A directory is not an archive-extraction command.

- Scanned or mixed PDFs: anydoc returns NeedsOcr with page numbers and fails extraction for that document. No built-in OCR or remote fallback is offered.
- Text PDFs: anydoc returns Markdown directly, without the shared Document/asset model. Embedded figures and exact page/coordinate reconstruction are unavailable through this API; keep the original and report the limitation.
- Office/EPUB/OpenDocument: export exposed asset bytes and use local relative links. Package media not placed by the parser may be appended as attachments; placement must remain marked unknown. External image URLs are not downloaded. Source-relative hyperlinks are retained without copying their targets or rebasing them into other bundles; a warning is recorded because these links may not resolve.
- Spreadsheets: cell values and tables form a reading representation. Merged cells, formulas/macros, hidden content and image placement require original-file inspection; formulas are not recalculated.
- Presentations: text reading order does not preserve the full slide layout. Speaker notes, diagrams and animation may not be represented.
- RTF/legacy formats: unsupported objects or recovery messages are recorded. Empty output is never called a successful conversion.

No Markdown representation can guarantee the full layout or meaning of arbitrary documents. Source copies preserve the fallback. Parser warnings and known limitations must accompany every downstream use.
