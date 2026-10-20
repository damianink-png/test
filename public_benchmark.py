"""Public CAD benchmarks; controlled edits are test fixtures, not author revisions."""
import sys,os,json,time,hashlib,urllib.request,zipfile,subprocess,traceback,shutil
from pathlib import Path
from collections import Counter
src,exe,out=map(lambda x:Path(x).resolve(),sys.argv[1:4]);sys.path.insert(0,str(src));out.mkdir(parents=True,exist_ok=True)
cases=[('SO101','https://raw.githubusercontent.com/TheRobotStudio/SO-ARM100/a758567c3978dfeefe282ede0500085a48fe8f78/STEP/SO101/SO101%20Assembly.step',266,'f754be35708382b05ce65768ae33c612f91dca11ad19d14807dc637eb944ba3d'),('OLSK_CNC','https://raw.githubusercontent.com/Open-Lab-Starter-Kit/OLSK-Small-CNC/cae066fa5b78b596743e1f2e432b93539cba8c24/OLSK_Small_CNC_V2/OLSK%20small%20CNC%20v2_Workshop.step.zip',712,'c2b8e022eb84dea2488c805375e4f0c3890a4f3702065b045dfef66481ea556a')]
results=[]
def write(): (out/'RESULTS.json').write_text(json.dumps({'version':'R11.3','environment':sys.version,'cases':results},ensure_ascii=False,indent=2),encoding='utf8')
def run(case,a,b,n,full,expected):
    folder=out/case;folder.mkdir(exist_ok=True)
    row={'case':case,'full_bom':full,'expected':expected,'input_sha256':[hashlib.sha256(p.read_bytes()).hexdigest() for p in (a,b)],'status':'FAIL'};results.append(row)
    cmd=[str(exe),'--worker','compare','--a',str(a),'--b',str(b),'--output',str(folder),'--generate-step','--revision-style','--max-solids','5000']
    if not full:cmd.append('--no-bom')
    start=time.perf_counter();step_at=None;report_at=None
    try:
        with (folder/'worker.log').open('w',encoding='utf8') as log:
            p=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT,env=dict(os.environ,QT_QPA_PLATFORM='offscreen'))
            while p.poll() is None:
                elapsed=time.perf_counter()-start
                if elapsed>1200:p.kill();p.wait();raise TimeoutError('1200s limit')
                try:
                    stage=json.loads((folder/'_ETAPY.json').read_text(encoding='utf8'))
                    if stage.get('step')=='gotowy' and step_at is None:step_at=elapsed
                    if stage.get('basic_report_ready') and report_at is None:report_at=elapsed
                except (OSError,ValueError):pass
                time.sleep(.2)
        row.update(total_s=round(time.perf_counter()-start,3),step_ready_s=step_at,quick_report_ready_s=report_at,exit_code=p.returncode)
        data=json.loads((folder/'PODSUMOWANIE.json').read_text(encoding='utf8'));worker=json.loads((folder/'_WYNIK_V37.json').read_text(encoding='utf8'));diag=json.loads((folder/'DIAGNOSTYKA_KOLOROW.json').read_text(encoding='utf8'))
        records=data['records'];counts=dict(Counter(r['status'] for r in records));row.update(status_counts=counts,import_diagnostics=data.get('import_diagnostics'),bom_warnings=data['bom_warnings'],timings=json.loads((folder/'CZASY_ANALIZY.json').read_text(encoding='utf8')),step_diagnostics=diag,step_bytes=(folder/'POROWNANIE_KOLORY.step').stat().st_size)
        assert p.returncode==0 and worker['ok'] and not worker['blad_step'],worker
        assert counts==expected,(counts,expected)
        for side in ('a_index','b_index'):
            indices=[r[side] for r in records if r[side] is not None]
            assert len(indices)==n and len(set(indices))==n,(side,len(indices),n)
        assert diag['pokolorowane_etykiety']==sum(expected.values())+expected.get('MOVED',0)
        assert diag['powierzchnie_bez_koloru']==0
        assert (folder/'RAPORT_ZMIAN.html').exists() and (folder/'RAPORT.html').exists()
        assert (folder/'BOM_A.csv').exists()==full
        assert not data['bom_warnings'],data['bom_warnings']
        row['status']='PASS'
    except Exception:row['error']=traceback.format_exc();row.setdefault('total_s',time.perf_counter()-start)
    write();print(json.dumps({k:v for k,v in row.items() if k in ('case','status','total_s','status_counts','error')},ensure_ascii=False),flush=True)
    # Keep logs and machine-readable reports; avoid redistributing public CAD.
    for path in folder.glob('*.step'):path.unlink()
    return row
for name,url,n,sha in cases:
    try:
        work=out.parent/('input_'+name);work.mkdir(exist_ok=True)
        blob=urllib.request.urlopen(url,timeout=120).read();a=work/'source.step'
        if url.endswith('.zip'):
            archive=work/'source.zip';archive.write_bytes(blob)
            with zipfile.ZipFile(archive) as z:
                entries=[x for x in z.namelist() if x.lower().endswith(('.step','.stp'))];assert len(entries)==1
                a.write_bytes(z.read(entries[0]))
        else:a.write_bytes(blob)
        assert hashlib.sha256(a.read_bytes()).hexdigest()==sha,'Source hash changed'
        (out/(name+'_SOURCE.json')).write_text(json.dumps({'url':url,'sha256':sha,'bytes':a.stat().st_size,'expected_solids':n},indent=2))
        for full in (False,True):run(name+('_identical_full' if full else '_identical_fast'),a,a,n,full,{'SAME':n})
        b=work/'different_bytes.step';b.write_bytes(a.read_bytes().replace(b'ISO-10303-21;',b'ISO-10303-21;\n/* DSCompare benchmark: unchanged geometry */',1))
        run(name+'_distinct_fast',a,b,n,False,{'SAME':n})
        if name=='SO101':
            from dsac29.step_io import load_step
            from generuj_przykladowe_step import save,box
            from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
            from OCP.gp import gp_Trsf,gp_Vec
            parts=load_step(str(a),max_solids=5000);assert len(parts)==n
            order=sorted(range(n),key=lambda i:parts[i].volume,reverse=True);removed,moved=order[:2]
            originals=[('PUBLIC_PART_%04d'%i,p.shape) for i,p in enumerate(parts)]
            tr=gp_Trsf();tr.SetTranslation(gp_Vec(10000,20000,30000))
            edited=[(label,BRepBuilderAPI_Transform(shape,tr,True).Shape() if i==moved else shape) for i,(label,shape) in enumerate(originals) if i!=removed]
            edited.append(('CONTROLLED_NEW',box(60000,60000,60000,37.123,43.456,59.789)))
            aa=work/'controlled_A.step';bb=work/'controlled_B.step';save(aa,originals);save(bb,edited)
            (out/'CONTROLLED_EDITS.json').write_text(json.dumps({'note':'Original public geometry re-exported with stable unique labels in A and B; not an upstream revision','removed_index':removed,'moved_index':moved,'translation_mm':[10000,20000,30000],'added':'box 37.123 x 43.456 x 59.789 mm'},indent=2))
            run(name+'_controlled_fast',aa,bb,n,False,{'SAME':n-2,'MOVED':1,'REMOVED':1,'ADDED':1})
    except Exception:
        results.append({'case':name+'_setup','status':'FAIL','error':traceback.format_exc()});write()
assert results and all(r['status']=='PASS' for r in results), 'Public assembly tests failed; see RESULTS.json'
