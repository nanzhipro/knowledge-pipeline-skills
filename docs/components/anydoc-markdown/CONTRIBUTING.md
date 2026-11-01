# Contributing

Use a Rust 1.88+ toolchain. Run `cargo fmt --check`, `cargo clippy --locked --all-targets -- -D warnings`, and `cargo test --locked` from `anydoc-markdown/scripts/anydoc-md/` before opening a change.

For a parser/output issue, provide a small redistributable fixture, its source/license, your OS and CLI version, the observed warning/error and the expected text or asset behavior. Keep private documents out of issues and commits. Prefer a regression test that checks the observable failure rather than a copy of the implementation.

The parser is the upstream `anydoc` crate. Renderer changes must preserve the attribution and update the recorded upstream/local fingerprints. Backend upgrades must update Cargo.toml, Cargo.lock, the version report and corpus results together. Document known losses rather than suppressing diagnostics to improve a success rate or evaluation score.
