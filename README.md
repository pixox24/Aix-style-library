# Aix 图片风格库

按稳定编号查询、按视觉描述检索、按用户画面要求应用的图片风格库。每个风格以结构化 `style.json` 与代表缩略图为核心资源。

当前状态：**预览版 0.1.0**（3 个风格，覆盖 3 个一级分类）。工程闭环（get/search/prepare/validate/索引/测试）已完成；正式 v1.0 要求的 20 个真实风格与 120 张视觉测试尚未完成，见 `evaluation/results/0.1.0/acceptance-report.md`。

## 目录

```text
aix-style-library-project/
├── PRD.md                     # 需求与验收规范
├── README.md                  # 本文件
├── requirements-dev.txt       # 仅开发校验依赖
├── skill/aix-style-library/   # 实际安装的运行包
├── tests/                     # 确定性测试与用例集
├── evaluation/                # 评测与授权记录（不装入运行包）
├── tools/                     # 开发辅助脚本
└── releases/                  # 打包产物
```

## 运行要求

- Python 3.11+（已在 Python 3.14 验证）。
- `get` / `search` / `prepare` / `build-index` 只依赖标准库，不需要联网或第三方包。
- 完整 `validate --scope release` 会使用开发依赖 `jsonschema` 与 `Pillow`；缺失时给出可操作提示，不自动安装。

## 安装

1. 确认目标宿主实际使用的 Skills 目录（不同宿主/版本位置不同，不要照抄某个人的绝对路径）。
2. 把 `skill/aix-style-library/` 整体复制到该目录下。
3. 让宿主重新发现 Skill（通常重启会话或重新加载）。
4. 显式调用：Codex 风格为 `$aix-style-library`；其他宿主按各自语法。

## 验证一条编号

```bash
python <skill-root>/scripts/aix.py get --id 0001
```

成功时 stdout 返回一个 JSON 对象，`data.stage` 为 `resolved`。失败时返回错误码，见 `skill/aix-style-library/references/protocol.md`。

## 常用命令

```bash
python <skill-root>/scripts/aix.py search  --input request.json
python <skill-root>/scripts/aix.py prepare --input request.json
python <skill-root>/scripts/aix.py validate --scope all
python <skill-root>/scripts/aix.py build-index
```

## 维护流程

1. 分配未占用 ID，建立 `styles/<ID>/` 与 draft 的 `style.json`。
2. 准备 `thumbnail.webp`（长边 640px，≤150 KiB 目标），补齐来源记录。
3. 在固定图像工具上完成三类主体测试并记录评测，设置 `quality` 与 `status=active`。
4. 运行 `validate --scope all`、`build-index` 和回归测试。
5. 构建发布包，运行 `validate --scope release --evidence-root evaluation --baseline <上一版本>`。

## 开发

```bash
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
python tools/generate_preview_assets.py
python tools/build_release.py
```

## 移除或恢复

- 移除：删除宿主 Skills 目录下的 `aix-style-library/` 文件夹。
- 恢复：解压 `releases/` 中上一个完整发布包到同一位置，不要只替换单个文件。
- 回滚会同时恢复风格数据、缩略图与索引，避免出现提示词与索引版本不一致。
