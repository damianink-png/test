"""Verify a revision frame from preserved faces, never certify whole bodies.

Feature extraction and original surface/wire proofs execute in isolated native
workers. A frame proven this way ALWAYS needs explicit placement approval.
Its faces are never placed in the body's certified_pairs map.
"""
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from time import monotonic
from types import SimpleNamespace
import json
import tempfile
import numpy as np
from . import cad_pose_search as search


def _matrix(location):
    tr=location.Transformation();m=np.eye(4)
    for i in range(3):
        for j in range(4):m[i,j]=tr.Value(i+1,j+1)
    return m.tolist()


def native_worker(request,result_path):
    """Dedicated face operations. No volume equality, mesh or repair shortcut."""
    from .brep_transport import read_brep,write_brep
    from .geometry import transform
    from .brep_safety import is_valid
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopAbs import TopAbs_FACE,TopAbs_WIRE,TopAbs_EDGE,TopAbs_VERTEX
    from OCP.TopoDS import TopoDS
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    from OCP.BRepGProp import BRepGProp
    from OCP.GProp import GProp_GProps
    from OCP.BRepBndLib import BRepBndLib
    from OCP.Bnd import Bnd_Box
    result_path=Path(result_path)
    def phase(name):result_path.with_suffix('.phase').write_text(name,encoding='utf-8')
    if request['operation']=='registration_face_features':
        output=Path(request['output']);output.mkdir(parents=True,exist_ok=True)
        prototypes={};features=[]
        for part in request['parts']:
            path=part['path'];phase('face_features_'+str(part['parent']))
            if path not in prototypes:
                shape=read_brep(path);faces=[];ex=TopExp_Explorer(shape,TopAbs_FACE)
                while ex.More():faces.append(TopoDS.Face_s(ex.Current()));ex.Next()
                # Bound expensive descriptors, independently of STEP face order.
                ids=list(range(len(faces))) if len(faces)<=32 else sorted(set(round(k*(len(faces)-1)/31) for k in range(32)))
                descriptions=[]
                for index in ids:
                    face=faces[index]
                    if not is_valid(face):continue
                    props=GProp_GProps();BRepGProp.SurfaceProperties_s(face,props)
                    area=abs(float(props.Mass()))
                    if not np.isfinite(area) or area<=1e-8:continue
                    from OCP.BRep import BRep_Tool
                    points={}
                    for vertex in search_items(face,TopAbs_VERTEX):
                        xyz=BRep_Tool.Pnt_s(TopoDS.Vertex_s(vertex)).Coord()
                        points.setdefault(tuple(round(float(v),8) for v in xyz),xyz)
                    center=(np.mean(sorted(points.values()),axis=0) if points else np.array(props.CentreOfMass().Coord()))
                    box=Bnd_Box();BRepBndLib.AddOptimal_s(face,box,False,False)
                    if box.IsVoid() or box.IsOpen():continue
                    bounds=np.asarray(box.Get());surface=BRepAdaptor_Surface(face);kind=str(surface.GetType())
                    count=lambda typ:len(search_items(face,typ))
                    direction=None
                    if 'Plane' in kind:direction=np.asarray(surface.Plane().Axis().Direction().Coord())
                    elif 'Cylinder' in kind:direction=np.asarray(surface.Cylinder().Axis().Direction().Coord())
                    matrix=props.MatrixOfInertia()
                    inertia=np.array([[matrix.Value(i+1,j+1) for j in range(3)] for i in range(3)])
                    eig,axes=np.linalg.eigh(inertia)
                    descriptions.append(dict(face=face,index=index,area=area,center=center,axes=axes,
                        inertia=inertia,bbox=bounds[3:]-bounds[:3],direction=direction,
                        kind=(kind,count(TopAbs_WIRE),count(TopAbs_EDGE))))
                # Large and differently oriented original faces, max 8/body.
                descriptions.sort(key=lambda f:-f['area']);selected=[];directions=[]
                for f in descriptions:
                    d=f['direction']
                    if d is not None and not any(abs(float(np.dot(d,old)))>.999 for old in directions):
                        selected.append(f);directions.append(d)
                    if len(selected)>=4:break
                selected += [f for f in descriptions if not any(f is old for old in selected)][:max(0,8-len(selected))]
                prototypes[path]=[]
                for f in selected:
                    face_path=output/f'face_{len(prototypes)}_{f["index"]}.brep'
                    write_brep(f['face'],face_path)
                    prototypes[path].append({k:v for k,v in f.items() if k!='face'}|{'file':str(face_path)})
            placement=np.asarray(part['placement']);r=placement[:3,:3];t=placement[:3,3]
            for f in prototypes[path]:
                features.append(dict(parent=part['parent'],name=part['name'],file=f['file'],
                    placement=part['placement'],area=f['area'],center=(r@f['center']+t).tolist(),
                    axes=(r@f['axes']).tolist(),inertia=(r@f['inertia']@r.T).tolist(),
                    bbox=(np.abs(r)@f['bbox']).tolist(),kind=f['kind'],
                    direction=(r@f['direction']).tolist() if f['direction'] is not None else None))
        response={'ok':True,'features':features}
    else:
        from .parametric_identity import prove
        from .step_reexport_tolerance import _faces
        tolerance=float(request['tolerance']);r=np.asarray(request['rotation']);t=np.asarray(request['translation'])
        matches=[]
        for number,pair in enumerate(request['pairs']):
            phase('preserved_face_'+str(number))
            left,right=pair['a'],pair['b'];ma=np.asarray(left['placement']);mb=np.asarray(right['placement'])
            a=transform(read_brep(left['file']),ma[:3,:3],ma[:3,3])
            b=transform(read_brep(right['file']),mb[:3,:3],mb[:3,3]);b=transform(b,r,t)
            # This is complete ORIGINAL oriented face + wire/edge equality.
            # It says nothing about the remainder of the parent solid.
            same=False
            if is_valid(a) and is_valid(b):
                data=_faces(SimpleNamespace(shape=a))
                if len(data)==1:
                    same=bool(prove(a,b,{0:0},data,tolerance,strict_repair=False))
            matches.append(bool(same))
        response={'ok':True,'matches':matches}
    result_path.write_text(json.dumps(response),encoding='utf-8')


def search_items(shape,kind):
    from OCP.TopExp import TopExp_Explorer
    ex=TopExp_Explorer(shape,kind);items=[]
    while ex.More():items.append(ex.Current());ex.Next()
    return items


def _run(request,directory,timeout):
    from .native_session import current
    from .native_guard import NativeGeometryFailure
    import subprocess
    root=Path(directory);req=root/'request.json';reply=root/'reply.json'
    reply.unlink(missing_ok=True);reply.with_suffix('.phase').unlink(missing_ok=True)
    req.write_text(json.dumps(request),encoding='utf-8')
    try:current().execute(req,reply,max(.1,float(timeout)))
    except (subprocess.TimeoutExpired,NativeGeometryFailure) as exc:
        phase=reply.with_suffix('.phase')
        detail=phase.read_text(encoding='utf-8') if phase.exists() else 'start procesu'
        raise NativeGeometryFailure('Nieukończony dowód zachowanych powierzchni; etap: '+detail) from exc
    try:data=json.loads(reply.read_text(encoding='utf-8'))
    except (OSError,ValueError) as exc:raise NativeGeometryFailure('Brak poprawnego wyniku powierzchni CAD') from exc
    if data.get('ok') is not True:raise NativeGeometryFailure('Nieukończona kontrola powierzchni CAD')
    return data


def _features(parts,points,root,deadline,cancelled,timeout_cap=15):
    from .brep_transport import write_brep
    from .geometry_registry import GeometryRegistry
    from OCP.TopLoc import TopLoc_Location
    context=GeometryRegistry();files={};selected=search.spread(range(len(parts)),points,min(48,len(parts)))
    records=[];root.mkdir(parents=True,exist_ok=True)
    for i in selected:
        search.check_cancel(cancelled)
        if monotonic()>=deadline:return []
        p=parts[i];key=context.definition(p)
        if key not in files:
            path=root/f'body_{key}.brep';write_brep(p.shape.Located(TopLoc_Location()),path);files[key]=str(path)
        records.append(dict(path=files[key],parent=i,name=p.name,placement=_matrix(p.shape.Location())))
    data=_run(dict(operation='registration_face_features',parts=records,output=str(root/'faces')),root,min(timeout_cap,deadline-monotonic()))
    return data.get('features',[])



def _independent_parent_matches(verified, left, right):
    """Give one frame vote per independent matched pair of complete parent parts.

    Multiple verified faces cannot promote a single parent into many anchors.
    This is FRAME evidence only: complete body SAME still needs native proof.
    """
    from collections import Counter
    counts=Counter((int(left[i].parent),int(right[j].parent)) for i,j in verified)
    first={}
    for i,j in verified:
        first.setdefault((int(left[i].parent),int(right[j].parent)),(i,j))
    used_a=set();used_b=set();out=[]
    for parent_a,parent_b in sorted(counts,key=lambda k:(-counts[k],k)):
        if parent_a in used_a or parent_b in used_b:
            continue
        out.append(first[(parent_a,parent_b)])
        used_a.add(parent_a);used_b.add(parent_b)
    return out


def propose(a,b,tolerance,state,*,extended=False,progress=None,cancelled=None,deadline=None):
    from .native_session import world_session
    from .native_guard import NativeGeometryFailure
    from .registration_gate import _select_diverse_proof_pairs
    from . import trace_r22 as trace
    if min(len(a),len(b))<4:return None
    own_deadline=monotonic()+(90 if extended else 40)
    deadline=own_deadline if deadline is None else min(deadline,own_deadline)
    if monotonic()>=deadline:return None
    if not hasattr(state,'surface_workspace'):
        state.surface_workspace=tempfile.TemporaryDirectory(prefix='dscompare_surfaces_',ignore_cleanup_errors=True)
        state.surface_features=None;state.surface_done=[];state.surface_winners=[]
    root=Path(state.surface_workspace.name)
    with world_session(True):
        try:
            if state.surface_features is None or not all(state.surface_features):
                if progress:progress('Zmieniona rewizja: szukam zachowanych powierzchni CAD, nie identycznych całych detali…')
                fa,fb=state.surface_features if state.surface_features is not None else ([],[])
                if not fa:fa=_features(a,state.features[0],root/'a',deadline,cancelled,30 if extended else 15)
                state.surface_features=(fa,fb)
                if not fb:fb=_features(b,state.features[1],root/'b',deadline,cancelled,30 if extended else 15)
                state.surface_features=(fa,fb)
            else:fa,fb=state.surface_features
            if not fa or not fb:return None
            def adapt(rows):
                return [SimpleNamespace(**row,volume=row['area'],eigenvalues=[0.,0.,0.],
                         feature_kind=tuple(row['kind']),path=str(row['parent'])) for row in rows]
            aa,bb=adapt(fa),adapt(fb)
            pa=np.asarray([f.center for f in aa]);pb=np.asarray([f.center for f in bb])
            # Lists from JSON become numeric arrays where registration needs math.
            for f in aa+bb:f.axes=np.asarray(f.axes);f.center=np.asarray(f.center)
            poses=search.hypotheses(aa,bb,tolerance,features=(pa,pb),extended=extended,cancelled=cancelled,progress=progress)
            identity_pairs=search.match_pose(aa,bb,pa,pb,np.eye(3),np.zeros(3),max(.05,5*tolerance))
            if len(identity_pairs)>=8:
                poses.insert(0,search.Pose(np.eye(3),np.zeros(3),identity_pairs,sum(aa[i].area for i,j in identity_pairs),'original_surface_frame'))
            # Translation first, then the same distance-consistent rigid search.
            rotations=None;tested=0
            for phase in range(2):
                if phase:
                    if state.surface_winners:break
                    rotations=search.hypotheses(aa,bb,tolerance,features=(pa,pb),extended=extended,rotations=True,
                                               cancelled=cancelled,progress=progress)
                    poses=rotations
                for pose in poses[:(10 if extended else 5)]:
                    search.check_cancel(cancelled)
                    if len(pose.pairs)<8:continue
                    if any(search.pose_distance(pose.rotation,pose.translation,r,t,pb)<=tolerance for r,t in state.surface_done):continue
                    if monotonic()>=deadline:return {'status':'unresolved','reason':'Limit czasu dowodu zachowanych powierzchni CAD.'}
                    pairs=_select_diverse_proof_pairs(pose.pairs,aa,48)
                    if len({aa[i].parent for i,j in pairs})<4 or len({bb[j].parent for i,j in pairs})<4:continue
                    tested+=1
                    if progress:progress(f'Zachowane powierzchnie: hipoteza {tested}; sprawdzam {len(pairs)} pełnych powierzchni i ich obrysów B-Rep.')
                    response=_run(dict(operation='registration_face_proofs',tolerance=tolerance,
                        rotation=pose.rotation.tolist(),translation=pose.translation.tolist(),
                        pairs=[{'a':fa[i],'b':fb[j]} for i,j in pairs]),root,min(20.,deadline-monotonic()))
                    matches=response.get('matches')
                    if not isinstance(matches,list) or len(matches)!=len(pairs) or any(type(v) is not bool for v in matches):
                        raise NativeGeometryFailure('Nieprawidłowa mapa dowodów powierzchni')
                    verified=[pair for pair,match in zip(pairs,matches) if match]
                    # A repeated face can support a frame, not cast another part vote.
                    independent=_independent_parent_matches(verified,aa,bb)
                    old={aa[i].parent for i,j in independent}
                    new={bb[j].parent for i,j in independent}
                    dirs=[aa[i].direction for i,j in verified if aa[i].direction is not None]
                    direction_rank=np.linalg.matrix_rank(np.asarray(dirs),tol=1e-5) if dirs else 0
                    corroborated=0
                    if len(verified)>=8 and min(len(old),len(new))>=4 and direction_rank<2:
                        # Parallel faces after size changes need an independent
                        # whole-body proof, never a mass/area equality hint.
                        from .cad_registration import place_for_proof
                        from .native_guard import guarded_registered_world
                        parents=list(dict.fromkeys((aa[i].parent,bb[j].parent) for i,j in verified))
                        parents=[(i,j) for i,j in parents if search.compatible(a[i],b[j])]
                        for i,j in parents[:3]:
                            remaining=deadline-monotonic()
                            if remaining<=0:break
                            try:
                                if guarded_registered_world(a[i],place_for_proof(b[j],pose.rotation,pose.translation),
                                                            tolerance,timeout_s=min(4.,remaining),allow_boolean=False):
                                    corroborated=1;break
                            except NativeGeometryFailure:continue
                    independent_points=pa[[i for i,j in independent]] if independent else np.empty((0,3))
                    spread_ok=(len(verified)>=8 and len(independent)>=4 and
                        np.linalg.matrix_rank(independent_points-independent_points.mean(axis=0),tol=tolerance)>=2 and
                        (direction_rank>=2 or corroborated>0))
                    trace.mark('registration_surfaces','PROOF',faces=len(verified),independent_parts=len(independent),parents_a=len(old),parents_b=len(new),accepted=bool(spread_ok))
                    state.surface_done.append((pose.rotation.copy(),pose.translation.copy()))
                    if progress:progress(f'Zachowane powierzchnie: {len(verified)}/{len(pairs)} dowodów; detale A/B: {len(old)}/{len(new)}. Całe bryły nadal wymagają porównania.')
                    if spread_ok:
                        state.surface_winners.append(dict(rotation=pose.rotation,translation=pose.translation,
                            faces=len(verified),parents_a=len(old),parents_b=len(new),independent_parts=len(independent),area=sum(aa[i].area for i,j in verified),
                            corroborating_bodies=corroborated))
            winners=state.surface_winners
            if not winners:return None
            winners.sort(key=lambda w:(-w['independent_parts'],-w['faces'],-w['area']))
            best=winners[0]
            identity=next((w for w in winners if np.linalg.norm(w['rotation']-np.eye(3))<1e-8 and np.linalg.norm(w['translation'])<=tolerance),None)
            if identity and identity['faces']>=best['faces'] and identity['area']>=best['area']*.95:best=identity
            elif any(w['independent_parts']>=max(4,best['independent_parts']-1) and
                     w['faces']>=best['faces']*.75 and w['area']>=best['area']*.8 and
                     search.pose_distance(w['rotation'],w['translation'],best['rotation'],best['translation'],pb)>tolerance for w in winners[1:]):
                return {'status':'unresolved','reason':'Kilka układów ma równoważne dowody zachowanych powierzchni; brak jednoznacznego wyrównania.'}
            original=np.linalg.norm(best['rotation']-np.eye(3))<1e-8 and np.linalg.norm(best['translation'])<=tolerance
            return dict(status='already_aligned' if original else 'registered',method='preserved_native_faces',
                requested=True,enabled=not original,translation_B_to_A_mm=best['translation'].tolist(),
                rotation_B_to_A=best['rotation'].tolist(),requires_confirmation=not original,
                verification_scope='surface_anchors_then_full_revision',certified_pairs=[],full_pair_map=[],
                votes=min(best['parents_a'],best['parents_b']),surface_anchor_count=best['faces'],
                surface_parts_a=best['parents_a'],surface_parts_b=best['parents_b'],
                reason='Położenie potwierdzone na zachowanych powierzchniach CAD. Nie jest to dowód zgodności całych detali; ich zmiany sprawdzi końcowe porównanie.')
        except NativeGeometryFailure as exc:
            trace.mark('registration_surfaces','INCOMPLETE',error=str(exc))
            return {'status':'unresolved','reason':str(exc)}
