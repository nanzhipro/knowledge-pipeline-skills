# Vendored anydoc Markdown renderer

Source: https://github.com/firecrawl/anydoc/tree/v0.2.4/src/render

Tag: `v0.2.4`

Commit: `42bf1c5ecdde9eb0d96d6bd75a9e6698cf93b14c`

Retrieved: 2026-11-01

License: MIT; exact upstream license is retained in `UPSTREAM-LICENSE`.

The six Rust source files are copied from the release tag. The only local
source change removes `#[cfg(test)]` and `mod tests;` (with their adjacent blank line) from `markdown/mod.rs`
because the upstream test module is not vendored. Production rendering is
unchanged. A root `pub use anydoc::model;` and a direct `log` dependency are
required. The parser remains the pinned crates.io dependency `anydoc = "=0.2.4"`.

`UPSTREAM-FINGERPRINTS.json` records SHA-256 of both upstream and local bytes.
