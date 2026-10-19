"""Large, deterministic end-to-end STEP benchmark for DS Compare R10."""
import json,os,platform,subprocess,sys,time
from pathlib import Path
from OCP.BRep import BRep_Builder
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox,BRepPrimAPI_MakeCylinder
from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut
from OCP.gp import gp_Ax2,gp_Dir,gp_Pnt,gp_Trsf,gp_Vec
from OCP.TDocStd import TDocStd_Document
from OCP.TCollection import TCollection_ExtendedString
from OCP.TDataStd import TDataStd_Name
from OCP.TopoDS import TopoDS_Compound
from OCP.TopLoc import TopLoc_Location
from OCP.XCAFDoc import XCAFDoc_DocumentTool
from OCP.STEPCAFControl import STEPCAFControl_Writer
from OCP.IFSelect import IFSelect_RetDone

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'v46'
OUTPUT=ROOT/'benchmark_results'
OUTPUT.mkdir(exist_ok=True)

def shapes():
    result=[]
    for k in range(12):
        dims=((53,41,8) if k==10 else (56,41,8) if k==11 else (19,16,5) if k==8 else
              (21,16,7) if k==9 else (28+k*3,23+k*2,7+(k%3)*2))
        sh=BRepPrimAPI_MakeBox(*dims).Shape()
        if k in (2,5):
            x,y,z=dims
            tool=BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(x/3,y/2,-2),gp_Dir(0,0,1)),3,z+4).Shape()
            cut=BRepAlgoAPI_Cut(sh,tool);cut.Build()
            if not cut.IsDone():raise RuntimeError('drilled plate generation failed')
            sh=cut.Shape()
        result.append(sh)
    return result

def instances(n,version):
    out=[]
    for i in range(n):
        mod=i%20;k=i%8
        if mod==16:
            if version=='B':continue
            k=8
        elif mod==17:
            if version=='A':continue
            k=9
        elif mod in (18,19): k=10 if version=='A' else 11
        x=(i%25)*120.;y=(i//25)*100.;z=(i//125)*40.
        if version=='B' and mod in (12,13,14):y+=33
        name=('NOWA_NAZWA_' if version=='B' and mod==15 else '')+'PROFIL_%02d'%k
        out.append((k,name,x,y,z))
    return out

def step(path,bodies,items):
    doc=TDocStd_Document(TCollection_ExtendedString('BinXCAF'))
    tool=XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())
    cp=TopoDS_Compound();BRep_Builder().MakeCompound(cp)
    root=tool.AddShape(cp,True)
    TDataStd_Name.Set_s(root,TCollection_ExtendedString('ZLOZENIE_TEST'))
    used={item[0] for item in items}
    defs={}
    for k in sorted(used):
        defs[k]=tool.AddShape(bodies[k],False)
        TDataStd_Name.Set_s(defs[k],TCollection_ExtendedString('DEFINICJA_%d'%k))
    for k,name,x,y,z in items:
        tr=gp_Trsf();tr.SetTranslation(gp_Vec(x,y,z))
        occurrence=tool.AddComponent(root,defs[k],TopLoc_Location(tr))
        TDataStd_Name.Set_s(occurrence,TCollection_ExtendedString(name))
    tool.UpdateAssemblies()
    writer=STEPCAFControl_Writer();writer.SetNameMode(True)
    if not writer.Transfer(doc) or writer.Write(str(path))!=IFSelect_RetDone:
        raise RuntimeError('STEP write failed: '+str(path))

def trial(n,timeout=1000):
    folder=OUTPUT/str(n);folder.mkdir(parents=True,exist_ok=True)
    out=folder/'results';out.mkdir(exist_ok=True)
    a=instances(n,'A');b=instances(n,'B');bodies=shapes()
    t0=time.perf_counter()
    step(folder/'A.step',bodies,a)
    step(folder/'B.step',bodies,b)
    creation=time.perf_counter()-t0
    cmd=[sys.executable,str(SOURCE/'DSCompareV3.py'),'--worker','compare',
         '--a',str(folder/'A.step'),'--b',str(folder/'B.step'),'--output',str(out),
         '--generate-step','--revision-style','--max-solids','2000',
         '--tolerance','0.01','--schema','AP214IS','--step-verify','fast','--old-alpha','0.4']
    start=time.perf_counter()
    p=subprocess.Popen(cmd,cwd=SOURCE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    handoff=None;transitions=[];stage=out/'_ETAPY.json'
    while p.poll() is None:
        elapsed=time.perf_counter()-start
        if stage.exists():
            try:
                item=json.loads(stage.read_text(encoding='utf-8'))
                state=(item.get('step'),item.get('reports'),item.get('report_percent'))
                if not transitions or transitions[-1][1]!=state:transitions.append((round(elapsed,2),state))
                if handoff is None and item.get('step')=='gotowy':handoff=elapsed
            except (OSError,ValueError):pass
        if elapsed>timeout:
            p.kill();stdout,stderr=p.communicate()
            return {'size':n,'ok':False,'reason':'TIMEOUT','elapsed':elapsed,'stderr':stderr[-1500:]}
        time.sleep(.04)
    stdout,stderr=p.communicate(timeout=30);elapsed=time.perf_counter()-start
    if handoff is None and stage.is_file() and json.loads(stage.read_text(encoding='utf-8')).get('step')=='gotowy':
        handoff=elapsed
    result=json.loads((out/'_WYNIK_V37.json').read_text(encoding='utf-8'))
    summary=json.loads((out/'PODSUMOWANIE.json').read_text(encoding='utf-8'))
    statuses=summary['statuses']
    covered_a=sum(v for key,v in statuses.items() if key not in ('ADDED',))
    covered_b=sum(v for key,v in statuses.items() if key not in ('REMOVED',))
    events=(out/'_POSTEP_V37.jsonl').read_text(encoding='utf-8')
    markers=['STEP GOTOWY','BOM A ukończony','Finalizowanie raportu']
    workflow_order=all(s in events for s in markers) and [events.index(s) for s in markers]==sorted(events.index(s) for s in markers)
    required=['POROWNANIE_KOLORY.step','RAPORT.html','BOM_A.csv','BOM_B.csv','ZMIANY.csv','PODSUMOWANIE.json']
    checks={'worker_ok':p.returncode==0 and result.get('ok',False),
            'all_reports':all((out/f).is_file() for f in required),
            'STEP_size':(out/'POROWNANIE_KOLORY.step').stat().st_size>1000 if (out/'POROWNANIE_KOLORY.step').is_file() else False,
            'count_A':covered_a==len(a),'count_B':covered_b==len(b),
            'no_uncertain':statuses.get('UNCERTAIN',0)==0,
            'STEP_before_reports':workflow_order,
            'reports_100pct':json.loads(stage.read_text(encoding='utf-8')).get('report_percent')==100}
    record={'size':n,'solids_A':len(a),'solids_B':len(b),
            'input_A_MiB':round((folder/'A.step').stat().st_size/1048576,2),
            'input_B_MiB':round((folder/'B.step').stat().st_size/1048576,2),
            'output_step_MiB':round((out/'POROWNANIE_KOLORY.step').stat().st_size/1048576,2) if (out/'POROWNANIE_KOLORY.step').exists() else 0,
            'input_generation_s':round(creation,2),'STEP_ready_s':round(handoff,2) if handoff is not None else None,
            'reports_complete_s':round(elapsed,2),'status_counts':statuses,
            'checks':checks,'stage_transitions':transitions[::max(1,len(transitions)//30)],
            'error':stderr[-1200:] if p.returncode else '', 'ok':all(checks.values())}
    print('BENCHMARK '+json.dumps(record,ensure_ascii=False),flush=True)
    return record

def main():
    report={'platform':platform.platform(),'python':sys.version,
            'test_type':'SYNTHETIC_XCAF_STEP_ASSEMBLIES',
            'caveat':'This is not a real ZW3D 2019 assembly nor an importer test',
            'cases':[]}
    for n in (120,400,800):
        result=trial(n)
        report['cases'].append(result)
        (OUTPUT/'wyniki_testow.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        if not result['ok']:return 1
    return 0

if __name__=='__main__':sys.exit(main())
