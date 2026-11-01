"""Compare real LFS-hosted Simple Swerve STEP assemblies with the patched CAD core."""
import json,sys,zipfile,time,traceback,hashlib
from pathlib import Path

base=Path(sys.argv[1]).resolve()
root=Path(sys.argv[2]).resolve()
root.mkdir(parents=True,exist_ok=True)
labels=['simple-swerve-v1.zip','simple-swerve-v2-gobilda.zip']
status={'sources':[],'stage':'start','result':'RUNNING'}
def save():
 (root/'SWERVE_TEST_RESULT.json').write_text(json.dumps(status,indent=2,ensure_ascii=False,default=str),encoding='utf8')

try:
 selected=[]
 for label in labels:
  p=base/label
  if not p.is_file():raise FileNotFoundError(p)
  record={'name':label,'size_bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
  status['sources'].append(record)
  if not zipfile.is_zipfile(p):raise RuntimeError(f'Nie pobrano prawdziwego ZIP przez Git LFS: {p}')
  target=root/label.removesuffix('.zip')
  with zipfile.ZipFile(p) as archive:
   files=[entry for entry in archive.infolist() if not entry.is_dir()]
   record['archive_entries']=len(files)
   record['extensions']=sorted(set(Path(entry.filename).suffix.lower() for entry in files))
   for entry in files:
    candidate=(target/entry.filename).resolve()
    if not candidate.is_relative_to(target.resolve()):
     raise RuntimeError('Niebezpieczna ścieżka ZIP: '+entry.filename)
   archive.extractall(target)
  steps=sorted((f for f in target.rglob('*') if f.is_file() and f.suffix.lower() in ('.step','.stp')),key=lambda f:f.stat().st_size,reverse=True)
  record['step_candidates']=[{'path':str(f.relative_to(target)),'bytes':f.stat().st_size} for f in steps[:12]]
  if not steps:raise RuntimeError(f'W archiwum {label} brak pliku STEP/STP. Dostępne formaty: {record["extensions"]}')
  selected.append(steps[0])
  record['selected_step']=str(steps[0])
  save()
 status['stage']='core_comparison'
 save()
 from dsac29.cli import process
 decisions=[]
 def choose_material(proposal):
  decisions.append({'type':'material','status':proposal.get('status'),'unverified_A':proposal.get('unverified_A'),'unverified_B':proposal.get('unverified_B'),'failed_pair':proposal.get('failed_pair')})
  save()
  return 'review'
 def choose_alignment(proposal):
  choice='align' if proposal.get('status')=='registered' else 'original'
  decisions.append({'type':'alignment','status':proposal.get('status'),'decision':choice})
  save()
  return choice
 started=time.monotonic()
 output=root/'comparison';output.mkdir(exist_ok=True)
 folder,records,err=process(str(selected[0]),str(selected[1]),str(output),tolerance=.01,
   step=True,preview3d=False,diff_step=False,full_bom=False,
   revision_style=True,auto_align=True,alignment_approval=choose_alignment,
   material_approval=choose_material,force_unrelated=True,progress=lambda line:print(str(line),flush=True))
 status.update(stage='comparison_finished',seconds=round(time.monotonic()-started,2),
               output_error=str(err) if err else None,decisions=decisions)
 summary=json.loads((folder/'PODSUMOWANIE.json').read_text(encoding='utf8'))
 status['summary']={key:summary.get(key) for key in ['solids_A','solids_B','statuses','analysis_complete','material_analysis_complete','step_ready','main_step_ready']}
 detail=summary.get('revision_overlap') or {}
 status['revision_overlap']=detail
 status['result']='PASS' if not err and summary.get('step_ready')!=False else 'FAIL'
 if status['result']=='FAIL':raise RuntimeError('Niekompletny eksport STEP: '+str(err))
 save()
 print('SWERVE_RESULT '+json.dumps({'result':status['result'],'summary':status['summary'],'revision_overlap':detail,'seconds':status['seconds']},ensure_ascii=False),flush=True)
except BaseException:
 status['result']='FAIL';status['error']=traceback.format_exc();save();raise
