//! Native cross-platform tests against attributed public anydoc fixtures.
use anydoc_md::{Options, convert_batch, sha256, verify};
use std::fs;
use std::path::Path;

#[test]
fn all_public_parser_families_and_negative_cases() {
    let fixture_root = Path::new(env!("CARGO_MANIFEST_DIR")).join("tests/fixtures");
    let sources: serde_json::Value =
        serde_json::from_slice(&fs::read(fixture_root.join("SOURCES.json")).unwrap()).unwrap();
    let fixtures = sources["fixtures"].as_array().unwrap();
    assert!(fixtures.len() >= 18);
    let temp = tempfile::tempdir().unwrap();
    for (index, fixture) in fixtures.iter().enumerate() {
        let input = fixture_root.join(fixture["path"].as_str().unwrap());
        assert_eq!(sha256(&fs::read(&input).unwrap()), fixture["sha256"].as_str().unwrap());
        let output = temp.path().join(format!("case-{index}"));
        let manifest = convert_batch(&input, &output, &Options::default()).unwrap();
        assert_eq!(manifest.entries.len(), 1);
        let entry = &manifest.entries[0];
        let expected = fixture["expected_status"].as_str().unwrap();
        if expected == "ok" {
            assert!(
                matches!(entry.status.as_str(), "converted" | "partial"),
                "{}: {}",
                input.display(),
                entry.status
            );
            let markdown =
                fs::read_to_string(output.join(&entry.bundle).join("document.md")).unwrap();
            assert!(markdown.starts_with("---\n"));
            assert!(markdown.contains("source_sha256:"));
            assert!(!markdown.contains("No document content was extracted."));
        } else if expected == "needs_ocr" {
            assert_eq!(entry.status, "needs_ocr");
            let report: serde_json::Value = serde_json::from_slice(
                &fs::read(output.join(&entry.bundle).join("report.json")).unwrap(),
            )
            .unwrap();
            assert!(!report["ocr_pages"].as_array().unwrap().is_empty());
        } else {
            assert!(
                matches!(entry.status.as_str(), "error" | "unsupported"),
                "{}: {}",
                input.display(),
                entry.status
            );
        }
        let verified = verify(&output).unwrap();
        assert!(verified.ok, "{:?}", verified.issues);
    }
}

#[test]
fn cli_converts_nested_input_and_refuses_existing_output() {
    let temp = tempfile::tempdir().unwrap();
    let input = temp.path().join("input");
    fs::create_dir_all(input.join("nested")).unwrap();
    fs::write(input.join("nested/sample.csv"), "key,value\na,1\n").unwrap();
    let output = temp.path().join("output");
    let binary = env!("CARGO_BIN_EXE_anydoc-md");
    let converted = std::process::Command::new(binary)
        .args(["convert"])
        .arg(&input)
        .arg("--output")
        .arg(&output)
        .output()
        .unwrap();
    assert!(matches!(converted.status.code(), Some(0 | 2)));
    let result: serde_json::Value = serde_json::from_slice(&converted.stdout).unwrap();
    assert_eq!(result["entries"][0]["source_relative_path"], "nested/sample.csv");
    let verified = std::process::Command::new(binary).arg("verify").arg(&output).output().unwrap();
    assert!(verified.status.success());
    let repeated = std::process::Command::new(binary)
        .arg("convert")
        .arg(&input)
        .arg("--output")
        .arg(&output)
        .output()
        .unwrap();
    assert_eq!(repeated.status.code(), Some(1));
}
