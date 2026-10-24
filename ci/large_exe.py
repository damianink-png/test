"""Public CAD tests: comparisons are performed by the frozen Windows EXE only."""
import argparse,json,hashlib,urllib.request,zipfile,time,subprocess,os,traceback
from pathlib import Path
MODELS={
 'v2':('Voron-2','e64c83bcb84d41c0324e104a1c911879174d08aa','CAD/Voron_2.4r2_Assembly_STEP.zip'),
 'v2_old':('Voron-2','e47cc70edbdb0c36916885b54a5e1f30f52a717a','CAD/Voron_2.4r2_Assembly_STEP.zip'),
 'trident':('Voron-Trident','1a49bdc2c524cd6f4491a01e8fd566d0bd6acd0a','CAD/trident_assembly.step.zip'),
 'trident_old':('Voron-Trident','9d9223311f2b0fce72484023d6a755e13a733319','CAD/trident_assembly.step.zip'),
 'switchwire':('Voron-Switchwire','92cc013ca2af94e6c09950dbe05c0973ee49aa00','CAD/Switchwire_Assembly_v1_STEP.zip')}
p=argparse.ArgumentParser();p.add_argument('exe');p.add_argument('model');p.add_argument('case',choices=['stationary','shift','revision']);args=p.parse_args()
root=Path('evidence').resolve();root.mkdir(exist_ok=True)
result={'model':args.model,'case':args.case,'sources':[],'exe_sha256':hashlib.sha256(Path(args.exe).read_bytes()).hexdigest(),'comparison_engine':'frozen Windows EXE'}
def save(): (root/'TEST_RESULT.json').write_text(json.dumps(result,indent=2),encoding='utf8')
def download(key):
 repo,ref,name=MODELS[key];url=f'https://raw.githubusercontent.com/VoronDesign/{repo}/{ref}/{name}'
 folder=Path('models')/key;folder.mkdir(parents=True,exist_ok=True);z=folder/'source.zip'
 urllib.request.urlretrieve(url,z)
 with zipfile.ZipFile(z) as f: f.extractall(folder)
 steps=[x for x in folder.rglob('*') if x.suffix.lower() in ('.stp','.step')];assert steps, 'No STEP in archive'
 source=max(steps,key=lambda x:x.stat().st_size).resolve()
 result['sources'].append({'url':url,'commit':ref,'file':source.name,'sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'bytes':source.stat().st_size});save();return source
try:
 a=download(args.model);b=a
 from dsac29.step_io import load_step,ColoredDocument
 parts=load_step(str(a),max_solids=20000);n=len(parts);result['source_solids']=n;save();print('SOURCE SOLIDS',n,flush=True)
 assert n>600, f'Assembly has only {n} solids; does not meet >600 requirement'
 if args.case=='shift':
  from OCP.gp import gp_Trsf,gp_Vec
  from OCP.TopLoc import TopLoc_Location
  tr=gp_Trsf();tr.SetTranslation(gp_Vec(1275.,-395.,210.));writer=ColoredDocument(group_by_status=False,reuse_definitions=True)
  for part in parts:writer.add(part.shape.Moved(TopLoc_Location(tr)),part.name,(.33,.57,.86),1.)
  b=Path('models/moved.step').resolve();writer.write(str(b))
 elif args.case=='revision':
  b=a;a=download(args.model+'_old');old=load_step(str(a),max_solids=20000);result['old_solids']=len(old);assert len(old)>600;del old
 del parts
 import gc;gc.collect()
 out=root/'comparison';out.mkdir(exist_ok=True)
 command=[str(Path(args.exe).resolve()),'--worker','compare','--a',str(a),'--b',str(b),'--output',str(out),'--align-auto','--generate-step','--preview3d','--revision-style','--no-bom']
 result['command']=command;save();start=time.monotonic();proc=subprocess.Popen(command);decisions=[]
 while proc.poll() is None:
  request=out/'_WYROWNANIE_PYTANIE.json'
  if request.exists():
   try:
    q=json.loads(request.read_text(encoding='utf8'))
    if q['token'] not in [x['token'] for x in decisions]:
     # Approval is only granted for a geometrically proven common translation.
     decision='align' if args.case=='shift' and not q.get('unresolved') and not q.get('unrelated') else 'original'
     decisions.append(dict(q,decision=decision));(out/'_WYROWNANIE_ODPOWIEDZ.json').write_text(json.dumps({'token':q['token'],'decision':decision}),encoding='utf8')
   except (ValueError,OSError):pass
  if time.monotonic()-start>2400:
   subprocess.run(['taskkill','/F','/T','/PID',str(proc.pid)],capture_output=True);raise TimeoutError('EXE comparison exceeded 2400 seconds')
  time.sleep(.5)
 result.update(seconds=round(time.monotonic()-start,2),exit_code=proc.returncode,decisions=decisions);save()
 assert proc.returncode==0, f'EXE exited {proc.returncode}'
 worker=json.loads((out/'_WYNIK_V37.json').read_text(encoding='utf8'));assert worker['ok'],worker
 s=json.loads((out/'PODSUMOWANIE.json').read_text(encoding='utf8'));result['summary']=s
 result['timing']=json.loads((out/'CZASY_ANALIZY.json').read_text(encoding='utf8'));save()
 assert min(s['solids_A'],s['solids_B'])>600
 assert s['main_step_ready'] and not s.get('main_step_error')
 assert s['preview_3d']['pominiete']==0,s['preview_3d']
 html=(out/'PODGLAD_KOLOROW_3D.html').read_text(encoding='utf8');assert 'function pathSegments' in html and 'const scene=[' in html
 if args.case!='revision':
  assert s['statuses'].get('SAME',0)+s['statuses'].get('RENAMED',0)==n,s['statuses']
  assert not any(s['statuses'].get(k,0) for k in ['ADDED','REMOVED','MOVED','CHANGED'])
  if args.case=='stationary':assert not decisions and not s['alignment'].get('applied'),s['alignment']
  else:
   assert s['alignment'].get('applied'),s['alignment']
   assert all(abs(x+y)<.05 for x,y in zip(s['alignment']['translation_B_to_A_mm'],[1275,-395,210]))
 else:result['oracle_note']='Authentic revision pair: no independently established expected classification counts; completion and export consistency checked only.'
 result['status']='PASS';save();print(json.dumps(result,ensure_ascii=False),flush=True)
except BaseException:
 result['status']='FAIL';result['error']=traceback.format_exc();save();raise
