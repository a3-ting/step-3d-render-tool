import json
import os

with open(r'C:\Users\yh\AppData\Roaming\TRAE SOLO CN\ModularData\ai-agent\work-mode-projects\6a9698e44f0e5b6cccc8a92c\rendered_parts.json', 'r', encoding='utf-8') as f:
    parts = json.load(f)

cards_html = ""
for i, p in enumerate(parts):
    img_path = f"part_images/{p['image']}"
    size = p['size']
    max_dim = max(size)
    if max_dim > 1000:
        badge = 'large'
        cat = '大型'
    elif max_dim > 100:
        badge = 'medium'
        cat = '中型'
    else:
        badge = 'small'
        cat = '小型'

    vol = size[0] * size[1] * size[2]

    cards_html += f'''
    <div class="card" data-name="{p['name'].lower()}" data-maxdim="{max_dim:.1f}" data-vol="{vol}" data-idx="{i}">
      <div class="card-img">
        <img src="{img_path}" alt="{p['name']}" loading="lazy">
      </div>
      <div class="card-body">
        <div class="card-title" title="{p['name']}">{p['name']}</div>
        <div class="card-dims">
          <span class="dim dim-x">X: {size[0]}mm</span>
          <span class="dim dim-y">Y: {size[1]}mm</span>
          <span class="dim dim-z">Z: {size[2]}mm</span>
        </div>
        <div class="card-meta">
          <span class="badge badge-{badge}">{cat}</span>
          <span class="vol">V: {vol:,.0f}mm³</span>
          <span class="edges">E: {p['edges']}</span>
        </div>
      </div>
    </div>'''

html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>STEP 零件 3D 渲染图与尺寸报告</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif; background: #0d1117; color: #e6edf3; padding: 20px; }}
  .header {{ background: linear-gradient(135deg, #161b22, #1a3a5a); border-radius: 12px; padding: 24px 30px; margin-bottom: 20px; border: 1px solid #30363d; }}
  .header h1 {{ font-size: 24px; color: #58a6ff; margin-bottom: 6px; }}
  .header .subtitle {{ color: #8b949e; font-size: 14px; }}
  .header .stats {{ display: flex; gap: 24px; margin-top: 16px; flex-wrap: wrap; }}
  .header .stat {{ text-align: center; }}
  .header .stat .num {{ font-size: 22px; font-weight: 700; color: #58a6ff; }}
  .header .stat .lbl {{ font-size: 11px; color: #8b949e; margin-top: 2px; }}
  .toolbar {{ display: flex; gap: 12px; margin-bottom: 20px; flex-wrap: wrap; align-items: center; position: sticky; top: 0; z-index: 100; background: #0d1117; padding: 12px 0; }}
  .toolbar input, .toolbar select {{ background: #161b22; border: 1px solid #30363d; color: #e6edf3; padding: 10px 14px; border-radius: 8px; font-size: 14px; }}
  .toolbar input {{ flex: 1; min-width: 200px; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 16px; }}
  .card {{ background: #161b22; border: 1px solid #30363d; border-radius: 10px; overflow: hidden; cursor: pointer; transition: transform 0.2s, border-color 0.2s; }}
  .card:hover {{ transform: translateY(-3px); border-color: #58a6ff; box-shadow: 0 8px 24px rgba(88, 166, 255, 0.15); }}
  .card-img {{ width: 100%; height: 220px; overflow: hidden; background: #0d1117; display: flex; align-items: center; justify-content: center; }}
  .card-img img {{ width: 100%; height: 100%; object-fit: contain; }}
  .card-body {{ padding: 12px 14px; }}
  .card-title {{ font-size: 14px; font-weight: 600; color: #58a6ff; margin-bottom: 8px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
  .card-dims {{ display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 8px; }}
  .card-dims .dim {{ font-size: 12px; font-family: 'Consolas', monospace; font-weight: 600; }}
  .dim-x {{ color: #ff7b72; }}
  .dim-y {{ color: #7ee787; }}
  .dim-z {{ color: #d29922; }}
  .card-meta {{ display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }}
  .badge {{ display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 10px; font-weight: 600; }}
  .badge-large {{ background: rgba(255, 123, 114, 0.15); color: #ff7b72; border: 1px solid rgba(255, 123, 114, 0.3); }}
  .badge-medium {{ background: rgba(210, 153, 34, 0.15); color: #d29922; border: 1px solid rgba(210, 153, 34, 0.3); }}
  .badge-small {{ background: rgba(126, 231, 135, 0.15); color: #7ee787; border: 1px solid rgba(126, 231, 135, 0.3); }}
  .vol, .edges {{ font-size: 11px; color: #8b949e; }}
  .modal {{ display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.9); z-index: 1000; align-items: center; justify-content: center; }}
  .modal.active {{ display: flex; }}
  .modal-content {{ max-width: 90%; max-height: 90%; background: #161b22; border-radius: 12px; border: 1px solid #30363d; overflow: hidden; display: flex; flex-direction: column; }}
  .modal-header {{ padding: 16px 20px; border-bottom: 1px solid #30363d; display: flex; justify-content: space-between; align-items: center; }}
  .modal-header h3 {{ color: #58a6ff; font-size: 18px; }}
  .modal-close {{ background: none; border: none; color: #8b949e; font-size: 28px; cursor: pointer; line-height: 1; }}
  .modal-close:hover {{ color: #ff7b72; }}
  .modal-body {{ display: flex; flex-direction: column; align-items: center; padding: 20px; overflow: auto; }}
  .modal-body img {{ max-width: 100%; max-height: 70vh; object-fit: contain; }}
  .modal-info {{ display: flex; gap: 20px; margin-top: 16px; flex-wrap: wrap; justify-content: center; }}
  .modal-info span {{ font-size: 14px; font-family: 'Consolas', monospace; }}
  .footer {{ text-align: center; padding: 20px; color: #6e7681; font-size: 12px; margin-top: 20px; }}
</style>
</head>
<body>

<div class="header">
  <h1>STEP 零件 3D 渲染图与尺寸报告</h1>
  <div class="subtitle">舱体+基座模型.stp &mdash; {len(parts)} 个去重零件的 BREP 线框 3D 渲染图，标注 X/Y/Z 包络框尺寸</div>
  <div class="stats">
    <div class="stat"><div class="num">{len(parts)}</div><div class="lbl">去重零件</div></div>
    <div class="stat"><div class="num">487</div><div class="lbl">原始实例</div></div>
    <div class="stat"><div class="num">{sum(p['edges'] for p in parts):,}</div><div class="lbl">总边数</div></div>
    <div class="stat"><div class="num">{sum(p['points'] for p in parts):,}</div><div class="lbl">总顶点</div></div>
  </div>
</div>

<div class="toolbar">
  <input type="text" id="search" placeholder="搜索零件名称..." oninput="filterCards()">
  <select id="sizeFilter" onchange="filterCards()">
    <option value="">全部尺寸</option>
    <option value="small">小型 (&lt;100mm)</option>
    <option value="medium">中型 (100-1000mm)</option>
    <option value="large">大型 (&gt;1000mm)</option>
  </select>
  <select id="sortOrder" onchange="sortCards()">
    <option value="default">默认顺序</option>
    <option value="volume-desc">体积 降序</option>
    <option value="volume-asc">体积 升序</option>
    <option value="name">名称排序</option>
  </select>
  <span style="color:#8b949e;font-size:14px" id="count">{len(parts)} 个零件</span>
</div>

<div class="grid" id="grid">
{cards_html}
</div>

<div class="modal" id="modal">
  <div class="modal-content">
    <div class="modal-header">
      <h3 id="modalTitle"></h3>
      <button class="modal-close" onclick="closeModal()">&times;</button>
    </div>
    <div class="modal-body">
      <img id="modalImg" src="" alt="">
      <div class="modal-info" id="modalInfo"></div>
    </div>
  </div>
</div>

<div class="footer">
  STEP 文件 3D 渲染报告 | 每个零件包含 BREP 线框 + 包络框尺寸标注 | 单位: 毫米 (mm)
</div>

<script>
function filterCards() {{
  const search = document.getElementById('search').value.toLowerCase();
  const sizeF = document.getElementById('sizeFilter').value;
  const cards = document.querySelectorAll('.card');
  let visible = 0;
  cards.forEach(card => {{
    const name = card.dataset.name || '';
    const maxDim = parseFloat(card.dataset.maxdim) || 0;
    let show = true;
    if (search && !name.includes(search)) show = false;
    if (show && sizeF) {{
      if (sizeF === 'small' && maxDim >= 100) show = false;
      if (sizeF === 'medium' && (maxDim < 100 || maxDim > 1000)) show = false;
      if (sizeF === 'large' && maxDim <= 1000) show = false;
    }}
    card.style.display = show ? '' : 'none';
    if (show) visible++;
  }});
  document.getElementById('count').textContent = visible + ' 个零件';
}}

function sortCards() {{
  const order = document.getElementById('sortOrder').value;
  const grid = document.getElementById('grid');
  const cards = Array.from(grid.querySelectorAll('.card'));
  cards.sort((a, b) => {{
    if (order === 'name') {{
      const na = a.querySelector('.card-title').textContent;
      const nb = b.querySelector('.card-title').textContent;
      return na.localeCompare(nb);
    }}
    if (order === 'volume-desc') return parseFloat(b.dataset.vol) - parseFloat(a.dataset.vol);
    if (order === 'volume-asc') return parseFloat(a.dataset.vol) - parseFloat(b.dataset.vol);
    return parseFloat(a.dataset.idx) - parseFloat(b.dataset.idx);
  }});
  cards.forEach(c => grid.appendChild(c));
}}

document.querySelectorAll('.card').forEach(card => {{
  card.addEventListener('click', function() {{
    const title = this.querySelector('.card-title').textContent;
    const imgSrc = this.querySelector('img').src;
    const dims = this.querySelectorAll('.dim');
    const x = dims[0].textContent.split(':')[1].trim().replace('mm','');
    const y = dims[1].textContent.split(':')[1].trim().replace('mm','');
    const z = dims[2].textContent.split(':')[1].trim().replace('mm','');
    const vol = parseFloat(this.dataset.vol);
    const edges = this.querySelector('.edges').textContent.split(':')[1].trim();
    document.getElementById('modalTitle').textContent = title;
    document.getElementById('modalImg').src = imgSrc;
    document.getElementById('modalInfo').innerHTML =
      '<span style="color:#ff7b72">X: ' + x + ' mm</span>' +
      '<span style="color:#7ee787">Y: ' + y + ' mm</span>' +
      '<span style="color:#d29922">Z: ' + z + ' mm</span>' +
      '<span style="color:#8b949e">体积: ' + vol.toLocaleString() + ' mm³</span>' +
      '<span style="color:#8b949e">边数: ' + edges + '</span>';
    document.getElementById('modal').classList.add('active');
  }});
}});

function closeModal() {{
  document.getElementById('modal').classList.remove('active');
}}

document.getElementById('modal').addEventListener('click', function(e) {{
  if (e.target === this) closeModal();
}});

document.addEventListener('keydown', (e) => {{
  if (e.key === 'Escape') closeModal();
}});
</script>

</body>
</html>'''

output_path = r'C:\Users\yh\AppData\Roaming\TRAE SOLO CN\ModularData\ai-agent\work-mode-projects\6a9698e44f0e5b6cccc8a92c\STEP_3D_render_report.html'
with open(output_path, 'w', encoding='utf-8') as f:
    f.write(html)
print(f"HTML report saved to {output_path}")
print(f"Report size: {os.path.getsize(output_path) / 1024:.1f} KB")
