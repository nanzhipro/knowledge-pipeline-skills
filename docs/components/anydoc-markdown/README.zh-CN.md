> Historical component snapshot. Current installation and release: [repository README](../../../README.md). Old repository URLs below are historical; use the migration mapping and portable backup.

# AnyDoc Markdown Skill

使用 **Rust anydoc 0.2.4**，把单个文档或目录批量转换为可追溯的本地 Markdown。支持 Windows 与 macOS，不依赖 Python/Node 解析绑定、云端 OCR、API Key、OKF 或 LLM Wiki。

[English](README.md) · [Skill 入口](anydoc-markdown/SKILL.md) · [验证记录](docs/validation.md)

## 安装与使用

```sh
npx skills add nanzhipro/anydoc-markdown-skill@anydoc-markdown
```

也可以把完整 `anydoc-markdown/` 目录复制到 Agent 的技能目录。随后告诉 Agent：

> 使用 $anydoc-markdown，把指定文件或目录转换到一个新的输出目录，保留原件和附件，说明所有未完整提取的内容。

安装 Rust/Cargo 1.88+ 后，也能直接运行；以下命令兼容 PowerShell 和 macOS shell：

```text
cargo run --locked --release --manifest-path anydoc-markdown/scripts/anydoc-md/Cargo.toml -- convert "输入文件或目录" --output "新的输出目录"
cargo run --locked --release --manifest-path anydoc-markdown/scripts/anydoc-md/Cargo.toml -- verify "新的输出目录"
```

首次构建需要联网下载依赖；转换本身完全本地执行。Windows 可能需要 Microsoft C++ Build Tools，macOS 可能需要 Xcode Command Line Tools。

## 每份文件输出什么

```text
输出目录/
  index.md
  manifest.json
  documents/doc-原文件名--路径哈希/
    document.md
    source/original.原扩展名
    assets/                 # 实际可提取的资产
    report.json
```

目录递归扫描，同名或大小写相近的文件通过路径哈希区分；已有输出不覆盖，输入与输出目录不能重叠。默认跳过隐藏项与符号链接，`--include-hidden` 可包含隐藏项。每个文件默认限 128 MiB，可用 `--max-file-mb` 调整。无法读取或超限的文件明确记录没有复制原件。

支持 DOC、DOCX/DOCM、PPT/PPS/POT、PPTX/PPTM/PPSX/PPSM、XLS/XLSX/XLSM/XLSB、ODT、ODS、ODP、RTF、EPUB、CSV、PDF。内容签名优先于扩展名；不支持的输入也会留下明确状态页。

可读提取与需要核对的提取分别标记 converted/partial；扫描 PDF 标记 needs_ocr；其他失败标记 unsupported/error。批次退出码 2 表示需要处理，不表示已生成的成果丢失。verify 检查原件、Markdown 与附件的字节摘要，不验证内容含义或视觉无损。

## 能力边界

保存原件、提取正文、保留可用资产是三个不同结果。PDF 当前接口不提供内嵌图像导出；扫描 PDF 不自动 OCR 或上传。复杂表格、公式缓存、幻灯片布局、动画、部分旧版对象需要对照原件。已知包内媒体会补充保留，位置未知时放附件附录，不伪造定位。外部图片链接不下载。[详细限制](anydoc-markdown/references/formats-and-limits.md)。

这里完成文档提取，不做总结、翻译、知识编译或事实认证。最终 Markdown 可供 Obsidian、普通阅读器和后续 Wiki Skill 使用。

## 质量与过程

以官方公开夹具补齐 14 种扩展名，并从 Downloads 搜集真实 DOCX、CSV、PDF、EPUB 做私有验证；公开仓库不含这些私人文档及转换正文。Plugin Eval 的评估、优化依据、原生双平台 CI 和真实测试范围见[验证记录](docs/validation.md)与[过程记录](docs/development-log.md)。静态评分不等于转换正确率。

采用 [MIT 协议](LICENSE)，上游解析器、渲染器和夹具保留各自许可声明。
