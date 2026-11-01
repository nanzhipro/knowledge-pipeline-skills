# Output contract v1

The input is one regular file or one directory. Directory conversion is recursive. Every discovered non-symlink regular file receives a bundle, including unsupported/corrupt documents. Hidden entries are excluded unless `--include-hidden` is supplied. Traversal errors are reported and the batch returns attention status. Original files remain untouched; each readable input within the configured size limit gets an exact source copy. Unreadable or oversized inputs get an explicit error page/report stating that no source copy was made.

## Layout and identity

`documents/<safe-name>--<path-hash>/` is deterministic from the input-relative path, including the extension. The name is portable on Windows/macOS and the path hash separates case variants and same basenames in different directories. Never use an untrusted archive path as an output path. Batch `manifest.json` records original relative path, bundle location, outcome and SHA-256. `index.md` links to every generated Markdown page.

Each bundle contains `document.md`, `source/original.<ext>`, `report.json`, and any `assets/` files. Markdown has flat YAML provenance fields (JSON-quoted strings are YAML-compatible), followed by extracted GFM. `source_sha256` identifies bytes, not credibility. Text is UTF-8 with LF line endings; normalization does not infer a new document structure. Downstream Wiki compilers should read successful extractions plus warnings and trace claims to the preserved original.

## Status

- `converted`: parser returned nonempty Markdown without a recorded omission; not a claim of losslessness.
- `partial`: readable output exists with known losses, recovery events, or resources needing manual attention. The default policy also flags format-wide review needs (such as CSV inference, slide layout, and PDF figures) conservatively as partial, even when readable text was extracted.
- `needs_ocr`: anydoc identified image-only PDF pages; Markdown is a status page, not extracted content.
- `unsupported`: this input is outside supported parsers.
- `error`: the input could not be read or parsed.

`report.json` records detected format, parser version, warnings, OCR page numbers when supplied, source/output/asset hashes, and artifact sizes. `manifest.json` has one entry per discovered file and separate traversal errors. A parser panic is contained per file and reported as an error; it must not terminate the remaining batch.

Exit codes: 0 for a clean batch/verification, 2 when attention is needed, 1 for invalid CLI/setup or a batch-level I/O failure. The output is staged beside the destination and published as a directory only when assembled; existing outputs are never overwritten. This does not claim crash recovery or atomic behavior across unrelated filesystems.

## Verification

`verify OUTPUT` checks manifest/bundle correspondence, preserved-source hashes, Markdown hashes, asset hashes and safe contained artifact paths. It checks reported bytes, not whether every source claim survived or whether the Markdown visually matches the source. Review representative content separately. Failed status pages remain failed after structural verification.
