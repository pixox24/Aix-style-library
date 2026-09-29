# 0.5.0 批次验收与发布记录

## 范围

- 版本：`0.5.0`（preview）
- 新增来源：收藏图 61–100
- 新增风格：`Aix0071–Aix0110`，40 个
- 每风格样例：6 张，人物/物体/场景各 2 张
- 新增真实样例：240 张
- 全库：110 个 active 风格、660 张视觉证据

## 真实出图

- 模型：`gpt-image-2`
- 当前路由：`https://gateway.change2pro.com`
- 请求尺寸：`1024x1536`
- 生成清单：`gen_manifest_v2.json`，240/240
- 实际像素：240/240 为 `1024x1536`
- 每个新风格：6/6 图片齐全
- 凭据未写入本记录或发布包

## 评审与证据

- `review_results.json`：240/240，0 条错误
- 风格评分：3 张 style=3、11 张 style=4、226 张 style=5；内容评分没有低于 4 的样例
- `Aix0071–Aix0110` 证据记录：40/40
- 每个证据记录：6 张样例，三类主体各 2 张
- 评审模式：自动化 self-blind；limitations 已写入证据记录
- 新风格缩略图：40/40，真实出图转换为 WebP，长边 640，均通过尺寸和体积检查

## 校验与测试

```text
validate --scope all       OK
  checked_styles=110
  checked_assets=110
  active_styles=110

validate --scope release   OK
  release_profile=preview
  visual_samples=660
  warning=PREVIEW_ONLY

python -m unittest discover -s tests
  Ran 78 tests
  OK
```

`PREVIEW_ONLY` 是预期状态：0.x 版本不代表正式 v1.0 验收，不包含正式五门 acceptance gates。

## 发布产物

- `releases/aix-style-library-0.5.0.zip`
- ZIP 解包测试：通过
- 包内版本：`0.5.0`
- 包内风格：110 个，active 110 个
- SHA-256：`fe5161fefe5a38ee7c337d5bd344640f85efd5c9aa4ec71bb72f2631649e5e84`
- 与 0.4.1 baseline 的版本/内容一致性检查：通过

## 备注

此前旧路由曾返回 `403 INSUFFICIENT_BALANCE`，导致 `Aix0110` 暂缺。切换到当前路由和凭据后，6 张缺失样例已断点补齐并重新评审；既有 234 张图片和 manifest 未被覆盖。
