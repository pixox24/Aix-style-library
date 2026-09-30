# Aix 图片风格库网页开发文档

文档版本：0.1
编写日期：2026-09-30
目标版本：Web MVP 0.1
状态：Milestone 0–5 已完成，进入 P1 迭代

> 2026-10-01 实现快照：`web/` 是独立的私有仓库，不包含在主仓库克隆内容中。以下规格供有权限的维护者参考。实际应用采用 React 19、TypeScript、Vite 7、原生 CSS 与轻量 history 路由，已实现 Explore、详情、Guide 和相关风格；比较、Playground 等仍为规划。下文包含原始设计规格，不应把所有要求视为已交付能力。

## 1. 文档目的

本文件把 Aix 图片风格库网页的产品、交互、视觉、数据管线和验收要求整理为可直接执行的开发规格。

网页的核心任务是：

1. 让用户快速浏览 160 个 active 风格。
2. 让用户通过编号、名称、标签或视觉描述找到风格。
3. 让用户在详情页同时理解风格本身和 6 张真实示例图。
4. 让用户复制正确的 Skill 调用方式、CLI 命令和协议示例。
5. 让网页内容始终从 Skill 数据生成，不手工维护风格文案。
6. 清楚区分“已找到风格”“已准备提示词”和“已实际生成图片”。

网页不是图片生成服务，也不在第一版中承诺调用外部图像模型。

## 2. 当前数据事实

开发开始前以仓库当前文件为准，不以旧 README 中的统计数字为准。

| 项目 | 当前值 |
|---|---|
| library version | `0.6.0` |
| active 风格 | 160 个 |
| illustration | 62 个 |
| graphic | 54 个 |
| painting | 30 个 |
| 3d | 10 个 |
| photographic | 4 个 |
| 每个风格缩略图 | 1 张，`thumbnail.webp`，427 × 640，2:3 |
| 每个风格示例图 | 6 张，编号 `01` 至 `06` |
| 示例图内容 | 人物 2 张、物体 2 张、场景 2 张 |

权威数据来源：

- `skill/aix-style-library/library.json`
- `skill/aix-style-library/catalog/index.json`
- `skill/aix-style-library/styles/<ID>/style.json`
- `evaluation/results/<version>/images/<ID>-01.png` 至 `<ID>-06.png`
- `evaluation/results/<version>/<ID>.json`
- `evaluation/rights/<ID>.md`

`evaluation/sources/` 是内部素材溯源目录，不进入网页资源，也不进入静态发布包。

## 3. 产品定位

网页定位为“视觉风格索引 + Skill 调用文档”，不是传统营销首页。

主要用户：

| 用户 | 任务 | 首要界面 |
|---|---|---|
| 创作者 | 找到适合画面的风格并查看视觉效果 | Explore、Style Detail |
| AI Agent 使用者 | 获取稳定编号和调用格式 | Guide、Style Detail |
| 开发者 | 理解字段、协议和数据版本 | Guide、Provenance |
| 维护者 | 检查网页是否完整反映数据 | Build Check、Data Manifest |

设计方向：中性画布、图片主导、编辑档案式排版、克制的工具感。避免营销型大 Hero、紫色渐变、纯文本卡片堆叠和虚构的风格分数。

## 4. 技术方案

### 4.1 推荐技术栈

第一版采用静态优先架构：

- React
- Vite
- TypeScript
- React Router
- Tailwind CSS v4 或原生 CSS Modules，二选一，全站统一
- `@phosphor-icons/react` 作为唯一图标库
- `vite-plugin-image-optimizer` 或等效构建期图片压缩工具，若现有环境允许

不引入数据库、登录、后端 API 或在线向量服务。

### 4.2 为什么静态优先

- 风格数据已经是本地 JSON，运行时无需联网。
- 160 个风格适合构建期生成静态数据。
- 详情页和示例图适合 CDN 或静态托管。
- 能够保证网页内容与某个明确的 Skill 版本绑定。
- 避免把运行时密钥、图像模型接口和网页混在一起。

### 4.3 目录结构

建议新建 `web/` 目录：

```text
web/
├── package.json
├── index.html
├── tsconfig.json
├── vite.config.ts
├── public/
│   ├── favicon.svg
│   ├── data/
│   │   ├── catalog.json
│   │   ├── styles.json
│   │   └── examples-manifest.json
│   └── assets/
│       ├── thumbnails/
│       │   └── Aix0001.webp
│       └── examples/
│           └── Aix0001/
│               ├── 01.png
│               ├── 02.png
│               └── 06.png
├── scripts/
│   ├── build-web-data.py
│   └── check-web-data.py
└── src/
    ├── app/
    │   ├── App.tsx
    │   ├── routes.tsx
    │   └── providers.tsx
    ├── components/
    │   ├── app-shell/
    │   ├── search/
    │   ├── filters/
    │   ├── style-card/
    │   ├── style-gallery/
    │   ├── style-anatomy/
    │   ├── invocation-panel/
    │   ├── compare/
    │   └── feedback/
    ├── pages/
    │   ├── ExplorePage.tsx
    │   ├── StyleDetailPage.tsx
    │   ├── GuidePage.tsx
    │   ├── PlaygroundPage.tsx
    │   └── NotFoundPage.tsx
    ├── data/
    │   ├── types.ts
    │   ├── loader.ts
    │   └── search.ts
    ├── state/
    │   ├── explore-state.ts
    │   └── compare-state.ts
    ├── styles/
    │   ├── tokens.css
    │   ├── globals.css
    │   └── typography.css
    └── main.tsx
```

`web/public/data/` 和 `web/public/assets/` 是已提交到独立 Web 仓库的发布快照。不要在其中手工编辑风格名称、描述、标签或样例来源；在主项目中显式运行 `npm run build:data`（工作目录为 `web/`）才会从 Skill 数据重新生成它们。`npm run dev` 和 `npm run build` 直接使用快照，不自动重建数据；数据生成还需安装 `cwebp`。

## 5. 页面与路由

### 5.1 `/` Explore

这是默认入口，也是最重要的页面。

桌面布局：

```text
┌─────────────────────────────────────────────────────────────┐
│ Header                                                      │
├─────────────────────────────────────────────────────────────┤
│ Search command bar                                          │
│ 160 styles · 5 categories · v0.6.0                         │
├───────────────┬─────────────────────────────────────────────┤
│ Filter rail   │ Result toolbar                              │
│               │ 48 results       [sort] [grid density]       │
│               ├─────────────────────────────────────────────┤
│               │ Style grid                                   │
│               │ 4 columns × repeated 2:3 cards              │
└───────────────┴─────────────────────────────────────────────┘
```

页面组成：

1. 顶部 Header。
2. 搜索命令栏。
3. 统计信息。
4. 筛选栏。
5. 结果工具栏。
6. 风格网格。
7. 空结果、错误和加载状态。

搜索输入支持：

- `0001`
- `1`
- `Aix0001`
- 风格名称
- 标签
- 描述关键词
- `适合儿童绘本的柔和水彩`

URL 必须同步保存探索状态：

```text
/?q=水彩&category=illustration&tag=绘本&sort=relevance
```

刷新页面、复制 URL 或返回浏览器历史后，筛选状态必须恢复。

搜索交互约定：

- Hero 搜索框输入停止约 400ms 后，平滑滚动到结果区；结果标题和卡片列表必须同时进入视口。
- Hero 搜索框离开视口后，顶部显示紧凑的悬浮搜索框，并与 Hero 搜索框共享查询状态。
- 从悬浮搜索框输入时只更新结果，不再次自动滚动，避免用户在结果区操作时页面跳动。
- `prefers-reduced-motion: reduce` 时使用即时定位和无过渡显示。

### 5.2 `/styles/:styleId` Style Detail

详情页必须围绕 6 张示例图重新设计，不能只把缩略图放大。

桌面推荐布局：

```text
┌──────────────────────────────┬──────────────────────────────┐
│                              │ Aix0001                      │
│                              │ 雾青胶片人像                  │
│                              │ description                  │
│       Active example         │ [复制调用] [加入比较]          │
│       large 2:3 image        │                              │
│                              │ Style anatomy                │
│                              │ medium / palette / ...       │
├───────────────┬──────────────┤                              │
│ 01  02        │ 03  04      │ Suitable / Weak / Avoid       │
│ 05  06        │              │                              │
└───────────────┴──────────────┴──────────────────────────────┘
```

推荐实际实现为：左侧 `5/12` 宽度 gallery，右侧 `7/12` 宽度信息区。左侧大图约占 gallery 的 60%，右侧是 6 张示例缩略图组成的 `3 行 × 2 列`网格。这样能同时展示全部示例，而不会把 6 张图压缩成看不清的横向小条。

详情页首屏必须显示：

- 大图
- 6 张示例缩略图
- 当前示例序号，例如 `03 / 06`
- 风格 ID
- 名称
- 描述
- 复制调用按钮
- 加入比较按钮

滚动后显示：

1. 风格结构
2. 适用场景
3. 弱项和已知失败
4. 避用项
5. 调用方式
6. 来源、授权和质量信息
7. 相关风格

### 5.3 `/guide` Guide

Guide 页面分为四个部分：

1. 这个 Skill 能做什么
2. 按编号调用
3. 按视觉描述搜索
4. 准备提示词和交给宿主生成

页面必须展示准确的阶段边界：

```text
resolved  找到风格
prepared  生成提示词计划
generated 实际生成了图片
```

复制示例：

```text
使用 $aix-style-library 的 0001 风格，
画一只坐在窗边的猫，竖版 9:16。
```

```bash
python <skill-root>/scripts/aix.py get --id 0001
```

```json
{
  "api_version": "1.0",
  "operation": "search",
  "query": "适合儿童绘本的柔和水彩",
  "terms": ["儿童绘本", "柔和", "水彩"],
  "category": null,
  "limit": 3
}
```

### 5.4 `/playground` Prompt Playground

第一阶段可隐藏入口，第二阶段开放。

功能：

- 选择风格
- 填写画面描述
- 填写画幅
- 填写必须保留的内容
- 填写文字内容
- 选择 `light / balanced / strong`
- 选择需要排除的视觉特征
- 展示结构化提示词
- 展示 `STYLE_ADJUSTED`、`NEGATIVE_ADJUSTED`、`WEAK_FIT` 等警告
- 复制结果

该页面只生成提示词计划，不显示“生成完成”。

## 6. 六张示例图的交互规格

### 6.1 资源语义

每个风格的 6 张示例图按照以下顺序展示：

| 编号 | subject_category | 用途 |
|---|---|---|
| 01 | 人物 | 证明风格在人物主体上的表现 |
| 02 | 人物 | 证明风格在另一种人物构图上的表现 |
| 03 | 物体 | 证明风格在物体主体上的迁移 |
| 04 | 物体 | 证明风格在另一种物体主体上的迁移 |
| 05 | 场景 | 证明风格在场景上的表现 |
| 06 | 场景 | 证明风格在另一种场景上的表现 |

网页中要显示“人物 / 物体 / 场景”标记，但不要把自动评审分数作为风格评分展示。

### 6.2 桌面端

- 主图固定使用 2:3 比例。
- 6 张缩略图为 3 行 × 2 列。
- 当前缩略图使用 2px 强调色边框和轻微遮罩。
- 点击缩略图切换主图。
- 主图切换时不改变 gallery 容器尺寸。
- 主图下方显示 `03 / 06 · 物体`。
- 右侧信息区滚动时，gallery 可保持 sticky，但不能覆盖 Header。

### 6.3 移动端

移动端不得继续使用桌面 5/12 + 7/12 布局。

- 主图占满内容宽度，固定 2:3。
- 6 张缩略图改为横向滚动条，单张宽度 72～88px。
- 横向滚动条显示 6 张完整缩略图，不使用无限循环。
- 点击缩略图切换主图。
- 主图上显示非阻塞的 `03 / 06` 计数。
- 详情信息紧跟 gallery 之后。
- 复制调用和加入比较按钮保持在首屏可见区域。

### 6.4 Lightbox

点击主图可以打开 Lightbox：

- 黑色或深灰背景
- 中央展示当前 2:3 图片
- 左右切换按钮
- 键盘 `ArrowLeft / ArrowRight`
- `Escape` 关闭
- 显示 `03 / 06`
- 显示样例类别
- 不自动播放
- 支持触摸左右滑动

Lightbox 中不要展示原始评测 prompt、生成 URL 或内部网关信息。

### 6.5 加载和错误状态

- 首屏主图使用骨架占位，尺寸必须等于最终 2:3 容器。
- 下一张图片在当前图片加载完成后预加载。
- 单张失败显示“示例图暂时不可用”，不能让整个详情页报错。
- 6 张图中缺少任意一张时，构建检查失败；开发模式可以显示缺失状态方便定位。

## 7. 风格卡片规格

每个风格卡片的固定结构：

```text
┌──────────────────────────────┐
│                              │
│        2:3 thumbnail         │
│                              │
├──────────────────────────────┤
│ Aix0001              graphic │
│ 扁平几何海报                  │
│ 扁平色块海报构成，高对比……     │
│ #扁平  #几何  #海报            │
└──────────────────────────────┘
```

要求：

- 缩略图全部使用 `object-fit: cover` 或 `contain`，统一验证后选择一种。
- 卡片高度稳定，描述最多 2 行，标签最多 1 行。
- ID 使用等宽字体。
- hover 时只做轻微图片缩放和边框变化。
- 不在卡片上显示虚构的评分、热度或推荐指数。
- 卡片点击进入详情页，按钮点击不能意外触发导航。

## 8. 数据模型

### 8.1 Web Style Record

前端直接消费的风格记录应由 `style.json` 转换得到：

```ts
export type WebStyle = {
  id: string;
  version: string;
  status: "draft" | "active" | "deprecated";
  name: string;
  description: string;
  category: "illustration" | "painting" | "photographic" | "3d" | "graphic";
  tags: string[];
  aliases: string[];
  thumbnail: {
    src: string;
    alt: string;
  };
  features: Array<{
    id: string;
    axis: "medium" | "line" | "palette" | "lighting" | "texture" | "composition";
    tier: "core" | "support" | "accent";
    text: string;
  }>;
  avoid: Array<{ id: string; text: string }>;
  suitableFor: string[];
  weakFor: string[];
  knownFailures: string[];
  provenance: {
    sourceType: string;
    sourceRef: string | null;
    licenseRef: string | null;
    commercialUse: string;
    attribution: string | null;
  };
  quality: {
    reviewStatus: string;
    testedTool: string | null;
    testedAt: string | null;
    evidenceRef: string | null;
  };
  examples: ExampleImage[];
};

export type ExampleImage = {
  id: string;
  src: string;
  alt: string;
  subjectCategory: "人物" | "物体" | "场景";
  sourceVersion: string;
};
```

### 8.2 Examples Manifest

构建脚本生成 `examples-manifest.json`：

```json
{
  "library_version": "0.6.0",
  "styles": {
    "Aix0111": {
      "source_version": "0.6.0",
      "rights_ref": "evaluation/rights/Aix0111.md",
      "examples": [
        {
          "id": "Aix0111-01",
          "src": "/assets/examples/Aix0111/01.png",
          "subject_category": "人物",
          "alt": "碎面星爆风格示例 1，人物"
        }
      ]
    }
  }
}
```

### 8.3 资源版本选择规则

示例图在不同 `evaluation/results` 版本中存在重复。构建脚本必须：

1. 扫描所有 `evaluation/results/*/images/<ID>-01.png` 至 `<ID>-06.png`。
2. 读取对应的 `evaluation/results/<version>/<ID>.json`。
3. 只接受 6 张图片全部存在且 JSON 中有 `subject_category` 的批次。
4. 按语义版本号排序，选择最高可用批次。
5. 将该批次复制到 `web/public/assets/examples/<ID>/`。
6. 记录 `source_version` 和 `rights_ref`。
7. 发现缺失、重复编号、非 6 张或权利记录缺失时终止构建。

当前预期映射大致为：

| 风格范围 | 优先批次 |
|---|---|
| Aix0001–Aix0010 | 0.2.0 优先，0.1.0 作为历史回退 |
| Aix0011–Aix0020 | 0.3.0 |
| Aix0021–Aix0070 | 0.4.0 |
| Aix0071–Aix0110 | 0.5.0 |
| Aix0111–Aix0160 | 0.6.0 |

不要把 `evaluation/results` 的内部路径直接写入浏览器 JSON。

## 9. 数据构建脚本

### 9.1 `build-web-data.py`

执行位置：仓库根目录。

```bash
python3 web/scripts/build-web-data.py
```

脚本步骤：

1. 读取 `library.json`。
2. 读取 `catalog/index.json`。
3. 为每个 active 风格读取 `styles/<ID>/style.json`。
4. 构建唯一示例图来源清单。
5. 校验每个风格正好有 6 张示例图。
6. 校验每张图的类别来自对应评测 JSON。
7. 复制缩略图和示例图到 `web/public/assets/`。
8. 生成 `catalog.json`、`styles.json`、`examples-manifest.json`。
9. 写入 `library_version`、生成日期和 source digest。

### 9.2 `check-web-data.py`

执行：

```bash
python3 web/scripts/check-web-data.py
```

必须检查：

- catalog 风格数量等于 styles 数量。
- active 风格数量等于当前预期数量。
- 每个 active 风格有详情记录。
- 每个 active 风格有 thumbnail。
- 每个 active 风格有 6 个 example。
- example 编号恰好是 `01` 至 `06`。
- example 类别恰好是人物 2、物体 2、场景 2。
- 所有资源路径都在 `web/public/assets/` 内。
- 不存在 `evaluation/sources/` 路径。
- 页面显示版本等于 `library.json`。
- 所有图片文件均可解码。

## 10. 搜索与筛选行为

### 10.1 精确编号

输入以下内容必须打开同一个详情页：

```text
0001
1
Aix0001
aix-0001
```

如果编号不存在：

```text
没有找到 Aix9999。
请检查编号，或改用视觉描述搜索。
```

网页不能自动跳到相邻编号。

### 10.2 关键词搜索

搜索字段顺序：

1. ID
2. name
3. aliases
4. tags
5. description
6. suitableFor

搜索结果必须保留匹配原因。默认最多展示 3 个高相关结果；用户点击“显示全部”后再显示完整结果。

### 10.3 筛选器

第一版筛选器：

- Category
- Tags
- Suitable for
- Visual axis
- Sort

筛选条件以 URL query string 保存。

### 10.4 空状态

搜索无结果时显示：

```text
没有匹配的风格

尝试减少关键词，或直接输入 Aix 编号。
[清除筛选]
```

不要在无匹配时强行推荐无关风格。

## 11. 调用面板

每个详情页都提供调用面板，分为三个 Tab：

### Tab 1：自然语言

```text
使用 $aix-style-library 的 Aix0001 风格，……
```

### Tab 2：CLI

```bash
python <skill-root>/scripts/aix.py get --id Aix0001
```

### Tab 3：JSON

展示符合 `request.schema.json` 的 `search` 或 `prepare` 示例。

每个代码块右侧提供复制按钮。复制成功使用短暂的非阻塞反馈，例如“已复制”，不使用阻塞弹窗。

## 12. 视觉设计系统

### 12.1 色彩

推荐“中性底色 + 单一信号色”：

```css
:root {
  --canvas: #f4f5f6;
  --surface: #ffffff;
  --ink: #15171a;
  --muted: #66707a;
  --line: #d9dde2;
  --accent: #e4572e;
  --accent-soft: #fff0eb;
  --danger: #a83a31;
}
```

不要使用 AI 紫色渐变，不要让 UI 色彩比缩略图更抢眼。

### 12.2 字体

- 中文正文：Noto Sans SC 或系统无衬线字体。
- 英文标题：Geist 或 IBM Plex Sans。
- 编号、命令、版本：IBM Plex Mono。

### 12.3 尺寸

- Header：64～72px。
- 内容最大宽度：1400px。
- 桌面页面边距：32～48px。
- 移动页面边距：16px。
- 网格间距：16～24px。
- 卡片圆角：4～8px。
- 主图和示例图统一 2:3。

### 12.4 可访问性

- 所有示例图使用可读 alt 文本。
- 颜色不能作为唯一的状态表达方式。
- 键盘可访问搜索、筛选、缩略图、Lightbox 和复制按钮。
- 所有按钮有明确 accessible name。
- Focus ring 不能被 `outline: none` 移除。
- 文字、边框和按钮满足 WCAG AA 对比度。
- 支持 `prefers-reduced-motion`。

## 13. 响应式断点

| 屏幕 | Explore | Detail Gallery |
|---|---|---|
| `< 640px` | 单列，筛选改为底部或顶部 Sheet | 主图 + 横向 6 张缩略图 |
| `640–1023px` | 2～3 列，筛选可折叠 | gallery 上下排列 |
| `>= 1024px` | 左侧筛选 + 4 列网格 | 左 5/12、右 7/12 |
| `>= 1440px` | 4～5 列网格 | 增大主图但保持 2:3 |

所有多列布局必须明确声明移动端折叠方式，不能依赖浏览器自动换行。

## 14. 状态设计

必须实现以下状态：

1. 初始加载。
2. 搜索中。
3. 有结果。
4. 无结果。
5. 详情资源加载中。
6. 单张示例图加载失败。
7. 不存在的风格编号。
8. 已复制。
9. Lightbox 打开。
10. 比较栏达到上限。

比较模式最多选择 3 个风格。达到上限后显示“最多比较 3 个风格”，不要静默删除旧选择。

## 15. 比较模式

比较模式为 P1，但组件结构从第一版就预留。

比较栏固定在底部，只显示已选编号和缩略图。点击“比较”进入：

```text
┌────────────┬────────────┬────────────┐
│ Aix0001    │ Aix0002    │ Aix0003    │
│ thumbnail  │ thumbnail  │ thumbnail  │
│ category   │ category   │ category   │
│ medium     │ medium     │ medium     │
│ palette    │ palette    │ palette    │
│ suitable   │ suitable   │ suitable   │
└────────────┴────────────┴────────────┘
```

比较结果必须基于真实字段，不显示算法分数。

## 16. 开发任务拆解

### Milestone 0：项目初始化

- [x] 创建 `web/` Vite + React + TypeScript 项目。
- [x] 配置轻量 history 路由（不引入额外路由依赖）。
- [x] 配置字体、颜色 token 和全局 CSS。
- [x] 确认开发命令：`npm run dev`、`npm run build`、`npm run check:data`。
- [x] 添加 `/`、`/styles/:styleId`、`/guide`、404 路由。

### Milestone 1：数据管线

- [x] 实现 `build-web-data.py`。
- [x] 实现最高可用评测批次选择。
- [x] 生成 160 个风格详情记录。
- [x] 生成 160 × 6 张示例图资源清单。
- [x] 复制缩略图到网页资源目录。
- [x] 实现 `check-web-data.py`。
- [x] 运行图片路径、数量和主体类别检查。

### Milestone 2：Explore

- [x] 实现 Header。
- [x] 实现搜索命令栏和 `⌘/Ctrl + K` 快捷键。
- [x] 实现分类和标签筛选。
- [x] 实现 URL query state。
- [x] 实现 StyleCard，并支持键盘打开。
- [x] 实现加载、空结果和错误状态。
- [x] 通过数据驱动路由确认 160 个风格均可打开详情页。

### Milestone 3：Style Detail

- [x] 实现 2:3 主图。
- [x] 实现 6 张示例缩略图布局。
- [x] 实现人物/物体/场景标记。
- [x] 实现点击切换和当前序号。
- [x] 实现移动端横向缩略图栏，并验证 390px 视口不发生页面横向溢出。
- [x] 实现 Lightbox、键盘切换和 Escape 关闭。
- [x] 实现 Style anatomy。
- [x] 实现 Suitable / Weak / Avoid / Known failures。
- [x] 实现 provenance 和 quality 信息。

### Milestone 4：Guide

- [x] 实现自然语言调用示例。
- [x] 实现 CLI 示例。
- [x] 实现搜索 JSON 示例。
- [x] 实现复制反馈和受限浏览器降级。
- [x] 解释 resolved / prepared / generated 边界。

### Milestone 5：质量与发布

- [x] 桌面端截图检查（1280px）。
- [x] 移动端截图检查（390px）。
- [x] 键盘交互检查（搜索、卡片、示例图、Lightbox）。
- [x] 检查所有图片 alt。
- [x] 检查无布局跳动和详情页横向溢出。
- [x] 检查无内部路径泄漏。
- [x] 检查版本号来自 `library.json`。
- [x] 构建静态发布包。

## 17. 验收标准

### 17.1 数据完整性

- active 风格数量与 catalog 一致。
- 每个 active 风格都有缩略图。
- 每个 active 风格都有 6 张样例。
- 每个风格样例编号是 01～06。
- 每个风格样例类别是人物 2、物体 2、场景 2。
- 任何风格缺少样例时，生产构建失败。

### 17.2 功能正确性

- `0001`、`1`、`Aix0001`、`aix-0001` 指向同一详情页。
- 不存在编号不会自动替换成相邻编号。
- 搜索结果显示匹配原因。
- 过滤状态可以通过 URL 分享和恢复。
- 详情页复制内容符合协议。
- 复制提示词不会声称图片已经生成。

### 17.3 视觉和布局

- 首页首屏可直接搜索和浏览。
- 详情页首屏能看到大图和 6 张样例缩略图。
- 桌面端 6 张样例不会被压缩到无法辨识。
- 移动端 6 张样例可横向浏览。
- 图片切换不会改变布局高度。
- 所有图片容器保持 2:3。
- Lightbox 不会遮挡操作按钮或产生页面横向滚动。

### 17.4 性能

- 首页首屏不加载所有示例大图，只加载缩略图和必要的第一张示例图。
- 示例图使用 lazy loading。
- 详情页只预加载当前图和下一张图。
- 160 个风格网格滚动保持流畅。
- 构建后不向浏览器暴露 `evaluation/sources`、生成 prompt 或远程生成 URL。

### 17.5 可访问性

- 键盘可以完成搜索、筛选、打开详情、切换样例和关闭 Lightbox。
- 图片 alt 包含风格名、示例编号和主体类别。
- 所有 icon-only button 有 tooltip 和 accessible label。
- 对比度通过 WCAG AA 检查。
- `prefers-reduced-motion` 下不执行非必要动画。

## 18. 测试清单

### 单元测试

- 编号归一化。
- 搜索排序和匹配原因。
- query string 编解码。
- 6 张样例 manifest 生成。
- 最高版本批次选择。
- `subject_category` 顺序校验。

### 集成测试

- Explore → Detail。
- Detail → 选择第 4 张样例。
- Detail → Lightbox → 键盘切换 → Escape。
- 搜索 → 筛选 → 刷新恢复。
- 复制自然语言、CLI、JSON。
- 失效图片的局部错误状态。

### 视觉回归

至少检查以下尺寸：

- 1440 × 900
- 1280 × 800
- 1024 × 768
- 768 × 1024
- 390 × 844
- 375 × 812

重点确认：

- 详情页 6 张示例图没有重叠。
- 移动端缩略图不会撑破页面。
- 主图切换前后容器尺寸不变。
- Header、Lightbox 和底部比较栏不互相遮挡。

## 19. 发布命令

建议最终命令：

```bash
python3 web/scripts/build-web-data.py
python3 web/scripts/check-web-data.py
cd web
npm run build
npm run preview
```

`npm run build` 已包含 TypeScript 类型检查；当前没有 `npm run test` 脚本。网页交互按测试清单另行验证。

发布前必须保存：

- 构建使用的 `library_version`。
- `catalog/index.json` 的 source digest。
- 示例图 manifest。
- 数据完整性检查结果。
- 桌面和移动端截图。

## 20. 后续迭代

### P1

- Prompt Playground。
- 风格比较。
- 相关风格推荐。
- 版本变更页。
- 本地最近浏览。

### P2

- 收藏夹。
- 本地导出选中风格。
- 用户生成结果归档。
- 多语言界面。
- 账号和云端同步。

账号、社区、在线生成和向量检索不纳入当前网页版本。

## 21. 开发完成定义

当以下条件全部满足时，Web MVP 才算完成：

1. `npm run build` 成功。
2. 数据构建检查通过。
3. 160 个 active 风格全部有详情页。
4. 每个详情页能浏览 6 张示例图。
5. 6 张图的主体类别显示正确。
6. 搜索、筛选、URL 状态和调用复制可用。
7. 桌面和移动端布局通过视觉检查。
8. 页面没有泄漏内部生成 prompt、原始素材路径或远程生成 URL。
9. 网页版本号和 Skill `library.json` 一致。
10. 网页明确区分 resolved、prepared 和 generated 三个阶段。
