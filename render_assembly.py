import re
import json
import os
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from collections import defaultdict

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
                if rest.startswith('('):
                    inner = rest[1:]
                    type_match = re.match(r'([A-Z][A-Z0-9_]*)\s*\(', inner)
                    if type_match:
                        etype = type_match.group(1)
                        if 'REPRESENTATION_RELATIONSHIP_WITH_TRANSFORMATION' in rest:
                            etype = 'REPRESENTATION_RELATIONSHIP_WITH_TRANSFORMATION'
                        elif 'SHAPE_REPRESENTATION_RELATIONSHIP' in rest:
                            etype = 'SHAPE_REPRESENTATION_RELATIONSHIP'
                        entities[eid] = (etype, rest)
                    else:
                        entities[eid] = ('COMPOUND', rest)
                else:
                    type_match = re.match(r'([A-Z][A-Z0-9_]*)\s*\(', rest)
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
    depth_at_start = 0
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

def parse_cartesian_point(entity_str):
    params = get_param_list(entity_str)
    for p in reversed(params):
        p = p.strip()
        if p.startswith('(') and p.endswith(')'):
            inner = p[1:-1]
            if ',' in inner:
                values = inner.split(',')
                coords = []
                for v in values:
                    try:
                        coords.append(eval_exponent(v.strip()))
                    except:
                        pass
                if len(coords) >= 3:
                    return coords[:3]
    return None

def parse_direction(entity_str):
    params = get_param_list(entity_str)
    for p in reversed(params):
        p = p.strip()
        if p.startswith('(') and p.endswith(')'):
            inner = p[1:-1]
            if ',' in inner:
                values = inner.split(',')
                coords = []
                for v in values:
                    try:
                        coords.append(eval_exponent(v.strip()))
                    except:
                        pass
                if len(coords) >= 3:
                    return coords[:3]
    return [0, 0, 1]

def get_axis2_placement(entities, eid):
    entity = entities.get(eid)
    if not entity:
        return None
    refs = extract_refs(entity[1])
    location = [0, 0, 0]
    axis = [0, 0, 1]
    ref_dir = [1, 0, 0]
    if len(refs) >= 1:
        loc_entity = entities.get(refs[0])
        if loc_entity and loc_entity[0] == 'CARTESIAN_POINT':
            pt = parse_cartesian_point(loc_entity[1])
            if pt:
                location = pt
    if len(refs) >= 2:
        dir_entity = entities.get(refs[1])
        if dir_entity and dir_entity[0] == 'DIRECTION':
            d = parse_direction(dir_entity[1])
            if d:
                axis = d
    if len(refs) >= 3:
        ref_entity = entities.get(refs[2])
        if ref_entity and ref_entity[0] == 'DIRECTION':
            d = parse_direction(ref_entity[1])
            if d:
                ref_dir = d
    return location, axis, ref_dir

def placement_to_matrix(location, axis, ref_dir):
    Z = np.array(axis, dtype=float)
    norm = np.linalg.norm(Z)
    if norm > 0:
        Z = Z / norm
    X = np.array(ref_dir, dtype=float)
    X = X - np.dot(X, Z) * Z
    norm = np.linalg.norm(X)
    if norm > 0:
        X = X / norm
    else:
        X = np.array([1, 0, 0])
    Y = np.cross(Z, X)
    M = np.eye(4)
    M[:3, 0] = X
    M[:3, 1] = Y
    M[:3, 2] = Z
    M[:3, 3] = np.array(location)
    return M

def matrix_inverse(M):
    R = M[:3, :3]
    t = M[:3, 3]
    R_inv = R.T
    t_inv = -R_inv @ t
    M_inv = np.eye(4)
    M_inv[:3, :3] = R_inv
    M_inv[:3, 3] = t_inv
    return M_inv

def extract_part_geometry(entities, brep_id):
    vertices = []
    edges = []
    visited = set()

    def get_point(eid):
        entity = entities.get(eid)
        if not entity or entity[0] != 'CARTESIAN_POINT':
            return None
        return parse_cartesian_point(entity[1])

    def process_edge_curve(eid):
        if eid in visited:
            return
        visited.add(eid)
        entity = entities.get(eid)
        if not entity:
            return
        refs = extract_refs(entity[1])
        v1, v2 = None, None
        for r in refs:
            rtype = entities.get(r, (None,))[0]
            if rtype == 'VERTEX_POINT':
                vrefs = extract_refs(entities[r][1])
                for vr in vrefs:
                    if entities.get(vr, (None,))[0] == 'CARTESIAN_POINT':
                        pt = get_point(vr)
                        if pt:
                            if v1 is None:
                                v1 = pt
                            else:
                                v2 = pt
            elif rtype == 'LINE':
                line_refs = extract_refs(entities[r][1])
                for lr in line_refs:
                    if entities.get(lr, (None,))[0] == 'CARTESIAN_POINT':
                        pt = get_point(lr)
                        if pt:
                            if v1 is None:
                                v1 = pt
                            elif v2 is None:
                                v2 = pt
                    elif entities.get(lr, (None,))[0] == 'VECTOR':
                        vec_refs = extract_refs(entities[lr][1])
                        for vr in vec_refs:
                            if entities.get(vr, (None,))[0] == 'DIRECTION':
                                d = parse_direction(entities[vr][1])
                                vec_entity = entities.get(lr)
                                if vec_entity:
                                    vparams = get_param_list(vec_entity[1])
                                    mag = 0.0
                                    if len(vparams) > 1:
                                        try:
                                            mag = float(vparams[1].strip())
                                        except:
                                            pass
                                    if v1 and d:
                                        v2 = [v1[i] + d[i] * mag for i in range(3)]
            elif rtype == 'CIRCLE':
                circle_refs = extract_refs(entities[r][1])
                center = None
                radius = 0
                axis_dir = [0, 0, 1]
                for cr in circle_refs:
                    crtype = entities.get(cr, (None,))[0]
                    if crtype == 'CARTESIAN_POINT':
                        center = get_point(cr)
                    elif crtype == 'DIRECTION':
                        axis_dir = parse_direction(entities[cr][1])
                circle_params = get_param_list(entities[r][1])
                if len(circle_params) > 2:
                    try:
                        radius = float(circle_params[2].strip().strip("'"))
                    except:
                        pass
                elif len(circle_params) > 1:
                    try:
                        radius = float(circle_params[1].strip().strip("'"))
                    except:
                        pass
                if center and radius > 0:
                    theta = np.linspace(0, 2*np.pi, 30)
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
                    for i in range(len(theta)-1):
                        edges.append(([xs[i], ys[i], zs[i]], [xs[i+1], ys[i+1], zs[i+1]]))
        if v1 and v2:
            edges.append((v1, v2))

    def process_oriented_edge(eid):
        if eid in visited:
            return
        visited.add(eid)
        entity = entities.get(eid)
        if not entity:
            return
        refs = extract_refs(entity[1])
        for r in refs:
            if entities.get(r, (None,))[0] == 'EDGE_CURVE':
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
            rtype = entities.get(r, (None,))[0]
            if rtype == 'ORIENTED_EDGE':
                process_oriented_edge(r)
            elif rtype == 'EDGE_LOOP':
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
            rtype = entities.get(r, (None,))[0]
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
        for r in refs:
            rtype = entities.get(r, (None,))[0]
            if rtype in ('FACE_BOUND', 'FACE_OUTER_BOUND'):
                process_face_bound(r)

    def process_shell(eid):
        if eid in visited:
            return
        visited.add(eid)
        entity = entities.get(eid)
        if not entity:
            return
        refs = extract_refs(entity[1])
        for r in refs:
            if entities.get(r, (None,))[0] == 'ADVANCED_FACE':
                process_advanced_face(r)

    def process_brep(eid):
        if eid in visited:
            return
        visited.add(eid)
        entity = entities.get(eid)
        if not entity:
            return
        refs = extract_refs(entity[1])
        for r in refs:
            rtype = entities.get(r, (None,))[0]
            if rtype in ('CLOSED_SHELL', 'OPEN_SHELL', 'ORIENTED_CLOSED_SHELL'):
                process_shell(r)

    brep_entity = entities.get(brep_id)
    if brep_entity:
        refs = extract_refs(brep_entity[1])
        for r in refs:
            rtype = entities.get(r, (None,))[0]
            if rtype == 'MANIFOLD_SOLID_BREP':
                process_brep(r)

    return edges

def main():
    filepath = r'c:\Users\yh\.trae-cn\attachments\6a9698e44f0e5b6cccc8a92f\e310c563-5814-4a8b-8303-751e1e4612dc_f9f74891-2cd8-41c9-9c67-11a4c4c66e78_舱体+基座模型.stp'

    print("Parsing STEP file...")
    entities = parse_step_file(filepath)
    print(f"Parsed {len(entities)} entities")

    print("Finding representation relationships with transformations...")
    rep_rels = []
    for eid, (etype, estr) in entities.items():
        if etype == 'REPRESENTATION_RELATIONSHIP_WITH_TRANSFORMATION' or \
           'REPRESENTATION_RELATIONSHIP_WITH_TRANSFORMATION' in estr:
            refs = extract_refs(estr)
            if len(refs) >= 3:
                child_rep = refs[0]
                parent_rep = refs[1]
                transform_id = refs[2]
                rep_rels.append({
                    'id': eid,
                    'child_rep': child_rep,
                    'parent_rep': parent_rep,
                    'transform': transform_id
                })
    print(f"Found {len(rep_rels)} representation relationships")

    print("Finding ITEM_DEFINED_TRANSFORMATION entities...")
    transforms = {}
    for eid, (etype, estr) in entities.items():
        if etype == 'ITEM_DEFINED_TRANSFORMATION':
            refs = extract_refs(estr)
            if len(refs) >= 2:
                transforms[eid] = {
                    'parent_placement': refs[0],
                    'child_placement': refs[1]
                }
    print(f"Found {len(transforms)} transformations")

    print("Computing transformation matrices...")
    transform_matrices = {}
    for tid, t in transforms.items():
        pp = get_axis2_placement(entities, t['parent_placement'])
        cp = get_axis2_placement(entities, t['child_placement'])
        if pp and cp:
            M_parent = placement_to_matrix(*pp)
            M_child = placement_to_matrix(*cp)
            M = M_child @ matrix_inverse(M_parent)
            transform_matrices[tid] = M
    print(f"Computed {len(transform_matrices)} transformation matrices")

    print("Building representation hierarchy...")
    rep_graph = defaultdict(list)
    for rr in rep_rels:
        rep_graph[rr['parent_rep']].append(rr)

    all_brep_reps = set()
    for eid, (etype, estr) in entities.items():
        if etype == 'ADVANCED_BREP_SHAPE_REPRESENTATION':
            all_brep_reps.add(eid)
    print(f"Found {len(all_brep_reps)} BREP representations")

    print("Finding root representations (parents that are never children)...")
    child_reps = set(rr['child_rep'] for rr in rep_rels)
    parent_reps = set(rr['parent_rep'] for rr in rep_rels)
    root_reps = parent_reps - child_reps
    print(f"Root representations: {root_reps}")

    print("\nCollecting all part placements (recursive)...")
    all_edges = []
    part_count = 0

    def collect_geometry(rep_id, accumulated_transform, depth=0, path=None):
        nonlocal part_count
        if path is None:
            path = set()
        if rep_id in path or depth > 20:
            return
        path.add(rep_id)

        children = rep_graph.get(rep_id, [])
        for child_rr in children:
            child_rep = child_rr['child_rep']
            transform_id = child_rr['transform']
            M = transform_matrices.get(transform_id, np.eye(4))
            combined = M @ accumulated_transform

            if child_rep in all_brep_reps:
                edges = extract_part_geometry(entities, child_rep)
                if edges:
                    for e in edges:
                        v1 = np.array(e[0] + [1])
                        v2 = np.array(e[1] + [1])
                        v1_t = combined @ v1
                        v2_t = combined @ v2
                        all_edges.append((v1_t[:3].tolist(), v2_t[:3].tolist()))
                    part_count += 1
                    if part_count % 50 == 0:
                        print(f"  Processed {part_count} parts, {len(all_edges)} edges...")
            else:
                collect_geometry(child_rep, combined, depth+1, path.copy())

        path.discard(rep_id)

    for root in root_reps:
        collect_geometry(root, np.eye(4))

    print(f"\nTotal parts placed: {part_count}")
    print(f"Total edges: {len(all_edges)}")

    if not all_edges:
        print("No edges found! Trying direct approach...")
        for rr in rep_rels:
            child_rep = rr['child_rep']
            if child_rep in all_brep_reps:
                transform_id = rr['transform']
                M = transform_matrices.get(transform_id, np.eye(4))
                edges = extract_part_geometry(entities, child_rep)
                for e in edges:
                    v1 = np.array(e[0] + [1])
                    v2 = np.array(e[1] + [1])
                    v1_t = M @ v1
                    v2_t = M @ v2
                    all_edges.append((v1_t[:3].tolist(), v2_t[:3].tolist()))
                part_count += 1
                if part_count % 50 == 0:
                    print(f"  Processed {part_count} parts, {len(all_edges)} edges...")
        print(f"Direct approach: {part_count} parts, {len(all_edges)} edges")

    if not all_edges:
        print("Still no edges. Rendering all BREP geometry without transforms...")
        for brep_id in all_brep_reps:
            edges = extract_part_geometry(entities, brep_id)
            all_edges.extend(edges)
            part_count += 1
        print(f"No-transform approach: {part_count} parts, {len(all_edges)} edges")

    print("\nRendering assembly...")
    if all_edges:
        all_pts = []
        for e in all_edges:
            all_pts.append(e[0])
            all_pts.append(e[1])
        all_pts = np.array(all_pts)
        mn = all_pts.min(axis=0)
        mx = all_pts.max(axis=0)
        center = (mn + mx) / 2
        size = mx - mn
        max_range = max(size) * 0.6

        fig = plt.figure(figsize=(16, 12), facecolor='#0d1117')
        ax = fig.add_subplot(111, projection='3d')
        ax.set_facecolor('#0d1117')

        print(f"Plotting {len(all_edges)} edges...")
        batch_size = 50000
        for i in range(0, len(all_edges), batch_size):
            batch = all_edges[i:i+batch_size]
            xs = []
            ys = []
            zs = []
            for e in batch:
                xs.extend([e[0][0], e[1][0], np.nan])
                ys.extend([e[0][1], e[1][1], np.nan])
                zs.extend([e[0][2], e[1][2], np.nan])
            ax.plot3D(xs, ys, zs, color='#58a6ff', linewidth=0.3, alpha=0.5)
            if (i // batch_size) % 10 == 0:
                print(f"  Plotted {i+len(batch)}/{len(all_edges)} edges...")

        bbox_corners = [
            [mn[0], mn[1], mn[2]], [mx[0], mn[1], mn[2]],
            [mx[0], mx[1], mn[2]], [mn[0], mx[1], mn[2]],
            [mn[0], mn[1], mx[2]], [mx[0], mn[1], mx[2]],
            [mx[0], mx[1], mx[2]], [mn[0], mx[1], mx[2]]
        ]
        bbox_edges_pairs = [
            (0,1), (1,2), (2,3), (3,0),
            (4,5), (5,6), (6,7), (7,4),
            (0,4), (1,5), (2,6), (3,7)
        ]
        for a, b in bbox_edges_pairs:
            ax.plot3D([bbox_corners[a][0], bbox_corners[b][0]],
                      [bbox_corners[a][1], bbox_corners[b][1]],
                      [bbox_corners[a][2], bbox_corners[b][2]],
                      color='#ff7b72', linewidth=1.5, linestyle='--', alpha=0.8)

        dx, dy, dz = mx - mn
        ax.text(mn[0] + dx/2, mn[1] - size[1]*0.05, mn[2],
                f'X: {dx:.0f} mm', color='#ff7b72', fontsize=12, fontweight='bold',
                ha='center', va='top')
        ax.text(mx[0] + size[0]*0.03, mn[1] + dy/2, mn[2],
                f'Y: {dy:.0f} mm', color='#7ee787', fontsize=12, fontweight='bold',
                ha='left', va='center')
        ax.text(mn[0] - size[0]*0.03, mn[1], mn[2] + dz/2,
                f'Z: {dz:.0f} mm', color='#d29922', fontsize=12, fontweight='bold',
                ha='right', va='center')

        ax.set_xlim(center[0] - max_range, center[0] + max_range)
        ax.set_ylim(center[1] - max_range, center[1] + max_range)
        ax.set_zlim(center[2] - max_range, center[2] + max_range)

        ax.set_xlabel('X (mm)', color='#8b949e', fontsize=10)
        ax.set_ylabel('Y (mm)', color='#8b949e', fontsize=10)
        ax.set_zlabel('Z (mm)', color='#8b949e', fontsize=10)

        title = f'Assembly 3D Render'
        subtitle = f'{part_count} parts | {len(all_edges):,} edges | X={dx:.0f} x Y={dy:.0f} x Z={dz:.0f} mm'
        ax.set_title(title, color='#58a6ff', fontsize=16, fontweight='bold', pad=25)
        fig.text(0.5, 0.94, subtitle, ha='center', color='#d29922', fontsize=13)

        ax.tick_params(colors='#6e7681', labelsize=8)
        ax.xaxis.pane.set_facecolor('#0d1117')
        ax.yaxis.pane.set_facecolor('#0d1117')
        ax.zaxis.pane.set_facecolor('#0d1117')
        ax.xaxis.pane.set_edgecolor('#21262d')
        ax.yaxis.pane.set_edgecolor('#21262d')
        ax.zaxis.pane.set_edgecolor('#21262d')

        ax.view_init(elev=20, azim=45)
        ax.set_box_aspect([1, 1, 0.8])

        output_path = r'C:\Users\yh\AppData\Roaming\TRAE SOLO CN\ModularData\ai-agent\work-mode-projects\6a9698e44f0e5b6cccc8a92c\assembly_3d_render.png'
        plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='#0d1117')
        plt.close(fig)
        print(f"\nAssembly render saved to {output_path}")
        print(f"Overall dimensions: X={dx:.1f} Y={dy:.1f} Z={dz:.1f} mm")
        print(f"Bounding box min: ({mn[0]:.1f}, {mn[1]:.1f}, {mn[2]:.1f})")
        print(f"Bounding box max: ({mx[0]:.1f}, {mx[1]:.1f}, {mx[2]:.1f})")
    else:
        print("ERROR: No geometry found to render!")

if __name__ == '__main__':
    main()
