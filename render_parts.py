import re
import json
import os
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from mpl_toolkits.mplot3d.art3d import Poly3DCollection, Line3DCollection
from collections import defaultdict
import math

def parse_step_file(filepath):
    entities = {}
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        in_data = False
        for line in f:
            line = line.strip()
            if not in_data:
                if line == 'DATA;':
                    in_data = True
                continue
            if line == 'ENDSEC;':
                break
            if not line or line.startswith('//') or line.startswith('/*'):
                continue
            match = re.match(r'#(\d+)=(.*)', line)
            if match:
                eid = int(match.group(1))
                rest = match.group(2)
                while not rest.rstrip().endswith(';'):
                    next_line = f.readline()
                    if not next_line:
                        break
                    rest += ' ' + next_line.strip()
                rest = rest.rstrip()
                if rest.endswith(';'):
                    rest = rest[:-1]
                type_match = re.match(r'([A-Z_]+)\s*\(', rest)
                if type_match:
                    etype = type_match.group(1)
                    entities[eid] = (etype, rest)
    return entities

def extract_refs(value_str):
    return [int(r) for r in re.findall(r'#(\d+)', value_str)]

def get_param_list(entity_str):
    paren_start = entity_str.find('(')
    if paren_start == -1:
        return []
    depth = 0
    last_paren = -1
    for i in range(paren_start, len(entity_str)):
        c = entity_str[i]
        if c == '(':
            depth += 1
        elif c == ')':
            depth -= 1
            if depth == 0:
                last_paren = i
                break
    if last_paren == -1:
        return []
    inner = entity_str[paren_start+1:last_paren]
    return split_params(inner)

def split_params(s):
    params = []
    depth = 0
    current = ''
    in_string = False
    for c in s:
        if c == "'" and not in_string:
            in_string = True
            current += c
        elif c == "'" and in_string:
            in_string = False
            current += c
        elif c == '(' and not in_string:
            depth += 1
            current += c
        elif c == ')' and not in_string:
            depth -= 1
            current += c
        elif c == ',' and depth == 0 and not in_string:
            params.append(current.strip())
            current = ''
        else:
            current += c
    if current.strip():
        params.append(current.strip())
    return params

def eval_exponent(s):
    s = s.strip()
    parts = s.split('E')
    if len(parts) == 2:
        base = float(parts[0])
        exp = int(parts[1])
        return base * (10 ** exp)
    return float(s)

def parse_cartesian_point(params):
    if len(params) >= 2:
        coords_str = params[1].strip()
        coord_match = re.search(r'\(([^)]+)\)', coords_str)
        if coord_match:
            coord_values = coord_match.group(1).split(',')
            coords = []
            for v in coord_values:
                v = v.strip()
                try:
                    coords.append(eval_exponent(v))
                except:
                    coords.append(0.0)
            if len(coords) == 3:
                return coords
    return None

def parse_direction(params):
    if len(params) >= 1:
        dir_str = params[0].strip()
        dir_match = re.search(r'\(([^)]+)\)', dir_str)
        if dir_match:
            values = dir_match.group(1).split(',')
            return [eval_exponent(v.strip()) for v in values]
    return [0, 0, 1]

def get_entity_type(eid, entities):
    if eid in entities:
        return entities[eid][0]
    return None

def find_product_from_pds(entities, pds_id):
    pds_entity = entities.get(pds_id)
    if not pds_entity:
        return None
    pds_refs = extract_refs(pds_entity[1])
    for r in pds_refs:
        if entities.get(r, (None,))[0] == 'PRODUCT_DEFINITION':
            pd_entity = entities.get(r)
            if not pd_entity:
                continue
            pd_refs = extract_refs(pd_entity[1])
            for r2 in pd_refs:
                if entities.get(r2, (None,))[0] in ('PRODUCT_DEFINITION_FORMATION', 'PRODUCT_DEFINITION_FORMATION_WITH_SPECIFIED_SOURCE'):
                    pdf_entity = entities.get(r2)
                    if not pdf_entity:
                        continue
                    pdf_refs = extract_refs(pdf_entity[1])
                    for r3 in pdf_refs:
                        if entities.get(r3, (None,))[0] == 'PRODUCT':
                            return r3
    return None

def get_product_name(entities, product_id):
    entity = entities.get(product_id)
    if not entity:
        return 'UNKNOWN'
    params = get_param_list(entity[1])
    if len(params) > 0:
        return params[0].strip().strip("'")
    return 'UNKNOWN'

def extract_geometry(entities, brep_id):
    """Extract vertices and edges from a BREP shape representation."""
    vertices = {}
    edges = []
    faces_data = []
    visited = set()

    def get_cartesian_point(eid):
        entity = entities.get(eid)
        if not entity or entity[0] != 'CARTESIAN_POINT':
            return None
        params = get_param_list(entity[1])
        return parse_cartesian_point(params)

    def process_edge_curve(eid):
        if eid in visited:
            return
        visited.add(eid)
        entity = entities.get(eid)
        if not entity:
            return
        refs = extract_refs(entity[1])
        v1 = None
        v2 = None
        edge_type = 'LINE'
        curve_data = None

        for r in refs:
            rtype = get_entity_type(r, entities)
            if rtype == 'VERTEX_POINT':
                vrefs = extract_refs(entities[r][1])
                for vr in vrefs:
                    if get_entity_type(vr, entities) == 'CARTESIAN_POINT':
                        pt = get_cartesian_point(vr)
                        if pt:
                            if v1 is None:
                                v1 = pt
                            else:
                                v2 = pt
            elif rtype == 'LINE':
                line_refs = extract_refs(entities[r][1])
                for lr in line_refs:
                    if get_entity_type(lr, entities) == 'CARTESIAN_POINT':
                        pt = get_cartesian_point(lr)
                        if pt:
                            if v1 is None:
                                v1 = pt
                            elif v2 is None:
                                v2 = pt
                    elif get_entity_type(lr, entities) == 'VECTOR':
                        vec_refs = extract_refs(entities[lr][1])
                        for vr in vec_refs:
                            if get_entity_type(vr, entities) == 'DIRECTION':
                                dparams = get_param_list(entities[vr][1])
                                direction = parse_direction(dparams)
                                vec_entity = entities.get(lr)
                                if vec_entity:
                                    vparams = get_param_list(vec_entity[1])
                                    magnitude = 0.0
                                    if len(vparams) > 1:
                                        try:
                                            magnitude = float(vparams[1].strip())
                                        except:
                                            pass
                                    if v1 and direction:
                                        v2 = [v1[i] + direction[i] * magnitude for i in range(3)]
            elif rtype == 'CIRCLE':
                edge_type = 'CIRCLE'
                circle_refs = extract_refs(entities[r][1])
                center = None
                radius = 0
                axis = [0, 0, 1]
                for cr in circle_refs:
                    crtype = get_entity_type(cr, entities)
                    if crtype == 'CARTESIAN_POINT':
                        center = get_cartesian_point(cr)
                    elif crtype == 'DIRECTION':
                        dparams = get_param_list(entities[cr][1])
                        axis = parse_direction(dparams)
                circle_params = get_param_list(entities[r][1])
                if len(circle_params) > 1:
                    try:
                        radius = float(circle_params[1].strip().strip("'"))
                    except:
                        pass
                curve_data = {'center': center, 'radius': radius, 'axis': axis}
            elif rtype in ('B_SPLINE_CURVE_WITH_KNOTS', 'B_SPLINE_CURVE'):
                edge_type = 'BSPLINE'
            elif rtype == 'POLYLINE':
                edge_type = 'POLYLINE'
                poly_refs = extract_refs(entities[r][1])
                poly_pts = []
                for pr in poly_refs:
                    if get_entity_type(pr, entities) == 'CARTESIAN_POINT':
                        pt = get_cartesian_point(pr)
                        if pt:
                            poly_pts.append(pt)
                curve_data = {'points': poly_pts}

        if v1 and v2:
            edges.append((v1, v2, edge_type, curve_data))
        elif curve_data and curve_data.get('points'):
            pts = curve_data['points']
            for i in range(len(pts)-1):
                edges.append((pts[i], pts[i+1], 'POLYLINE', None))

    def process_oriented_edge(eid):
        if eid in visited:
            return
        visited.add(eid)
        entity = entities.get(eid)
        if not entity:
            return
        refs = extract_refs(entity[1])
        for r in refs:
            if get_entity_type(r, entities) == 'EDGE_CURVE':
                process_edge_curve(r)

    def process_edge_loop(eid):
        if eid in visited:
            return
        visited.add(eid)
        entity = entities.get(eid)
        if not entity:
            return
        refs = extract_refs(entity[1])
        for r in refs:
            if get_entity_type(r, entities) == 'ORIENTED_EDGE':
                process_oriented_edge(r)
            elif get_entity_type(r, entities) == 'EDGE_LOOP':
                process_edge_loop(r)

    def process_face_bound(eid):
        if eid in visited:
            return
        visited.add(eid)
        entity = entities.get(eid)
        if not entity:
            return
        refs = extract_refs(entity[1])
        for r in refs:
            rtype = get_entity_type(r, entities)
            if rtype in ('EDGE_LOOP', 'VERTEX_LOOP'):
                process_edge_loop(r)

    def process_advanced_face(eid):
        if eid in visited:
            return
        visited.add(eid)
        entity = entities.get(eid)
        if not entity:
            return
        refs = extract_refs(entity[1])
        face_surface = None
        for r in refs:
            rtype = get_entity_type(r, entities)
            if rtype in ('FACE_BOUND', 'FACE_OUTER_BOUND'):
                process_face_bound(r)
            elif rtype in ('PLANE', 'CYLINDRICAL_SURFACE', 'CONICAL_SURFACE',
                           'SPHERICAL_SURFACE', 'TOROIDAL_SURFACE', 'B_SPLINE_SURFACE',
                           'SURFACE_OF_REVOLUTION', 'SURFACE_OF_LINEAR_EXTRUSION'):
                face_surface = rtype

    def process_closed_shell(eid):
        if eid in visited:
            return
        visited.add(eid)
        entity = entities.get(eid)
        if not entity:
            return
        refs = extract_refs(entity[1])
        for r in refs:
            if get_entity_type(r, entities) == 'ADVANCED_FACE':
                process_advanced_face(r)

    def process_manifold_solid_brep(eid):
        if eid in visited:
            return
        visited.add(eid)
        entity = entities.get(eid)
        if not entity:
            return
        refs = extract_refs(entity[1])
        for r in refs:
            rtype = get_entity_type(r, entities)
            if rtype in ('CLOSED_SHELL', 'OPEN_SHELL'):
                process_closed_shell(r)

    def traverse(eid, depth=0):
        if eid in visited or depth > 5:
            return
        entity = entities.get(eid)
        if not entity:
            return
        refs = extract_refs(entity[1])
        for r in refs:
            rtype = get_entity_type(r, entities)
            if rtype == 'MANIFOLD_SOLID_BREP':
                process_manifold_solid_brep(r)
            elif rtype == 'ADVANCED_BREP_SHAPE_REPRESENTATION':
                traverse(r, depth+1)

    brep_entity = entities.get(brep_id)
    if brep_entity:
        refs = extract_refs(brep_entity[1])
        for r in refs:
            rtype = get_entity_type(r, entities)
            if rtype == 'MANIFOLD_SOLID_BREP':
                process_manifold_solid_brep(r)
            elif rtype == 'AXIS2_PLACEMENT_3D':
                pass
            elif rtype == 'ADVANCED_BREP_SHAPE_REPRESENTATION':
                traverse(r)

    all_pts = []
    for e in edges:
        all_pts.append(e[0])
        all_pts.append(e[1])
        if e[3] and 'points' in (e[3] or {}):
            all_pts.extend(e[3].get('points', []))

    if not all_pts:
        for v in vertices.values():
            all_pts.append(v)

    return edges, all_pts

def compute_bbox(points):
    if not points:
        return None
    arr = np.array(points)
    mn = arr.min(axis=0)
    mx = arr.max(axis=0)
    return mn, mx

def render_part_3d(edges, points, part_name, bbox_size, output_dir, idx):
    """Render a 3D view of the part with dimension annotations."""
    fig = plt.figure(figsize=(10, 8), facecolor='#1a1a2e')
    ax = fig.add_subplot(111, projection='3d')
    ax.set_facecolor('#1a1a2e')

    if points:
        arr = np.array(points)
        cx, cy, cz = arr.mean(axis=0)
        max_range = max(bbox_size) if bbox_size else 1
        if max_range == 0:
            max_range = 1

        for e in edges:
            v1, v2, etype, cdata = e
            if etype == 'LINE' or etype == 'POLYLINE':
                ax.plot3D([v1[0], v2[0]], [v1[1], v2[1]], [v1[2], v2[2]],
                         color='#4fc3f7', linewidth=0.8, alpha=0.6)
            elif etype == 'CIRCLE' and cdata:
                center = cdata.get('center')
                radius = cdata.get('radius', 0)
                axis_dir = cdata.get('axis', [0, 0, 1])
                if center and radius > 0:
                    theta = np.linspace(0, 2*np.pi, 50)
                    if abs(axis_dir[2]) > 0.9:
                        xs = center[0] + radius * np.cos(theta)
                        ys = center[1] + radius * np.sin(theta)
                        zs = np.full_like(theta, center[2])
                    elif abs(axis_dir[1]) > 0.9:
                        xs = center[0] + radius * np.cos(theta)
                        ys = np.full_like(theta, center[1])
                        zs = center[2] + radius * np.sin(theta)
                    else:
                        xs = np.full_like(theta, center[0])
                        ys = center[1] + radius * np.cos(theta)
                        zs = center[2] + radius * np.sin(theta)
                    ax.plot3D(xs, ys, zs, color='#66bb6a', linewidth=0.8, alpha=0.5)
            else:
                ax.plot3D([v1[0], v2[0]], [v1[1], v2[1]], [v1[2], v2[2]],
                         color='#4fc3f7', linewidth=0.6, alpha=0.4)

    if points:
        mn = np.array(points).min(axis=0)
        mx = np.array(points).max(axis=0)
    else:
        mn = np.array([0, 0, 0])
        mx = np.array(bbox_size) if bbox_size else np.array([1, 1, 1])

    dx, dy, dz = mx - mn
    corners = [
        [mn[0], mn[1], mn[2]], [mx[0], mn[1], mn[2]],
        [mx[0], mx[1], mn[2]], [mn[0], mx[1], mn[2]],
        [mn[0], mn[1], mx[2]], [mx[0], mn[1], mx[2]],
        [mx[0], mx[1], mx[2]], [mn[0], mx[1], mx[2]]
    ]
    bbox_edges = [
        (0,1), (1,2), (2,3), (3,0),
        (4,5), (5,6), (6,7), (7,4),
        (0,4), (1,5), (2,6), (3,7)
    ]
    for a, b in bbox_edges:
        ax.plot3D([corners[a][0], corners[b][0]],
                  [corners[a][1], corners[b][1]],
                  [corners[a][2], corners[b][2]],
                  color='#ff6b6b', linewidth=1.5, linestyle='--', alpha=0.8)

    ax.text(mn[0] + dx/2, mn[1] - max(dx,dy,dz)*0.08, mn[2],
            f'X: {dx:.1f} mm', color='#ff6b6b', fontsize=11, fontweight='bold',
            ha='center', va='top')
    ax.text(mx[0] + max(dx,dy,dz)*0.05, mn[1] + dy/2, mn[2],
            f'Y: {dy:.1f} mm', color='#51cf66', fontsize=11, fontweight='bold',
            ha='left', va='center')
    ax.text(mn[0] - max(dx,dy,dz)*0.05, mn[1], mn[2] + dz/2,
            f'Z: {dz:.1f} mm', color='#ffd43b', fontsize=11, fontweight='bold',
            ha='right', va='center')

    margin = max(dx, dy, dz) * 0.15 if max(dx,dy,dz) > 0 else 1
    ax.set_xlim(mn[0] - margin, mx[0] + margin)
    ax.set_ylim(mn[1] - margin, mx[1] + margin)
    ax.set_zlim(mn[2] - margin, mx[2] + margin)

    ax.set_xlabel('X (mm)', color='#78909c', fontsize=9)
    ax.set_ylabel('Y (mm)', color='#78909c', fontsize=9)
    ax.set_zlabel('Z (mm)', color='#78909c', fontsize=9)

    title = f'{part_name}'
    subtitle = f'X={dx:.1f} × Y={dy:.1f} × Z={dz:.1f} mm'
    ax.set_title(title, color='#4fc3f7', fontsize=13, fontweight='bold', pad=20)
    fig.text(0.5, 0.92, subtitle, ha='center', color='#ffd43b', fontsize=11)

    ax.tick_params(colors='#546e7a', labelsize=8)
    ax.xaxis.pane.set_facecolor('#1a1a2e')
    ax.yaxis.pane.set_facecolor('#1a1a2e')
    ax.zaxis.pane.set_facecolor('#1a1a2e')
    ax.xaxis.pane.set_edgecolor('#2a2a4e')
    ax.yaxis.pane.set_edgecolor('#2a2a4e')
    ax.zaxis.pane.set_edgecolor('#2a2a4e')

    ax.view_init(elev=25, azim=45)

    safe_name = re.sub(r'[^\w\-.]', '_', part_name)[:50]
    filename = f'part_{idx:04d}_{safe_name}.png'
    filepath = os.path.join(output_dir, filename)
    plt.savefig(filepath, dpi=120, bbox_inches='tight', facecolor='#1a1a2e')
    plt.close(fig)
    return filename

def main():
    filepath = r'c:\Users\yh\.trae-cn\attachments\6a9698e44f0e5b6cccc8a92f\e310c563-5814-4a8b-8303-751e1e4612dc_f9f74891-2cd8-41c9-9c67-11a4c4c66e78_舱体+基座模型.stp'
    output_dir = r'C:\Users\yh\AppData\Roaming\TRAE SOLO CN\ModularData\ai-agent\work-mode-projects\6a9698e44f0e5b6cccc8a92c\part_images'
    os.makedirs(output_dir, exist_ok=True)

    print("Parsing STEP file...")
    entities = parse_step_file(filepath)
    print(f"Parsed {len(entities)} entities")

    print("Loading parts info...")
    with open(r'C:\Users\yh\AppData\Roaming\TRAE SOLO CN\ModularData\ai-agent\work-mode-projects\6a9698e44f0e5b6cccc8a92c\step_parts_info.json', 'r', encoding='utf-8') as f:
        parts_info = json.load(f)

    unique_parts = {}
    for p in parts_info:
        if p.get('bbox') is None:
            continue
        key = (p['name'], tuple(p['bbox']['size']))
        if key not in unique_parts:
            unique_parts[key] = p

    print(f"Total parts: {len(parts_info)}, Unique parts: {len(unique_parts)}")

    print("Extracting geometry and rendering 3D views...")
    results = []
    for i, (key, p) in enumerate(unique_parts.items()):
        name, size = key
        brep_id = p['brep_id']
        print(f"  [{i+1}/{len(unique_parts)}] {name} ({size[0]}x{size[1]}x{size[2]}mm)...")

        edges, points = extract_geometry(entities, brep_id)
        print(f"    Edges: {len(edges)}, Points: {len(points)}")

        filename = render_part_3d(edges, points, name, list(size), output_dir, i+1)

        results.append({
            'idx': i + 1,
            'name': name,
            'size': list(size),
            'image': filename,
            'edges': len(edges),
            'points': len(points),
            'bbox': p['bbox']
        })

    json_path = r'C:\Users\yh\AppData\Roaming\TRAE SOLO CN\ModularData\ai-agent\work-mode-projects\6a9698e44f0e5b6cccc8a92c\rendered_parts.json'
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\nRendered {len(results)} unique parts")
    print(f"Images saved to {output_dir}")
    print(f"Data saved to {json_path}")

if __name__ == '__main__':
    main()
