# xinhuo Image to Code

`xinhuo-image-to-code` 是一个面向 AI 编程助手（Codex、Cursor、TRAE等）的图片UI设计稿转代码与切图 Skill，目标是把选中的 UI 图片或设计截图按 **750px 画板宽度**进行像素级还原，并导出独立透明 PNG 切图资源。

## 调用名

```text
$xinhuo-image-to-code
```

## 适用场景

- 将移动端 UI 截图还原为 HTML/CSS/JS 或项目内前端代码
- 将设计图按 750px 宽度等比还原
- 从源图中提取头像、图标、插画、装饰图、导航图标等透明 PNG 资源
- 保留文本为可编辑文本层
- 将简单矩形、圆角卡片、按钮、分割线等转为原生 CSS / 矢量形状
- 对切图位置、尺寸、透明背景和整页还原效果做验收

## 核心原则

- 原图是唯一视觉源，不允许凭感觉重绘或重新设计
- 画板宽度必须精确为 `750px`
- 所有元素按同一比例缩放
- 禁止自动排版、优化间距、重排布局
- 禁止用相似图标库、相似插画、AI 生成图或占位素材替代原图资源
- 切图必须来自当前源图对应区域
- 切图必须是透明背景 PNG
- 切图区域必须先通过 bbox 预览确认
- 不允许自动 trim、智能裁边、内容自适应缩边
- 交付前必须进行 bbox、PNG 透明度、贴边和整页叠图校验

## 工作流

```text
1. 读取当前源图，记录原始尺寸
2. 计算缩放比例：scale = 750 / source_width
3. 创建 layers.manifest.json（原图 bbox / 缩放 bbox / 类型 / z-index / 资源路径）
4. 使用 bbox 预览脚本检查切图区域
5. 按 manifest 从源图导出透明 PNG 切图
6. 使用 manifest 坐标实现 750px 固定画板代码
7. 分别验收矢量层、文本层、位图/图标切图层
8. 截图并与 750px 原图叠图复核
```

## 目录结构

```text
xinhuo-image-to-code/
├── SKILL.md              # Skill 主指令文件
├── README.md             # Skill说明文件
├── agents/
│   └── codeai.yaml       # Agent 配置
├── references/
│   └── slicing.md        # 切图规范参考
└── scripts/
    ├── audit_png_assets.py    # PNG 切图审计
    ├── compare_images.py      # 图片差异对比
    ├── extract_png_asset.py   # 按 bbox 导出 PNG
    └── preview_bboxes.py      # 预览 bbox 框选
```

## Manifest 示例

以下数据来自真实项目——将一张 390px 宽的江苏城市足球联赛 UI 设计图还原为 750px 画板代码。manifest 记录了源图信息、缩放比例以及每个图层的精确坐标：

```json
{
  "source_image": "sl.png",
  "source_dimensions": { "width": 390, "height": 876 },
  "scale_factor": 1.923077,
  "target_dimensions": { "width": 750, "height": 1685 },
  "background": {
    "id": "page-background",
    "type": "bitmap",
    "asset": "assets/zhuweibg.jpg",
    "notes": "整个页面背景图，包含蓝色边框和浅蓝渐变内容区域"
  },
  "layers": [
    {
      "id": "header-illustration",
      "type": "bitmap",
      "source_bbox": { "x": 0, "y": 0, "width": 390, "height": 170 },
      "scaled_bbox": { "x": 0, "y": 0, "width": 750, "height": 327 },
      "z_index": 1,
      "asset": "assets/header-illustration.png",
      "transparent_required": false,
      "notes": "顶部体育场背景插画"
    },
    {
      "id": "team-nanjing",
      "type": "bitmap",
      "source_bbox": { "x": 170, "y": 550, "width": 50, "height": 50 },
      "scaled_bbox": { "x": 327, "y": 1058, "width": 96, "height": 96 },
      "z_index": 10,
      "asset": "assets/teams/nanjing.png",
      "transparent_required": true,
      "notes": "南京队队徽"
    },
    {
      "id": "team-suzhou",
      "type": "bitmap",
      "source_bbox": { "x": 35, "y": 550, "width": 50, "height": 50 },
      "scaled_bbox": { "x": 67, "y": 1058, "width": 96, "height": 96 },
      "z_index": 10,
      "asset": "assets/teams/suzhou.png",
      "transparent_required": true,
      "notes": "苏州队队徽"
    }
  ]
}
```

关键要点：`scale_factor = 750 / 390 ≈ 1.923`，所有 `source_bbox` 坐标乘以该比例得到 `scaled_bbox`，代码实现直接使用 `scaled_bbox` 在 750px 画板上定位。队徽类资源设置 `transparent_required: true` 以导出透明背景 PNG。

## skill脚本说明

### 预览 bbox

在源图上画出 manifest 中记录的 bbox，用于检查切图区域是否准确。

```bash
scripts/preview_bboxes.py source.png layers.manifest.json qa/bbox-preview.png --only-type bitmap
```

### 按 bbox 导出 PNG

从源图按精确 bbox 导出透明 PNG，不会自动 trim，输出画布固定等于 bbox。

```bash
scripts/extract_png_asset.py source.png assets/icons/icon-user.png \
  --x 120 --y 980 --width 72 --height 72 \
  --remove-bg floodfill \
  --manifest layers.manifest.json \
  --id icon-user
```

### 审计 PNG 切图

检查 PNG 是否贴边、尺寸是否匹配、透明背景是否合格。

```bash
scripts/audit_png_assets.py assets/icons assets/images \
  --require-transparent-bg \
  --manifest layers.manifest.json
```

### 图片差异对比

对比 750px 原图和最终渲染截图。

```bash
scripts/compare_images.py reference-750.png render-750.png --json
```

## 验收标准

| 检查项 | 要求 |
|--------|------|
| 画板宽度 | 精确 `750px` |
| 页面布局 | 和原图同位置、同尺寸、同层级 |
| 文本 | 可编辑文本，不 rasterize 到整页图中 |
| 简单图形 | CSS / 原生矢量实现 |
| 切图来源 | 头像、图标、插画、装饰图等从当前源图提取 |
| PNG 透明度 | 有 alpha 通道，背景透明 |
| PNG 边缘 | 不贴边、不缺失、不带白色或灰色矩形背景 |
| bbox 预览 | 框选区域准确覆盖完整元素外框 |
| 整页叠图 | 最终截图和 750px 原图叠图无明显偏移、缺图、裁切 |

## 安装

将整个目录放到 您常用的AI 编程助手的 skills 目录即可

然后在对话中调用：

```text
使用 $xinhuo-image-to-code 将当前选中的 UI 图片或设计稿转换为代码，并导出透明 PNG 切图资源。
```

## License

MIT
