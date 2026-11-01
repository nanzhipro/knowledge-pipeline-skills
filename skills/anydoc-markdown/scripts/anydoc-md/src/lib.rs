//! Portable local document bundles. Parsing and Markdown rendering use anydoc.
pub use anydoc::model;
mod conversion;
mod render;

use chrono::Utc;
use conversion::Failure;
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::collections::{BTreeMap, HashSet};
use std::fs;
use std::io::{self, Read};
use std::path::{Component, Path, PathBuf};
use walkdir::WalkDir;

pub const ANYDOC_VERSION: &str = "0.2.4";
pub const SCHEMA: &str = "anydoc-markdown/1";

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct Artifact {
    pub path: String,
    pub sha256: String,
    pub bytes: u64,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub origin: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub media_type: Option<String>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct Report {
    pub schema: String,
    pub source_relative_path: String,
    pub source_sha256: String,
    pub status: String,
    pub format: String,
    pub engine: String,
    pub warnings: Vec<String>,
    pub ocr_pages: Vec<usize>,
    pub error: Option<String>,
    pub artifacts: Vec<Artifact>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct Entry {
    pub source_relative_path: String,
    pub bundle: String,
    pub status: String,
    pub source_sha256: String,
    pub report_sha256: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct Manifest {
    pub schema: String,
    pub converter_version: String,
    pub anydoc_version: String,
    pub created_at: String,
    pub entries: Vec<Entry>,
    pub counts: BTreeMap<String, usize>,
    pub traversal_errors: Vec<String>,
    pub excluded: Vec<String>,
    pub index_sha256: String,
}

pub struct Options {
    pub include_hidden: bool,
    pub max_file_bytes: u64,
}

impl Default for Options {
    fn default() -> Self {
        Self { include_hidden: false, max_file_bytes: 128 * 1024 * 1024 }
    }
}

fn error(message: impl std::fmt::Display) -> io::Error {
    io::Error::other(message.to_string())
}

pub fn sha256(bytes: &[u8]) -> String {
    format!("{:x}", Sha256::digest(bytes))
}

fn hidden_entry(entry: &walkdir::DirEntry) -> bool {
    if entry.file_name().to_string_lossy().starts_with('.') {
        return true;
    }
    let Ok(metadata) = entry.metadata() else {
        return false;
    };
    #[cfg(target_os = "macos")]
    {
        use std::os::macos::fs::MetadataExt;
        metadata.st_flags() & 0x8000 != 0 // UF_HIDDEN
    }
    #[cfg(windows)]
    {
        use std::os::windows::fs::MetadataExt;
        metadata.file_attributes() & (0x2 | 0x4) != 0 // HIDDEN or SYSTEM
    }
    #[cfg(not(any(target_os = "macos", windows)))]
    {
        let _ = metadata;
        false
    }
}

fn publish_directory(source: &Path, destination: &Path) -> io::Result<()> {
    #[cfg(any(target_os = "macos", target_os = "linux"))]
    {
        // RENAME_EXCL on macOS / RENAME_NOREPLACE on Linux closes the exists+rename race.
        rustix::fs::renameat_with(
            rustix::fs::CWD,
            source,
            rustix::fs::CWD,
            destination,
            rustix::fs::RenameFlags::NOREPLACE,
        )
        .map_err(io::Error::from)
    }
    #[cfg(windows)]
    {
        use std::os::windows::ffi::OsStrExt;
        let source_wide: Vec<u16> = source.as_os_str().encode_wide().chain(Some(0)).collect();
        let destination_wide: Vec<u16> =
            destination.as_os_str().encode_wide().chain(Some(0)).collect();
        if source_wide[..source_wide.len() - 1].contains(&0)
            || destination_wide[..destination_wide.len() - 1].contains(&0)
        {
            return Err(error("NUL byte in publication path"));
        }
        // SAFETY: both buffers are NUL-terminated UTF-16 and remain alive for
        // this synchronous call. Flags=0 deliberately omits REPLACE_EXISTING.
        let moved = unsafe {
            windows_sys::Win32::Storage::FileSystem::MoveFileExW(
                source_wide.as_ptr(),
                destination_wide.as_ptr(),
                0,
            )
        };
        if moved == 0 { Err(io::Error::last_os_error()) } else { Ok(()) }
    }
    #[cfg(not(any(target_os = "macos", target_os = "linux", windows)))]
    {
        let _ = (source, destination);
        Err(error("Publishing is supported on Windows, macOS, and Linux"))
    }
}

fn portable_name(path: &str) -> String {
    let base = path.rsplit('/').next().unwrap_or("document");
    let mut name = String::new();
    for c in base.chars().take(64) {
        if c.is_ascii_alphanumeric()
            || c == '-'
            || c == '_'
            || c == '.'
            || (!c.is_ascii() && !c.is_control())
        {
            name.push(c);
        } else {
            name.push('_');
        }
    }
    let name = name.trim_matches('.');
    let name = if name.is_empty() { "document" } else { name };
    // Prefix prevents Windows device names; hash separates paths and case variants.
    format!("doc-{name}--{}", &sha256(path.as_bytes())[..16])
}

fn relative_string(path: &Path) -> io::Result<String> {
    let mut parts = Vec::new();
    for component in path.components() {
        match component {
            Component::Normal(part) => parts.push(
                part.to_str()
                    .ok_or_else(|| error("Non-UTF-8 source path; rename it before conversion"))?,
            ),
            _ => return Err(error("Expected a normal relative input path")),
        }
    }
    Ok(parts.join("/"))
}

fn future_path(path: &Path) -> io::Result<PathBuf> {
    let absolute =
        if path.is_absolute() { path.to_path_buf() } else { std::env::current_dir()?.join(path) };
    let mut normalized = PathBuf::new();
    for component in absolute.components() {
        match component {
            Component::ParentDir => {
                normalized.pop();
            }
            Component::CurDir => {}
            other => normalized.push(other.as_os_str()),
        }
    }
    let mut missing = Vec::new();
    let mut ancestor = normalized.as_path();
    while !ancestor.exists() {
        missing
            .push(ancestor.file_name().ok_or_else(|| error("Invalid output path"))?.to_os_string());
        ancestor = ancestor.parent().ok_or_else(|| error("No existing output ancestor"))?;
    }
    let mut canonical = fs::canonicalize(ancestor)?;
    for part in missing.into_iter().rev() {
        canonical.push(part);
    }
    Ok(canonical)
}

fn write_artifact(bundle: &Path, relative: &str, bytes: &[u8]) -> io::Result<Artifact> {
    let path = bundle.join(relative);
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent)?;
    }
    fs::write(&path, bytes)?;
    Ok(Artifact {
        path: relative.to_string(),
        sha256: sha256(bytes),
        bytes: bytes.len() as u64,
        origin: None,
        media_type: None,
    })
}

fn quote(value: &str) -> String {
    serde_json::to_string(value).expect("serializing a string cannot fail")
}

fn normalize(text: &str) -> String {
    let text = text.replace("\r\n", "\n").replace('\r', "\n");
    format!("{}\n", text.trim_end_matches('\n'))
}

fn failure_page(status: &str, message: &str, pages: &[usize]) -> String {
    let mut body = format!(
        "# Conversion requires attention\n\nStatus: `{status}`\n\nNo document content was extracted. The diagnostic below is parser output, not source content.\n\n```text\n{}\n```\n\n[Preserved original](source/ORIGINAL)\n",
        message.replace("```", "~~~")
    );
    if !pages.is_empty() {
        body.push_str(&format!("\nPages requiring OCR: {pages:?}. No remote OCR was attempted.\n"));
    }
    body
}

fn convert_one(source: &Path, relative: &str, bundle: &Path, limit: u64) -> io::Result<Report> {
    fs::create_dir_all(bundle)?;
    let extension = source.extension().and_then(|x| x.to_str()).unwrap_or("").to_ascii_lowercase();
    let safe_extension = if !extension.is_empty()
        && extension.len() <= 12
        && extension.chars().all(|c| c.is_ascii_alphanumeric())
    {
        extension.clone()
    } else {
        "bin".to_string()
    };
    let source_path = format!("source/original.{safe_extension}");
    let file = fs::File::open(source);
    let bytes = match file {
        Ok(mut file) => {
            let size = match file.metadata() {
                Ok(metadata) => metadata.len(),
                Err(err) => {
                    return write_unreadable(
                        bundle,
                        relative,
                        &extension,
                        &format!("Could not stat original: {err}"),
                    );
                }
            };
            if size > limit {
                return write_unreadable(
                    bundle,
                    relative,
                    &extension,
                    "Input exceeds --max-file-mb; no original copy was made",
                );
            }
            let mut bytes = Vec::with_capacity(size as usize);
            if let Err(err) = file.by_ref().take(limit.saturating_add(1)).read_to_end(&mut bytes) {
                return write_unreadable(
                    bundle,
                    relative,
                    &extension,
                    &format!("Could not read original: {err}"),
                );
            }
            if bytes.len() as u64 > limit {
                return write_unreadable(
                    bundle,
                    relative,
                    &extension,
                    "Input grew beyond --max-file-mb while reading; no original copy was made",
                );
            }
            bytes
        }
        Err(err) => {
            return write_unreadable(
                bundle,
                relative,
                &extension,
                &format!("Could not read original: {err}"),
            );
        }
    };
    let detected_format = anydoc::Format::from_bytes(&bytes)
        .or_else(|| anydoc::Format::from_extension(&extension))
        .map(|format| format!("{format:?}").to_ascii_lowercase())
        .unwrap_or_else(|| extension.clone());
    let source_digest = sha256(&bytes);
    let mut artifacts = vec![write_artifact(bundle, &source_path, &bytes)?];
    let result = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
        conversion::convert(&bytes, &extension)
    }));
    let result = match result {
        Ok(result) => result,
        Err(_) => Err(Failure {
            kind: "error".into(),
            message: "Parser panicked on this input; the remaining batch continued".into(),
            pages: Vec::new(),
        }),
    };
    let (body, status, format, engine, warnings, pages, failure) = match result {
        Ok(converted) if !converted.markdown.trim().is_empty() => {
            let mut warnings = converted.warnings;
            for asset in converted.assets {
                if !asset.path.starts_with("assets/") || !safe_relative(&asset.path) {
                    warnings.push(
                        "Parser asset path rejected because it was not a contained assets/ path"
                            .into(),
                    );
                    continue;
                }
                let mut artifact = write_artifact(bundle, &asset.path, &asset.bytes)?;
                artifact.origin = Some(asset.origin);
                artifact.media_type = Some(asset.media_type);
                artifacts.push(artifact);
            }
            let status = if warnings.is_empty() { "converted" } else { "partial" }.to_string();
            (
                converted.markdown,
                status,
                converted.format,
                converted.engine,
                warnings,
                Vec::new(),
                None,
            )
        }
        Ok(_) => {
            let message =
                "Parser returned empty Markdown; source content requires manual inspection"
                    .to_string();
            (
                failure_page("error", &message, &[]),
                "error".into(),
                detected_format.clone(),
                format!("anydoc/{ANYDOC_VERSION}"),
                Vec::new(),
                Vec::new(),
                Some(message),
            )
        }
        Err(failure) => {
            let body = failure_page(&failure.kind, &failure.message, &failure.pages)
                .replace("source/ORIGINAL", &source_path);
            (
                body,
                failure.kind,
                detected_format.clone(),
                format!("anydoc/{ANYDOC_VERSION}"),
                Vec::new(),
                failure.pages,
                Some(failure.message),
            )
        }
    };
    let header = format!(
        "---\ntitle: {}\nsource: {}\nsource_relative_path: {}\nsource_sha256: {}\nformat: {}\nconversion_status: {}\nconverter: {}\n---\n\n",
        quote(source.file_stem().and_then(|x| x.to_str()).unwrap_or("Document")),
        quote(&source_path),
        quote(relative),
        quote(&source_digest),
        quote(&format),
        quote(&status),
        quote(&engine)
    );
    let markdown = header + &normalize(&body);
    artifacts.push(write_artifact(bundle, "document.md", markdown.as_bytes())?);
    let report = Report {
        schema: SCHEMA.into(),
        source_relative_path: relative.into(),
        source_sha256: source_digest,
        status,
        format,
        engine,
        warnings,
        ocr_pages: pages,
        error: failure,
        artifacts,
    };
    write_json(&bundle.join("report.json"), &report)?;
    Ok(report)
}

fn write_unreadable(
    bundle: &Path,
    relative: &str,
    extension: &str,
    message: &str,
) -> io::Result<Report> {
    let markdown = format!(
        "# Source unavailable\n\nNo source copy or extracted text is available.\n\n```text\n{}\n```\n",
        message.replace("```", "~~~")
    );
    let artifact = write_artifact(bundle, "document.md", markdown.as_bytes())?;
    let report = Report {
        schema: SCHEMA.into(),
        source_relative_path: relative.into(),
        source_sha256: String::new(),
        status: "error".into(),
        format: extension.into(),
        engine: format!("anydoc/{ANYDOC_VERSION}"),
        warnings: vec![
            "Original bytes were not copied; consult the input before using this bundle".into(),
        ],
        ocr_pages: Vec::new(),
        error: Some(message.into()),
        artifacts: vec![artifact],
    };
    write_json(&bundle.join("report.json"), &report)?;
    Ok(report)
}

fn write_json(path: &Path, value: &impl Serialize) -> io::Result<()> {
    let mut bytes = serde_json::to_vec_pretty(value).map_err(error)?;
    bytes.push(b'\n');
    fs::write(path, bytes)
}

pub fn convert_batch(input: &Path, output: &Path, options: &Options) -> io::Result<Manifest> {
    if fs::symlink_metadata(input)?.file_type().is_symlink() {
        return Err(error("Input symlinks are refused; select the actual file or directory"));
    }
    let input = fs::canonicalize(input)?;
    let output = future_path(output)?;
    if output.exists() {
        return Err(error("Output already exists; choose a new output directory"));
    }
    if input.is_dir() && (output.starts_with(&input) || input.starts_with(&output)) {
        return Err(error("Input and output directories must not overlap"));
    }
    let parent = output.parent().ok_or_else(|| error("Output requires a parent directory"))?;
    fs::create_dir_all(parent)?;
    let stage = tempfile::Builder::new().prefix(".anydoc-md-").tempdir_in(parent)?;
    fs::create_dir(stage.path().join("documents"))?;
    let mut paths = Vec::new();
    let mut traversal_errors = Vec::new();
    let mut excluded = Vec::new();
    if input.is_file() {
        let relative = relative_string(Path::new(
            input.file_name().ok_or_else(|| error("Input filename missing"))?,
        ))?;
        paths.push((relative, input.clone()));
    } else if input.is_dir() {
        for entry in WalkDir::new(&input).follow_links(false).into_iter().filter_entry(|entry| {
            options.include_hidden || entry.depth() == 0 || !hidden_entry(entry)
        }) {
            match entry {
                Ok(entry) if entry.file_type().is_symlink() => excluded.push(format!(
                    "{}: symlink",
                    entry.path().strip_prefix(&input).unwrap_or(entry.path()).display()
                )),
                Ok(entry) if entry.file_type().is_file() => {
                    match relative_string(entry.path().strip_prefix(&input).map_err(error)?) {
                        Ok(relative) => paths.push((relative, entry.path().to_path_buf())),
                        Err(err) => traversal_errors.push(err.to_string()),
                    }
                }
                Ok(_) => {}
                Err(err) => traversal_errors.push(err.to_string()),
            }
        }
    } else {
        return Err(error("Input is not a regular file or directory"));
    }
    paths.sort_by(|a, b| a.0.cmp(&b.0));
    let mut entries = Vec::new();
    let mut counts = BTreeMap::new();
    let mut names = HashSet::new();
    let mut index = String::from(
        "# Document conversion index\n\nEach link opens an extraction or an explicit failure page. Read its report before downstream use.\n\n",
    );
    for (relative, source) in paths {
        let bundle = format!("documents/{}", portable_name(&relative));
        if !names.insert(bundle.to_lowercase()) {
            return Err(error("Output identity collision; no output was published"));
        }
        let report =
            convert_one(&source, &relative, &stage.path().join(&bundle), options.max_file_bytes)?;
        *counts.entry(report.status.clone()).or_insert(0) += 1;
        let link = format!("{bundle}/document.md");
        index.push_str(&format!(
            "- [{}](<{}>) — {}\n",
            relative.replace('[', "\\[").replace(']', "\\]").replace(['\n', '\r'], " "),
            link,
            report.status
        ));
        entries.push(Entry {
            source_relative_path: relative,
            bundle: bundle.clone(),
            status: report.status,
            source_sha256: report.source_sha256,
            report_sha256: sha256(&fs::read(stage.path().join(&bundle).join("report.json"))?),
        });
    }
    if entries.is_empty() {
        index.push_str("No regular input files were discovered.\n");
    }
    fs::write(stage.path().join("index.md"), &index)?;
    let manifest = Manifest {
        schema: SCHEMA.into(),
        converter_version: env!("CARGO_PKG_VERSION").into(),
        anydoc_version: ANYDOC_VERSION.into(),
        created_at: Utc::now().to_rfc3339(),
        entries,
        counts,
        traversal_errors,
        excluded,
        index_sha256: sha256(index.as_bytes()),
    };
    write_json(&stage.path().join("manifest.json"), &manifest)?;
    // Same-parent staging avoids partially published bundles. Never replace an existing destination.
    if output.exists() {
        return Err(error("Output appeared during conversion; refusing to overwrite"));
    }
    publish_directory(stage.path(), &output)?;
    Ok(manifest)
}

fn safe_relative(value: &str) -> bool {
    !value.is_empty()
        && !value.contains('\\')
        && !value.contains(':')
        && Path::new(value).components().all(|c| matches!(c, Component::Normal(_)))
}

fn checked_file(root: &Path, relative: &str) -> io::Result<PathBuf> {
    if !safe_relative(relative) {
        return Err(error(format!("Unsafe artifact path: {relative}")));
    }
    let mut path = root.to_path_buf();
    for part in Path::new(relative).components() {
        path.push(part.as_os_str());
        if fs::symlink_metadata(&path)?.file_type().is_symlink() {
            return Err(error(format!("Symlink artifact refused: {relative}")));
        }
    }
    if !path.is_file() {
        return Err(error(format!("Artifact is not a file: {relative}")));
    }
    Ok(path)
}

#[derive(Debug, Serialize)]
pub struct Verification {
    pub ok: bool,
    pub documents: usize,
    pub attention_required: usize,
    pub issues: Vec<String>,
    pub semantic_fidelity_checked: bool,
}

pub fn verify(root: &Path) -> io::Result<Verification> {
    let root = fs::canonicalize(root)?;
    let manifest: Manifest =
        serde_json::from_slice(&fs::read(checked_file(&root, "manifest.json")?)?).map_err(error)?;
    let mut issues = Vec::new();
    let mut counts = BTreeMap::new();
    let mut bundles = HashSet::new();
    if manifest.schema != SCHEMA {
        issues.push("Unknown manifest schema".into());
    }
    if sha256(&fs::read(checked_file(&root, "index.md")?)?) != manifest.index_sha256 {
        issues.push("index.md hash mismatch".into());
    }
    for entry in &manifest.entries {
        *counts.entry(entry.status.clone()).or_insert(0usize) += 1;
        if !safe_relative(&entry.bundle)
            || !entry.bundle.starts_with("documents/")
            || !bundles.insert(entry.bundle.clone())
        {
            issues.push(format!("Unsafe or duplicate bundle: {}", entry.bundle));
            continue;
        }
        let report_path = format!("{}/report.json", entry.bundle);
        let report_bytes = match checked_file(&root, &report_path).and_then(fs::read) {
            Ok(bytes) => bytes,
            Err(err) => {
                issues.push(err.to_string());
                continue;
            }
        };
        if sha256(&report_bytes) != entry.report_sha256 {
            issues.push(format!("{report_path}: hash mismatch"));
        }
        let report: Report = match serde_json::from_slice(&report_bytes) {
            Ok(value) => value,
            Err(err) => {
                issues.push(format!("{report_path}: {err}"));
                continue;
            }
        };
        if report.schema != SCHEMA
            || report.source_relative_path != entry.source_relative_path
            || report.status != entry.status
            || report.source_sha256 != entry.source_sha256
        {
            issues.push(format!("{report_path}: manifest/report mismatch"));
        }
        let mut artifact_paths = HashSet::new();
        let mut source_count = 0;
        for artifact in &report.artifacts {
            if !artifact_paths.insert(&artifact.path) {
                issues.push(format!("{report_path}: duplicate artifact"));
            }
            let relative = format!("{}/{}", entry.bundle, artifact.path);
            if !safe_relative(&artifact.path) {
                issues.push(format!("Unsafe artifact: {relative}"));
                continue;
            }
            if artifact.path.starts_with("source/") {
                source_count += 1;
                if artifact.sha256 != entry.source_sha256 {
                    issues.push(format!("{relative}: source digest mismatch"));
                }
            }
            match checked_file(&root, &relative).and_then(fs::read) {
                Ok(bytes)
                    if bytes.len() as u64 == artifact.bytes
                        && sha256(&bytes) == artifact.sha256 => {}
                Ok(_) => issues.push(format!("{relative}: size/hash mismatch")),
                Err(err) => issues.push(err.to_string()),
            }
        }
        if !artifact_paths.contains(&"document.md".to_string()) {
            issues.push(format!("{report_path}: Markdown artifact missing"));
        }
        if !entry.source_sha256.is_empty() && source_count != 1 {
            issues.push(format!("{report_path}: expected one preserved source"));
        }
    }
    if counts != manifest.counts {
        issues.push("Manifest counts do not match entries".into());
    }
    let attention_required = manifest.entries.iter().filter(|e| e.status != "converted").count()
        + manifest.traversal_errors.len();
    Ok(Verification {
        ok: issues.is_empty(),
        documents: manifest.entries.len(),
        attention_required,
        issues,
        semantic_fidelity_checked: false,
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn identities_are_portable_and_separate_case_and_paths() {
        let names = ["a/report.docx", "b/report.docx", "a/REPORT.docx", "CON.txt", "a?<b>.docx"];
        let names: HashSet<_> =
            names.iter().map(|name| portable_name(name).to_lowercase()).collect();
        assert_eq!(names.len(), 5);
        assert!(names.iter().all(|n| !n.contains(['<', '>', ':', '?'])));
    }

    #[test]
    fn artifact_paths_reject_escape_and_windows_paths() {
        for value in ["../x", "/x", "C:/x", "assets/../../x", "assets\\x", ""] {
            assert!(!safe_relative(value));
        }
        assert!(safe_relative("assets/image.png"));
    }

    #[test]
    fn batch_preserves_originals_continues_failures_and_verifies_hashes() {
        let temp = tempfile::tempdir().unwrap();
        let input = temp.path().join("input");
        fs::create_dir(&input).unwrap();
        let rtf = b"{\\rtf1\\ansi A \\b bold\\b0 paragraph.}";
        fs::write(input.join("good.rtf"), rtf).unwrap();
        fs::write(input.join("bad.pdf"), b"%PDF-1.7 broken").unwrap();
        fs::write(input.join("unknown.bin"), b"unknown").unwrap();
        let out = temp.path().join("output");
        let manifest = convert_batch(&input, &out, &Options::default()).unwrap();
        assert_eq!(manifest.entries.len(), 3);
        assert!(
            manifest.entries.iter().any(|e| matches!(e.status.as_str(), "converted" | "partial"))
        );
        assert!(manifest.entries.iter().any(|e| e.status == "unsupported"));
        assert!(verify(&out).unwrap().ok);
        let entry = manifest.entries.iter().find(|e| e.source_relative_path == "good.rtf").unwrap();
        assert_eq!(fs::read(out.join(&entry.bundle).join("source/original.rtf")).unwrap(), rtf);
        fs::write(out.join(&entry.bundle).join("document.md"), "tampered").unwrap();
        assert!(!verify(&out).unwrap().ok);
        assert!(convert_batch(&input, &out, &Options::default()).is_err());
    }

    #[test]
    fn overlapping_destinations_are_refused_without_mutating_input() {
        let temp = tempfile::tempdir().unwrap();
        let input = temp.path().join("input");
        fs::create_dir(&input).unwrap();
        fs::write(input.join("x.csv"), b"name,value\na,1\n").unwrap();
        assert!(convert_batch(&input, &input.join("out"), &Options::default()).is_err());
        assert!(!input.join("out").exists());
    }

    #[test]
    fn unicode_and_quoted_filenames_round_trip_as_json() {
        let temp = tempfile::tempdir().unwrap();
        let input = temp.path().join("中文 空格.csv");
        fs::write(&input, "名称,值\n甲,1\n").unwrap();
        let out = temp.path().join("out");
        let manifest = convert_batch(&input, &out, &Options::default()).unwrap();
        assert_eq!(manifest.entries[0].source_relative_path, "中文 空格.csv");
        assert!(verify(&out).unwrap().ok);
    }

    #[test]
    fn publish_never_replaces_an_existing_empty_directory() {
        let temp = tempfile::tempdir().unwrap();
        let stage = temp.path().join("stage");
        let output = temp.path().join("output");
        fs::create_dir(&stage).unwrap();
        fs::create_dir(&output).unwrap();
        fs::write(stage.join("new.txt"), b"new").unwrap();
        assert!(publish_directory(&stage, &output).is_err());
        assert!(stage.join("new.txt").exists());
        assert_eq!(fs::read_dir(&output).unwrap().count(), 0);
    }

    #[test]
    fn failed_mislabeled_pdf_reports_detected_format() {
        let temp = tempfile::tempdir().unwrap();
        let input = temp.path().join("scan.docx");
        fs::copy(
            Path::new(env!("CARGO_MANIFEST_DIR")).join("tests/fixtures/negative/scanned.pdf"),
            &input,
        )
        .unwrap();
        let output = temp.path().join("output");
        let manifest = convert_batch(&input, &output, &Options::default()).unwrap();
        let report: Report = serde_json::from_slice(
            &fs::read(output.join(&manifest.entries[0].bundle).join("report.json")).unwrap(),
        )
        .unwrap();
        assert_eq!(report.status, "needs_ocr");
        assert_eq!(report.format, "pdf");
    }

    #[test]
    #[cfg(any(target_os = "macos", windows))]
    fn system_hidden_attributes_are_respected_and_can_be_included() {
        let temp = tempfile::tempdir().unwrap();
        let input = temp.path().join("input");
        fs::create_dir(&input).unwrap();
        let hidden = input.join("hidden.csv");
        fs::write(&hidden, b"a,b\n1,2\n").unwrap();
        #[cfg(target_os = "macos")]
        let result = std::process::Command::new("/usr/bin/chflags")
            .arg("hidden")
            .arg(&hidden)
            .status()
            .unwrap();
        #[cfg(windows)]
        let result =
            std::process::Command::new("attrib.exe").arg("+H").arg(&hidden).status().unwrap();
        assert!(result.success());
        let excluded =
            convert_batch(&input, &temp.path().join("excluded"), &Options::default()).unwrap();
        assert_eq!(excluded.entries.len(), 0);
        let included = convert_batch(
            &input,
            &temp.path().join("included"),
            &Options { include_hidden: true, ..Options::default() },
        )
        .unwrap();
        assert_eq!(included.entries.len(), 1);
    }
}
