# anydoc-markdown 最终独立评估

**最终完整干净源 Plugin Eval：95/100，A，risk=medium，超过90；官方 Agent Skills参考校验通过。** 原始报告 `final-result.json` / `final-result.md`；改进brief `final-improvement-brief.json`；官方结果 `final-agent-skills-validation.json`。没有调整评估器、删除必要内容或伪造覆盖率。

## 已核验的源快照

目标源：`/Users/nanzhi/Downloads/知本设计研究/anydoc-markdown-skill/anydoc-markdown`。

完整59文件复制到 `final-source/anydoc-markdown/`，仅排除生成目录 `target/.git/.work`，保留全部Rust代码、测试、夹具、许可和参考。逐文件清单及SHA-256在 `final-source-inventory.json`；树哈希（按有序path+NUL+文件SHA+LF计算）：

```text
7d2381f98b42441d4477142fd87a4af71c1f0ab63f40ee4a1c42963f880e9061
```

最终forward结束后再次比较，目标源全部59文件与该快照无哈希差异。

## 分数与边界

阶段轨迹：早期不完整before95 → 含编译缓存的开发目录91 → 前次完整干净源95 → 修复forward发现后最终完整干净源95。初始description触发warning已解决；最终两项扣分是fixture README启发式warning4.5及无覆盖率文件info0.25。`tests/fixtures/README.md`解释语料和选取规则，保留有益，不建议为分数删除。

最终静态估算 trigger31/invoke741/deferred8468 tokens，均moderate。before→最终对比保存在 `final-compare.json/.md`。该工具只对Python/TypeScript做启发式代码扫描，未检查Rust质量，亦未执行测试；无模型实际usage。95不是转换正确率、无损率或跨平台验证结果。官方参考校验也仅验证技能格式/命名。

## 修复后再次实际forward

复用 `/tmp/anydoc-eval-setup/forward-cargo-target`，按Skill运行锁定release Cargo入口，将 `tests/fixtures/valid` 转换到全新 `forward-final-output/`。Cargo只重新编译本crate，耗时13.48秒，未全量重编依赖。原始进程输出/退出码见 `forward-final-convert.json`。

- 转换退出2；14个文档输出14个bundle，1 converted、13 partial；无error、unsupported、needs_ocr、遍历错误或排除项。
- **DOC、DOCX、ODT报告均实际出现新警告**：各1条源相对超链接被保留，未复制/重定位目标，可能无法在输出包中解析；三者保持partial。此前的未专门标示风险现已显式记录。
- 随后按Skill运行verify，退出0，`ok=true`、`documents=14`、`attention_required=13`、`issues=[]`、`semantic_fidelity_checked=false`。与更新后的说明一致：核验通过不取消partial状态。
- 原始verify stdout/stderr见 `forward-final-verify.json`；全部逐文档warning、资产数、源码快照比较和二进制哈希见 `forward-final-inspection.json`。

最终二进制SHA-256：`9dc62e3c02cc40f48d40743960c36acfa4dc6922991c0e7ad73672ee7c5f292c`。

本轮独立重跑范围是14个公开有效夹具及新超链接警告，不代替主代理新增的hidden flags、原子发布、失败格式检测回归测试，也不代替后续Windows/macOS原生CI。前次已完成代表Markdown和图片的人工查看；最终检查集中于本轮修复的报告行为。
