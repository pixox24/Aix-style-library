# Aix Style Library：9 分差距复核

评估日期：2026-09-19。对象：`skill/aix-style-library`，库版本 0.1.0，仓库提交 `45be7bf6023b814f977434c33c2f79bd7fcab2eb`。

## 结论与评分

入口说明的设计已较成熟，单看 SKILL.md 可给约 **8.5/10**；将脚本、资源、检索、工具交接和验证证据一并纳入，按本项目 PRD 权重复核，当前约 **6.3/10**。这是本次证据审查的判断分，不是完成全部正式验收后的认证分。

离 9 分的关键差距同时存在于工程正确性、真实素材质量和验收证据。原验收报告“差距的唯一实质来源是内容与真实工具门槛，不是工程质量”的结论不成立：本次已复现发布校验、路径限制、异常协议和打包范围方面的问题。

采用 [PRD §3.3](/Users/huazi/Desktop/aix-style-library-project/PRD.md:142) 的权重：

| 维度 | 权重 | 本次评分 | 主要依据 |
|---|---:|---:|---|
| 调用与语义正确性 | 25% | 7 | 常规 get/search/prepare 可运行；产品提示词存在人物特征残留，异常协议有缺陷 |
| 风格资产质量 | 25% | 5 | 3 个结构化配方，但图片为程序化示意，缺少真实模型生成与有效视觉评审 |
| Agent 行为与交互 | 20% | 6 | 规则较完整；现有摘要混合脚本测试与行为观察，缺少 96 次可追溯执行与真实工具交接 |
| 数据与维护可靠性 | 15% | 6 | 单一数据源、摘要、原子索引写入有效；发布校验和打包仍会放行不合格输入 |
| 效率与依赖控制 | 10% | 9 | 入口简短，运行使用标准库，本机 1000 风格命中检索性能达标 |
| 可移植性与说明 | 5% | 6 | 相对资源路径及能力说明较好；Mac 测试报错，宿主安装尚无验收证据 |

加权分：`7×25% + 5×25% + 6×20% + 6×15% + 9×10% + 6×5% = 6.30`。

**20 个风格、120 张图是本项目既定的正式版门槛，并非所有优秀 Skill 的通用要求。** 即使先收窄为 3 个风格的小型产品，下面的正确性缺陷和真实效果验证仍需解决。

## 本次实际验证

- 阅读入口、3 份流程参考、4 份 Schema、运行脚本、测试、维护工具、3 个风格数据及既有评测记录；打开了一个程序化样例图核对其性质。
- 本机 macOS 26.5.2 / arm64，Python 3.14.6：原有 **53 项测试，50 通过、1 错误、2 跳过**。错误来自直接调用 Windows `cmd`；跳过来自本机未安装 `jsonschema`，不将跳过算作通过。
- 在临时副本运行 16 条定向探针记录，见 [结果](/Users/huazi/Desktop/aix-style-library-project/evaluation/reviews/2026-09-19/probe-results.json)。这是脚本及数据边界检查，不是 16 次独立 Agent 行为测试。
- 1000 个合成风格、每项预热后 30 次，包含 CLI 启动；get p95 **53.42 ms**，search p95 **68.71 ms**。检索实际返回 3 个候选，见 [性能记录](/Users/huazi/Desktop/aix-style-library-project/evaluation/reviews/2026-09-19/benchmark.json)。合成数据只能证明该测量条件下的性能，不能证明检索质量。
- 现有发布 ZIP 的 19 个文件与源运行包一致，SHA-256 校验匹配。
- 未进行真实出图、96 次 Agent 对话、正式宿主安装或 Windows 复测；旧记录中的相关结论未当作本轮新实测。
- 本轮只新增评估报告和复现材料，未修改运行包、既有测试和历史验收报告。

## 优先修复的问题

### 1. 发布校验没有真正拦住不合格资源（正式发布阻断）

位置：[aix.py `_validate_release`](/Users/huazi/Desktop/aix-style-library-project/skill/aix-style-library/scripts/aix.py:847)。

已复现：

- 把 `thumbnail.webp` 换成纯文本并重建索引，release 校验仍返回 `OK`。
- 将某风格 6 条样本改为同一条重复样本，风格、内容、跨题材分数都为 1，仍返回 `OK`。
- 临时副本将库版本改成 1.0.0，保留 3 个程序化风格，仍返回 `OK`。

脚本没有实际调用 `jsonschema` 或 Pillow，与 README 关于完整发布校验的说明不一致。现有检查主要检查文件存在、必要字段和分数取值范围，没有实施图片解码、样本唯一性、题材覆盖和质量阈值。

**建议：** 明确区分预览包结构检查与正式验收；正式验收检查真实可解码图片、尺寸/体积、每类 2 个不同样本、逐风格均分和全库达标比例。把已执行的人工复核、工具验收与行为记录关联到正式版本；缺证据返回未完成，不将文件存在等同于质量通过。开发依赖缺失时明确失败并提示维护者，运行命令继续保持标准库依赖。

**完成标准：** 损坏图、重复样本、缺题材、低分和缺必要证据均能被独立负例拦截；允许合法预览版，但不能给出正式达标结果。

### 2. 索引完整性检查可以被保留的摘要字段绕过（正式发布阻断）

位置：[发布时的索引比较](/Users/huazi/Desktop/aix-style-library-project/skill/aix-style-library/scripts/aix.py:900)。

已复现：仅将 `catalog/index.json` 的 `styles` 清空、保留原 `source_digest`，release 校验仍为 `OK`；随后搜索“水彩”返回成功的空列表。

原因是只比较索引声称的摘要和版本，没有验证磁盘索引记录确实对应这个摘要及源数据。

**建议：** 发布时验证完整索引结构，将磁盘索引与根据源数据生成的规范化 payload 比较；至少核对记录集合、字段及从记录重算的摘要。保持普通搜索按需回读，避免每次搜索都扫描全库。

**完成标准：** 清空、删项、修改检索字段或伪造摘要均被拒绝；正常构建仍有确定性。

### 3. 文件级符号链接绕过库路径限制（正式发布阻断）

位置：[aix.py `style_paths`](/Users/huazi/Desktop/aix-style-library-project/skill/aix-style-library/scripts/aix.py:380)。

已复现：整个风格目录指向库外时正确拒绝；但单独将 `style.json` 或 `thumbnail.webp` 链接到库外文件，get 都返回 `OK`。

当前只对风格目录做真实路径检查，再拼接文件名；没有对最终要读取的文件重复检查。本次库外文件都是探针自行创建的测试文件，没有访问用户私人文件。

**建议：** 对最终文件路径做 realpath 和库内限制；同样核对库元数据读取路径。测试分别覆盖目录链接、文件链接、合法库内链接以及目标平台的 junction。

**完成标准：** 最终解析到库外的资源稳定返回 `PATH_OUTSIDE_LIBRARY`。

### 4. 错误协议、Schema 与跨平台测试还未闭合（高优先级）

位置：[元数据读取](/Users/huazi/Desktop/aix-style-library-project/skill/aix-style-library/scripts/aix.py:171)、[响应构造](/Users/huazi/Desktop/aix-style-library-project/skill/aix-style-library/scripts/aix.py:994)、[平台相关测试](/Users/huazi/Desktop/aix-style-library-project/tests/test_aix.py:579)。

已复现：

- `library.json` 为合法 JSON 数组 `[]` 时，CLI 返回退出码 1，stdout 为空，stderr 出现堆栈；错误处理再次读取同一坏元数据而再次失败。
- 删除 Schema 要求的 `replacement_id` 字段，get 仍成功，说明手写校验与 Schema 存在差异。
- Mac 上测试无平台判断地执行 `cmd /c mklink /J`，导致测试报错。

另外，[response.schema.json](/Users/huazi/Desktop/aix-style-library-project/skill/aix-style-library/references/schemas/response.schema.json:27) 只要求 data 为 object/null，未限定 resolved/candidates/prepared 各分支的必要结构。

**建议：** 验证库元数据根类型与版本；使错误响应不依赖可能再次失败的读取；补齐 request/response/style 校验的一致性检查。按操作及状态定义必要响应字段，覆盖 malformed 元数据与失败输出。Windows 用 junction 测试，POSIX 用 symlink 测试；发布验证环境应明确安装开发依赖，不依赖被跳过的 Schema 测试。

**完成标准：** Windows 和一个 POSIX 环境测试全绿，必要检查没有无解释的跳过；异常 stdout 始终是单一、符合协议的 JSON。

### 5. 打包范围与版本身份缺少约束（高优先级）

位置：[build_release.py](/Users/huazi/Desktop/aix-style-library-project/tools/build_release.py:29)。

已在临时副本复现：draft 风格被装入发布包；额外的测试请求文件也被装入；传入版本 9.9.9 时，ZIP 文件名为 9.9.9，但包内 `library_version` 仍为 0.1.0。当前已发布的 0.1.0 ZIP 本身与源数据一致，这些是维护流程尚未防住的情况。

**建议：** 在临时 staging 目录按运行资源清单组包，排除 draft 和临时文件，在 staging 内重建索引；保留允许发布的弃用记录以支持旧 ID 解释。版本参数必须匹配包内版本。校验 staging、执行解包冒烟后，再生成不可覆盖产物。

**完成标准：** 包内清单、索引、源数据和版本身份一致；新增 draft 或临时请求不会污染正式包。

### 6. 风格组件仍夹带特定题材，影响迁移（高优先级）

位置：[Aix0001 的核心组件 F01](/Users/huazi/Desktop/aix-style-library-project/skill/aix-style-library/styles/Aix0001/style.json:17)。

用现成的咖啡机请求执行 prepare，得到的视觉风格仍包含：

> 摄影式胶片画面，真实皮肤质感与自然形体

这份请求已经排除了影响机身颜色的 F02，但 F01 把“胶片媒介”与“皮肤”绑定在同一核心组件中。Agent 只能排除整个组件；再排除 F01 就会失去全部 core。当前结构难以表达“保留胶片感、去掉人物材质”。这证明的是提示词污染，尚未实测它对最终图片的影响。

**建议：** 首先把核心特征改为主体无关的视觉描述；将皮肤、服饰等题材要求移出通用 core，必要时再增加条件组件。人物、产品、建筑分别核对迁移后的提示词和真实图片。对每个风格明确哪些核心特征共同构成辨识度，不能只靠“还剩一个 core”认定适配。

**完成标准：** 产品提示词没有人物材质残留；保留准确产品颜色时仍有足够的真实风格辨识度。

## 必须补齐的能力与证据

### 7. 真实风格资产与可信质量状态

当前 3 个风格都标记 `active`、`review_status=passed`，但 `tested_tool` 为程序化 Pillow 预览。样本分数由 [write_evidence.py](/Users/huazi/Desktop/aix-style-library-project/tools/write_evidence.py:73) 固定写入 4；文件明确披露这只是结构占位，不能把这些数值当作视觉评审。

建议先让 3 个风格完成真实出图与评审，验证核心方法，再扩充到 PRD 要求的 20 个。演示资产应有明确的预览身份，实际查询和交付也能辨认；不应只在未必会被读取的历史报告中解释限制。可以采用独立预览包或版本化的质量阶段字段，选一种简单一致的方案即可。

每个风格应有来自固定工具的可追溯提示词、实际参数、图片和评审理由。正式版按当前 PRD 完成至少 120 张结果，人物/物体/场景各 2 张；每风格三维均分 ≥4，全库风格分 ≥4 比例 ≥90%、内容分 ≥4 比例 ≥95%。保留失败图及修订前后的差异；采用独立复核或确实执行的盲复评。

### 8. 一个实际可用的宿主出图闭环

[host-tools.md](/Users/huazi/Desktop/aix-style-library-project/skill/aix-style-library/references/host-tools.md:5) 明确没有已验证宿主或工具。边界说明是优点，但仍不能证明“用编号生成图片”已完成。

先选当前目标宿主实际提供的一种图像工具，填入已核验的参数契约；完成普通出图、指定竖版、文字、工具失败、排队未完成、不支持参数和返回资源打不开这些场景。只有拿到真实图片并能访问时记为 generated。保留工具身份、实际参数、风格版本和图片引用。

### 9. 可追溯的 Agent 行为执行

[现有记录](/Users/huazi/Desktop/aix-style-library-project/evaluation/results/0.1.0/agent-behavior.md:39) 将部分脚本测试算入行为覆盖；A27 是规则验证，A30 未验证；A19 写了“已修正”，未附独立复测轨迹。仓库中没有足以独立核对全部行为结论的逐次调用记录。

按现有 PRD 补齐 32 案例 × 3 次独立上下文。保存实际输入/必要历史、宿主与模型、工具调用、结果、判定理由和缺陷引用；分开记录通过、失败、未运行、阻塞及修复后重测。验收输入不提前泄露标准答案。关键案例全过，总体至少 92/96；不能用 JSON 包含某些词替代模型行为观察。

### 10. 搜索评估需要覆盖用户原话和有效的排序难度

当前测试手工给定 `terms`，并非从自然语言到结果的完整链路；3 个风格返回最多 3 条的 Hit@3 对排序区分度很弱，不能支持扩库后的质量承诺。

已复现：terms 为“水彩”时命中 Aix0002；单独用“儿童绘本”或“奶油色系”时结果为空。前者出现在适用场景，后者出现在描述。现有字段与阈值设计可以解释这个结果，但与自然语言找风格的期望有差距。

建议将原话 → Agent 提炼检索词 → 检索排序分别测量。扩充有效同义词，考虑让适用场景参与检索，并基于留出样例调节描述命中的权重和置信度；同时保留库外需求应为空的约束。无需先上向量数据库。

按 PRD 完成 30 正例、10 负例与新留出查询；加入近似风格、组合要求及容易混淆的候选。扩库后再评 Hit@3，补看首选结果是否合理。

## 建议执行顺序

| 顺序 | 工作 | 完成信号 |
|---|---|---|
| 第一批 | 修复发布校验、索引验证、文件路径、错误协议、跨平台测试、打包范围 | 本报告复现问题的负例均被正确拒绝；合法流程仍通过 |
| 第二批 | 用现有 3 个风格完成真实工具交接，修正组件的题材绑定 | 18 张真实跨题材结果、实际评审与一次完整安装/生成冒烟 |
| 第三批 | 按真实失败迭代后扩到 20 个可区分风格，补检索与行为矩阵 | 120 张视觉证据、96 次行为记录、30+10 搜索集和留出结果达标 |
| 第四批 | 在干净目录验证完整发布包并演练回滚，重新计算分数 | 所有硬门槛通过、每维 ≥8、加权 ≥9 |

不建议现在扩大 SKILL.md、增加更多原则段落、引入数据库/MCP 服务或堆砌模型适配参数。入口正文约 1107 字符，触发边界清楚，编号直取、用户意图优先、候选顺序绑定和真实生成状态等设计应保留。当前最有价值的投入是让现有规则在失败输入、真实图片和实际宿主中都成立。

## 复现方式

探针仅对临时复制的风格库与评测目录做修改；报告生成不会修复这些缺陷。探针记录观察结果，不以进程退出成功表示全部检查通过。

```bash
python3 /Users/huazi/Desktop/aix-style-library-project/evaluation/reviews/2026-09-19/probes.py /Users/huazi/Desktop/aix-style-library-project
```

附件：[复现脚本](/Users/huazi/Desktop/aix-style-library-project/evaluation/reviews/2026-09-19/probes.py)、[探针结果](/Users/huazi/Desktop/aix-style-library-project/evaluation/reviews/2026-09-19/probe-results.json)、[性能结果](/Users/huazi/Desktop/aix-style-library-project/evaluation/reviews/2026-09-19/benchmark.json)。
