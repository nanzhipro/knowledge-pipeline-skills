use anydoc_md::{Options, convert_batch, verify};
use clap::{Parser, Subcommand};
use std::path::PathBuf;
use std::process::ExitCode;

#[derive(Parser)]
#[command(version, about = "Local document-to-Markdown bundles using Rust anydoc 0.2.4")]
struct Cli {
    #[command(subcommand)]
    command: Command,
}

#[derive(Subcommand)]
enum Command {
    /// Recursively convert a file/directory; never overwrite existing output.
    Convert {
        input: PathBuf,
        #[arg(short, long)]
        output: PathBuf,
        #[arg(long)]
        include_hidden: bool,
        /// Maximum input size per file in MiB; oversized files get an error report.
        #[arg(long, default_value_t = 128, value_parser = clap::value_parser!(u64).range(1..=4096))]
        max_file_mb: u64,
    },
    /// Verify recorded source, Markdown, and asset hashes without changing output.
    Verify { output: PathBuf },
    /// List supported parser families and limitations.
    Formats,
}

fn run(cli: Cli) -> Result<u8, Box<dyn std::error::Error>> {
    match cli.command {
        Command::Convert { input, output, include_hidden, max_file_mb } => {
            let manifest = convert_batch(
                &input,
                &output,
                &Options { include_hidden, max_file_bytes: max_file_mb * 1024 * 1024 },
            )?;
            println!("{}", serde_json::to_string_pretty(&manifest)?);
            Ok(
                if manifest.entries.iter().all(|e| e.status == "converted")
                    && manifest.traversal_errors.is_empty()
                {
                    0
                } else {
                    2
                },
            )
        }
        Command::Verify { output } => {
            let result = verify(&output)?;
            println!("{}", serde_json::to_string_pretty(&result)?);
            Ok(if !result.ok { 2 } else { 0 })
        }
        Command::Formats => {
            println!(
                "{}",
                serde_json::json!({"anydoc_version":anydoc_md::ANYDOC_VERSION,"families":["doc","docx/docm","ppt/pps/pot","pptx/pptm/ppsx/ppsm","xls/xlsx/xlsm/xlsb","odt","ods","odp","rtf","epub","csv","pdf"],"ocr":false,"network_during_conversion":false,"fidelity":"Readable extraction; original preserved; see per-file warnings"})
            );
            Ok(0)
        }
    }
}

fn main() -> ExitCode {
    match run(Cli::parse()) {
        Ok(code) => ExitCode::from(code),
        Err(err) => {
            eprintln!("{}", serde_json::json!({"error":err.to_string()}));
            ExitCode::from(1)
        }
    }
}
