# Conversion self-test fixtures

All document bytes come from the MIT-licensed `firecrawl/anydoc` tag `v0.2.4` (`42bf1c5ecdde9eb0d96d6bd75a9e6698cf93b14c`). `SOURCES.json` records original paths, hashes, expected outcomes, and the one truncation operation. The original MIT notice is in `LICENSE.anydoc`.

- `valid/`: one readable document per 14 supported extensions.
- `assets/`: DOCX and EPUB cases with a real embedded PNG.
- `negative/scanned.pdf`: image-only PDF; expected `needs_ocr`.
- `negative/truncated.pdf`: first 128 bytes of the upstream text PDF; expected a controlled conversion failure.
- `expected/`: upstream Markdown snapshots for the 16 successful cases. Image destinations can differ when the bridge externalizes resources.

Do not submit this fixture root wholesale as conversion input: it also contains metadata and expected outputs. Select the relevant document subtree or explicit document files. This corpus proves baseline behavior, not fidelity for arbitrary real-world documents.
