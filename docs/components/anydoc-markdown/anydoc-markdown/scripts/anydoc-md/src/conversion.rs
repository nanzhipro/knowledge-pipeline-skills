//! Local conversion and asset localization; this module never performs network I/O.

use std::cell::RefCell;
use std::collections::{HashMap, HashSet};
use std::io::{Cursor, Read};
use std::sync::OnceLock;

use anydoc::{ConvertError, Format};
use sha2::{Digest, Sha256};

use crate::model::{Block, CellSlot, Document, ImageSource, Inline, LinkTarget};

const ENGINE: &str = "anydoc/0.2.4";
const MAX_ASSET_BYTES: usize = 128 * 1024 * 1024;
const MAX_ZIP_ENTRIES: usize = 100_000;
const MAX_CAPTURED_LOGS: usize = 128;

#[derive(Debug)]
pub struct AssetOutput {
    pub path: String,
    pub bytes: Vec<u8>,
    pub origin: String,
    pub media_type: String,
}

#[derive(Debug)]
pub struct Conversion {
    pub markdown: String,
    pub format: String,
    pub engine: String,
    pub warnings: Vec<String>,
    pub assets: Vec<AssetOutput>,
}

#[derive(Debug)]
pub struct Failure {
    pub kind: String,
    pub message: String,
    pub pages: Vec<usize>,
}

/// Detect from bytes first, then use the extension for signature-less inputs.
pub fn convert(bytes: &[u8], extension: &str) -> Result<Conversion, Failure> {
    let capture_available = *LOGGER_INSTALLED.get_or_init(|| {
        if log::set_logger(&PARSER_LOGGER).is_ok() {
            log::set_max_level(log::LevelFilter::Debug);
            true
        } else {
            false
        }
    });
    let guard = capture_available.then(LogGuard::new);
    let result = convert_inner(bytes, extension);
    let logs = guard.map(LogGuard::finish).unwrap_or_default();
    result.map(|mut converted| {
        converted.warnings.extend(logs);
        if !capture_available {
            converted.warnings.push(
                "Upstream recovery logs could not be captured because another logger is registered."
                    .into(),
            );
        }
        let mut seen = HashSet::new();
        converted.warnings.retain(|warning| seen.insert(warning.clone()));
        converted
    })
}

fn convert_inner(bytes: &[u8], extension: &str) -> Result<Conversion, Failure> {
    let extension = extension.trim_start_matches('.');
    let format = Format::from_bytes(bytes)
        .or_else(|| Format::from_extension(extension))
        .ok_or_else(|| Failure {
            kind: "unsupported".into(),
            message: "Unrecognized document content and extension.".into(),
            pages: Vec::new(),
        })?;
    let mut warnings = Vec::new();

    if format == Format::Pdf {
        let markdown = anydoc::to_markdown_bytes(bytes, format).map_err(from_anydoc)?;
        if markdown.trim().is_empty() {
            return Err(failure("PDF conversion returned no readable Markdown."));
        }
        warnings.push(
            "This PDF API returns text Markdown only; PDF images and embedded attachments are not extracted."
                .into(),
        );
        warnings.push(
            "Review PDF reading order, tables, font encoding, and page coverage against the original."
                .into(),
        );
        return Ok(Conversion {
            markdown,
            format: format_name(format).into(),
            engine: ENGINE.into(),
            warnings,
            assets: Vec::new(),
        });
    }

    let document = anydoc::to_document(bytes, format).map_err(from_anydoc)?;
    let (markdown, assets) = render_document(document, bytes, format, &mut warnings)?;
    Ok(Conversion {
        markdown,
        format: format_name(format).into(),
        engine: ENGINE.into(),
        warnings,
        assets,
    })
}

fn render_document(
    mut document: Document,
    original: &[u8],
    format: Format,
    warnings: &mut Vec<String>,
) -> Result<(String, Vec<AssetOutput>), Failure> {
    let mut store = AssetStore::default();
    let mut asset_ids = HashMap::new();
    for asset in &mut document.assets {
        let media_type = media_type_for(&asset.origin_part, &asset.media_type);
        let index = store.insert(
            std::mem::take(&mut asset.bytes),
            asset.origin_part.clone(),
            media_type,
        )?;
        asset_ids.insert(asset.id.0, index);
    }

    // An archive can contain media which its format parser does not model,
    // notably Excel drawings. Preserve those bytes without inventing placement.
    supplement_zip_assets(original, format, &mut store, warnings);

    let mut observed = Observed::default();
    rewrite_blocks(&mut document.blocks, &asset_ids, &mut store, &mut observed);
    for note in &mut document.notes {
        rewrite_blocks(&mut note.blocks, &asset_ids, &mut store, &mut observed);
    }
    if !observed.relative_links.is_empty() {
        warnings.push(format!("{} distinct source-relative hyperlink(s) are retained without target copying or rebasing; they may not resolve inside the output bundle.", observed.relative_links.len()));
    }
    if !observed.external_images.is_empty() {
        warnings.push(format!(
            "{} distinct image URI reference(s) remain as authored; their bytes were not fetched or localized.",
            observed.external_images.len()
        ));
    }
    if observed.unavailable_images > 0 {
        warnings.push(format!(
            "{} image/object reference(s) have missing or unreadable source bytes; only available alt text remains.",
            observed.unavailable_images
        ));
    }
    if observed.merged_cells > 0 {
        warnings.push(format!(
            "{} merged table cell(s) were rendered through Markdown; review spans, geometry, and reading order.",
            observed.merged_cells
        ));
    }
    if observed.math > 0 {
        warnings.push(format!(
            "{} mathematical expression(s) were retained as LaTeX; they were not evaluated.",
            observed.math
        ));
    }
    add_format_warnings(format, warnings);
    if store.assets.iter().any(|asset| asset.media_type == "application/vnd.ms-ole-object") {
        warnings.push(
            "Embedded OLE objects are retained as stored binary containers; their inner application files are not unpacked."
                .into(),
        );
    }

    let mut markdown = crate::render::markdown::document_to_markdown(&document);
    let unplaced: Vec<_> = store
        .assets
        .iter()
        .enumerate()
        .filter(|(index, _)| !store.referenced.contains(index))
        .collect();
    if !unplaced.is_empty() {
        warnings.push(format!(
            "{} extracted asset(s) have no modeled position; links are appended below without claiming original placement.",
            unplaced.len()
        ));
        if !markdown.ends_with('\n') {
            markdown.push('\n');
        }
        markdown.push_str("\n## Extracted attachments (position unknown)\n\n");
        for (_, asset) in unplaced {
            // Only generated ASCII names enter Markdown, never package paths.
            let filename = asset.path.rsplit('/').next().unwrap_or("attachment");
            markdown.push_str(&format!("- [{filename}]({})\n", asset.path));
        }
    }
    if markdown.trim().is_empty() {
        return Err(failure(
            "Conversion returned no readable Markdown or extractable attachments.",
        ));
    }
    Ok((markdown, store.assets))
}

#[derive(Default)]
struct AssetStore {
    assets: Vec<AssetOutput>,
    by_hash: HashMap<String, usize>,
    referenced: HashSet<usize>,
    total_bytes: usize,
}

impl AssetStore {
    fn insert(
        &mut self,
        bytes: Vec<u8>,
        origin: String,
        media_type: String,
    ) -> Result<usize, Failure> {
        let digest: String =
            Sha256::digest(&bytes).iter().map(|byte| format!("{byte:02x}")).collect();
        if let Some(&index) = self.by_hash.get(&digest) {
            let existing = &mut self.assets[index];
            if !existing.origin.split("; ").any(|part| part == origin) {
                existing.origin.push_str("; ");
                existing.origin.push_str(&origin);
            }
            return Ok(index);
        }
        let total = self.total_bytes.checked_add(bytes.len()).ok_or_else(|| {
            failure("Extracted asset sizes overflowed the local retention budget.")
        })?;
        if total > MAX_ASSET_BYTES {
            return Err(failure("Extracted assets exceed the 128 MiB local retention limit."));
        }
        let index = self.assets.len();
        let extension = asset_extension(&origin, &media_type);
        let path = format!("assets/asset-{:04}-{}.{}", index + 1, &digest[..16], extension);
        self.assets.push(AssetOutput { path, bytes, origin, media_type });
        self.by_hash.insert(digest, index);
        self.total_bytes = total;
        Ok(index)
    }
}

#[derive(Default)]
struct Observed {
    external_images: HashSet<String>,
    relative_links: HashSet<String>,
    unavailable_images: usize,
    merged_cells: usize,
    math: usize,
}

fn rewrite_blocks(
    blocks: &mut [Block],
    asset_ids: &HashMap<usize, usize>,
    store: &mut AssetStore,
    observed: &mut Observed,
) {
    for block in blocks {
        match block {
            Block::Heading { content, .. } | Block::Paragraph(content) => {
                rewrite_inlines(content, asset_ids, store, observed);
            }
            Block::List(list) => {
                for item in &mut list.items {
                    rewrite_blocks(&mut item.blocks, asset_ids, store, observed);
                }
            }
            Block::Table(table) => {
                for row in &mut table.grid {
                    for slot in row {
                        if let CellSlot::Origin(cell) = slot {
                            if cell.col_span > 1 || cell.row_span > 1 {
                                observed.merged_cells += 1;
                            }
                            rewrite_blocks(&mut cell.blocks, asset_ids, store, observed);
                        }
                    }
                }
            }
            Block::BlockQuote(blocks) => rewrite_blocks(blocks, asset_ids, store, observed),
            Block::Math(_) => observed.math += 1,
            Block::CodeBlock { .. } | Block::Rule => {}
        }
    }
}

fn rewrite_inlines(
    inlines: &mut [Inline],
    asset_ids: &HashMap<usize, usize>,
    store: &mut AssetStore,
    observed: &mut Observed,
) {
    for inline in inlines {
        match inline {
            Inline::Link { content, target } => {
                if let LinkTarget::Relative(path) = target {
                    observed.relative_links.insert(path.clone());
                }
                rewrite_inlines(content, asset_ids, store, observed);
            }
            Inline::Math(_) => observed.math += 1,
            Inline::Image { alt, source } => match source {
                ImageSource::Asset(id) => {
                    if let Some(&index) = asset_ids.get(&id.0) {
                        store.referenced.insert(index);
                        let asset = &store.assets[index];
                        if asset.media_type.starts_with("image/") {
                            // The upstream renderer's External branch renders a
                            // URI verbatim, including a relative local asset URI.
                            *source = ImageSource::External(asset.path.clone());
                        } else {
                            let label = if alt.trim().is_empty() {
                                "Embedded attachment".to_string()
                            } else {
                                alt.clone()
                            };
                            *inline = Inline::Link {
                                content: vec![Inline::plain(label)],
                                target: LinkTarget::Relative(asset.path.clone()),
                            };
                        }
                    } else {
                        observed.unavailable_images += 1;
                        *source = ImageSource::Unavailable;
                    }
                }
                ImageSource::External(url) => {
                    observed.external_images.insert(url.clone());
                }
                ImageSource::Unavailable => observed.unavailable_images += 1,
            },
            Inline::Text { .. }
            | Inline::Anchor(_)
            | Inline::NoteRef(_)
            | Inline::LineBreak
            | Inline::Checkbox(_) => {}
        }
    }
}

fn supplement_zip_assets(
    original: &[u8],
    format: Format,
    store: &mut AssetStore,
    warnings: &mut Vec<String>,
) {
    if !matches!(
        format,
        Format::Docx
            | Format::Pptx
            | Format::Excel
            | Format::Odt
            | Format::Ods
            | Format::Odp
            | Format::Epub
    ) || !original.starts_with(b"PK")
    {
        return;
    }
    let mut archive = match zip::ZipArchive::new(Cursor::new(original)) {
        Ok(archive) => archive,
        Err(error) => {
            warnings
                .push(format!("Supplementary package asset scan could not open the ZIP: {error}"));
            return;
        }
    };
    if archive.len() > MAX_ZIP_ENTRIES {
        warnings.push("Supplementary asset scan skipped: ZIP exceeds 100,000 entries.".into());
        return;
    }
    let mut skipped = 0usize;
    let mut scan_bytes = 0usize;
    for index in 0..archive.len() {
        let mut entry = match archive.by_index(index) {
            Ok(entry) => entry,
            Err(_) => {
                skipped += 1;
                continue;
            }
        };
        if entry.is_dir() || !is_asset_part(entry.name()) {
            continue;
        }
        let origin = entry.name().to_string();
        // A total read budget also bounds repeated entries whose bytes will
        // later be deduplicated. Declared ZIP sizes are never trusted alone.
        if entry.size() > MAX_ASSET_BYTES as u64 || scan_bytes >= MAX_ASSET_BYTES {
            skipped += 1;
            continue;
        }
        let allowed = MAX_ASSET_BYTES - scan_bytes;
        let mut bytes = Vec::new();
        let result = entry.by_ref().take(allowed as u64 + 1).read_to_end(&mut bytes);
        scan_bytes = scan_bytes.saturating_add(bytes.len());
        if result.is_err() || bytes.len() > allowed {
            skipped += 1;
            continue;
        }
        let media_type = media_type_for(&origin, "application/octet-stream");
        if store.insert(bytes, origin, media_type).is_err() {
            skipped += 1;
        }
    }
    if skipped > 0 {
        warnings.push(format!(
            "Supplementary ZIP scan could not retain {skipped} entry/entries (unreadable, encrypted, or over the 128 MiB read/retention limit); attachment completeness is not established."
        ));
    }
}

fn is_asset_part(name: &str) -> bool {
    let lower = name.replace('\\', "/").to_ascii_lowercase();
    let parts: Vec<_> = lower.split('/').collect();
    let in_resource_directory = parts.iter().any(|part| {
        matches!(*part, "media" | "pictures" | "embeddings" | "attachments" | "objectreplacements")
    });
    let extension = lower.rsplit_once('.').map(|(_, extension)| extension).unwrap_or("");
    in_resource_directory
        || matches!(
            extension,
            "png"
                | "jpg"
                | "jpeg"
                | "gif"
                | "bmp"
                | "tif"
                | "tiff"
                | "svg"
                | "emf"
                | "wmf"
                | "webp"
                | "avif"
                | "heic"
                | "heif"
                | "ico"
        )
}

fn media_type_for(origin: &str, supplied: &str) -> String {
    if !supplied.is_empty() && supplied != "application/octet-stream" {
        return supplied.to_string();
    }
    let extension = origin
        .rsplit_once('.')
        .map(|(_, extension)| extension.to_ascii_lowercase())
        .unwrap_or_default();
    match extension.as_str() {
        "png" => "image/png",
        "jpg" | "jpeg" => "image/jpeg",
        "gif" => "image/gif",
        "bmp" => "image/bmp",
        "tif" | "tiff" => "image/tiff",
        "svg" => "image/svg+xml",
        "emf" => "image/emf",
        "wmf" => "image/wmf",
        "webp" => "image/webp",
        "avif" => "image/avif",
        "heic" | "heif" => "image/heif",
        "ico" => "image/x-icon",
        "pdf" => "application/pdf",
        "mp3" => "audio/mpeg",
        "wav" => "audio/wav",
        "ogg" => "audio/ogg",
        "mp4" => "video/mp4",
        "webm" => "video/webm",
        _ => "application/octet-stream",
    }
    .into()
}

fn asset_extension(origin: &str, media_type: &str) -> String {
    let known = match media_type {
        "image/png" => Some("png"),
        "image/jpeg" => Some("jpg"),
        "image/gif" => Some("gif"),
        "image/bmp" => Some("bmp"),
        "image/tiff" => Some("tiff"),
        "image/svg+xml" => Some("svg"),
        "image/emf" | "image/x-emf" => Some("emf"),
        "image/wmf" | "image/x-wmf" => Some("wmf"),
        "image/webp" => Some("webp"),
        "image/avif" => Some("avif"),
        "image/heif" | "image/heic" => Some("heif"),
        "image/x-icon" => Some("ico"),
        "application/pdf" => Some("pdf"),
        "audio/mpeg" => Some("mp3"),
        "audio/wav" => Some("wav"),
        "audio/ogg" => Some("ogg"),
        "video/mp4" => Some("mp4"),
        "video/webm" => Some("webm"),
        _ => None,
    };
    if let Some(extension) = known {
        return extension.into();
    }
    let extension = origin
        .rsplit_once('.')
        .map(|(_, extension)| extension.to_ascii_lowercase())
        .unwrap_or_default();
    match extension.as_str() {
        "doc" | "docx" | "docm" | "ppt" | "pptx" | "pptm" | "xls" | "xlsx" | "xlsm" | "xlsb"
        | "rtf" | "odt" | "ods" | "odp" | "epub" | "zip" | "txt" | "csv" | "bin" | "dat"
        | "xml" | "json" | "eps" => extension,
        _ => "bin".into(),
    }
}

fn add_format_warnings(format: Format, warnings: &mut Vec<String>) {
    match format {
        Format::Excel | Format::Ods => warnings.push(
            "Spreadsheet conversion uses stored cell values and does not recalculate formulas; review cached values, merged cells, charts, and drawing placement."
                .into(),
        ),
        Format::Csv => warnings.push(
            "CSV encoding, delimiter, and header rows are inferred; verify them against the original."
                .into(),
        ),
        Format::Ppt | Format::Pptx | Format::Odp => warnings.push(
            "Presentation text and available notes are extracted; slide layout, animation, and reading order require review."
                .into(),
        ),
        Format::Rtf => warnings.push(
            "RTF exposes supported pictures; embedded object payloads and unsupported picture formats may be absent from the parser model."
                .into(),
        ),
        _ => {}
    }
    if matches!(format, Format::Odt | Format::Ods | Format::Odp) {
        warnings.push(
            "OpenDocument embedded objects other than formulas are not fully interpreted; retained package resources preserve bytes only."
                .into(),
        );
    }
    if format == Format::Excel {
        warnings.push(
            "Excel pictures are not positioned by the parser; ZIP media are recovered separately when present, and legacy XLS object extraction is limited."
                .into(),
        );
    }
}

fn format_name(format: Format) -> &'static str {
    match format {
        Format::Doc => "doc",
        Format::Docx => "docx",
        Format::Odt => "odt",
        Format::Pdf => "pdf",
        Format::Ppt => "ppt",
        Format::Pptx => "pptx",
        Format::Rtf => "rtf",
        Format::Epub => "epub",
        Format::Excel => "excel",
        Format::Ods => "ods",
        Format::Odp => "odp",
        Format::Csv => "csv",
    }
}

fn failure(message: impl Into<String>) -> Failure {
    Failure { kind: "error".into(), message: message.into(), pages: Vec::new() }
}

fn from_anydoc(error: ConvertError) -> Failure {
    match error {
        ConvertError::NeedsOcr { pages, page_count } => Failure {
            kind: "needs_ocr".into(),
            message: format!(
                "PDF pages {} of {page_count} require OCR; no partial Markdown was returned and no OCR service was contacted.",
                pages.iter().map(u32::to_string).collect::<Vec<_>>().join(", ")
            ),
            pages: pages.into_iter().map(|page| page as usize).collect(),
        },
        ConvertError::Unsupported(message) => {
            Failure { kind: "unsupported".into(), message, pages: Vec::new() }
        }
        other => failure(other.to_string()),
    }
}

struct ParserLogger;
static PARSER_LOGGER: ParserLogger = ParserLogger;
static LOGGER_INSTALLED: OnceLock<bool> = OnceLock::new();

#[derive(Default)]
struct CapturedLogs {
    messages: Vec<String>,
    skipped: usize,
}

thread_local! {
    static ACTIVE_LOGS: RefCell<Option<CapturedLogs>> = const { RefCell::new(None) };
}

impl log::Log for ParserLogger {
    fn enabled(&self, metadata: &log::Metadata<'_>) -> bool {
        metadata.level() <= log::Level::Debug
    }

    fn log(&self, record: &log::Record<'_>) {
        if !self.enabled(record.metadata())
            || !(record.target().starts_with("anydoc")
                || record.target().starts_with("pdf_inspector"))
        {
            return;
        }
        ACTIVE_LOGS.with(|active| {
            let Ok(mut active) = active.try_borrow_mut() else {
                return;
            };
            let Some(captured) = active.as_mut() else {
                return;
            };
            let message = record.args().to_string();
            let lower = message.to_ascii_lowercase();
            if record.level() > log::Level::Warn
                && ![
                    "skip",
                    "recover",
                    "unsupported",
                    "unreadable",
                    "missing",
                    "unresolved",
                    "garbled",
                    "encoding",
                    "dropp",
                    "duplicate",
                ]
                .iter()
                .any(|keyword| lower.contains(keyword))
            {
                return;
            }
            if captured.messages.len() < MAX_CAPTURED_LOGS {
                captured.messages.push(format!(
                    "Upstream {} ({}): {message}",
                    record.level(),
                    record.target()
                ));
            } else {
                captured.skipped += 1;
            }
        });
    }

    fn flush(&self) {}
}

struct LogGuard {
    previous: Option<CapturedLogs>,
    finished: bool,
}

impl LogGuard {
    fn new() -> Self {
        Self {
            previous: ACTIVE_LOGS.with(|active| active.replace(Some(CapturedLogs::default()))),
            finished: false,
        }
    }

    fn finish(mut self) -> Vec<String> {
        let mut captured =
            ACTIVE_LOGS.with(|active| active.replace(self.previous.take())).unwrap_or_default();
        self.finished = true;
        if captured.skipped > 0 {
            captured.messages.push(format!(
                "{} additional upstream recovery log(s) were omitted after the 128-message capture limit.",
                captured.skipped
            ));
        }
        captured.messages
    }
}

impl Drop for LogGuard {
    fn drop(&mut self) {
        if !self.finished {
            ACTIVE_LOGS.with(|active| active.replace(self.previous.take()));
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::model::{
        Asset, AssetId, Cell, List, ListItem, MarkerKind, Note, NoteKind, Table, TableKind,
    };
    use std::io::Write;

    #[test]
    fn rtf_content_wins_over_mislabeled_extension() {
        let converted = convert(b"{\\rtf1\\ansi A {\\b bold} paragraph.}", "docx").unwrap();
        assert_eq!(converted.format, "rtf");
        assert!(converted.markdown.contains("A **bold** paragraph."));
    }

    #[test]
    fn invalid_document_is_an_explicit_failure() {
        let failed = convert(b"not a ZIP or a Word document", "docx").unwrap_err();
        assert_eq!(failed.kind, "error");
        assert!(!failed.message.is_empty());
    }

    #[test]
    fn rtf_embedded_image_is_localized_at_its_text_position() {
        let converted =
            convert(b"{\\rtf1\\ansi before {\\pict\\pngblip 89504e470d0a1a0a0102} after}", "rtf")
                .unwrap();
        assert_eq!(converted.assets.len(), 1);
        let asset = &converted.assets[0];
        assert_eq!(asset.bytes, b"\x89PNG\r\n\x1a\n\x01\x02");
        assert!(asset.path.starts_with("assets/asset-0001-"));
        assert!(asset.path.ends_with(".png"));
        let before = converted.markdown.find("before").unwrap();
        let image = converted.markdown.find(&asset.path).unwrap();
        let after = converted.markdown.find("after").unwrap();
        assert!(before < image && image < after);
        assert!(converted.markdown.contains("![]("));
    }

    #[test]
    fn nested_images_and_objects_keep_model_positions_and_safe_names() {
        let image =
            || Inline::Image { alt: "chart".into(), source: ImageSource::Asset(AssetId(0)) };
        let mut document = Document {
            blocks: vec![
                Block::Paragraph(vec![Inline::NoteRef("n".into())]),
                Block::List(List {
                    marker: MarkerKind::Bullet,
                    start: 1,
                    items: vec![ListItem {
                        blocks: vec![Block::BlockQuote(vec![Block::Table(Table::from_rows(
                            vec![vec![Cell::from_inlines(vec![Inline::Link {
                                content: vec![image()],
                                target: LinkTarget::External("https://example.com".into()),
                            }])]],
                            0,
                            TableKind::Data,
                        ))])],
                        marker_label: None,
                    }],
                }),
                Block::Paragraph(vec![Inline::Image {
                    alt: "Original workbook".into(),
                    source: ImageSource::Asset(AssetId(1)),
                }]),
            ],
            notes: vec![Note {
                id: "n".into(),
                kind: NoteKind::Footnote,
                blocks: vec![Block::Paragraph(vec![image()])],
            }],
            assets: vec![
                Asset {
                    id: AssetId(0),
                    media_type: "image/png".into(),
                    origin_part: "../../escape.png".into(),
                    bytes: vec![1, 2, 3],
                },
                Asset {
                    id: AssetId(1),
                    media_type: "application/vnd.ms-ole-object".into(),
                    origin_part: "C:/bad/../../payload.bin".into(),
                    bytes: vec![4, 5, 6],
                },
            ],
        };
        document.blocks.push(Block::Paragraph(vec![Inline::plain("end marker")]));
        let mut warnings = Vec::new();
        let (markdown, assets) =
            render_document(document, b"", Format::Docx, &mut warnings).unwrap();
        assert_eq!(assets.len(), 2);
        assert_eq!(markdown.matches(&assets[0].path).count(), 2);
        assert!(markdown.contains(&format!("[Original workbook]({})", assets[1].path)));
        assert!(markdown.find(&assets[1].path).unwrap() < markdown.find("end marker").unwrap());
        assert!(!markdown.contains("../../"));
        assert!(assets.iter().all(|asset| {
            asset.path.starts_with("assets/")
                && !asset.path.contains("..")
                && !asset.path.contains('\\')
        }));
    }

    #[test]
    fn supplementary_zip_assets_are_deduplicated_and_unplaced() {
        let mut writer = zip::ZipWriter::new(Cursor::new(Vec::new()));
        for name in ["xl/media/image1.png", "../../outside.png", "xl/embeddings/object1.bin"] {
            writer.start_file(name, zip::write::SimpleFileOptions::default()).unwrap();
            writer
                .write_all(if name.ends_with(".png") { b"same-image" } else { b"object" })
                .unwrap();
        }
        let package = writer.finish().unwrap().into_inner();
        let document = Document {
            blocks: vec![Block::Paragraph(vec![Inline::plain("Workbook")])],
            ..Default::default()
        };
        let mut warnings = Vec::new();
        let (markdown, assets) =
            render_document(document, &package, Format::Excel, &mut warnings).unwrap();
        assert_eq!(assets.len(), 2);
        assert!(assets[0].origin.contains("xl/media/image1.png"));
        assert!(assets[0].origin.contains("../../outside.png"));
        assert!(markdown.contains("Extracted attachments (position unknown)"));
        assert!(warnings.iter().any(|warning| warning.contains("no modeled position")));
        assert!(!markdown.contains("outside.png"));
    }

    #[test]
    fn needs_ocr_keeps_one_based_page_numbers() {
        let failed = from_anydoc(ConvertError::NeedsOcr { pages: vec![2, 5], page_count: 7 });
        assert_eq!(failed.kind, "needs_ocr");
        assert_eq!(failed.pages, vec![2, 5]);
        assert!(failed.message.contains("no partial Markdown"));
    }
}
