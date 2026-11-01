# Runtime setup

Requires Rust/Cargo 1.88+ (https://rustup.rs/). On Windows select the MSVC toolchain and install Microsoft C++ Build Tools if rustup requests them; macOS may require Xcode Command Line Tools. First build downloads pinned crates, then document conversion needs no network access or credentials.

Commands are identical in PowerShell and macOS shells when quoted paths are used. Replace the manifest path with the installed skill's actual absolute path:

```text
cargo run --locked --release --manifest-path "PATH/anydoc-markdown/scripts/anydoc-md/Cargo.toml" -- convert "INPUT" --output "OUTPUT"
cargo run --locked --release --manifest-path "PATH/anydoc-markdown/scripts/anydoc-md/Cargo.toml" -- verify "OUTPUT"
```

To avoid compiling on every invocation, Cargo reuses its target cache. For a permanent local executable:

```text
cargo install --locked --path "PATH/anydoc-markdown/scripts/anydoc-md"
anydoc-md --version
anydoc-md convert "INPUT" --output "OUTPUT"
anydoc-md verify "OUTPUT"
```

Use `anydoc-md formats` to list coverage. Review the release's platform-specific archive and checksum if choosing a prebuilt binary; do not run an executable for another architecture. A successful macOS run is not evidence of Windows compatibility; native CI results are recorded separately.
