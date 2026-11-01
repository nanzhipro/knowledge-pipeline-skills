# Obsidian LLM Wiki Skill

[![Native Python checks](https://github.com/nanzhipro/obsidian-llm-wiki-skill/actions/workflows/ci.yml/badge.svg)](https://github.com/nanzhipro/obsidian-llm-wiki-skill/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

把 [anydoc-markdown](https://github.com/nanzhipro/anydoc-markdown-skill) 的转换结果，编译成可持续维护的 Obsidian 本地知识库。基于作者自己的 [Karpathy-llm-wiki-bootstrap-skill](https://github.com/nanzhipro/Karpathy-llm-wiki-bootstrap-skill) 演进，保留原始证据、概念复用、矛盾处理和长期维护工作流，**不引入 OKF**。

```mermaid
flowchart LR
  A[多格式文档 / 目录] --> B[anydoc-markdown · Rust anydoc]
  B --> C[校验 manifest / report / Markdown / 原件 / 附件]
  C --> D[隔离工作区 · raw 不可变快照]
  D --> E[Agent 逐份阅读 · 来源摘要 · 概念 / 关系 / 矛盾 / 概览]
  E --> F[prepare · 结构检查 · 完整 diff]
  F --> G[apply · 哈希冲突检测 · 恢复日志]
  G --> H[Obsidian 本地库]
  H --> I[只读查询 / 巡检 / 新批次维护]
  I --> D
```

这是一个 Agent Skill，配套 Python 工具管理文件、来源身份和发布过程。**知识内容由 Agent 阅读证据后编写**；单独运行导入命令只会生成待编译来源卡片。结构检查与 Plugin Eval 分数均不证明事实正确或模型理解正确。

## 安装

需要支持 Agent Skills 的编程 Agent、Python **3.10+**，以及 `PyYAML==6.0.3`。运行知识库不需要 Rust、Obsidian 插件、模型 API 密钥或其他云服务；第一个 Skill 的转换阶段独立运行 Rust anydoc。

```bash
gh repo clone nanzhipro/obsidian-llm-wiki-skill
```

把仓库中的 **`obsidian-llm-wiki/` 整个目录**放入项目的 `.agents/skills/`。也可以使用对应 Agent 的技能安装机制，选择这个子目录。安装后让 Agent 使用 `$obsidian-llm-wiki`。

macOS / Linux：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r obsidian-llm-wiki/requirements.txt
.venv/bin/python obsidian-llm-wiki/scripts/wiki.py --help
```

Windows PowerShell：

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r .\obsidian-llm-wiki\requirements.txt
.\.venv\Scripts\python.exe .\obsidian-llm-wiki\scripts\wiki.py --help
```

后续示例的 `python` 指上面的虚拟环境解释器。输入、工作区、知识库使用彼此独立的路径。

## 使用

对 Agent 说：

> 使用 `$obsidian-llm-wiki`，把 `/path/to/anydoc-output` 导入 `/path/to/my-vault`，collection 为 `research-library`。新建中文知识库；逐份阅读来源，维护概念、分歧和概览，检查 diff 后发布。

已有库维护：

> 使用 `$obsidian-llm-wiki`，导入同一 collection 的新批次。比较来源版本，保留旧证据与尚未解决的矛盾；保留我手工编辑的页面。

查询：

> 在这个库中查询……，打开命中页面和原始上下文，给出来源引用；只读，不归档答案。

也可手动运行文件管线：

```bash
python obsidian-llm-wiki/scripts/wiki.py init --vault ../my-vault --name 知识库 --domain 研究资料 --language zh-CN
python obsidian-llm-wiki/scripts/wiki.py workspace --vault ../my-vault --output ../work-001
python obsidian-llm-wiki/scripts/wiki.py import --workspace ../work-001 --batch ../anydoc-output --collection research-library
```

此时由 Agent 在工作区读取完整来源、编写摘要与知识页，移除实际完成的来源卡 `semantic-pending` 标记，再准备发布：

```bash
python obsidian-llm-wiki/scripts/wiki.py prepare --vault ../my-vault --workspace ../work-001 --reason '编译本批资料并保留分歧' --operation ingest --compiled s-SOURCE_ID
python obsidian-llm-wiki/scripts/wiki.py diff --vault ../my-vault --proposal p-PROPOSAL_ID
python obsidian-llm-wiki/scripts/wiki.py apply --vault ../my-vault --proposal p-PROPOSAL_ID --reviewed DIFF_REVIEW_HASH
python obsidian-llm-wiki/scripts/wiki.py lint --vault ../my-vault
python obsidian-llm-wiki/scripts/wiki.py search --vault ../my-vault --query 知识管理
```

`--compiled` 可重复；不传时来源保留待编译状态。`--reviewed` 使用 `diff` 返回的 `review_hash`，绑定本次候选内容，不替代人的授权或 Agent 的证据检查。只要求“准备”的任务停在 diff，已有完整写入授权的任务可以直接完成发布。详细流程见 [工作流参考](obsidian-llm-wiki/references/workflows.md)。

打开 Obsidian，选择 **Open folder as vault** 并打开 `my-vault` 即可。初始化不会更改 `.obsidian` 设置，也不会向已有笔记目录强行套用结构。

## 输入与输出

输入是第一个 Skill 完整输出目录，协议为 `anydoc-markdown/1`，包含 `manifest.json`、`index.md` 及各文件 bundle。消费者校验清单、状态、大小、哈希、路径、Markdown 元数据、原件和附件；拒绝未知协议、篡改、路径越界、重复身份及符号链接。它不会把目录中任意 Markdown 都当作资料。

| 解析状态 | 处理 |
| --- | --- |
| `converted` | 创建来源快照与待编译来源卡；仍需阅读和核对 |
| `partial` | 可用内容可进入来源卡；保留解析限制，不能据缺失内容作结论 |
| `needs_ocr` / `error` / `unsupported` | 记录诊断，不创建可支持知识结论的来源卡 |
| 批次遍历有遗漏 | 明确警告发现不完整；不声称已覆盖整个集合 |

```text
my-vault/
├── SCHEMA.md                         # 知识库操作约定
├── AGENTS.md                         # 指向 SCHEMA 的薄入口
├── .llm-wiki-bootstrap/EXTEND.md      # 项目偏好，供 Agent 读取
├── raw/<source-id>/<snapshot-id>/    # 完整且不可变的可读转换 bundle
│   ├── document.md
│   ├── report.json
│   ├── source/original.ext
│   └── assets/                       # 第一 Skill 实际提取到的附件
├── wiki/
│   ├── sources/                      # 来源摘要与精确原文链接
│   ├── entities/ concepts/ comparisons/ synthesis/
│   ├── questions/ decisions/
│   ├── index.md                      # 自动导航
│   ├── concept-table.md              # 从概念元数据生成
│   ├── overview.md                   # Agent 维护的整体理解
│   └── log.md                        # 追加操作记录
└── .llm-wiki/                        # 登记、原始批次收据、提案、恢复日志
```

普通知识页使用标准 Markdown、相对链接与扁平 YAML 属性。原始解析 Markdown 保持原字节及附件位置。相同原文件字节共享来源身份；改名不算独立佐证。相同 collection 与输入相对路径只表示可能的版本关系，Agent 仍需比较时间与适用范围。参见 [协议与维护设计](docs/design.md)。

## 验证与边界

公开测试夹具由第一个 Skill 实际转换的合成资料组成，包含图片、表格、同名文件、版本变化、指令注入文本及受控解析失败。运行：

```bash
python -m pip install -r requirements-dev.txt
python -m unittest discover -s obsidian-llm-wiki/tests -v
python -m black --check obsidian-llm-wiki/scripts obsidian-llm-wiki/tests
```

[验证记录](docs/validation.md)、[Plugin Eval 过程](docs/evaluation/README.md) 与 [开发记录](docs/development-log.md) 区分静态评分、结构测试、Agent 语义演练及平台执行。测试资料和证据可公开，用户 Downloads 私有材料不进入仓库。

多文件发布不是文件系统事务。工具锁只约束本工具，外部编辑器仍可能同时写入；发布窗口应停止手工编辑。遇冲突停止，已开始的发布保留恢复日志。`recover --vault ... --rollback` 只回滚已知前后字节，遇未知编辑拒绝覆盖；陈旧锁确认原进程已停后才能 `--clear-lock`。工具不会保证任意断电场景或所有并发写入都自动恢复。

默认查询只读，使用 Unicode 文本搜索。可显式 `index-search --vault ...` 建立本地 SQLite FTS5/BM25 缓存，`search --bm25` 会检查新增、修改、删除，过期或未命中时回退文本搜索。缓存不是知识来源；中文分词、引文支持和真实语义仍需 Agent 检查。没有运行 Obsidian GUI 自动化测试。

## 来源、贡献与许可

新 Skill 基于作者拥有的原始项目固定提交演进；没有打包原仓库中的第三方文章、封面或示例资料。具体来源、依赖与夹具许可见 [NOTICE](NOTICE.md)。欢迎提交可复现问题或 PR；请附匿名最小输入、平台、Python 版本和错误 JSON，避免上传私人资料。

本仓库新代码与技能文档按 [MIT](LICENSE) 发布。外部依赖、测试素材保留各自许可，MIT 不改变用户输入文档的权利归属。
