"""Fail-closed overlap exclusion for an invalid OCCT Common.

Never accepts a CHANGED/SAME result; may only reject a CHANGED candidate when
two independently validated displaced Common/Cut partitions establish a
conservative upper bound below the original required overlap.
"""
import json,math,subprocess,sys,tempfile
from pathlib import Path

def _volume(shape):
    from OCP.BRepGProp import BRepGProp
    from OCP.GProp import GProp_GProps
    p=GProp_GProps();BRepGProp.VolumeProperties_s(shape,p);v=float(p.Mass())
    if not math.isfinite(v) or v<0:raise ValueError('Invalid signed volume')
    return v

def _area(shape):
    from OCP.BRepGProp import BRepGProp
    from OCP.GProp import GProp_GProps
    p=GProp_GProps();BRepGProp.SurfaceProperties_s(shape,p);v=float(p.Mass())
    if not math.isfinite(v) or v<=0:raise ValueError('Invalid surface area')
    return v

def _operation(kind,a,b,fuzzy):
    from OCP.TopTools import TopTools_ListOfShape
    from OCP.BRepCheck import BRepCheck_Analyzer
    x=TopTools_ListOfShape();x.Append(a)
    y=TopTools_ListOfShape();y.Append(b)
    op=kind();op.SetArguments(x);op.SetTools(y)
    op.SetNonDestructive(True);op.SetUseOBB(True);op.SetFuzzyValue(fuzzy)
    op.Build()
    if not op.IsDone():raise RuntimeError('Incomplete Boolean')
    result=op.Shape()
    if result.IsNull() or not BRepCheck_Analyzer(result).IsValid():
        raise ValueError('Invalid Boolean topology')
    return _volume(result)

def screen(a,b,tolerance,threshold):
    from OCP.BRepCheck import BRepCheck_Analyzer
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Common,BRepAlgoAPI_Cut
    from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
    from OCP.gp import gp_Trsf,gp_Vec
    tol=float(tolerance);limit=float(threshold)
    if not 0<tol<=.01 or limit<=0:raise ValueError('Unsafe tolerance')
    if not BRepCheck_Analyzer(a).IsValid() or not BRepCheck_Analyzer(b).IsValid():
        return dict(excluded=False,reason='Invalid source')
    va,vb=_volume(a),_volume(b);area=_area(b)
    if min(va,vb)<=0:return dict(excluded=False,reason='Invalid source volume')
    fuzzy=max(tol/100.,1e-6)
    balance_tol=max(1e-3,10*tol**3,5e-5*max(va,vb))
    witnesses=[]
    for delta in ((0.,tol*.1,0.),(0.,tol,0.),(tol*.5,0.,0.),(0.,0.,tol*.5)):
        try:
            transform=gp_Trsf();transform.SetTranslation(gp_Vec(*delta))
            shifted=BRepBuilderAPI_Transform(b,transform,True).Shape()
            if not BRepCheck_Analyzer(shifted).IsValid():continue
            common=_operation(BRepAlgoAPI_Common,a,shifted,fuzzy)
            removed=_operation(BRepAlgoAPI_Cut,a,shifted,fuzzy)
            added=_operation(BRepAlgoAPI_Cut,shifted,a,fuzzy)
            error_a=abs(common+removed-va);error_b=abs(common+added-vb)
            if error_a>balance_tol or error_b>balance_tol:continue
            distance=math.sqrt(sum(x*x for x in delta))
            # Translation-volume bound uses B's surface area times shift.
            # The 10x inflation also covers Boolean fuzzy and numerical error.
            upper=common+10*area*(distance+fuzzy)+10*balance_tol
            witnesses.append(dict(translation_mm=list(delta),common_mm3=common,
                 removed_mm3=removed,added_mm3=added,balance_A_mm3=error_a,
                 balance_B_mm3=error_b,upper_bound_mm3=upper))
            if len(witnesses)>=2:break
        except (RuntimeError,ValueError,TypeError):continue
    return dict(excluded=len(witnesses)>=2 and all(v['upper_bound_mm3']<limit for v in witnesses),
        witnesses=witnesses,threshold_mm3=limit,source_volume_A_mm3=va,
        source_volume_B_mm3=vb,surface_area_B_mm2=area,
        method='two_valid_translated_common_cut_conservative_upper_bounds')

def worker(request,result_path):
    from .brep_transport import read_brep
    result=screen(read_brep(request['a']),read_brep(request['b']),
                  request['tolerance'],request['minimum_common_mm3'])
    Path(result_path).write_text(json.dumps(dict(ok=True,**result)),encoding='utf8')
    return 0

def guarded_exclusion(a,b,tolerance,threshold,*,timeout_s=45,process_args=None):
    from .brep_transport import write_brep
    from .native_guard import NativeGeometryFailure
    with tempfile.TemporaryDirectory(prefix='dscompare_exclusion_') as tmp:
        root=Path(tmp);write_brep(a,root/'A.brep');write_brep(b,root/'B.brep')
        request=root/'request.json';reply=root/'reply.json'
        request.write_text(json.dumps(dict(operation='common_exclusion',a=str(root/'A.brep'),
            b=str(root/'B.brep'),tolerance=float(tolerance),
            minimum_common_mm3=float(threshold))),encoding='utf8')
        cmd=process_args or ([sys.executable,'--native-brep-compare']
             if getattr(sys,'frozen',False) else [sys.executable,'-m','dsac29.native_guard'])
        try:
            proc=subprocess.run([*cmd,str(request),str(reply)],
                timeout=timeout_s,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
            if proc.returncode or not reply.exists():
                raise ValueError('Isolated proof process failed: '+str(proc.returncode))
            data=json.loads(reply.read_text(encoding='utf8'))
            if data.get('ok') is not True or type(data.get('excluded')) is not bool:
                raise ValueError('Invalid isolated proof reply')
            return data
        except (subprocess.TimeoutExpired,OSError,ValueError,TypeError) as exc:
            raise NativeGeometryFailure('Nie udało się wykluczyć podobnej rewizji: '+str(exc)) from exc
