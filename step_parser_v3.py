import re
import sys
import json
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
                type_match = re.match(r'([A-Z_]+)\s*\(', rest)
                if type_match:
                    etype = type_match.group(1)
                    entities[eid] = (etype, rest)
    return entities

def extract_refs(value_str):
    refs = re.findall(r'#(\d+)', value_str)
    return [int(r) for r in refs]

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

def eval_exponent(s):
    s = s.strip()
    parts = s.split('E')
    if len(parts) == 2:
        base = float(parts[0])
        exp = int(parts[1])
        return base * (10 ** exp)
    return float(s)

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
        name = params[0].strip().strip("'")
        return name
    return 'UNKNOWN'

def collect_points_recursive(entities, eid, visited, depth=0, max_depth=30):
    if eid in visited or depth > max_depth:
        return []
    visited.add(eid)

    entity = entities.get(eid)
    if not entity:
        return []

    etype = entity[0]
    refs = extract_refs(entity[1])
    points = []

    for r in refs:
        if r in visited:
            continue
        rtype = entities.get(r, (None,))[0]
        if rtype is None:
            continue

        if rtype == 'CARTESIAN_POINT':
            params = get_param_list(entities[r][1])
            coords = parse_cartesian_point(params)
            if coords:
                points.append(coords)
        elif rtype in (
            'ADVANCED_FACE', 'EDGE_CURVE', 'VERTEX_POINT',
            'FACE_SURFACE', 'ORIENTED_EDGE', 'EDGE_LOOP', 'FACE_BOUND',
            'MANIFOLD_SOLID_BREP', 'CLOSED_SHELL', 'OPEN_SHELL',
            'AXIS2_PLACEMENT_3D', 'LINE', 'CIRCLE', 'ELLIPSE', 'PLANE',
            'CYLINDRICAL_SURFACE', 'CONICAL_SURFACE', 'SPHERICAL_SURFACE',
            'TOROIDAL_SURFACE', 'B_SPLINE_SURFACE', 'B_SPLINE_CURVE',
            'POLYLINE', 'TRIMMED_CURVE', 'COMPOSITE_CURVE',
            'SURFACE_CURVE', 'SEAM_CURVE', 'CURVE_REPLICA',
            'SURFACE_REPLICA', 'FACE_OUTER_BOUND', 'FACE_BOUND',
            'VERTEX_LOOP', 'PATH', 'VERTEX_POINT',
            'POINT', 'DIRECTION', 'VECTOR',
            'B_SPLINE_CURVE_WITH_KNOTS', 'B_SPLINE_SURFACE_WITH_KNOTS',
            'BEZIER_CURVE', 'BEZIER_SURFACE',
            'QUASI_UNIFORM_CURVE', 'QUASI_UNIFORM_SURFACE',
            'UNIFORM_CURVE', 'UNIFORM_SURFACE',
            'RATIONAL_B_SPLINE_CURVE', 'RATIONAL_B_SPLINE_SURFACE',
            'CURVE_REPLICA', 'SURFACE_REPLICA',
            'OFFSET_CURVE_3D', 'OFFSET_SURFACE',
            'TRIMMED_CURVE', 'COMPOSITE_CURVE_SEGMENT',
            'BOUNDED_CURVE', 'BOUNDED_SURFACE'
        ):
            points.extend(collect_points_recursive(entities, r, visited, depth+1, max_depth))

    return points

def compute_bbox(points):
    if not points:
        return None
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    zs = [p[2] for p in points]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    min_z, max_z = min(zs), max(zs)
    dx = max_x - min_x
    dy = max_y - min_y
    dz = max_z - min_z
    return {
        'min': [round(min_x, 2), round(min_y, 2), round(min_z, 2)],
        'max': [round(max_x, 2), round(max_y, 2), round(max_z, 2)],
        'size': [round(dx, 2), round(dy, 2), round(dz, 2)],
        'point_count': len(points)
    }

def main():
    filepath = r'c:\Users\yh\.trae-cn\attachments\6a9698e44f0e5b6cccc8a92f\e310c563-5814-4a8b-8303-751e1e4612dc_f9f74891-2cd8-41c9-9c67-11a4c4c66e78_舱体+基座模型.stp'

    print("Parsing STEP file (handling multi-line entities)...")
    entities = parse_step_file(filepath)
    print(f"Parsed {len(entities)} entities")

    print("Finding SHAPE_DEFINITION_REPRESENTATION entities...")
    sdr_ids = []
    for eid, (etype, estr) in entities.items():
        if etype == 'SHAPE_DEFINITION_REPRESENTATION':
            sdr_ids.append(eid)
    print(f"Found {len(sdr_ids)} SHAPE_DEFINITION_REPRESENTATION entities")

    print("\nLinking products to BREP shapes and computing bounding boxes...")
    results = []
    seen_products = set()
    processed = 0

    for sdr_id in sdr_ids:
        sdr_entity = entities.get(sdr_id)
        if not sdr_entity:
            continue
        sdr_refs = extract_refs(sdr_entity[1])
        if len(sdr_refs) < 2:
            continue

        pds_id = sdr_refs[0]
        shape_rep_id = sdr_refs[1]

        shape_type = get_entity_type(shape_rep_id, entities)

        if shape_type != 'ADVANCED_BREP_SHAPE_REPRESENTATION':
            continue

        pds_entity = entities.get(pds_id)
        if not pds_entity:
            continue

        pds_type = pds_entity[0]
        if pds_type not in ('PRODUCT_DEFINITION_SHAPE', 'PROPERTY_DEFINITION'):
            continue

        product_id = find_product_from_pds(entities, pds_id)
        if product_id is None:
            if pds_type == 'PRODUCT_DEFINITION_SHAPE':
                pds_refs = extract_refs(pds_entity[1])
                for r in pds_refs:
                    if entities.get(r, (None,))[0] == 'PRODUCT_DEFINITION':
                        product_id = find_product_from_pd(entities, r)
                        break
            if product_id is None:
                continue

        if product_id in seen_products:
            continue
        seen_products.add(product_id)

        product_name = get_product_name(entities, product_id)
        processed += 1
        if processed % 10 == 0:
            print(f"  Processed {processed} products...")

        visited = set()
        points = collect_points_recursive(entities, shape_rep_id, visited)
        bbox = compute_bbox(points)

        entry = {
            'product_id': product_id,
            'name': product_name,
            'brep_id': shape_rep_id,
            'bbox': bbox
        }
        results.append(entry)

        if bbox:
            print(f"  {product_name}: {bbox['size']} mm (points: {bbox['point_count']})")
        else:
            print(f"  {product_name}: no points found")

    print(f"\nTotal products with BREP shapes: {len(results)}")

    output_path = r'C:\Users\yh\AppData\Roaming\TRAE SOLO CN\ModularData\ai-agent\work-mode-projects\6a9698e44f0e5b6cccc8a92c\step_parts_info.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"Results saved to {output_path}")

def find_product_from_pd(entities, pd_id):
    pd_entity = entities.get(pd_id)
    if not pd_entity:
        return None
    pd_refs = extract_refs(pd_entity[1])
    for r in pd_refs:
        if entities.get(r, (None,))[0] in ('PRODUCT_DEFINITION_FORMATION', 'PRODUCT_DEFINITION_FORMATION_WITH_SPECIFIED_SOURCE'):
            pdf_entity = entities.get(r)
            if not pdf_entity:
                continue
            pdf_refs = extract_refs(pdf_entity[1])
            for r3 in pdf_refs:
                if entities.get(r3, (None,))[0] == 'PRODUCT':
                    return r3
    return None

if __name__ == '__main__':
    main()
