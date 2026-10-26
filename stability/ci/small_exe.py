"""Small CAD regression: comparisons use the frozen Windows executable only."""
import json, os, subprocess, sys, time, traceback
from pathlib import Path
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCP.gp import gp_Pnt
from dsac29.step_io import ColoredDocument, load_step
exe=Path(sys.argv[1]).resolve();root=Path('small_evidence').resolve();root.mkdir(exist_ok=True)
os.environ['DSCOMPARE_CACHE_DIR']=str(root/'cache')
os.environ['DSCOMPARE_PARALLEL_IMPORT']='off'
results=[]
def model(path,count=12,changed=False,shift=0):
    doc=ColoredDocument()
    for i in range(count):
        length=20+i+(2 if changed and i==0 else 0)
        shape=BRepPrimAPI_MakeBox(gp_Pnt(i*60+shift,(i%3)*50,0),length,10+i,10).Shape()
        doc.add(shape,('revision_plate' if changed and i==0 else 'plate_'+str(i)),(.5,.5,.5))
    doc.write(path)
a=root/'a.step';b=root/'b.step';shift=root/'b_shift.step'
model(a);model(b,changed=True);model(shift,changed=True,shift=1000)
for case,mode,bfile in [('revision_off','off',b),('revision_cold','on',b),('revision_warm','on',b),('revision_warm_repeat','on',b),('identical','off',a),('shift_revision','off',shift)]:
    entry={'case':case,'cache':mode};out=root/case;out.mkdir(exist_ok=True);start=time.monotonic()
    try:
        env=os.environ.copy();env['DSCOMPARE_IMPORT_CACHE']=mode
        args=[str(exe),'--worker','compare','--a',str(a),'--b',str(bfile),'--output',str(out),'--align-auto','--generate-step','--preview3d','--revision-style','--no-bom']
        with (out/'console.log').open('w',encoding='utf8') as log:
            p=subprocess.Popen(args,env=env,stdout=log,stderr=subprocess.STDOUT)
            while p.poll() is None:
                q=out/'_WYROWNANIE_PYTANIE.json'
                if q.exists():
                    data=json.loads(q.read_text(encoding='utf8'))
                    (out/'_WYROWNANIE_ODPOWIEDZ.json').write_text(json.dumps({'token':data['token'],'decision':'align' if case=='shift_revision' else 'original'}),encoding='utf8')
                if time.monotonic()-start>180:
                    subprocess.run(['taskkill','/F','/T','/PID',str(p.pid)],capture_output=True)
                    raise TimeoutError('180 s scenario deadline')
                time.sleep(.2)
        assert p.returncode==0,p.returncode
        result=json.loads((out/'_WYNIK_V37.json').read_text(encoding='utf8'));assert result['ok'],result
        summary=json.loads((out/'PODSUMOWANIE.json').read_text(encoding='utf8'));counts=summary['statuses']
        entry['statuses']=counts
        expected={'SAME':12} if case=='identical' else {'SAME':11,'CHANGED':1}
        assert {k:v for k,v in counts.items() if v}==expected,counts
        assert summary['main_step_ready'] and not summary.get('main_step_error'),summary.get('main_step_error')
        assert not summary.get('material_errors'),summary.get('material_errors')
        assert summary.get('preview_3d',{}).get('pominiete')==0
        assert (out/'PODGLAD_KOLOROW_3D.html').stat().st_size>1000
        solids=load_step(str(out/'POROWNANIE_KOLORY.step'))
        assert len(solids)>=12,len(solids)
        events=(out/'_POSTEP_V37.jsonl').read_text(encoding='utf8')
        if 'warm' in case:assert 'Cache STEP:' in events,'Cache HIT missing'
        entry['step_solids']=len(solids);entry['result']='PASS'
    except Exception:
        entry['result']='FAIL';entry['error']=traceback.format_exc()
    entry['seconds']=round(time.monotonic()-start,2);results.append(entry)
    (root/'RESULTS.json').write_text(json.dumps(results,indent=2,ensure_ascii=False),encoding='utf8')
    print(json.dumps(entry,ensure_ascii=False),flush=True)
# Additional displacement coverage: distinct solid counts up to 50, with and without a revision.
for count in (5,10,20,30,40,50):
    for changed in (False,True):
        case=f'shift_{count}_'+('revision' if changed else 'identical')
        aa=root/f'a_{count}.step';bb=root/f'b_{count}_{changed}_shift.step'
        model(aa,count=count);model(bb,count=count,changed=changed,shift=1000+count*17)
        out=root/case;out.mkdir(exist_ok=True);start=time.monotonic()
        entry={'case':case,'count':count,'shift_x_mm':1000+count*17}
        try:
            env=os.environ.copy();env['DSCOMPARE_IMPORT_CACHE']='off'
            args=[str(exe),'--worker','compare','--a',str(aa),'--b',str(bb),'--output',str(out),'--align-auto','--generate-step','--preview3d','--revision-style','--no-bom']
            with (out/'console.log').open('w',encoding='utf8') as log:
                p=subprocess.Popen(args,env=env,stdout=log,stderr=subprocess.STDOUT)
                while p.poll() is None:
                    q=out/'_WYROWNANIE_PYTANIE.json'
                    if q.exists():
                        data=json.loads(q.read_text(encoding='utf8'))
                        (out/'_WYROWNANIE_ODPOWIEDZ.json').write_text(json.dumps({'token':data['token'],'decision':'align'}),encoding='utf8')
                    if time.monotonic()-start>240:
                        subprocess.run(['taskkill','/F','/T','/PID',str(p.pid)],capture_output=True)
                        raise TimeoutError('240 s scenario deadline')
                    time.sleep(.2)
            assert p.returncode==0,p.returncode
            result=json.loads((out/'_WYNIK_V37.json').read_text(encoding='utf8'));assert result['ok'],result
            summary=json.loads((out/'PODSUMOWANIE.json').read_text(encoding='utf8'))
            counts={k:v for k,v in summary['statuses'].items() if v}
            expected={'SAME':count} if not changed else {'SAME':count-1,'CHANGED':1}
            assert counts==expected,(counts,expected)
            assert summary['main_step_ready'] and not summary.get('main_step_error'),summary.get('main_step_error')
            assert not summary.get('material_errors'),summary.get('material_errors')
            assert summary.get('preview_3d',{}).get('pominiete')==0
            assert (out/'PODGLAD_KOLOROW_3D.html').stat().st_size>1000
            solids=load_step(str(out/'POROWNANIE_KOLORY.step'))
            assert len(solids)>=count,len(solids)
            entry.update(statuses=counts,step_solids=len(solids),result='PASS')
        except Exception:
            entry.update(result='FAIL',error=traceback.format_exc())
        entry['seconds']=round(time.monotonic()-start,2);results.append(entry)
        (root/'RESULTS.json').write_text(json.dumps(results,indent=2,ensure_ascii=False),encoding='utf8')
        print(json.dumps(entry,ensure_ascii=False),flush=True)
assert all(x['result']=='PASS' for x in results),results
