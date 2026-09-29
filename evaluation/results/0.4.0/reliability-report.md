# 0.4.1 收藏扩容第二批次验收（批次目录：0.4.0）

日期：2026-09-21。范围：风格池 20→70（从个人插画库收藏 11–60 号图逐张入库，新增 Aix0021–Aix0070 共 50 个风格）、每新风格 6 张真实样张（共 300 张）、从严盲评、证据记录、发布打包与回滚演练。**结论：预览档全部通过**（78/78 测试、两级发布校验、打包、解包冒烟与回滚）；正式 v1.0 的规模条件（≥20 风格、全库 ≥120 张真实视觉证据）已大幅超出（70 风格 / 420 张），但形式要求（`acceptance.json` 五门验收声明、96 次行为记录等）尚未启动，仍以预览版对外。

> **版本说明**：本批证据目录为 `results/0.4.0/`（批次号）。打包后、交付前做了交付前修正：① Aix0068 回写 `known_failures`（内容防护实测风险）；② 运行文档对齐（`references/host-tools.md` 批次信息与内容防护记录更新到 0.4.x）。按“发布产物不可覆盖”规则，修正版以 `library_version 0.4.1` 重新打包；`releases/aix-style-library-0.4.0.zip` 为**未交付的中间构建**（保留供追溯），**交付件为 `aix-style-library-0.4.1.zip`**。

## 改动

- 风格池 20 → 70：新增 Aix0021–Aix0070（对应收藏图 11–60；每张图一个风格，属「单图 = 风格种子」模式；每条为原创、主体无关的结构化风格定义，未复制原图画面）。分类分布：illustration 42、graphic 4、3d 2、painting 1、photographic 1。
- 每新风格 6 张真实样张（人物 / 物体 / 场景各 2），共 300 张，gpt-image-2 via change2pro；提示词全部由 skill 的 `prepare` 命令合成；300 个请求、生成记录（sha256、实际像素、耗时、提示词哈希）与评审理由完整存档于 `evaluation/results/0.4.0/`。
- 逐张视觉评审：qwen3.7-plus（百炼，打乱顺序、从严口径，默认 4 分起评）；证据记录 `results/0.4.0/AixNNNN.json` 与 `generations/`。
- **内容防护调整（1 例，透明披露）**：Aix0068-01 原描述「黑影人形胸口裂开，心脏位置红光迸发」反复触发上游暴力内容防护（重试 6 次全被拒，HTTP 400 `upstream_text_reply`）；调整为等效非损伤表述「黑影人形，胸前红光如心脏般搏动」（must_preserve「人形黑影；红光心脏」保持不变），重新走 `prepare` 合成提示词后以第 2 次尝试成功。调整记录见 `moderation-adjustments.json`（含新旧描述与新旧提示词哈希）；**失败模式已回写 Aix0068 `known_failures`**（打包前完成）。
- 缩略图：50 个新风格全部替换为真实出图（case 01；长边恰 640px、8–114 KiB）。出图期间曾先以 `thumbs_incremental.py` 增量替换已出图部分，终态仍以 `thumbs.py` 全量替换为准。
- 版本：`library_version` 0.3.2 → 0.4.1（0.4.0 为交付前中间构建）；README 同步。

## 本批实测

| 项目 | 结果 |
|---|---|
| 测试（78 项） | **78/78 通过**（51.9s；`reliability-tests.txt`） |
| validate --scope all | OK（70 风格 / 70 资产 / 70 active） |
| validate --scope release | OK；release_profile=preview；visual_samples=420；PREVIEW_ONLY 警告符合预期 |
| 性能基准（30 次） | get p50 51.8ms / p95 61.0ms；search p50 58.1ms / p95 58.6ms |
| 打包 | `aix-style-library-0.4.1.zip`（154 个文件），sha256 `800112a28aeab37b16e056d74559f37b6accc9c1b80ec6ed2c8ed743b2c64c7b` |
| 解包冒烟 | 解压即用：get / search / prepare 全 OK |
| 回滚演练 | 0.4.1 → 0.3.2 → 0.4.1 共 9 项操作全 OK；包与源逐字节一致；0.3.2 旧包校验和完好 |

评审成绩：300/300 出图、300/300 评审；本批风格均分 **4.93**、内容均分 **4.97**；逐风格均分区间 4.50–5.00（风格）/ 4.67–5.00（内容）；无任何低于 4 分的单样。全库累计 **70 风格 / 420 张真实视觉证据**，≥4 比例 100%。

出图过程记录：① 首批主跑在 change2pro 服务边做边限速的波动下完成 271/300，其余 29 张经网络抖动（SSL EOF / 连接重置 / 超时）被跳过；② 补跑轮完成 24 张后服务一度放缓（~210s/张），恢复后正常速度，最终 299/300；③ 最后 1 张（Aix0068-01）为内容防护拦截，经上述透明调整后成功；④ 出图期间 Mac 曾于夜间进入系统睡眠致进程挂起约 20 小时，已用 `caffeinate` 防睡眠锁定后恢复并完成（对断点续跑无损坏，生成记录以最终成功版本核 sha256）。

支持文件：`validate-all.json`、`release-validation.json`、`benchmark.json`、`reliability-tests.txt`、`package-rollback.json`、`moderation-adjustments.json`、`contact-sheet-1..5.png`、`overview_50styles_a/b.png`。（本批无测试改动——扩库未触发新的测试脆弱点，78 项全量通过。）

## 遗留与后续

- 剩余收藏图 61–204（144 张）未入库；候选与批次规划见 `references/collection-intake-2026-09.md`。
- 出图网关（change2pro）在高压时段偶发限速/抖动：断点续跑补齐即可，无需改提示词；内容防护拦截以等效非损伤表述透明调整（记录于 `moderation-adjustments.json`）。
- Mac 长时间批量任务需 `caffeinate -is -w <pid>` 防睡眠（或保持电源设置「防止自动睡眠」）。
