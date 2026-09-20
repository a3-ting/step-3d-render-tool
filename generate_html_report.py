import json
import os
import re
import html

PROJECT_DIR = r'C:\Users\yh\AppData\Roaming\TRAE SOLO CN\ModularData\ai-agent\work-mode-projects\6a9698e44f0e5b6cccc8a92c'
PARTS_JSON = os.path.join(PROJECT_DIR, 'step_parts_info.json')
PART_IMAGES_DIR = os.path.join(PROJECT_DIR, 'part_images')
SVG_DIR = os.path.join(PROJECT_DIR, 'production_files', 'SVG')
DXF_DIR = os.path.join(PROJECT_DIR, 'production_files', 'DXF')
STEP_DIR = os.path.join(PROJECT_DIR, 'production_files', 'STEP')
BOM_PATH = os.path.join(PROJECT_DIR, 'production_files', 'BOM', 'BOM.xlsx')
ASSEMBLY_IMG = os.path.join(PROJECT_DIR, 'assembly_3d_render.png')
OUTPUT_HTML = os.path.join(PROJECT_DIR, 'production_report.html')

def safe_filename(name, idx):
    safe = re.sub(r'[^\w\-]', '_', name)
    return f"part_{idx:04d}_{safe}"

def main():
    with open(PARTS_JSON, 'r', encoding='utf-8') as f:
        parts_info = json.load(f)

    unique_parts = []
    seen = set()
    for p in parts_info:
        if p['name'] not in seen:
            seen.add(p['name'])
            unique_parts.append(p)

    name_counts = {}
    for p in parts_info:
        name_counts[p['name']] = name_counts.get(p['name'], 0) + 1

    parts_data = []
    for i, part in enumerate(unique_parts):
        name = part['name']
        bbox = part.get('bbox') or {}
        size = bbox.get('size', [0, 0, 0])
        file_base = safe_filename(name, i + 1)

        img_path = None
        for ext in ['.png']:
            candidate = os.path.join(PART_IMAGES_DIR, file_base + ext)
            if os.path.exists(candidate):
                img_path = f"part_images/{file_base}{ext}"
                break
        if not img_path:
            try:
                files = [f for f in os.listdir(PART_IMAGES_DIR) if f.startswith(f"part_{i+1:04d}")]
                if files:
                    img_path = f"part_images/{files[0]}"
            except:
                pass

        svg_exists = os.path.exists(os.path.join(SVG_DIR, file_base + '.svg'))
        dxf_exists = os.path.exists(os.path.join(DXF_DIR, file_base + '.dxf'))
        step_exists = os.path.exists(os.path.join(STEP_DIR, file_base + '.stp'))

        parts_data.append({
            'idx': i + 1,
            'name': name,
            'x': size[0],
            'y': size[1],
            'z': size[2],
            'qty': name_counts.get(name, 1),
            'img': img_path,
            'svg': f"production_files/SVG/{file_base}.svg" if svg_exists else None,
            'dxf': f"production_files/DXF/{file_base}.dxf" if dxf_exists else None,
            'stp': f"production_files/STEP/{file_base}.stp" if step_exists else None,
            'volume': round(size[0] * size[1] * size[2], 1),
        })

    parts_json = json.dumps(parts_data, ensure_ascii=False)

    html_content = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Production Files Report - 舱体+基座模型</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: 'Segoe UI', system-ui, sans-serif; background: #0d1117; color: #c9d1d9; }}
.header {{ background: linear-gradient(135deg, #1a1f2e, #0d1117); padding: 24px 32px; border-bottom: 1px solid #30363d; position: sticky; top: 0; z-index: 100; }}
.header h1 {{ color: #58a6ff; font-size: 22px; margin-bottom: 4px; }}
.header .stats {{ display: flex; gap: 24px; flex-wrap: wrap; }}
.header .stat {{ color: #8b949e; font-size: 13px; }}
.header .stat span {{ color: #d29922; font-weight: bold; }}
.search-box {{ padding: 12px 32px; background: #161b22; border-bottom: 1px solid #30363d; }}
.search-box input {{ width: 100%; max-width: 400px; padding: 8px 12px; background: #0d1117; border: 1px solid #30363d; border-radius: 6px; color: #c9d1d9; font-size: 14px; }}
.search-box input::placeholder {{ color: #6e7681; }}
.main {{ display: flex; gap: 1px; background: #30363d; min-height: calc(100vh - 120px); }}
.table-panel {{ flex: 0 0 480px; background: #0d1117; overflow-y: auto; }}
.detail-panel {{ flex: 1; background: #0d1117; overflow-y: auto; padding: 24px; }}
table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
thead {{ position: sticky; top: 0; background: #161b22; z-index: 10; }}
th {{ padding: 10px 12px; text-align: left; color: #8b949e; font-weight: 600; border-bottom: 1px solid #30363d; cursor: pointer; user-select: none; }}
th:hover {{ color: #58a6ff; }}
td {{ padding: 8px 12px; border-bottom: 1px solid #21262d; cursor: pointer; }}
tr:hover {{ background: #161b22; }}
tr.selected {{ background: #1c2536; }}
.dim {{ color: #7ee787; font-family: 'Consolas', monospace; }}
.link-btn {{ display: inline-block; padding: 4px 10px; border-radius: 4px; text-decoration: none; font-size: 12px; margin: 2px; }}
.link-btn.svg {{ background: #1f6feb; color: #fff; }}
.link-btn.dxf {{ background: #238636; color: #fff; }}
.link-btn.stp {{ background: #8957e5; color: #fff; }}
.link-btn.bom {{ background: #d29922; color: #000; }}
.link-btn:hover {{ opacity: 0.85; }}
.detail-card {{ background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 20px; margin-bottom: 20px; }}
.detail-card h2 {{ color: #58a6ff; margin-bottom: 12px; font-size: 18px; }}
.detail-card .dims {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 16px; }}
.detail-card .dim-box {{ background: #0d1117; border: 1px solid #30363d; border-radius: 6px; padding: 12px; text-align: center; }}
.detail-card .dim-box .label {{ color: #8b949e; font-size: 12px; margin-bottom: 4px; }}
.detail-card .dim-box .value {{ color: #d29922; font-size: 20px; font-weight: bold; font-family: 'Consolas', monospace; }}
.detail-card .dim-box .unit {{ color: #6e7681; font-size: 12px; }}
.part-img {{ max-width: 100%; border-radius: 8px; border: 1px solid #30363d; }}
.assembly-section {{ margin-bottom: 24px; }}
.assembly-section img {{ max-width: 100%; border-radius: 8px; border: 1px solid #30363d; }}
.file-links {{ display: flex; flex-wrap: wrap; gap: 8px; margin-top: 12px; }}
.no-select {{ color: #6e7681; font-style: italic; padding: 40px; text-align: center; }}
.qty-badge {{ display: inline-block; background: #238636; color: #fff; border-radius: 10px; padding: 1px 8px; font-size: 11px; margin-left: 6px; }}
</style>
</head>
<body>
<div class="header">
    <h1>Production Files Report</h1>
    <div class="stats">
        <div class="stat">Parts: <span>{len(parts_data)}</span></div>
        <div class="stat">Instances: <span>{len(parts_info)}</span></div>
        <div class="stat">SVG: <span>481</span></div>
        <div class="stat">DXF: <span>481</span></div>
        <div class="stat">STEP: <span>482</span></div>
        <div class="stat">BOM: <span>1</span></div>
    </div>
</div>
<div class="search-box">
    <input type="text" id="searchInput" placeholder="Search part name..." oninput="filterTable()">
</div>
<div class="main">
    <div class="table-panel">
        <table id="partsTable">
            <thead>
                <tr>
                    <th onclick="sortTable(0)">#</th>
                    <th onclick="sortTable(1)">Name</th>
                    <th onclick="sortTable(2)">X</th>
                    <th onclick="sortTable(3)">Y</th>
                    <th onclick="sortTable(4)">Z</th>
                    <th onclick="sortTable(5)">Qty</th>
                </tr>
            </thead>
            <tbody id="partsBody"></tbody>
        </table>
    </div>
    <div class="detail-panel" id="detailPanel">
        <div class="assembly-section">
            <div class="detail-card">
                <h2>Assembly 3D Render</h2>
                <img src="assembly_3d_render.png" alt="Assembly" class="part-img">
                <div class="file-links">
                    <a class="link-btn bom" href="production_files/BOM/BOM.xlsx">Download BOM (Excel)</a>
                </div>
            </div>
        </div>
        <div class="no-select">Click a part from the table to view details</div>
    </div>
</div>
<script>
const partsData = {parts_json};
let currentIdx = -1;

function renderTable(data) {{
    const tbody = document.getElementById('partsBody');
    tbody.innerHTML = data.map(p => `
        <tr ${{p.idx === currentIdx ? 'class="selected"' : ''}} onclick="selectPart(${{p.idx}})">
            <td>${{p.idx}}</td>
            <td>${{escapeHtml(p.name)}}${{p.qty > 1 ? `<span class="qty-badge">x${{p.qty}}</span>` : ''}}</td>
            <td class="dim">${{p.x.toFixed(1)}}</td>
            <td class="dim">${{p.y.toFixed(1)}}</td>
            <td class="dim">${{p.z.toFixed(1)}}</td>
            <td>${{p.qty}}</td>
        </tr>
    `).join('');
}}

function escapeHtml(s) {{
    const d = document.createElement('div');
    d.textContent = s;
    return d.innerHTML;
}}

function selectPart(idx) {{
    currentIdx = idx;
    document.querySelectorAll('tr').forEach(tr => tr.classList.remove('selected'));
    const part = partsData.find(p => p.idx === idx);
    if (!part) return;

    let links = '';
    if (part.svg) links += `<a class="link-btn svg" href="${{part.svg}}" download>SVG Drawing</a>`;
    if (part.dxf) links += `<a class="link-btn dxf" href="${{part.dxf}}" download>DXF File</a>`;
    if (part.stp) links += `<a class="link-btn stp" href="${{part.stp}}" download>STEP File</a>`;
    if (!links) links = '<span style="color:#6e7681">No production files available</span>';

    let imgHtml = part.img
        ? `<img src="${{part.img}}" alt="${{escapeHtml(part.name)}}" class="part-img">`
        : '<div class="no-select">No 3D render available</div>';

    document.getElementById('detailPanel').innerHTML = `
        <div class="detail-card">
            <h2>${{escapeHtml(part.name)}} ${{part.qty > 1 ? `<span class="qty-badge">x${{part.qty}}</span>` : ''}}</h2>
            <div class="dims">
                <div class="dim-box"><div class="label">Length (X)</div><div class="value">${{part.x.toFixed(1)}}</div><div class="unit">mm</div></div>
                <div class="dim-box"><div class="label">Width (Y)</div><div class="value">${{part.y.toFixed(1)}}</div><div class="unit">mm</div></div>
                <div class="dim-box"><div class="label">Height (Z)</div><div class="value">${{part.z.toFixed(1)}}</div><div class="unit">mm</div></div>
            </div>
            <div style="color:#8b949e;font-size:13px;margin-bottom:12px">Volume: ${{part.volume.toLocaleString()}} mm³ | Part #${{part.idx}}</div>
            <div class="file-links">${{links}}</div>
        </div>
        <div class="detail-card">
            <h2>3D Render</h2>
            ${{imgHtml}}
        </div>
    `;
    renderTable(filteredParts);
}}

let filteredParts = partsData;
function filterTable() {{
    const query = document.getElementById('searchInput').value.toLowerCase();
    filteredParts = partsData.filter(p =>
        p.name.toLowerCase().includes(query) ||
        String(p.idx) === query
    );
    renderTable(filteredParts);
}}

let sortCol = -1, sortAsc = true;
function sortTable(col) {{
    if (sortCol === col) sortAsc = !sortAsc;
    else {{ sortCol = col; sortAsc = true; }}
    const sorted = [...filteredParts].sort((a, b) => {{
        let va = Object.values(a)[col], vb = Object.values(b)[col];
        if (typeof va === 'string') return sortAsc ? va.localeCompare(vb) : vb.localeCompare(va);
        return sortAsc ? va - vb : vb - va;
    }});
    filteredParts = sorted;
    renderTable(sorted);
}}

renderTable(partsData);
</script>
</body>
</html>'''

    with open(OUTPUT_HTML, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"HTML report saved to: {OUTPUT_HTML}")
    print(f"Parts in report: {len(parts_data)}")

if __name__ == '__main__':
    main()
