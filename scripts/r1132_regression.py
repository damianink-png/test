"""R11.32 verify CAD movement decisions, safe settings transaction and About animation."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCP.gp import gp_Trsf,gp_Vec
from OCP.TopLoc import TopLoc_Location
from dsac29.geometry import describe
from dsac29.registration_gate import frame_support,already_world_aligned
from dsac29.alignment import align_assembly
from dsac29.compare import compare
from dsac29.revision_rules import classify_revisions
from PySide6.QtWidgets import QApplication,QMessageBox
from PySide6.QtCore import QProcess
from dsac29.gui46 import Window

def parts(n,shift=0,moved=None):
 out=[]
 for i in range(n):
  x=i*53+shift;y=i*17+(12 if i==moved else 0)
  t=gp_Trsf();t.SetTranslation(gp_Vec(x,y,0))
  out.append(describe(BRepPrimAPI_MakeBox(19+i,13,12).Shape().Located(TopLoc_Location(t)),
                      f'P{i}',f'P{i}'))
 return out

# Synthetic assembly with one moved component should remain in world frame.
a=parts(12);b=parts(12,moved=11)
same=frame_support(a,b,.01)
assert same['count']==11 and already_world_aligned(a,b,.01),same
recs=compare(a,b,.01,revision_only=True,exact_serialization=True)
statuses=[r.status for r in classify_revisions(a,b,recs,.01)]
assert statuses.count('SAME')==11 and statuses.count('MOVED')==1,statuses

# Whole model translation + a different moved part requires registration and
# afterwards 11 SAME + 1 MOVED; don't transform moved part independently.
b2=parts(12,shift=90,moved=11)
assert not already_world_aligned(a,b2,.01)
aligned,info=align_assembly(a,b2,.01)
correct=frame_support(a,aligned,.01)
assert correct['count']==11 and correct['ratio']>.60
rows=classify_revisions(a,aligned,compare(a,aligned,.01,revision_only=True,exact_serialization=True),.01)
states=[r.status for r in rows]
assert states.count('SAME')==11 and states.count('MOVED')==1,states
print('PASS: 11 green unchanged + one purple MOVED with and without global translation')

app=QApplication.instance() or QApplication([])
with TemporaryDirectory() as folder:
 w=Window();w.show();app.processEvents()
 w.navigate('settings');app.processEvents()
 assert not w._settings_dirty()
 assert not w._settings_save_button.isEnabled()
 assert not w._settings_cancel_button.isEnabled()
 before=w.tolerance.value();w.tolerance.setValue(.026 if before!=.026 else .017)
 assert w._settings_dirty() and w._settings_save_button.isEnabled()
 # Test discard on navigation with actual QMessageBox button click.
 original=QMessageBox.exec
 def choose_discard(dialog):
  button=next(x for x in dialog.buttons() if 'Odrzuć' in x.text())
  button.click();return 0
 try:
  QMessageBox.exec=choose_discard
  w.navigate('mass')
 finally:QMessageBox.exec=original
 assert w.stack.currentWidget() is w.pages['mass']
 assert w.tolerance.value()==before and not w._settings_dirty()
 # Edit and accept save on leave, then ensure persistent state.
 w.navigate('settings');w.tolerance.setValue(.021)
 def choose_save(dialog):
  next(x for x in dialog.buttons() if x.text()=='Zapisz').click();return 0
 try:
  QMessageBox.exec=choose_save
  w.navigate('compare')
 finally:QMessageBox.exec=original
 assert abs(float(w.store.value('tolerance',0))-.021)<1e-6
 w.navigate('settings');w.tolerance.setValue(.029)
 worker=QProcess(w);w.process=worker;w._set_busy_ui(True)
 assert not w._settings_save_button.isEnabled()
 assert w._settings_cancel_button.isEnabled()
 w._settings_cancel_button.click()
 assert not w._settings_dirty()
 w.navigate('compare');w.navigate('mass');assert w.stack.currentWidget() is w.pages['mass']
 w.process=None;w._set_busy_ui(False)
 w.toggle_theme();app.processEvents()
 assert w.styleSheet() and '#ABBED3' in w.styleSheet() if w.theme.currentText()=='Jasny' else True
 from dsac29.gui_modern import CompareLogo
 logo=CompareLogo(w);logo._frame=102
 # Directly rendering the final state must not raise an exception.
 from PySide6.QtGui import QImage,QPainter
 image=QImage(400,320,QImage.Format_ARGB32)
 image.fill(0)
 logo.resize(400,320)
 logo.render(image)
 w.close()
print('R11.32 PASS: alignment, saved/discarded changes, busy settings behavior, light theme and About drawing')
