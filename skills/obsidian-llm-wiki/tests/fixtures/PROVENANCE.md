# Public pipeline fixtures

These two batches were produced by the real `anydoc-md 0.1.0` helper from
[nanzhipro/anydoc-markdown-skill](https://github.com/nanzhipro/anydoc-markdown-skill),
using Rust anydoc 0.2.4, on 2026-11-01. They are converter outputs rather than
prewritten Wiki pages. They contain no private documents.

Seven source documents are newly authored synthetic MIT fixtures covered by this
included `LICENSE.synthetic`: the EPUB, service protocol, research and operations memos,
prompt-injection example, CSV, and unsupported binary. Their fictional facts are
listed in `semantic-oracle.json`. The prompt injection is inert test content.

The image DOCX, scanned PDF, and truncated PDF are small upstream fixtures from
[firecrawl/anydoc v0.2.4](https://github.com/firecrawl/anydoc/tree/v0.2.4), under
MIT. Their copied license is `LICENSE.anydoc`. The DOCX's PNG/OLE assets and original
bytes are preserved. No claim is made that the OLE binary has been interpreted.

Each batch has ten entries: one `converted`, six `partial`, one `needs_ocr`, one
`error`, and one `unsupported`. Revision 2 changes two fictional original files;
unchanged bytes should deduplicate while older raw evidence remains available.

Git must preserve every fixture byte, including binary-looking RTF and source
originals, because reports bind SHA-256 to their exact contents.
