# Native Windows修复后的最终静态复核

实际 Plugin Eval **95/100，A，risk=medium**；官方 `skills-ref` 参考格式校验通过。原始评分JSON、Markdown、improvement brief、官方验证JSON均保存在本目录。之前的 `final-result/` 和顶层 `final-result.json` 完整保留为native修复前记录，未覆盖。

重新复制全部59文件，仅排除 `target/.git/.work`，快照在 `../release-final-source/anydoc-markdown/`。与native修复前相比，仅 `scripts/anydoc-md/Cargo.toml`、`Cargo.lock`、`src/lib.rs` 内容哈希改变；无文件被移除。

完整逐文件大小/哈希见 `source-inventory.json`（顶层副本 `../release-final-source-inventory.json`）。有序path+NUL+文件SHA+LF的树SHA-256：

```text
e9056d50ba85471bd32920c76c9af3217f9362d0120d31d9180613d87b6632cf
```

分数仍只扣fixture README启发式4.5分和无覆盖率文件info0.25分；预算trigger31/invoke741/deferred8501估算tokens，均moderate。与前次结果的原始对比见 `compare-pre-native.json`。

本轮依任务仅重跑静态评估/格式验证/文件指纹，未重跑forward，也未独立执行Windows CI。Plugin Eval不分析Rust代码，因此该95分不构成MoveFileExW行为或Windows原子发布正确性的证明；应以保留的回归测试和原生CI结果为行为证据。
