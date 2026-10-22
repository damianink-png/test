"""R3 GUI: update STEP/BOM readiness only on a change of stage state."""
from pathlib import Path
import os
root=Path(os.environ['DS_COMPARE_SOURCE'])
p=root/"dsac29/gui_modern.py"
s=p.read_text('utf8')
old="""  super().start(kind)
  if self.process is not None:self._set_busy_ui(True)"""
new="""  super().start(kind)
  if kind=='compare':
   self._last_compare_stage=None
   self._compare_step_announced=False
  if self.process is not None:self._set_busy_ui(True)"""
assert s.count(old)==1;s=s.replace(old,new,1)
old="""  try:data=json.loads(stage.read_text(encoding='utf8'))
  except (OSError,ValueError):return
  step=Path(self.current_folder)/'POROWNANIE_KOLORY.step'"""
new="""  try:data=json.loads(stage.read_text(encoding='utf8'))
  except (OSError,ValueError):return
  signature=(data.get('step'),data.get('step_bytes'),
             data.get('reports'),data.get('report_percent'),data.get('step_error'))
  if signature==getattr(self,'_last_compare_stage',None):
   return
  self._last_compare_stage=signature
  step=Path(self.current_folder)/'POROWNANIE_KOLORY.step'"""
assert s.count(old)==1;s=s.replace(old,new,1)
old="""   self.results['compare']=Path(self.current_folder)
   self._actions.show()
   self._refresh_outputs()
   self._bom_label.setText("""
new="""   if not getattr(self,'_compare_step_announced',False):
    self.results['compare']=Path(self.current_folder)
    self._actions.show()
    self._refresh_outputs()
    self._compare_step_announced=True
   self._bom_label.setText("""
assert s.count(old)==1;s=s.replace(old,new,1)
p.write_text(s,'utf8')
print('R3 Qt: stage signatures avoid repeated disk validation, action panel redraw, and heavy output refresh every poll')
