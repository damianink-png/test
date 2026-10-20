"""Windows EXE benchmark for cold/warm validated STEP import cache.
Tests frozen R11.13 vs R11.14 on same CAD inputs; validates full BOM/records.
"""
from __future__ import annotations
import json, os, sys, traceback, time
from pathlib import Path
from r1113_large_benchmark import large_pair, public_pair, execute, PUBLIC

root=Path(sys.argv[1]).resolve();optimized=Path(sys.argv[2]).resolve();baseline=Path(sys.argv[3]).resolve()
root.mkdir(parents=True,exist_ok=True)
rows=[];report=root/'R1114_IMPORT_RESULTS.json'
def write():
    report.write_text(json.dumps({'base':'R11.13','new':'R11.14','cases':rows},ensure_ascii=False,indent=2),encoding='utf8')
def run_case(name,a,b):
    row=dict(case=name,status='FAIL',input_bytes=[a.stat().st_size,b.stat().st_size])
    rows.append(row);write();print('START IMPORT CACHE',name,flush=True)
    try:
        env_before=dict(os.environ)
        try:
            os.environ['DSCOMPARE_IMPORT_CACHE']='off'
            base_time,base_stage,base_data,base_meta=execute(baseline,root/name/'r1113',a,b,seconds=1200)
            os.environ['DSCOMPARE_IMPORT_CACHE']='on'
            os.environ['DSCOMPARE_CACHE_DIR']=str(root/name/'persistent_cache')
            cold_time,cold_stage,cold_data,cold_meta=execute(optimized,root/name/'cold_r1114',a,b,seconds=1200)
            warm_time,warm_stage,warm_data,warm_meta=execute(optimized,root/name/'warm_r1114',a,b,seconds=1200)
        finally:
            os.environ.clear();os.environ.update(env_before)
        assert base_data==cold_data==warm_data,'Geometry classification, BOM grouping or mass differ across runs'
        if not all(s.get('persistent_cache')=='HIT' for s in warm_meta['import_diagnostics'].values()):
            raise AssertionError('Expected two verified persistent-cache hits')
        row.update(baseline_s=round(base_time,3),cold_s=round(cold_time,3),
                   warm_s=round(warm_time,3),cold_import_s=cold_stage.get('import_A_including_fingerprint_s',0)+cold_stage.get('import_B_s',0),
                   warm_import_s=warm_stage.get('import_A_including_fingerprint_s',0)+warm_stage.get('import_B_s',0),
                   baseline_timings=base_stage,cold_timings=cold_stage,warm_timings=warm_stage,
                   counts=cold_meta['statuses'],solids_A=cold_meta['solids_A'],solids_B=cold_meta['solids_B'],
                   cache_hits_verified=True,equal_classification_and_bom=True,status='PASS')
    except Exception:
        row['error']=traceback.format_exc()
    write()
    print('RESULT',json.dumps({k:v for k,v in row.items() if k in ('case','status','baseline_s','cold_s','warm_s','cold_import_s','warm_import_s','error')},ensure_ascii=False),flush=True)
    return row['status']=='PASS'

def main():
    ok=True
    for n in (1600,2600):
        name=f'SYNTHETIC_{n}'
        a,b=large_pair(name,n)
        ok=run_case(name,a,b) and ok
    name,url,sha,inner=PUBLIC[0]  # SO101 266 physical solids, distinct realistic CAD faces
    try:
        a,b=public_pair(name,url,sha,inner)
        ok=run_case(name,a,b) and ok
    except Exception as exc:
        rows.append({'case':name,'status':'PUBLIC_SOURCE_UNAVAILABLE','error':str(exc)})
        write();print('UNAVAILABLE',name,str(exc),flush=True)
    print('RESULT_FILE',report,flush=True)
    if not ok:
        raise SystemExit('Import cache regression failed — inspect report JSON')
if __name__=='__main__':main()
