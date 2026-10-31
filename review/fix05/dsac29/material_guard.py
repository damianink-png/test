"""Isolated, deadline-bounded material difference proof for every assembly size."""
import json, os, subprocess, sys, tempfile, time, hashlib
from pathlib import Path
from .native_guard import NativeGeometryFailure, _load_brep, _preserve_failure, _worker_metrics


def calculate_isolated(old, new, tolerance=.01, *, common_shape=None, timeout_s=35, process_args=None):
    from .material_deltas import MaterialRegions, CommonEvidence, volume
    from . import trace_r22 as trace
    with tempfile.TemporaryDirectory(prefix='dscompare_material_') as td:
        root=Path(td)
        req=dict(operation='material_regions', tolerance=tolerance,
                 old_volume=float(old.volume), new_volume=float(new.volume), root=td)
        reuse=(isinstance(common_shape,CommonEvidence) and common_shape.tolerance_mm==float(tolerance)
               and common_shape.old_shape.IsEqual(old.shape) and common_shape.new_shape.IsEqual(new.shape))
        cached=common_shape.shape if reuse else None
        for name,shape in [('a',old.shape),('b',new.shape),('common',cached)]:
            if shape is None:continue
            path=root/(name+'.brep')
            from .brep_transport import write_brep
            write_brep(shape,path)
            req[name]=str(path)
        if reuse:
            req['common_evidence']=dict(operation='common',tolerance=float(tolerance),
                hashes={key:hashlib.sha256(Path(req[key]).read_bytes()).hexdigest() for key in ('a','b','common')})
        request=root/'request.json';reply=root/'reply.json' 
        request.write_text(json.dumps(req),encoding='utf8')
        argv=process_args or ([sys.executable,'--native-brep-compare'] if getattr(sys,'frozen',False) else [sys.executable,'-m','dsac29.native_guard'])
        trace.mark('material_regions_isolated','BEGIN',old_name=old.name,new_name=new.name,timeout_s=timeout_s)
        try:
            p=subprocess.run([*argv,str(request),str(reply)],timeout=timeout_s,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
            if p.returncode:raise RuntimeError('Proces materiału: '+str(p.returncode)+' '+p.stderr.decode('utf8',errors='replace')[-2000:])
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
        trace.mark('material_regions_isolated','END',volumes=values,native_operations=_worker_metrics(root))
        return MaterialRegions(*shapes,*values)


def worker(req,result_path):
    from types import SimpleNamespace
    from .material_deltas import calculate,bind_common
    root=Path(req['root'])
    a=SimpleNamespace(shape=_load_brep(req['a']),volume=req['old_volume'])
    b=SimpleNamespace(shape=_load_brep(req['b']),volume=req['new_volume'])
    common=None
    evidence=req.get('common_evidence')
    if evidence is not None:
        if (evidence.get('operation')!='common' or evidence.get('tolerance')!=req['tolerance']
            or evidence.get('hashes')!={key:hashlib.sha256(Path(req[key]).read_bytes()).hexdigest() for key in ('a','b','common')}):
            raise ValueError('Common provenance mismatch during IPC')
        common=bind_common(_load_brep(req['common']),a.shape,b.shape,req['tolerance'])
    result=calculate(a,b,req['tolerance'],common_shape=common)
    for name,shape in [('result_common',result.common),('added',result.added),('removed',result.removed)]:
        from .brep_transport import write_brep
        write_brep(shape,root/(name+'.brep'))
    Path(result_path).write_text(json.dumps({'ok':True}),encoding='utf8')
    return 0
