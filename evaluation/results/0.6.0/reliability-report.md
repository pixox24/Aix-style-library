# 0.6.0 本地发布与可靠性验证

验证日期：2026-10-01。范围为当前 160 个 active 风格、160 个缩略图和各风格当前证据指向的 960 个样例。以下是确定性检查结果，不是正式质量验收声明。

| 检查 | 结果 |
|---|---|
| `python -m unittest discover -s tests -v` | 78 项通过，128.352 秒 |
| `validate --scope all` | 160 个风格、160 个资源通过；索引一致 |
| `validate --scope release --evidence-root evaluation` | 960 个样例通过；`release_profile=preview` |
| 正式验收标志 | `formal_evidence_checked=false`，警告 `PREVIEW_ONLY` |
| 0.5.0 基线兼容 | 通过：旧 ID 保留，版本与同版内容未发生不允许的变化 |
| 0.6.0 发布打包 | 通过：staging 校验、ZIP 解包后发布校验、get/search/prepare 冒烟 |

库索引 `source_digest`：

```text
49bff7aee4b8dfbdc0ae4c5ea3863eeda49bae87f0b367c129207916bdd3ecd5
```

运行包 SHA-256：

```text
8b86c73877eb58a5beced6910ad4891070925fc5d0be3e5121b63d09c804d10e
```

产物：[aix-style-library-0.6.0.zip](../../../releases/aix-style-library-0.6.0.zip) 与 [校验文件](../../../releases/aix-style-library-0.6.0.zip.sha256)。构建使用已发布 0.5.0 ZIP 的临时解压目录作为 `--baseline`。没有覆盖历史发布产物。

本次为本地 macOS 验证；远程 CI 的 Linux、Windows 与其他 Python 组合不在上述通过声明内。完整测试覆盖异常协议、路径和符号链接越界、索引漂移、图片损坏、重复与缺失证据、正式门槛拒绝、版本回退和打包失败等情况。合成测试夹具不作为真实视觉证据。

正式 v1.0 仍需按 PRD 完成真实行为、搜索、宿主工具、跨平台和回滚五门验收，并保存绑定版本与库摘要的 `acceptance.json`。本次解包冒烟验证新运行包可用，不代表已在实际宿主完成旧包安装回滚，也不证明自动评审分数或图像授权声明的真实性。
