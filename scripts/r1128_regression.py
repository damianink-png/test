"""R11.28 regressions for translation alignment, WinError 5 and frozen UI."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import numpy as np
from PySide6.QtWidgets import QApplication,QMessageBox
from PySide6.QtCore import QProcess
from PySide6.QtGui import QCloseEvent
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCP.gp import gp_Trsf,gp_Vec
from OCP.TopLoc import TopLoc_Location

from dsac29.geometry import describe,equivalent_world
from dsac29.alignment import align_assembly,AlignmentUnavailable
from dsac29.compare import compare
from dsac29.revision_rules import classify_revisions
from dsac29.geometry_registry import GeometryRegistry
from dsac29.stage_fast import StageWriter
import dsac29.stage_fast as stage_fast
from dsac29.step_io import export_revision_step,load_step
from dsac29.gui46 import Window

def make(name,x,y,z,width):
    tr=gp_Trsf();tr.SetTranslation(gp_Vec(float(x),float(y),float(z)))
    shape=BRepPrimAPI_MakeBox(width,16,12).Shape().Located(TopLoc_Location(tr))
    return describe(shape,name,name)
def classified(a,b):
    context=GeometryRegistry()
    records=compare(a,b,revision_only=True,geometry_context=context)
    return classify_revisions(a,b,records,.01,geometry_context=context)

with TemporaryDirectory() as d:
    folder=Path(d)
    # PermissionError is NOT a CAD failure; retry (and ultimately suppress).
    writer=StageWriter(folder)
    original=stage_fast.os.replace
    attempts=[0]
    def flaky(*args,**kwargs):
        attempts[0]+=1
        if attempts[0]<3:raise PermissionError(5,"Windows file sharing violation")
        return original(*args,**kwargs)
    stage_fast.os.replace=flaky
    try:
        writer.update(step="eksport")
    finally:
        stage_fast.os.replace=original
    assert attempts[0]==3 and writer.path.exists()
    assert json.loads(writer.path.read_text('utf8'))['step']=='eksport'
    writer2=StageWriter(folder)
    stage_fast.os.replace=lambda *args,**kwargs:(_ for _ in ()).throw(PermissionError(5,"still locked"))
    try:
        writer2.update(step="gotowy")
    finally:
        stage_fast.os.replace=original
    assert writer2.errors==1
    assert not list(folder.glob('_ETAPY_*.tmp')),'temp leaked'
    writer2.update(reports='gotowe')
    assert json.loads(writer2.path.read_text('utf8'))['reports']=='gotowe'
    print('PASS - transient and persistent WinError 5 do not abort STEP/report',flush=True)

    # One unique asymmetric solid: translation must register without 3 parts.
    aa=[make('BRYLA',10,20,5,23)]
    bb=[make('BRYLA',210,120,45,23)]
    aligned,info=align_assembly(aa,bb,.01)
    assert info['enabled'] and info['votes']==1,info
    assert equivalent_world(aa[0],aligned[0],.01)
    records=classified(aa,aligned)
    assert all(r.status in ('SAME','RENAMED') for r in records),[r.status for r in records]
    step=folder/'aligned_single.step'
    diag=export_revision_step(str(step),records,aa,aligned)
    assert step.is_file() and diag.get('rzeczywiste_bryly_step',0)>=1
    reloaded=load_step(str(step),max_solids=100)
    assert reloaded and all(np.linalg.norm(p.center-aa[0].center)<.01 for p in reloaded)
    print('PASS - one-solid translation recognized and written in registered coordinates',flush=True)

    # Three unique parts, one intentionally moved relative to overall B.
    a=[make('P1',0,0,0,18),make('P2',65,15,0,24),make('P3',140,45,0,30)]
    b=[make('P1',110,35,0,18),make('P2',175,50,0,24),make('P3',259,80,0,30)]
    result,info=align_assembly(a,b,.01)
    assert info['enabled'] and info['votes']>=2,info
    assert equivalent_world(a[0],result[0],.01)
    assert equivalent_world(a[1],result[1],.01)
    assert not equivalent_world(a[2],result[2],.01)
    rec=classified(a,result)
    stats=[r.status for r in rec]
    assert stats.count('MOVED')==1,stats
    assert stats.count('SAME')>=2,stats
    print('PASS - global translation corrected while one truly moved element remains MOVED',flush=True)

    # Ambiguous multi-part registration must NOT fall back to wrong coordinates.
    unique_a=[make('A',0,0,0,17),make('X',45,25,0,13)]
    unique_b=[make('A',200,0,0,17),make('Y',245,25,0,33)]
    try:
        align_assembly(unique_a,unique_b,.01)
    except AlignmentUnavailable:
        pass
    else:raise AssertionError('Ambiguous registration silently accepted')
    print('PASS - ambiguous registration fails instead of fabricating aligned STEP',flush=True)

app=QApplication.instance() or QApplication([])
w=Window();w.show();app.processEvents()
w.navigate('compare')
initial=w.align.isChecked()
worker=QProcess(w)
w.process=worker;w.task='compare'
w._set_busy_ui(True)
assert all(not b.isEnabled() for b in w.nav.values())
assert w._analysis_busy_banner.isVisible()
assert w.pages['settings'].isEnabled()
assert w.align.isChecked()==initial
w.navigate('mass');assert w.stack.currentWidget() is w.pages['compare']
# The window cannot be torn down while the worker still owns DLLs/MEI.
old=QMessageBox.information
QMessageBox.information=lambda *args,**kwargs:QMessageBox.Ok
try:
    event=QCloseEvent();w.closeEvent(event)
    assert not event.isAccepted(),'Close should be rejected until worker ends'
finally:
    QMessageBox.information=old
w.process=None
w._set_busy_ui(False)
assert all(b.isEnabled() for b in w.nav.values())
assert not w._analysis_busy_banner.isVisible()
assert w.align.isChecked()==initial
w.navigate('mass')
assert w.stack.currentWidget() is w.pages['mass']
w.close()
print('PASS - disabled navigation, visible wait banner, preserved settings checkboxes, safe shutdown',flush=True)
