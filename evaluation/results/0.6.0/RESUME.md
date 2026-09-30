# 0.6.0 批次恢复指针

> 2026-10-01 更新：以下保留历史执行记录。当前 50 个新增风格的证据和缩略图已存在，全库 160 个风格/960 个样例通过发布校验；78 项测试与 0.6.0 打包、解包冒烟已完成。最新事实见 [本版可靠性报告](reliability-report.md)。正式五门验收与实际宿主回滚仍未在本记录中声明完成。

## 范围

- 来源：收藏图 101–150，共 50 张；每张作为一个独立风格种子。
- 新风格：Aix0111–Aix0160，共 50 个。
- 验收：每个风格 6 张真实样例，人物/物体/场景各 2，共 300 张。
- 发布档位：0.6.0 preview / PREVIEW_ONLY；不等同正式 v1.0。

## 已完成

- 已读取并视觉分析收藏图 101–150。
- 已创建 0.6.0 批次脚本骨架：setup_batch4.py、batch300.py、review.py、build_evidence.py、thumbs.py、make_sheets.py、canary06.py。
- 已将 library.json 升至 0.6.0，等待新风格定义和真实出图验收。
- 已写入 Aix0111–Aix0160 定义、50 条权利记录和 300 条样例计划；`batch300.py prep` 为 300/300。
- Canary `Aix0111-01` 与 `Aix0136-01` 均通过视觉质检（严格评分 4/5，允许全量）；Aix0111 的内容防护调整已记录在 `moderation-adjustments.json`。
- 300/300 真实出图完成（`gen_manifest_v2.json` 300 条；plan/image/manifest 键集一致，每风格 6 张）。
- Aix0146 四个样例因内容防护被拒（HTTP 400）：描述与风格定义改为等效非损伤表述，re-prep 后 4 张全部成功；新旧描述/提示词哈希已记录在 `moderation-adjustments.json`（共 5 条）。
- 评审已启动（`review.py --workers 3`，session `proc_79edd5eec134`），进行中。

## 下一步

1. ~~写入 Aix0111–Aix0160 定义，执行 setup_batch4.py。~~
2. ~~运行 batch300.py prep，核对 300/300 prompts。~~
3. ~~Canary：Aix0111-01、Aix0136-01，逐张视觉质检后再全量。~~
4. ~~`batch300.py gen` 断点续跑~~ → 300/300 完成。
5. ~~比较 plan/image/manifest 键集和每风格 6 张计数~~ → 一致。
6. 评审（进行中）→ evidence → thumbs → README/report 更新 → build-index → validate all → validate release → 全量测试 → 打包 0.6.0（--baseline /tmp/aix-baseline-050）→ 回滚演练 → 验收报告。

## 约束

- 凭据只从 `~/.hermes/.env` 读取，不写入项目、日志、证据或发布包。
- 继续沿用 gpt-image-2 via gateway.change2pro，实际返回尺寸以 PNG 为准。
- 出图、评审、证据、缩略图和校验全部完成后，才将风格标记为可用。
