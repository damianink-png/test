"""Windows CI: frozen DSCompare.exe on actual >600-solid public assemblies.
The deterministic test shift is (+507.4569, -249.1752, +524) mm. On any failure the
partial diagnostic journal is left intact for upload; never assert 'same'.
"""
import argparse,hashlib,json,os,subprocess,time,traceback,urllib.request,zipfile,gc
from pathlib import Path
from OCP.gp import gp_Trsf,gp_Vec
from OCP.TopLoc import TopLoc_Location
from dsac29.step_io import load_step,ColoredDocument
from fixture_oracles import expected_count,verify_counts,sha256_file

MODELS={
 'v2':('Voron-2','e64c83bcb84d41c0324e104a1c911879174d08aa','CAD/Voron_2.4r2_Assembly_STEP.zip'),
 'v2_old':('Voron-2','e47cc70edbdb0c36916885b54a5e1f30f52a717a','CAD/Voron_2.4r2_Assembly_STEP.zip'),
 'trident':('Voron-Trident','1a49bdc2c524cd6f4491a01e8fd566d0bd6acd0a','CAD/trident_assembly.step.zip'),
 'trident_old':('Voron-Trident','9d9223311f2b0fce72484023d6a755e13a733319','CAD/trident_assembly.step.zip'),
}
p=argparse.ArgumentParser();p.add_argument('exe');p.add_argument('model',choices=['v2','trident']);p.add_argument('case',choices=['shift','revision_shift']);args=p.parse_args()
root=Path('evidence').resolve();root.mkdir(parents=True,exist_ok=True)
result={'model':args.model,'case':args.case,'sources':[],'comparison_engine':'frozen Windows EXE',
        'exe_sha256':hashlib.sha256(Path(args.exe).read_bytes()).hexdigest()}
def save(): (root/'TEST_RESULT.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
def download(key):
 repo,ref,name=MODELS[key]
 url=f'https://raw.githubusercontent.com/VoronDesign/{repo}/{ref}/{name}'
 folder=Path('models')/key;folder.mkdir(parents=True,exist_ok=True)
 z=folder/'source.zip'
 # GitHub raw/CDN occasionally returns 503 during a long ZIP transfer.
 # Never expose a partial download to the STEP importer.
 errors=[]
 for attempt in range(4):
  temp=folder/'source.zip.partial'
  try:
   temp.unlink(missing_ok=True)
   request=urllib.request.Request(url,headers={'User-Agent':'DSCompare-CAD-regression/1.0'})
   with urllib.request.urlopen(request,timeout=120) as response, temp.open('wb') as dest:
    while True:
     chunk=response.read(1024*1024)
     if not chunk:break
     dest.write(chunk)
   with zipfile.ZipFile(temp) as check:
    if check.testzip() is not None:raise zipfile.BadZipFile('Corrupt ZIP member')
   temp.replace(z)
   break
  except (OSError,zipfile.BadZipFile,EOFError) as exc:
   errors.append(f'{type(exc).__name__}: {exc}')
   temp.unlink(missing_ok=True)
   if attempt==3:raise RuntimeError(f'Source download failed after 4 attempts: {url}; '+repr(errors)) from exc
   time.sleep(min(2**attempt,8))
 with zipfile.ZipFile(z) as archive:archive.extractall(folder)
 candidates=[x for x in folder.rglob('*') if x.suffix.lower() in ('.step','.stp')]
 if not candidates:raise RuntimeError('STEP missing from '+key)
 f=max(candidates,key=lambda path:path.stat().st_size).resolve()
 digest=sha256_file(f);count=expected_count(ref,digest)
 result['sources'].append({'expected_solids':count,'url':url,'commit':ref,'sha256':digest,
                           'size_bytes':f.stat().st_size,'name':f.name});save()
 return f

def shifted_copy(file):
 parts=load_step(str(file),max_solids=20000)
 result['new_solids']=len(parts);save()
 if len(parts)<=600:raise AssertionError('Input assembly is not >600 solids')
 tr=gp_Trsf();tr.SetTranslation(gp_Vec(507.4569,-249.1752,524.))
 loc=TopLoc_Location(tr)
 writer=ColoredDocument(group_by_status=False,reuse_definitions=True)
 for part in parts:writer.add(part.shape.Moved(loc),part.name,(.33,.57,.86),1.)
 dest=Path('models')/'moved.step';writer.write(str(dest))
 del parts,writer;gc.collect()
 return dest.resolve()

try:
 newer=download(args.model)
 old=download(args.model+'_old') if args.case=='revision_shift' else newer
 moved=shifted_copy(newer)
 out=root/'comparison';out.mkdir(exist_ok=True)
 cmd=[str(Path(args.exe).resolve()),'--worker','compare','--a',str(old),'--b',str(moved),
      '--output',str(out),'--align-auto','--generate-step','--preview3d','--revision-style']
 result['command']=cmd;save()
 start=time.monotonic()
 stdout_path=root/'EXE_STDOUT.log'
 stderr_path=root/'EXE_STDERR.log'
 stdout_handle=open(stdout_path,'wb')
 stderr_handle=open(stderr_path,'wb')
 proc=subprocess.Popen(cmd,stdout=stdout_handle,stderr=stderr_handle)
 responses=[]
 while proc.poll() is None:
  request=out/'_WYROWNANIE_PYTANIE.json'
  if request.exists():
   try:
    proposal=json.loads(request.read_text(encoding='utf-8'))
    if proposal['token'] not in [x['token'] for x in responses]:
     # Approval only if B-Rep registration has a nonzero candidate.
     decision='align' if not proposal.get('unrelated') and not proposal.get('unresolved') and proposal.get('votes',0)>=8 else 'original'
     responses.append({'token':proposal['token'],'decision':decision})
     (out/'_WYROWNANIE_ODPOWIEDZ.json').write_text(json.dumps(responses[-1]),encoding='utf-8')
   except (ValueError,KeyError,OSError):pass
  if time.monotonic()-start>2400:
   subprocess.run(['taskkill','/F','/T','/PID',str(proc.pid)],capture_output=True)
   raise TimeoutError('EXE comparison exceeded 2400 seconds (unchanged cap)')
  time.sleep(.5)
 stdout_handle.close();stderr_handle.close()
 result.update(seconds=round(time.monotonic()-start,2),exit_code=proc.returncode,decisions=responses);save()
 if proc.returncode!=0:
  for name in ('EXE_STDOUT.log','EXE_STDERR.log'):
   p=root/name
   if p.exists():print('DIAGNOSTIC '+name+': '+p.read_text(encoding='utf-8',errors='replace')[-15000:],flush=True)
 if proc.returncode!=0:raise RuntimeError('EXE crashed/failed, exit='+str(proc.returncode))
 worker=json.loads((out/'_WYNIK_V37.json').read_text(encoding='utf-8'))
 if not worker['ok']:raise RuntimeError('Worker returned failure: '+repr(worker))
 summary=json.loads((out/'PODSUMOWANIE.json').read_text(encoding='utf-8'))
 expected_a=result['sources'][1 if args.case=='revision_shift' else 0]['expected_solids']
 expected_b=result['sources'][0]['expected_solids']
 verify_counts(summary,expected_a,expected_b)
 timing=out/'CZASY_ANALIZY.json'
 if timing.is_file():result['timings']=json.loads(timing.read_text(encoding='utf8'))
 result['summary']=summary;save()
 if min(summary['solids_A'],summary['solids_B'])<=600:raise AssertionError('Insufficient solids')
 if not summary.get('alignment',{}).get('applied'):raise AssertionError('No applied alignment')
 offset=summary['alignment']['translation_B_to_A_mm']
 if any(abs(x+y)>.01 for x,y in zip(offset,(507.4569,-249.1752,524))):raise AssertionError('Wrong shift '+repr(offset))
 counts=summary['statuses']
 if args.case=='shift':
  same=counts.get('SAME',0)+counts.get('RENAMED',0)
  if same!=result['new_solids']:raise AssertionError('False revisions: '+repr(counts))
  if any(counts.get(k,0) for k in ('ADDED','REMOVED','MOVED','CHANGED','UNCERTAIN')):raise AssertionError('False changes: '+repr(counts))
 else:
  if sum(counts.get(k,0) for k in ('ADDED','REMOVED','CHANGED'))<=0:raise AssertionError('Real revision changes were lost: '+repr(counts))
  if counts.get('SAME',0)+counts.get('RENAMED',0)>=min(summary['solids_A'],summary['solids_B']):raise AssertionError('Whole assembly incorrectly declared identical')
 if not summary.get('main_step_ready') or summary.get('main_step_error'):raise AssertionError('STEP export failed')
 if summary.get('preview_3d',{}).get('pominiete')!=0:raise AssertionError('HTML skipped solids')
 result['status']='PASS';save();print(json.dumps(result,ensure_ascii=False),flush=True)
except BaseException:
 result['status']='FAIL';result['error']=traceback.format_exc();save();raise
