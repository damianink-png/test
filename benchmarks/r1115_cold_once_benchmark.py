"""R11.15 first-use Windows EXE benchmark: R11.14 cold default cache vs R11.15 cache OFF.
Compare only independent, first-time analyses and exact BOM/classification, no warm runs.
"""
import os,sys,json,time,traceback,subprocess
from pathlib import Path
from benchmarks.r1113_large_benchmark import large_pair,public_pair,PUBLIC
repo=Path(sys.argv[1]).resolve()
new=Path(sys.argv[2]).resolve()
old=Path(sys.argv[3]).resolve()
repo.mkdir(parents=True,exist_ok=True)
records=[]
report=repo/'R1115_COLD_RESULTS.json'
def save():report.write_text(json.dumps({'scenario':'first-use cold STEP, parallel import forced when possible','results':records},ensure_ascii=False,indent=2),encoding='utf8')
def run_binary(exe,folder,a,b,cache_mode):
    folder.mkdir(parents=True,exist_ok=True)
    args=[str(exe),'--worker','compare','--a',str(a),'--b',str(b),'--output',str(folder),'--generate-step','--revision-style','--step-verify','fast','--no-bom-csv']
    env=dict(os.environ,DSCOMPARE_IMPORT_CACHE=cache_mode,DSCOMPARE_CACHE_DIR=str(folder/'empty_persistent_cache'),DSCOMPARE_PARALLEL_IMPORT='on',QT_QPA_PLATFORM='offscreen')
    t=time.perf_counter()
    with (folder/'worker.log').open('w',encoding='utf8') as log:
        proc=subprocess.run(args,stdout=log,stderr=subprocess.STDOUT,timeout=900,env=env)
    dt=time.perf_counter()-t
    assert proc.returncode==0,(proc.returncode,(folder/'worker.log').read_text(encoding='utf8',errors='replace')[-2000:])
    summary=json.loads((folder/'PODSUMOWANIE.json').read_text(encoding='utf8'))
    timings=json.loads((folder/'CZASY_ANALIZY.json').read_text(encoding='utf8'))
    assert summary['step_ready'] and not summary['bom_warnings'],summary
    bom={}
    for side in ('A','B'):
        groups=json.loads((folder/f'BOM_GRUPY_{side}.json').read_text(encoding='utf8'))
        bom[side]=sorted(tuple(sorted(occ['index'] for occ in group['wystapienia'])) for group in groups)
    verdict=dict(statuses=summary['statuses'],solids_A=summary['solids_A'],solids_B=summary['solids_B'],records=summary['records'],mass_A_kg=summary['mass_A_kg'],mass_B_kg=summary['mass_B_kg'],bom=bom)
    return dt,timings,verdict
def check(name,a,b):
    row=dict(case=name,status='FAIL',a_bytes=a.stat().st_size,b_bytes=b.stat().st_size)
    records.append(row);save()
    try:
        ot,od,ov=run_binary(old,repo/name/'r1114_cold',a,b,'on')
        nt,nd,nv=run_binary(new,repo/name/'r1115_cold',a,b,'off')
        assert ov==nv,'Geometry, classification, mass or BOM changed'
        row.update(status='PASS',old_s=round(ot,3),new_s=round(nt,3),
                   first_run_savings_pct=round((ot-nt)/ot*100,2),identical_results=True,
                   old_import_wall_s=od.get('parallel_import_wall_s'),
                   new_import_wall_s=nd.get('parallel_import_wall_s'),
                   old_timings=od,new_timings=nd)
    except Exception:
        row['error']=traceback.format_exc()
    save()
    print('COLD RESULT',json.dumps({k:v for k,v in row.items() if k in ('case','status','old_s','new_s','first_run_savings_pct','error')},ensure_ascii=False),flush=True)
    return row['status']=='PASS'
if __name__=='__main__':
    allok=True
    for n in (1600,2600):
        a,b=large_pair('R1115_COLD_'+str(n),n)
        allok=check(str(n)+'_SOLIDS',a,b) and allok
    name,url,sha,inner=PUBLIC[0]
    a,b=public_pair('R1115_COLD_'+name,url,sha,inner)
    allok=check(name,a,b) and allok
    print('COLD_REPORT',report,flush=True)
    if not allok:raise SystemExit('Cold first-run benchmark failed')
