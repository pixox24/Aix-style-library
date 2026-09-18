# Aix 图片风格库 · 授权边界

本文件区分三类对象的授权，三者不自动互相覆盖。

## 1. 软件与协议文本

`scripts/aix.py`、`references/`、`catalog/` 的软件与协议描述文本采用 MIT 许可，允许在保留版权与许可声明的前提下使用、修改和再分发。

## 2. 风格提示词与结构化数据

`styles/*/style.json` 的视觉组件与提示词文本由本库维护者创作，采用 CC BY 4.0。再分发时须保留风格 ID、名称与来源说明。

## 3. 缩略图与评测图片

`styles/*/thumbnail.webp` 与 `evaluation/` 内的图片，其授权以每个风格 `provenance.source_ref` 和 `license_ref` 指向的记录为准。当前预览版（library_version 0.1.0）内的缩略图均为本项目程序化生成的原创示意图，`source_type=original`，`commercial_use=allowed`，允许商用，无需署名。

## 4. 不构成承诺的部分

- 授权字段记录的是资源使用事实，不构成对生成模型输出跨模型一致性的承诺。
- 填写 `commercial_use=allowed` 本身不构成完整授权证据链；正式发行前须由发布检查核对 `evaluation/rights/` 中的来源记录。
- 本预览版不包含第三方受版权保护的素材，因此不存在第三方授权文件。

## 5. 商标

"Aix" 为本项目风格编号前缀，不声明任何商标权。
