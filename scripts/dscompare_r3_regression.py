"""R3 regression for dedup alignment, independent export status and SHA cache."""
import json,os,time,hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCP.gp import gp_Trsf,gp_Vec
from OCP.TopLoc import TopLoc_Location
import dsac29.alignment as alignment
from dsac29.geometry import describe, equivalent_world
from dsac29.registration_gate import frame_support
from dsac29.compare import compare
from dsac29.revision_rules import classify_revisions
from dsac29 import import_cache,report
from dsac29.geometry_registry import GeometryRegistry

def solid(i,dx=0,dy=0,moved=False):
 t=gp_Trsf()
 t.SetTranslation(gp_Vec(i*63+dx,i*17+dy+(11 if moved else 0),0))
 shape=BRepPrimAPI_MakeBox(20+i,12,14).Shape().Located(TopLoc_Location(t))
 return describe(shape,f'ANCHOR{i}',f'ANCHOR{i}')

a=[solid(i) for i in range(22)]
b=[solid(i,120,39,i==21) for i in range(22)]
calls=[0]
original=alignment.equivalent_world
def counted(*args,**kwargs):
 calls[0]+=1
 return original(*args,**kwargs)
alignment.equivalent_world=counted
try:
 aligned,info=alignment.align_assembly(a,b,.01)
finally:alignment.equivalent_world=original
assert info['status']=='registered' and info['votes']>=21,info
assert len(aligned)==len(b)
assert calls[0]<200, f'Nearly identical transforms still trigger redundant OCC checks: {calls[0]}'
rows=classify_revisions(a,aligned,compare(a,aligned,.01,revision_only=True,exact_serialization=True),.01)
statuses=[r.status for r in rows]
assert statuses.count('SAME')==21 and statuses.count('MOVED')==1,statuses
print(f'PASS: registered whole assembly, one truly moved component; {calls[0]} native B-Rep world tests')

with TemporaryDirectory() as d:
 folder=Path(d)
 src=folder/'input.step'
 src.write_bytes(b'STEP test material'*170_000)
 digest=hashlib.sha256(src.read_bytes()).hexdigest()
 stat=src.stat()
 state=(stat.st_size,stat.st_mtime_ns)
 os.environ['DSCOMPARE_IMPORT_CACHE']='on'
 old_open=Path.open
 counts=[0]
 def tracking(self,*args,**kwargs):
  if self==src:counts[0]+=1
  return old_open(self,*args,**kwargs)
 Path.open=tracking
 try:
  key=import_cache.cache_key(src,source_sha256=digest,source_stat=state)
 finally:Path.open=old_open
 assert key and key[1]==digest and counts[0]==0,(key,counts)
 src.write_bytes(src.read_bytes()+b'changed')
 changed=import_cache.cache_key(src,source_sha256=digest,source_stat=state)
 assert changed and changed[1]!=digest
 print('PASS: cached SHA reused with original metadata, stale SHA invalidated after content change')

 # The main STEP is produced successfully while the optional differences
 # exporter fails: report must NOT mark the genuine colored STEP as broken.
 left=[solid(0)];right=[solid(0)]
 rows=classify_revisions(left,right,compare(left,right,.01,revision_only=True),.01)
 main=report.export_revision_step
 optional=report.export_differences_step
 def fake_main(path,*args,**kwargs):
  Path(path).write_bytes(b'STEP'+b'#1=SHAPE_REPRESENTATION();\\n'*30)
  return {'weryfikacja':'testowa','pokolorowane_etykiety':1}
 def fake_optional(*args,**kwargs):
  raise RuntimeError('Optional B-Rep writer deliberately failed')
 report.export_revision_step=fake_main
 report.export_differences_step=fake_optional
 try:
  target,err=report.produce(folder/'result',left,right,rows,7850.,
    generate_step=True,diff_step=True,revision_style=True,full_bom=False,
    report_context={'A':'old.step','B':'new.step',
                   'import':{'A':{'faces_outside_solids':2},'B':{}},
                   'fingerprints':{'A':'hash_old','B':'hash_new'},
                   'alignment':{'status':'already_aligned'},
                   'source_A':'source_old','source_B':'source_new'})
 finally:
  report.export_revision_step=main
  report.export_differences_step=optional
 summary=json.loads((target/'PODSUMOWANIE.json').read_text(encoding='utf8'))
 assert err is None and summary['step_ready'] and summary['main_step_ready'],(err,summary)
 assert summary['optional_diff_errors'] and 'Optional B-Rep' in summary['optional_diff_errors'][0]
 assert summary['source_fingerprints']['A']=='hash_old'
 assert summary['import_diagnostics']['A']['faces_outside_solids']==2
 body=(target/'RAPORT.html').read_text(encoding='utf8')
 assert body.count('A — stara rewizja:')==1
 assert body.count('Pominięto 2 powierzchni')==1
 assert (target/'UWAGI_ROZNICE_BREP.txt').is_file()
 print('PASS: valid main colored STEP remains ready even if optional B-Rep export failed')

from PySide6.QtWidgets import QApplication
from dsac29.gui46 import Window
app=QApplication.instance() or QApplication([])
w=Window();w.show();app.processEvents()
assert hasattr(w,'_global_status')
w.close()
print('R3 regression complete')
