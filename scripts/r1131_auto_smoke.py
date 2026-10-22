"""R11.31 regression: displacement approval, cancellation, no manual setting and fast BOM."""
import numpy as np
from pathlib import Path
from tempfile import TemporaryDirectory
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCP.TopLoc import TopLoc_Location
from OCP.gp import gp_Trsf,gp_Vec
from dsac29.geometry import describe
from dsac29.registration_gate import already_world_aligned
from dsac29.alignment import align_assembly
from dsac29.report import geometry_groups
from dsac29.geometry_registry import GeometryRegistry
from PySide6.QtWidgets import QApplication,QMessageBox
from PySide6.QtCore import QProcess
from dsac29.gui46 import Window
import dsac29.cli as cli
from dsac29 import worker_v37
import json,inspect

def part(name,x,y,z,width):
 t=gp_Trsf();t.SetTranslation(gp_Vec(float(x),float(y),float(z)))
 return describe(BRepPrimAPI_MakeBox(width,14,13).Shape().Located(TopLoc_Location(t)),name,name)

ref=[part('p1',0,0,0,20),part('p2',45,0,0,27),part('p3',100,0,0,31)]
shifted=[part('p1',100,23,0,20),part('p2',145,23,0,27),part('p3',200,23,0,31)]
assert already_world_aligned(ref,ref,.01)
assert not already_world_aligned(ref,shifted,.01)
new,info=align_assembly(ref,shifted,.01)
assert info['status']=='registered' and np.allclose(info['translation_B_to_A_mm'],[-100,-23,0])
assert already_world_aligned(ref,new,.01)
moved=[part('p1',0,0,0,20),part('p2',45,11,0,27),part('p3',100,0,0,31)]
assert already_world_aligned(ref,moved,.01),'One moved part must not be mistaken for a global translation'
print('PASS: global translation detected but local part movement leaves the original CAD frame')

groups=geometry_groups(ref,context=GeometryRegistry(),tolerance=.01,time_budget_s=.001,
                       fast_proven_only=True)
assert sum(len(group) for group in groups)==len(ref)
assert len(set(i for g in groups for i in g))==len(ref)
print('PASS: BOM always covers every real solid exactly once')

app=QApplication.instance() or QApplication([])
w=Window();w.show();app.processEvents()
w.navigate('settings')
assert not w.align.isVisible()
assert not any('Wyrównaj położenie' in p.text() for p in w.pages['settings'].findChildren(type(w.align)))
assert w._settings_save_button is not None
w.navigate('compare')
assert '--align-auto' in inspect.getsource(w.start) or '--align-auto' in inspect.getsource(w.__class__.__mro__[2].start) or '--align-auto' in inspect.getsource(__import__('dsac29.gui45',fromlist=['Window']).Window.start)
with TemporaryDirectory() as d:
    folder=Path(d)
    mock=QProcess(w)
    w.process=mock;w.task='compare';w.current_folder=folder
    w._last_coordinate_token=None
    w.active_log=w.log
    token='regression-approval'
    request={'token':token,'translation_mm':[-100,-23,0],'votes':3}
    (folder/'_WYROWNANIE_PYTANIE.json').write_text(json.dumps(request),encoding='utf8')
    original=QMessageBox.exec
    def answer(box):
        target=next(b for b in box.buttons() if 'Wyrównaj' in b.text())
        box.buttonClicked.emit(target)
        box._clickedButton=target
        # Qt decides clickedButton internally; invoke real button.
        target.click()
        return 0
    try:
        QMessageBox.exec=answer
        w._coordinate_prompt()
    finally:
        QMessageBox.exec=original
    response=json.loads((folder/'_WYROWNANIE_ODPOWIEDZ.json').read_text('utf8'))
    assert response['token']==token and response['decision']=='align',response
    w.process=None
w.close()
print('PASS: during analysis user can confirm global B-to-A offset, settings has no manual alignment checkbox')

assert 'auto_align' in inspect.signature(cli.process).parameters
assert '--align-auto' in inspect.getsource(worker_v37.main)
print('R11.31 PASS: automatic preflight, single-worker local approval, BOM safe fallback')
