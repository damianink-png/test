"""Read-only, versioned STEP diagnostics without exporting B-Rep or mesh data."""
import hashlib
import json
import math
from pathlib import Path
from time import perf_counter


def _xyz(value):
    return [float(value.X()), float(value.Y()), float(value.Z())]


def _items(shape, kind):
    from OCP.TopExp import TopExp
    from OCP.TopTools import TopTools_IndexedMapOfShape
    result = TopTools_IndexedMapOfShape()
    TopExp.MapShapes_s(shape, kind, result)
    return [result.FindKey(i) for i in range(1, result.Extent()+1)]


def _shape_details(shape):
    """Inspect once per definition, in its unlocated native coordinate frame.

    No Common/Cut, healing, meshing or expensive optimal spline extrema.
    Topological validity explicitly excludes full geometric validation.
    """
    from OCP.TopLoc import TopLoc_Location
    from OCP.TopAbs import TopAbs_FACE, TopAbs_EDGE, TopAbs_VERTEX, TopAbs_SOLID, TopAbs_SHELL
    from OCP.TopoDS import TopoDS
    from OCP.BRep import BRep_Tool
    from OCP.BRepAdaptor import BRepAdaptor_Surface, BRepAdaptor_Curve
    from OCP.BRepCheck import BRepCheck_Analyzer
    from OCP.BRepGProp import BRepGProp
    from OCP.GProp import GProp_GProps
    from collections import Counter
    local = shape.Located(TopLoc_Location())
    out = {'coordinate_frame': 'native_shape_without_top_level_location',
           'errors': [], 'faces': [], 'edges': []}
    def attempt(label, fn):
        try:
            return fn()
        except Exception as exc:
            out['errors'].append({'operation': label, 'error': type(exc).__name__+': '+str(exc)})
            return None
    checker = attempt('topology_check', lambda: BRepCheck_Analyzer(local, False))
    out['topology_valid_without_geometric_checks'] = bool(checker.IsValid()) if checker is not None else None
    out['full_geometric_validation'] = 'not_run; isolated comparison diagnostics carry native failures'
    faces = _items(local, TopAbs_FACE)
    edges = _items(local, TopAbs_EDGE)
    vertices = _items(local, TopAbs_VERTEX)
    from OCP.TopTools import TopTools_IndexedMapOfShape
    edge_map = TopTools_IndexedMapOfShape()
    for edge in edges: edge_map.Add(edge)
    out['counts'] = dict(faces=len(faces), edges=len(edges), vertices=len(vertices),
                         solids=len(_items(local, TopAbs_SOLID)), shells=len(_items(local, TopAbs_SHELL)))
    for i, raw in enumerate(faces):
        def face_info():
            face = TopoDS.Face_s(raw)
            surface = BRepAdaptor_Surface(face, True)
            info = {'index': i, 'type': str(surface.GetType()), 'orientation': str(face.Orientation()),
                    'tolerance_mm': float(BRep_Tool.Tolerance_s(face)),
                    'uv_bounds': [surface.FirstUParameter(), surface.LastUParameter(),
                                  surface.FirstVParameter(), surface.LastVParameter()]}
            info['topology_status'] = [str(v) for v in checker.Result(face).Status()] if checker is not None else None
            info['boundary_edges'] = [dict(edge_index=edge_map.FindIndex(e)-1,
                orientation=str(e.Orientation()), seam=bool(BRep_Tool.IsClosed_s(TopoDS.Edge_s(e), face)))
                for e in _items(face, TopAbs_EDGE)]
            props = GProp_GProps(); BRepGProp.SurfaceProperties_s(face, props)
            info.update(area_mm2=float(props.Mass()), center_mm=_xyz(props.CentreOfMass()))
            typ = info['type']
            if typ.endswith('Plane'):
                plane = surface.Plane()
                info['analytic'] = dict(origin_mm=_xyz(plane.Location()), normal=_xyz(plane.Axis().Direction()))
            elif typ.endswith('Cylinder') or typ.endswith('Cone'):
                obj = surface.Cylinder() if typ.endswith('Cylinder') else surface.Cone()
                info['analytic'] = dict(origin_mm=_xyz(obj.Location()), axis=_xyz(obj.Axis().Direction()))
                if typ.endswith('Cylinder'): info['analytic']['radius_mm'] = obj.Radius()
                else: info['analytic'].update(reference_radius_mm=obj.RefRadius(), semi_angle_rad=obj.SemiAngle())
            elif typ.endswith('Sphere'):
                obj = surface.Sphere()
                info['analytic'] = dict(center_mm=_xyz(obj.Location()), radius_mm=obj.Radius())
            elif typ.endswith('Torus'):
                obj = surface.Torus()
                info['analytic'] = dict(center_mm=_xyz(obj.Location()), axis=_xyz(obj.Axis().Direction()),
                                        major_radius_mm=obj.MajorRadius(), minor_radius_mm=obj.MinorRadius())
            elif typ.endswith('BSplineSurface') or typ.endswith('BezierSurface'):
                obj = surface.BSpline() if typ.endswith('BSplineSurface') else surface.Bezier()
                info['spline'] = dict(u_degree=obj.UDegree(), v_degree=obj.VDegree(),
                    u_poles=obj.NbUPoles(), v_poles=obj.NbVPoles(),
                    u_rational=obj.IsURational(), v_rational=obj.IsVRational())
                if typ.endswith('BSplineSurface'):
                    info['spline'].update(u_knots=obj.NbUKnots(), v_knots=obj.NbVKnots(),
                                          u_periodic=obj.IsUPeriodic(), v_periodic=obj.IsVPeriodic())
            return info
        info = attempt('face_'+str(i), face_info)
        out['faces'].append(info if info is not None else {'index': i, 'unavailable': True})
    for i, raw in enumerate(edges):
        def edge_info():
            edge = TopoDS.Edge_s(raw)
            info = dict(index=i, tolerance_mm=float(BRep_Tool.Tolerance_s(edge)),
                        degenerated=bool(BRep_Tool.Degenerated_s(edge)),
                        same_parameter=bool(BRep_Tool.SameParameter_s(edge)),
                        same_range=bool(BRep_Tool.SameRange_s(edge)))
            info['topology_status'] = [str(v) for v in checker.Result(edge).Status()] if checker is not None else None
            if not info['degenerated']:
                curve = BRepAdaptor_Curve(edge)
                info.update(type=str(curve.GetType()), parameter_range=[curve.FirstParameter(), curve.LastParameter()])
            return info
        info = attempt('edge_'+str(i), edge_info)
        out['edges'].append(info if info is not None else {'index': i, 'unavailable': True})
    points=[]; tolerances=[]
    for i, raw in enumerate(vertices):
        def vertex_info():
            vertex=TopoDS.Vertex_s(raw)
            return _xyz(BRep_Tool.Pnt_s(vertex)), float(BRep_Tool.Tolerance_s(vertex))
        info=attempt('vertex_'+str(i), vertex_info)
        if info is not None:
            points.append(info[0]); tolerances.append(info[1])
    out['vertex_tolerances_mm']=tolerances
    out['vertex_bounds_mm'] = ([min(p[k] for p in points) for k in range(3)]+
                                [max(p[k] for p in points) for k in range(3)]) if points else None
    out['vertex_bounds_note']='Bounds of vertices only; curved edges and faces can extend beyond them.'
    out['surface_types']=dict(Counter(f.get('type','unavailable') for f in out['faces']))
    out['curve_types']=dict(Counter(e.get('type','degenerated' if e.get('degenerated') else 'unavailable') for e in out['edges']))
    out['maximum_tolerance_mm']=max([0., *tolerances,
        *(f.get('tolerance_mm',0.) for f in out['faces']), *(e.get('tolerance_mm',0.) for e in out['edges'])])
    return out


def _finite_json(value):
    if isinstance(value, float): return value if math.isfinite(value) else None
    if isinstance(value, dict): return {str(k): _finite_json(v) for k,v in value.items()}
    if isinstance(value, (list,tuple)): return [_finite_json(v) for v in value]
    return value


def run(paths, folder, max_solids, progress):
    from .step_io import load_step
    from .step_diagnostics import schema_header
    from .geometry_registry import GeometryRegistry
    reports=[]
    output=Path(folder)/'DIAGNOSTYKA_MODELI.txt'
    output.parent.mkdir(parents=True, exist_ok=True)
    data={'report_schema': 2, 'complete': False,
          'description':'Dane diagnostyczne CAD, nie dowód zgodności. Bez B-Rep, siatki i współrzędnych biegunów spline. Nazwy, wymiary i położenia mogą być poufne.',
          'non_finite_values':'Non-finite numerical values are written as null.', 'models':reports}
    build=Path(__file__).resolve().parent.parent/'build_info.json'
    if build.exists(): data['engine_build']=json.loads(build.read_text(encoding='utf-8-sig'))
    def save():
        temp=output.with_suffix('.txt.tmp')
        temp.write_text(json.dumps(_finite_json(data),ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
        temp.replace(output)
    save()
    for label,path in zip(('A','B'),paths):
        stats={};started=perf_counter()
        with Path(path).open('rb') as stream: digest=hashlib.file_digest(stream, 'sha256').hexdigest()
        parts=load_step(path,max_solids=max_solids,progress=progress,diagnostics=stats)
        import_seconds=perf_counter()-started
        registry=GeometryRegistry();groups={}
        for i,p in enumerate(parts): groups.setdefault(registry.definition(p),[]).append(i)
        model={'model':label,'file_name':Path(path).name,'source_sha256':digest,
            'schema':schema_header(Path(path)),'import_seconds':import_seconds,
            'import_diagnostics':stats,'solid_count':len(parts),'native_definition_count':len(groups),
            'definitions':[]}
        reports.append(model)
        save()
        for number,ids in enumerate(groups.values()):
            p=parts[ids[0]]
            if progress: progress(f'Diagnostyka {label}: geometria definicji {number+1}/{len(groups)}; {p.name}, indeks {ids[0]}; wystąpień {len(ids)}.')
            item={'definition_id':number,'representative_index':ids[0], 'occurrence_indices':ids,
                'occurrences':len(ids),'name':p.name,'path':p.path,
                'volume_mm3':float(p.volume),'area_mm2':float(p.area),
                'central_principal_moments':list(map(float,p.eigenvalues)),
                'bbox_mm':list(map(float,p.bbox)),
                'bbox_note':'Imported conservative extents; not exact geometric extrema.',
                'centers_mm':[list(map(float,parts[i].center)) for i in ids],
                'placements':[]}
            for i in ids:
                part=parts[i]; tr=part.shape.Location().Transformation()
                item['placements'].append(dict(index=i,name=part.name,path=part.path,
                    location_3x4=[[float(tr.Value(r,c)) for c in range(1,5)] for r in range(1,4)],
                    orientation=str(part.shape.Orientation())))
            try: item['geometry']=_shape_details(p.shape)
            except Exception as exc: item['geometry']={'errors':[{'operation':'definition','error':type(exc).__name__+': '+str(exc)}]}
            model['definitions'].append(item)
            if (number+1)%10==0: save()
        model['diagnostic_total_seconds']=perf_counter()-started
        save()
    data['complete']=True
    data['has_inspection_errors']=any(d['geometry'].get('errors') for m in reports for d in m['definitions'])
    save()
    return output
