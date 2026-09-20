# STEP 3D Render Tool

STEP 文件解析与 3D 渲染工具，可将 STEP 格式的工程零件文件转换为可视化 3D 图像。

## 功能特性

- **STEP 文件解析**：解析 STEP AP203/AP214 格式的 3D CAD 数据
- **单部件渲染**：将单个零件渲染为 PNG 图像（多角度视图）
- **装配体渲染**：解析并渲染完整装配体，生成组合渲染图
- **HTML 报告**：生成包含所有渲染结果的交互式 HTML 报告
- **生产文件生成**：自动生成 BOM、图纸标注等生产相关文件

## 技术栈

| 项目 | 技术 |
|------|------|
| 语言 | Python 3.8+ |
| 3D 渲染 | matplotlib (Agg 后端) |
| 数据处理 | numpy, json |
| 输出格式 | PNG, HTML, JSON |

## 核心模块

| 文件 | 说明 |
|------|------|
| `step_parser_v3.py` | STEP 文件解析器，提取面/边/顶点数据 |
| `render_parts.py` | 单部件渲染，生成多角度 PNG 视图 |
| `render_assembly.py` | 装配体渲染，合并多个部件 |
| `generate_3d_report_v2.py` | 生成 3D 渲染 HTML 报告 |
| `generate_html_report.py` | 生成通用 HTML 报告 |
| `generate_production_files.py` | 生成生产相关导出文件 |

## 使用方法

```python
# 解析 STEP 文件
from step_parser_v3 import parse_step_file
entities = parse_step_file("part.step")

# 渲染单部件
from render_parts import render_part
render_part(entities, "output.png")

# 渲染装配体
from render_assembly import render_assembly
render_assembly(entities_list, "assembly.png")
```

## 输入输出

**输入**: `.step` 或 `.stp` 格式的 CAD 文件
**输出**: 
- PNG 渲染图 (`part_images/` 目录)
- HTML 报告 (`*_report.html`)
- JSON 数据 (`*.json`)

## 环境要求

- Python 3.8+
- `matplotlib` (与 Agg 后端)
- `numpy`

```bash
pip install matplotlib numpy
```

## 许可证

MIT
