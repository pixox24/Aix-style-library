# Aix 图片风格库

按稳定编号查询、按视觉描述检索、按用户画面要求应用的图片风格库。每个风格以结构化 `style.json` 与代表缩略图为核心资源。

当前状态：**预览版 0.5.0**（110 个风格，覆盖 5 个一级分类：illustration / painting / photographic / 3d / graphic）。本版从个人插画库收藏逐张扩容 40 个新风格（Aix0071–Aix0110，对应收藏图 61–100），完成每新风格 6 张（三类主体各 2）、共 240 张真实样张与逐张评审，全库累计 110 风格 / 660 张真实视觉证据（gpt-image-2，经由当前 change2pro OpenAI 兼容 Images API 路由 `gateway.change2pro.com`）；发布打包与回滚演练完成（见 [0.5.0 验收报告](evaluation/results/0.5.0/reliability-report.md)）；[宿主工具记录](skill/aix-style-library/references/host-tools.md) 已登记当前路由实测契约。正式 v1.0 的规模条件（≥20 风格、≥120 张视觉证据）已大幅超出，但正式五门验收声明等形式要求仍未完成，其判定以本 README 与验收报告为准。

本版验证结果见 [0.5.0 验收报告](evaluation/results/0.5.0/reliability-report.md)：78 项测试全部通过，发布校验、打包与解包回滚演练完成；0.x 版本仍明确标记为 `PREVIEW_ONLY`，正式 v1.0 形式验收尚未完成。Windows/Linux CI 已配置，尚未在本轮实际运行。

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
- 完整 `validate --scope release` 必须使用开发依赖 `jsonschema` 与 `Pillow`；缺失时返回 `DEPENDENCY_MISSING`，不自动安装。
- 0.x.y 发布校验明确标记 `PREVIEW_ONLY`；1.x.y 起执行正式素材数量、真实生成记录及版本绑定验收声明检查。详见 `skill/aix-style-library/references/release.md`。

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
4. 运行 `build-index`、`validate --scope all` 和回归测试。
5. 运行 `python tools/build_release.py --evidence-root evaluation --baseline <上一版本解压后的Skill根目录>`。首次发布可省略 baseline。
6. 工具按运行资源清单排除 draft/临时文件，在 staging 重建索引、执行 release 校验，再解包进行 get/search/prepare 冒烟；全部通过才生成不可覆盖的 ZIP 和 SHA-256。

## 开发

```bash
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
python tools/build_release.py
```

开发依赖必须安装后运行完整测试。`tools/generate_preview_assets.py` 仅供制作程序化演示夹具，会改变资产；不要用它替代真实出图与视觉评审。已发布风格发生变化时须提升风格版本，任何发布实现变更须提升库版本。

## 移除或恢复

- 移除：删除宿主 Skills 目录下的 `aix-style-library/` 文件夹。
- 恢复：解压 `releases/` 中上一个完整发布包到同一位置，不要只替换单个文件。
- 回滚会同时恢复风格数据、缩略图与索引，避免出现提示词与索引版本不一致。
