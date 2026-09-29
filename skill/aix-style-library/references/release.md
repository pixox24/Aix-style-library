# 发布校验与打包

本文件仅供维护者发布时读取。运行命令 get/search/prepare 不安装依赖、不联网、不修改库。

## 运行检查

- `validate --scope all`：校验全部风格结构、最终资源路径、文件大小及完整索引一致性。修改数据后先运行 `build-index`。
- `validate --scope release --evidence-root <evaluation>`：额外进行 JSON Schema、静态 WebP 解码、尺寸与体积、来源文件、评测样本和质量阈值检查。需要 `jsonschema` 与 Pillow，缺失返回 `DEPENDENCY_MISSING`，不自动安装。
- `--baseline <旧包根目录>`：验证旧包索引，拦截已发布 ID 消失、版本倒退、同版本内容变化。

库版本 0.x.y 自动采用 `preview`，1.x.y 及更高版本采用 `formal`，不能用参数将正式版本降为预览校验。release 输出包含 `release_profile`、`visual_samples`、`formal_evidence_checked`。预览通过总是附 `PREVIEW_ONLY`；不代表真实出图或 9 分验收通过。

所有发布包禁止 draft。开发库中的 draft 由打包工具排除；运行时仍能说明相应 ID 尚未发布。弃用记录保留，replacement_id 必须指向包内 active 风格。

## 图片与评测

缩略图必须可解码为静态 WebP，长边 640px，短边至少 320px，大小不超过 250 KiB。所有样例必须为可解码的静态图片。

每个 active 风格至少 6 条样本，人物、物体、场景各至少 2 条；case_id 和图片路径不重复，全库解码后的图片像素不得重复。风格与内容均分、跨题材评分均至少为 4；全库风格分 ≥4 的比例至少 90%，内容分 ≥4 的比例至少 95%。分数必须是整数，布尔值无效。预览数据的分数仅用于验证数据链路，不能被解释为真实视觉质量。

证据风格 ID、版本、tested_tool、tested_at 必须与 style.json 一致，日期有效，reviewer 非空；self_blind 必须注明 limitations。rights_record 必须指向评测根目录内的非空文件。本地 source_ref 相对评测根目录（兼容 `evaluation/` 前缀）；本地 license_ref 相对 Skill 根目录，可带 Markdown fragment。网络来源链接不被自动访问，仍必须有本地授权记录供人工复核。

## 正式版本额外要求

至少 20 个 active 风格，覆盖至少三个分类。每份风格证据声明 `evidence_type: "image_model"`。每个 sample 增加 `generation_ref`，相对评测根目录，指向如下真实调用记录：

```json
{"status":"generated","tool":"与 tested_tool 一致的工具身份","prompt":"与该 sample 一致的实际提示词","image_sha256":"实际图片文件的 SHA-256","parameters":{}}
```

图片哈希、提示词与工具身份必须匹配；不得用排队状态冒充完成。参数只记录工具实际提供的值。

在 `results/<库版本>/acceptance.json` 保存正式验收声明：

```json
{
  "library_version": "1.0.0",
  "source_digest": "当前发布包索引摘要",
  "reviewer": "实际验收人",
  "gates": {
    "agent_behavior": {"status":"passed","record_ref":"真实记录路径","sha256":"记录文件摘要"},
    "search": {"status":"passed","record_ref":"真实记录路径","sha256":"记录文件摘要"},
    "host_tool": {"status":"passed","record_ref":"真实记录路径","sha256":"记录文件摘要"},
    "portability": {"status":"passed","record_ref":"真实记录路径","sha256":"记录文件摘要"},
    "rollback": {"status":"passed","record_ref":"真实记录路径","sha256":"记录文件摘要"}
  }
}
```

这些声明由验收者根据 PRD 的 96 次行为、搜索集、真实宿主工具、跨平台与回滚门槛填写。自动校验保证必填声明、版本绑定、记录存在及摘要一致，不能证明评分诚实、授权有效或图片确由所声明工具生成；语义、视觉与法律判断仍需真实人工复核。不要自动产生 passed 声明或虚构记录。

## 组包

开发仓库运行 `python tools/build_release.py --evidence-root evaluation [--baseline <旧包根目录>]`。

工具将固定运行资源、active/deprecated 风格复制到临时 staging，排除 draft、任意附加文件、临时请求、缓存；在 staging 重建索引，完成 release 校验，生成 ZIP 后解包再校验并执行 get/search/prepare 冒烟。失败不产生正式 ZIP。发布路径以不可覆盖方式创建，旧 ZIP 或校验文件存在时拒绝。

`--version` 只能与 library.json 一致，不能只改 ZIP 名称。改变实现也应提升库版本，重新生成索引；不要覆盖历史发布包。运行资源清单维护在开发工具中，新增必要运行文件时同步更新。
