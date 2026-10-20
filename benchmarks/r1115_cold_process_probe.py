"""Measure safe process-parallel exact OCCT property evaluation on SO101 after initial read."""
import hashlib,json,os,sys,time,subprocess,urllib.request
from pathlib import Path
from OCP.BRep import BRep_Builder
from OCP.TopoDS import TopoDS_Compound
from OCP.BRepTools import BRepTools
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_SOLID
from OCP.BRepGProp import BRepGProp
from OCP.GProp import GProp_GProps
def numeric(s):
    vol=GProp_GProps(); BRepGProp.VolumeProperties_s(s,vol)
    area=GProp_GProps(); BRepGProp.SurfaceProperties_s(s,area)
    return [vol.Mass(),area.Mass()]
def child():
    path=Path(sys.argv[2]);builder=BRep_Builder();shape=TopoDS_Compound()
    ts=time.perf_counter()
    status=BRepTools.Read_s(shape,str(path),builder)
    if status is False:raise RuntimeError('Cannot read BREP '+str(path))
    ex=TopExp_Explorer(shape,TopAbs_SOLID)
    vals=[]
    while ex.More():
        vals.append(numeric(ex.Current()))
        ex.Next()
    (path.with_suffix('.json')).write_text(json.dumps(vals),encoding='utf8')
    print('CHILD',path.name,'count',len(vals),'secs',round(time.perf_counter()-ts,3),flush=True)
def parent():
    from dsac29.step_io import load_step
    url='https://raw.githubusercontent.com/TheRobotStudio/SO-ARM100/a758567c3978dfeefe282ede0500085a48fe8f78/STEP/SO101/SO101%20Assembly.step'
    dest=Path(os.environ['RUNNER_TEMP'])/'SO101_cold_process_probe.step'
    data=urllib.request.urlopen(url,timeout=120).read()
    assert hashlib.sha256(data).hexdigest()=='f754be35708382b05ce65768ae33c612f91dca11ad19d14807dc637eb944ba3d'
    dest.write_bytes(data);os.environ['DSCOMPARE_IMPORT_CACHE']='off'
    t=time.perf_counter();parts=load_step(str(dest),max_solids=5000)
    print('COLD STEP IMPORT',round(time.perf_counter()-t,3),'S',len(parts),'parts',flush=True)
    for workers in (2,4):
        t=time.perf_counter();paths=[]
        for i in range(workers):
            group=parts[i::workers];comp=TopoDS_Compound();b=BRep_Builder();b.MakeCompound(comp)
            for part in group:b.Add(comp,part.shape)
            path=dest.with_name(f'R1115_process_{workers}_{i}.brep')
            BRepTools.Write_s(comp,str(path))
            paths.append(path)
        ser=time.perf_counter()-t
        t=time.perf_counter()
        procs=[subprocess.Popen([sys.executable,str(Path(__file__).resolve()),'child',str(p)],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True) for p in paths]
        for process in procs:
            out,_=process.communicate(timeout=180)
            print(out,flush=True)
            if process.returncode:raise RuntimeError('Worker failed '+out)
        parallel=time.perf_counter()-t
        byworker=[json.loads(p.with_suffix('.json').read_text('utf8')) for p in paths]
        errors=0
        for i,z in enumerate(parts):
            pair=byworker[i%workers][i//workers]
            for ref,got in zip((z.volume,z.area),pair):
                if abs(ref-got)>max(1e-8,abs(ref)*1e-9):
                    errors+=1
        sizes=sum(p.stat().st_size for p in paths)
        print('PROCESS RESULT',workers,'serialization_s',round(ser,3),'parallel_eval_s',round(parallel,3),
              'total_s',round(ser+parallel,3),'BREP_MB',round(sizes/1048576,1),
              'property_mismatches',errors,flush=True)
        assert not errors
        for p in paths:
            p.unlink(missing_ok=True);p.with_suffix('.json').unlink(missing_ok=True)
if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='child':child()
    else:parent()
