"""DS Compare R11.13 Windows benchmark: real frozen EXE on large STEP models.
Includes deterministic synthetic CAD and pinned public GitHub STEP models.
Never treat synthetic controlled edits as author revisions.
"""
import os, sys, json, subprocess, hashlib, time, urllib.request, zipfile, traceback
from collections import Counter
from pathlib import Path
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCP.TopLoc import TopLoc_Location
from OCP.gp import gp_Trsf,gp_Vec
from OCP.TDocStd import TDocStd_Document
from OCP.TCollection import TCollection_ExtendedString
from OCP.XCAFDoc import XCAFDoc_DocumentTool
from OCP.TDataStd import TDataStd_Name
from OCP.STEPCAFControl import STEPCAFControl_Writer
from OCP.IFSelect import IFSelect_RetDone
ROOT=Path(sys.argv[1]).resolve()
EXE=Path(sys.argv[2]).resolve()
BASE=Path(sys.argv[3]).resolve() if len(sys.argv)>3 and sys.argv[3]!='none' else None
REPORT=ROOT/'R1113_LARGE_TESTS.json'
ROOT.mkdir(parents=True,exist_ok=True)
RESULTS=[]
def save():
    REPORT.write_text(json.dumps({'optimized_executable':str(EXE),'baseline_executable':str(BASE) if BASE else None,'cases':RESULTS},ensure_ascii=False,indent=2),encoding='utf8')
def write_step(path,solids):
    doc=TDocStd_Document(TCollection_ExtendedString('BinXCAF'))
    tool=XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())
    for label,shape in solids:
        ent=tool.AddShape(shape,False)
        TDataStd_Name.Set_s(ent,TCollection_ExtendedString(label))
    writer=STEPCAFControl_Writer();writer.SetNameMode(True)
    if not writer.Transfer(doc) or writer.Write(str(path))!=IFSelect_RetDone:raise RuntimeError('STEP writer failed')
def large_pair(name,count):
    folder=ROOT/name;folder.mkdir(exist_ok=True)
    a,b=folder/'large_A.step',folder/'large_B.step'
    shapes=[BRepPrimAPI_MakeBox(16+j*.8,9+j*.39,5+j*.27).Shape() for j in range(12)]
    original=[];edited=[]
    for i in range(count):
        k=i%12
        pos=gp_Trsf();pos.SetTranslation(gp_Vec(float((i%60)*90),float((i//60)*110),float((i%5)*2)))
        shape=shapes[k].Located(TopLoc_Location(pos))
        original.append((f'CZESC_{k:02d}',shape))
        if i%73==11:continue
        if i%89==22:
            move=gp_Trsf();move.SetTranslation(gp_Vec(0.,0.,30.))
            shape=shape.Moved(TopLoc_Location(move))
        edited.append((f'CZESC_{k:02d}',shape))
    for i in range(max(1,count//70)):
        tr=gp_Trsf();tr.SetTranslation(gp_Vec(float(10000+i*40),float(4000+i*20),0.))
        edited.append((f'NOWA_{i}',shapes[i%12].Located(TopLoc_Location(tr))))
    write_step(a,original);write_step(b,edited)
    return a,b
PUBLIC=[
    ('SO101_266','https://raw.githubusercontent.com/TheRobotStudio/SO-ARM100/a758567c3978dfeefe282ede0500085a48fe8f78/STEP/SO101/SO101%20Assembly.step','f754be35708382b05ce65768ae33c612f91dca11ad19d14807dc637eb944ba3d',None),
    ('OLSK_712','https://raw.githubusercontent.com/Open-Lab-Starter-Kit/OLSK-Small-CNC/cae066fa5b78b596743e1f2e432b93539cba8c24/OLSK_Small_CNC_V2/OLSK%20small%20CNC%20v2_Workshop.step.zip','c2b8e022eb84dea2488c805375e4f0c3890a4f3702065b045dfef66481ea556a','OLSK small CNC v2_Workshop.step'),
]
def public_pair(name,url,sha,inner):
    folder=ROOT/name;folder.mkdir(exist_ok=True)
    blob=urllib.request.urlopen(url,timeout=90).read()
    assert hashlib.sha256(blob).hexdigest()==sha,f'{name}: SHA mismatch'
    if inner:
        with zipfile.ZipFile(__import__('io').BytesIO(blob)) as f:
            names=[x for x in f.namelist() if Path(x).name==inner and not x.startswith('__MACOSX/')]
            assert len(names)==1,names
            blob=f.read(names[0])
    a,b=folder/'public_A.step',folder/'public_B.step'
    a.write_bytes(blob)
    # Harmless textual change forces geometry comparison through two imports.
    b.write_bytes(blob.replace(b'ISO-10303-21;',b'ISO-10303-21;\n/* controlled benchmark: same geometry */',1))
    return a,b
def execute(exe,folder,a,b,seconds=720):
    folder.mkdir(exist_ok=True)
    cmd=[str(exe),'--worker','compare','--a',str(a),'--b',str(b),'--output',str(folder),
         '--generate-step','--revision-style','--body-colors','--no-bom-csv','--step-verify','fast']
    env=dict(os.environ,DSCOMPARE_PARALLEL_IMPORT='off',QT_QPA_PLATFORM='offscreen')
    started=time.perf_counter()
    with (folder/'worker.log').open('w',encoding='utf8') as out:
        subprocess.run(cmd,stdout=out,stderr=subprocess.STDOUT,env=env,timeout=seconds,check=True)
    elapsed=time.perf_counter()-started
    meta=json.loads((folder/'PODSUMOWANIE.json').read_text(encoding='utf8'))
    timings=json.loads((folder/'CZASY_ANALIZY.json').read_text(encoding='utf8'))
    worker=json.loads((folder/'_WYNIK_V37.json').read_text(encoding='utf8'))
    assert worker['ok'] and not worker.get('blad_step'),worker
    assert meta['step_ready'] and not meta['bom_warnings'],(meta['step_ready'],meta['bom_warnings'])
    assert (folder/'POROWNANIE_KOLORY.step').is_file()
    assert not (folder/'BOM_A.csv').exists()
    assert (folder/'RAPORT.html').exists()
    groups={}
    for side in ('A','B'):
        values=json.loads((folder/f'BOM_GRUPY_{side}.json').read_text(encoding='utf8'))
        groups[side]=sorted(tuple(sorted(entry['index'] for entry in group['wystapienia'])) for group in values)
    normalized={'statuses':meta['statuses'],'records':meta['records'],'mass_A_kg':meta['mass_A_kg'],
                'mass_B_kg':meta['mass_B_kg'],'solids_A':meta['solids_A'],'solids_B':meta['solids_B'],
                'group_A':groups['A'],'group_B':groups['B']}
    return elapsed,timings,normalized,meta
def check(name,a,b):
    row={'case':name,'status':'FAIL','sha':[hashlib.sha256(a.read_bytes()).hexdigest(),hashlib.sha256(b.read_bytes()).hexdigest()]}
    RESULTS.append(row);save();print('START',name,flush=True)
    try:
        opt_time,opt_t,opt_data,opt_meta=execute(EXE,ROOT/name/'r1113',a,b)
        row.update(optimized_time_s=round(opt_time,3),optimized_timings=opt_t,
                   count_A=opt_meta['solids_A'],count_B=opt_meta['solids_B'],
                   statuses=opt_meta['statuses'],groups_A=len(opt_data['group_A']),groups_B=len(opt_data['group_B']))
        if BASE is not None:
            old_time,old_t,old_data,old_meta=execute(BASE,ROOT/name/'r1112',a,b)
            assert old_data==opt_data,'CLASSIFICATION, BOM OR MASS MISMATCH'
            row.update(baseline_time_s=round(old_time,3),baseline_timings=old_t,exact_results_equal=True)
        row['status']='PASS'
    except Exception:
        row['error']=traceback.format_exc()
    save();print(json.dumps({k:v for k,v in row.items() if k in ('case','status','optimized_time_s','baseline_time_s','error')},ensure_ascii=False),flush=True)
    return row['status']=='PASS'
def main():
    all_ok=True
    for count in (1600,2600):
        name=f'SYNTHETIC_{count}'
        a,b=large_pair(name,count)
        all_ok=check(name,a,b) and all_ok
    for name,url,sha,inner in PUBLIC:
        try:
            a,b=public_pair(name,url,sha,inner)
            all_ok=check(name,a,b) and all_ok
        except Exception as exc:
            RESULTS.append({'case':name,'status':'PUBLIC_SOURCE_UNAVAILABLE','error':str(exc)})
            save();print('PUBLIC_SOURCE_UNAVAILABLE',name,exc,flush=True)
    print('RESULT_FILE',REPORT,flush=True)
    if not all_ok:raise SystemExit('Large-model comparison regressions failed')
if __name__=='__main__':main()
