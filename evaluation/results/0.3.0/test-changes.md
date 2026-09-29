# 0.3.0 批次 · 测试修改披露（2026-09-20）

按项目惯例（"修改测试必须逐项透明披露"）。本批次库扩容 10 → 20 个风格后，暴露出 3 处"写死库状态"的测试脆弱点，修复如下。所有修改均为**动态化 / 健壮化**，保护意图保留或加强；无断言被放宽为恒真。

## 1. tests/test_aix.py · test_category_filter

- **改了什么**：原断言把「海报」× graphic 候选写死为 `[Aix0003, Aix0010]`、并断言 illustration 分类结果为空。改为动态核对：graphic 过滤结果的每个候选必须逐个读 `style.json` 验证 category=graphic，且须包含已知命中 `Aix0003`；illustration 过滤结果的每个候选同样必须属于 illustration。
- **为什么**：新增 Aix0011（撞色黑色电影海报）、Aix0015（暗黑颗粒版画）同为 graphic 且命中「海报」；illustration 侧也可能出现合法命中，原"必须为空"同属状态耦合。
- **保护意图**：类别过滤不得跨类泄漏 + 已知命中必须可检索。强度：从两条写死断言 → 全量候选逐项校验 + 已知命中锚点。

## 2. tests/test_reliability.py · test_archive_excludes_drafts_and_extras_and_matches_index

- **改了什么**：计算索引期望的迭代器增加 `d.is_dir()` 过滤（styles/ 下可能存在的 `.DS_Store` 等非目录条目不再参与）；归档内容断言追加 `'.DS_Store' in n` 排除检查。
- **为什么**：macOS 在 styles/ 目录产生 `.DS_Store` 后，原迭代器对数非目录条目调用 `read_json` 崩溃（NotADirectoryError）——环境相关脆弱点，与库内容无关。
- **保护意图**：包内索引必须与"全部非 draft 风格"一致，且任意杂项文件（含 `.DS_Store`）不得进入发布包。归档侧排除检查为**新增强化**。

## 3. tests/test_reliability.py · test_declaring_formal_version_cannot_bypass_gate

- **改了什么**：测试开头将夹具收缩到 5 个风格后再声明 `1.0.0`；断言保持 `RELEASE_NOT_READY` 不变。
- **为什么**：原测试隐性依赖"真实库 <20 个风格"才会先触发规模门槛；库扩到 20 后先触发的变成样本级 formal 检查（generation_ref → STYLE_INVALID），偏离"声明正式档不能绕过未就绪门槛"的意图。
- **保护意图**：完全保留——显式构造"规模不足"前提，使 `RELEASE_NOT_READY` 门槛在任何库规模下确定性地被验证。

---

未改动其他 75 项测试；全量 78 项修复后全绿（见 `reliability-tests.txt`，2026-09-20 运行）。
