"""Isolated, deadline-bounded material difference proof for every assembly size."""
import json, os, subprocess, sys, tempfile, time
from pathlib import Path
from .native_guard import NativeGeometryFailure, _load_brep, _preserve_failure


def calculate_isolated(old, new, tolerance=.01, *, common_shape=None, timeout_s=35, process_args=None):
    from OCP.BRepTools import BRepTools
    from .material_deltas import MaterialRegions, volume
    from . import trace_r22 as trace
    with tempfile.TemporaryDirectory(prefix='dscompare_material_') as td:
        root=Path(td)
        req=dict(operation='material_regions', tolerance=tolerance,
                 old_volume=float(old.volume), new_volume=float(new.volume), root=td)
        for name,shape in [('a',old.shape),('b',new.shape),('common',common_shape)]:
            if shape is None:continue
            path=root/(name+'.brep')
            with path.open('wb') as f:
                if BRepTools.Write_s(shape,f) is False:raise NativeGeometryFailure('Nie zapisano geometrii do weryfikacji')
            req[name]=str(path)
        request=root/'request.json';reply=root/'reply.json'
        request.write_text(json.dumps(req),encoding='utf8')
        argv=process_args or ([sys.executable,'--native-brep-compare'] if getattr(sys,'frozen',False) else [sys.executable,'-m','dsac29.native_guard'])
        trace.mark('material_regions_isolated','BEGIN',old_name=old.name,new_name=new.name,timeout_s=timeout_s)
        try:
            p=subprocess.run([*argv,str(request),str(reply)],timeout=timeout_s,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
            if p.returncode:raise RuntimeError('Proces materiału: '+str(p.returncode))
            data=json.loads(reply.read_text(encoding='utf8'))
            if data.get('ok') is not True:raise ValueError('Brak poprawnego wyniku')
            shapes=[_load_brep(root/(key+'.brep')) for key in ('result_common','added','removed')]
            values=[volume(s) for s in shapes]
            import math
            if not all(math.isfinite(v) and v>=0 for v in values):raise ValueError('Nieprawidłowe objętości')
            limit=max(1e-3,10*tolerance**3,5e-5*max(old.volume,new.volume))
            c,a,r=values
            if abs(c+r-old.volume)>limit or abs(c+a-new.volume)>limit:raise ValueError('Niespójny bilans materiału')
        except (subprocess.TimeoutExpired,RuntimeError,ValueError,OSError,TypeError) as exc:
            _preserve_failure(root,'material_regions')
            trace.mark('material_regions_isolated','ERROR',error=str(exc))
            raise NativeGeometryFailure('Obliczenie Common/Cut nieukończone (limit '+str(timeout_s)+' s): '+str(exc)) from exc
        trace.mark('material_regions_isolated','END',volumes=values)
        return MaterialRegions(*shapes,*values)


def worker(req,result_path):
    from types import SimpleNamespace
    from OCP.BRepTools import BRepTools
    from .material_deltas import calculate
    root=Path(req['root'])
    a=SimpleNamespace(shape=_load_brep(req['a']),volume=req['old_volume'])
    b=SimpleNamespace(shape=_load_brep(req['b']),volume=req['new_volume'])
    common=_load_brep(req['common']) if 'common' in req else None
    result=calculate(a,b,req['tolerance'],common_shape=common)
    for name,shape in [('result_common',result.common),('added',result.added),('removed',result.removed)]:
        with (root/(name+'.brep')).open('wb') as f:
            if BRepTools.Write_s(shape,f) is False:raise RuntimeError('Nie zapisano wyniku materiału')
    Path(result_path).write_text(json.dumps({'ok':True}),encoding='utf8')
    return 0
