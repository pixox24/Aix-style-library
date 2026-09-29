# 0.5.0 批次恢复指针

## 已完成

- 定义 `Aix0071–Aix0110`：40 个风格，对应收藏图 61–100。
- 写入 40 个 `style.json`、40 条权利记录、40 份素材副本和 `sources_mapping.json`。
- `plan240.json`：240 条样例计划，每个风格 6 张，人物/物体/场景各 2。
- `batch240.py prep`：240/240 成功，240 份 prompt/prepare/request 已落盘。
- Canary：`Aix0071-01`、`Aix0095-01` 均通过视觉质检，记录见 `canary-review.md`。
- 生成脚本已适配 `pub-*.r2.dev` 资源 URL：下载请求带 `User-Agent`。
- 完整出图正在后台运行，使用 `caffeinate -is` 防 macOS 睡眠挂起。

## 运行中的任务

- Hermes terminal session：`proc_9946ea4a3d9b`
- 命令：`/tmp/aix-dev/bin/python -u batch240.py gen`
- 日志：`gen.log`
- 目标：240 张新样例，断点续跑。

## 当前状态

- 0.5.0 批次已完成真实出图：240/240；`Aix0071–Aix0110` 各 6 张完整。
- 240/240 样例已完成自动化视觉评审，40/40 风格证据已构建。
- 40/40 真实缩略图、索引、全库校验、release 校验、78 项测试和 0.5.0 发布包均已完成。
- 当前发布档位：`preview` / `PREVIEW_ONLY`；正式 v1.0 五门验收仍未完成。


```bash
/tmp/aix-dev/bin/python review.py --workers 3
/tmp/aix-dev/bin/python build_evidence.py
/tmp/aix-dev/bin/python thumbs.py
python3 /Users/huazi/Desktop/aix-style-library-project/skill/aix-style-library/scripts/aix.py build-index
python3 /Users/huazi/Desktop/aix-style-library-project/skill/aix-style-library/scripts/aix.py validate --scope all
python3 /Users/huazi/Desktop/aix-style-library-project/skill/aix-style-library/scripts/aix.py validate --scope release --evidence-root /Users/huazi/Desktop/aix-style-library-project/evaluation
/tmp/aix-dev/bin/python make_sheets.py
```

然后跑全量测试、构建 0.5.0 发布包、解包冒烟与旧包基线一致性检查，并更新项目状态文档。
