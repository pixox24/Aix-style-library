# Aix 请求、响应与错误协议

仅在需要构造请求、解释机器输出或处理失败时读取本文件。风格数据字段见 `schemas/style.schema.json`。

## 命令

所有命令使用 Skill 根目录下的脚本绝对路径调用，不假设当前目录：

```text
python <skill-root>/scripts/aix.py get --id 0001
python <skill-root>/scripts/aix.py get --id Aix0001 --version 1.0.0
python <skill-root>/scripts/aix.py search  --input <request.json>
python <skill-root>/scripts/aix.py prepare --input <request.json>
python <skill-root>/scripts/aix.py validate --scope all
python <skill-root>/scripts/aix.py validate --scope release --evidence-root <dir> [--baseline <dir>]
python <skill-root>/scripts/aix.py build-index
```

运行命令（get/search/prepare）只依赖 Python 标准库，不联网、不写入风格库。请求文件由调用者写入自己的工作目录或临时目录。

## 请求

`get` 用参数直接传编号。`search` 与 `prepare` 用 UTF-8 JSON 请求文件，结构见 `schemas/request.schema.json`，上限 64 KiB。

search：

```json
{"api_version":"1.0","operation":"search","query":"适合儿童绘本的柔和水彩",
 "terms":["儿童绘本","柔和","水彩"],"category":null,"limit":3}
```

- `terms` 由 Agent 从用户自然语言提炼，1～8 项，每项 1～40 字符；不引入分词依赖。
- `limit` 为 1～5，默认展示不超过 3 条。`category` 是过滤器，可为 null。

prepare：

```json
{"api_version":"1.0","operation":"prepare","style_id":"0001","style_version":null,
 "mode":"generate","target":"generic-text-v1","strength":"balanced",
 "intent":{"description":"需要保留的完整画面意图","aspect_ratio":"1:1",
           "text_literals":["春日限定"],"must_preserve":["红色机身"]},
 "resolution":{"exclude_features":[{"id":"F02","reason":"排除原因"}],"exclude_avoid":[]}}
```

- `style_id` 由脚本归一化，可写 `0001`、`1`、`Aix0001`。
- `mode` 只表达用户意图，脚本不会自行出图。`target` 本版仅支持 `generic-text-v1`。
- `strength` 必须显式填写：`light`=core，`balanced`=core+support，`strong`=core+support+accent。
- `intent.description` 必须包含要保留的完整画面，不能只写风格词。
- `aspect_ratio` 会约分（`18:32` → `9:16`）。`text_literals` 逐字保留。
- `exclude_features` 只能排除当前强度原本会选中的组件，否则 `INVALID_REQUEST`。

## 响应信封

所有命令输出一个 JSON 对象到 stdout：

```json
{"api_version":"1.0","operation":"get","status":"ok","code":"OK","message":"...",
 "data":{},"warnings":[],"meta":{"library_version":"1.0.0",
 "execution_mode":"script","elapsed_ms":4}}
```

- `status` 为 `ok` 或 `error`；失败时 `data` 为 null。
- `execution_mode` 为 `script` 或 `manual_fallback`；人工降级时 `elapsed_ms` 与未计算的摘要为 null。
- stdout 只有一个 JSON 对象；调试信息在 stderr，默认无堆栈。退出码见下表。

## 错误码与应做的事

| 错误码 | 退出码 | Agent 行为 |
|---|---:|---|
| `INVALID_REQUEST` | 2 | 修正可确定的格式问题；缺实质意图时澄清 |
| `INVALID_STYLE_ID` | 2 | 请用户核对编号，不猜号 |
| `STYLE_NOT_FOUND` | 3 | 明确不存在；有视觉描述时可另做搜索，不自动代用 |
| `STYLE_NOT_ACTIVE` | 3 | 说明尚未发布，不拿草稿执行 |
| `STYLE_DEPRECATED` | 3 | 展示 `REPLACEMENT_SUGGESTED` 的替代编号，等用户选择 |
| `STYLE_VERSION_UNAVAILABLE` | 3 | 说明可用版本，不静默替代、不联网下载 |
| `STYLE_INVALID` | 4 | 停止该风格，指出维护问题 |
| `ASSET_MISSING` | 4 | 正式流程停止，不声称风格完整可用 |
| `PATH_OUTSIDE_LIBRARY` | 4 | 停止并报告资源问题 |
| `SCHEMA_UNSUPPORTED` | 4 | 告知需要匹配版本，不自改数据 |
| `INDEX_MISSING` / `INDEX_STALE` | 4 | 告知维护者重建；编号调用仍可独立使用 |
| `DEPENDENCY_MISSING` | 4 | 发布校验缺少开发依赖；由维护者安装，不自动安装 |
| `RELEASE_NOT_READY` | 4 | 正式发布门槛或证据不完整，保留失败原因，不降为预览以绕过检查 |
| `STYLE_NOT_APPLICABLE` | 5 | 说明核心冲突，请用户改需求或另选风格 |
| `TARGET_UNSUPPORTED` | 5 | 回到已支持目标或解释限制，不伪造映射 |
| `INTERNAL_ERROR` | 6 | 一次简明报告，不无限重试 |

## 警告码

脚本只产生自己有证据的警告；宿主能力相关警告由 Agent 交接层补充。

| 警告码 | 含义 |
|---|---|
| `STYLE_ADJUSTED` | 为保留明确要求而省略了风格组件 |
| `NEGATIVE_ADJUSTED` | 为保留用户要求而省略了避用建议 |
| `WEAK_FIT` | 题材落在 `weak_for`，由 Agent 判断并说明 |
| `IMAGE_NOT_VIEWED` | 仅使用文本/alt，未实际打开缩略图 |
| `UNVERIFIED_FALLBACK` | 无脚本，未完成 Schema、摘要等确定性检查 |
| `GENERATION_UNAVAILABLE` | 用户要求出图但无可用工具 |
| `RATIO_APPROXIMATED` | 工具只能近似尺寸，实际比例不同 |
| `REPLACEMENT_SUGGESTED` | 弃用风格给出已登记替代，仍需用户确认 |
| `PREVIEW_ONLY` | 仅通过预览发布校验，未认证真实出图或正式质量 |

警告不能掩盖应返回 error 的情况。

维护命令的完整检查、预览/正式版本区分和证据格式见 `release.md`。`validate --scope all` 会核对完整索引，修改数据后先由维护者运行 `build-index`。坏库元数据返回 `SCHEMA_UNSUPPORTED`，meta.library_version 为 null；未知子命令在响应中使用 operation=unknown。

## 降级

| 环境问题 | 允许行为 | 禁止声称 |
|---|---|---|
| 无 Python/禁止脚本 | 按规范 ID 直接读取 `styles/<ID>/style.json`，按合成规则处理；标记 `manual_fallback`，`content_hash=null`，附 `UNVERIFIED_FALLBACK` | 已执行 Schema、hash 或完整路径校验 |
| 无视觉工具 | 使用名称、description、alt、features | 已观看缩略图 |
| 无图像生成工具 | 返回提示词与 `GENERATION_UNAVAILABLE` | 已生成图片 |
| 图片无法显示 | 提供可访问路径与文字描述 | 图片已成功展示 |
| 缩略图缺失 | 脚本失败；人工模式只说明数据不完整 | 完整可用风格、视觉验证通过 |
| 资源不可读取 | 明确说明不能访问，停在事实层 | 根据编号凭空猜风格 |
