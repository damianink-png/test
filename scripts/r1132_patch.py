"""R11.32: safer/faster shared-frame proof, transactional settings, contrast and About motion."""
import os
from pathlib import Path
root=Path(os.environ["DS_COMPARE_SOURCE"])
def edit(rel,func):
 p=root/rel;s=p.read_text(encoding="utf8");p.write_text(func(s),encoding="utf8")
def put(s,old,new):
 n=s.count(old)
 if n!=1:raise RuntimeError("R11.32 expected one source anchor, found "+str(n)+": "+old[:95])
 return s.replace(old,new,1)

registration='''"""Fast world-coordinate consensus with bounded B-Rep verification."""
from collections import defaultdict
from itertools import product
from math import floor
import numpy as np
from .geometry import signature,candidate,equivalent_world

def frame_support(a,b,tolerance,proofs=8):
 if not a or not b:return dict(count=0,ratio=0.,proofs=0,checked=0)
 tol=max(tolerance,1.e-6);cell_size=max(tol*2,.002)
 buckets=defaultdict(list)
 for i,part in enumerate(a):
  pos=tuple(floor(float(v)/cell_size) for v in part.center)
  buckets[signature(part),pos].append(i)
 occupied=set();pairs=[]
 for j,part in enumerate(b):
  pos=np.asarray(part.center)
  base=tuple(floor(float(v)/cell_size) for v in pos)
  found=None
  for steps in product((-1,0,1),repeat=3):
   loc=tuple(x+y for x,y in zip(base,steps))
   for i in buckets.get((signature(part),loc),()):
    if i in occupied:continue
    if np.linalg.norm(a[i].center-pos)>tol or not candidate(a[i],part,tol):continue
    found=i;break
   if found is not None:break
  if found is not None:occupied.add(found);pairs.append((found,j))
 if not pairs:return dict(count=0,ratio=0.,proofs=0,checked=0)
 n=min(proofs,len(pairs))
 selection=[pairs[k*(len(pairs)-1)//max(1,n-1)] for k in range(n)]
 confirmed=sum(bool(equivalent_world(a[i],b[j],tol)) for i,j in selection)
 return dict(count=len(pairs),ratio=len(pairs)/max(1,min(len(a),len(b))),
             proofs=confirmed,checked=n)

def already_world_aligned(a,b,tolerance):
 r=frame_support(a,b,tolerance)
 return (r['ratio']>=.55 and r['proofs']==r['checked'] and
         r['checked']>=min(2,min(len(a),len(b))))
'''
(root/"dsac29/registration_gate.py").write_text(registration,encoding="utf8")
def cli_patch(s):
 s=put(s,"""        # Large parallel importers in frozen EXE may exhaust RAM; prefer one
        # sequential OCC reader for interactive comparisons.
        parallel,reason=(False,'tryb bezpieczny: import sekwencyjny') if auto_align else should_parallel(a_path,b_path)""",
 """        # Parallel import for moderate files, sequential for large models.
        combined_size=Path(a_path).stat().st_size+Path(b_path).stat().st_size
        parallel,reason=should_parallel(a_path,b_path)
        if combined_size>75_000_000:
            parallel,reason=False,'duże STEP: import sekwencyjny chroni pamięć'""")
 s=put(s,"""        from .registration_gate import already_world_aligned
        if already_world_aligned(a,b,tolerance):""",
 """        from .registration_gate import frame_support
        initial=frame_support(a,b,tolerance)
        if (initial['ratio']>=.55 and initial['proofs']==initial['checked']
            and initial['checked']>=min(2,min(len(a),len(b)))):""")
 s=put(s,"""            delta=proposal.get('translation_B_to_A_mm',(0,0,0))
            import numpy as np""",
 """            # Avoid 'correcting' individually moved elements using a false
            # global transform. It must improve the entire assembly strongly.
            after=frame_support(a,shifted,tolerance)
            population=min(len(a),len(b))
            if (after['ratio']<.60 or
                after['count']-initial['count']<max(2,int(population*.12)) or
                after['proofs']!=after['checked']):
                raise RuntimeError('Przesunięcie CAŁEGO złożenia niepotwierdzone: '
                    f'bez wyrównania {initial["count"]}, po {after["count"]} '
                    f'z {population} wspólnych brył; anulowano eksport.')
            delta=proposal.get('translation_B_to_A_mm',(0,0,0))
            import numpy as np""")
 return s
edit("dsac29/cli.py",cli_patch)

def ui_patch(s):
 s=put(s,"LIGHT={'bg':'#EBF0F7','surface':'#FFFFFF','field':'#F2F6FC','hover':'#E8F2FF','line':'#CED8E6','ink':'#162235','muted':'#65768C','accent':'#1677F7','soft':'#E6F0FF'}",
       "LIGHT={'bg':'#E5ECF4','surface':'#FFFFFF','field':'#E9F0FA','hover':'#DDEAFB','line':'#ABBED3','ink':'#15243A','muted':'#4C6079','accent':'#1268D8','soft':'#D8E8FA'}")
 s=put(s,"  self.apply_theme(self.theme.currentText())\n  self.navigate('compare')",
       "  self.apply_theme(self.theme.currentText())\n  self._install_settings_transactions()\n  self.navigate('compare')")
 start=s.index(" def navigate(self,key):",s.index(" def _set_busy_ui(self,busy):"))
 end=s.index(" def _modern_compare(self):",start)
 s=s[:start]+''' def _settings_snapshot(self):
  return dict(tolerance=self.tolerance.value(),solid_limit=self.solid_limit.value(),
       full_bom=self.full_bom.isChecked(),bom_mode=self.bom_mode.currentIndex(),
       bom_csv=self.bom_csv.isChecked(),cache_import=self.cache_import.isChecked(),
       output=self.output.text())
 def _install_settings_transactions(self):
  self._settings_saved=self._settings_snapshot();self._settings_restoring=False
  for widget,signal in ((self.tolerance,'valueChanged'),(self.solid_limit,'valueChanged'),
     (self.full_bom,'toggled'),(self.bom_mode,'currentIndexChanged'),
     (self.bom_csv,'toggled'),(self.cache_import,'toggled'),(self.output,'textChanged')):
   getattr(widget,signal).connect(self._settings_changed)
  self._settings_changed()
 def _settings_dirty(self):
  return hasattr(self,'_settings_saved') and self._settings_snapshot()!=self._settings_saved
 def _settings_changed(self,*args):
  if getattr(self,'_settings_restoring',False):return
  if hasattr(self,'_settings_save_button'):
   dirty=self._settings_dirty()
   self._settings_save_button.setEnabled(dirty and self.process is None)
   self._settings_cancel_button.setEnabled(dirty)
   self._settings_save_feedback.setText('● Niezapisane zmiany' if dirty else '')
 def _settings_revert(self):
  if not hasattr(self,'_settings_saved'):return
  self._settings_restoring=True
  try:
   saved=self._settings_saved
   self.tolerance.setValue(saved['tolerance'])
   self.solid_limit.setValue(saved['solid_limit'])
   self.full_bom.setChecked(saved['full_bom'])
   self.bom_csv.setChecked(saved['bom_csv'])
   self.cache_import.setChecked(saved['cache_import'])
   self.bom_mode.setCurrentIndex(saved['bom_mode'])
   self.output.setText(saved['output'])
  finally:self._settings_restoring=False
  self._settings_changed()
 def navigate(self,key):
  if (hasattr(self,'_settings_saved') and key!='settings' and
      self.stack.currentWidget() is self.pages['settings'] and self._settings_dirty()):
   prompt=QMessageBox(self);prompt.setWindowTitle('Niezapisane ustawienia')
   prompt.setIcon(QMessageBox.Question)
   prompt.setText('Zmodyfikowano ustawienia. Co zrobić przed zmianą zakładki?')
   save=prompt.addButton('Zapisz',QMessageBox.AcceptRole)
   discard=prompt.addButton('Odrzuć zmiany',QMessageBox.DestructiveRole)
   stay=prompt.addButton('Pozostań',QMessageBox.RejectRole)
   if self.process is not None:save.setEnabled(False)
   prompt.setDefaultButton(stay);prompt.exec()
   clicked=prompt.clickedButton()
   if clicked is save and self.process is None:self._save_settings_explicit()
   elif clicked is discard:self._settings_revert()
   else:return
  return super().navigate(key)
 def save_settings(self,*args):
  # Legacy change handlers cannot persist without explicit Save.
  return None
 def _save_settings_explicit(self):
  if self.process is not None:return
  super().save_settings()
  for key,value in (('solid_limit',self.solid_limit.value()),
      ('full_bom',self.full_bom.isChecked()),
      ('bom_mode',self.bom_mode.currentData()),
      ('bom_csv',self.bom_csv.isChecked()),
      ('output',self.output.text().strip()),
      ('import_cache',self.cache_import.isChecked())):
   self.store.setValue(key,value)
  self.store.sync()
  self._settings_saved=self._settings_snapshot()
  self._settings_changed()
  self._settings_save_feedback.setText('✓ Zapisano.')
''' + s[end:]
 s=put(s,"  self._settings_save_button.setEnabled(not busy)",
       "  self._settings_save_button.setEnabled(not busy and self._settings_dirty())\n  if hasattr(self,'_settings_cancel_button'):self._settings_cancel_button.setEnabled(self._settings_dirty())")
 s=put(s,"  save_row.addWidget(self._settings_save_button)\n  lay.insertLayout(lay.count()-1,save_row)",
       "  save_row.addWidget(self._settings_save_button)\n  self._settings_cancel_button=QPushButton('Anuluj')\n  self._settings_cancel_button.setObjectName('text-button')\n  self._settings_cancel_button.clicked.connect(self._settings_revert)\n  save_row.addWidget(self._settings_cancel_button)\n  lay.insertLayout(lay.count()-1,save_row)")
 start=s.index("  pos=min(1,max(0,(self._frame-40)/33));ease=pos*pos*(3-2*pos)")
 end=s.index("  p.end()",start)
 s=s[:start]+'''  pos=min(1,max(0,(self._frame-30)/65));ease=pos*pos*(3-2*pos)
  p.setOpacity(min(1,max(0,(self._frame-25)/18)))
  # Overlapping, zooming wireframe cubes, no final blue circle.
  for index,(start,c) in enumerate(((-83,muted),(83,blue))):
   p.save();p.translate(start*(1-ease),0);p.scale(1+.22*ease,1+.22*ease)
   p.setOpacity(.7 if index==0 else .9)
   cube(0,-1,c);p.restore()
  p.setOpacity(1)
'''+s[end:]
 return s
edit("dsac29/gui_modern.py",ui_patch)
(root/"VERSION.txt").write_text("R11.32\n",encoding="utf8")
meta=root/"build_info.json"
if meta.is_file():
 import json
 d=json.loads(meta.read_text("utf8"));d["version"]="R11.32 · GitHub "+os.environ.get("GITHUB_SHA","")[:8]
 meta.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding="utf8")
print("Applied R11.32 safe alignment, bounded parallel import, explicit Save/Cancel and light/About enhancements")
