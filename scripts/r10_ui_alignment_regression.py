"""R10 regression: partial translation and native Qt mass row interaction."""
import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
import numpy as np
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCP.TopoDS import TopoDS_Shape
from OCP.TopLoc import TopLoc_Location
from OCP.gp import gp_Trsf,gp_Vec
from dsac29.geometry import describe
from dsac29.alignment import align_assembly,AlignmentUnavailable
from dsac29.registration_gate import frame_support

def make(shape,pos,i):
 t=gp_Trsf();t.SetTranslation(gp_Vec(*map(float,pos)))
 return describe(shape.Located(TopLoc_Location(t)),f'Part{i}',f'Part{i}')
rng=np.random.default_rng(821)
stable=[BRepPrimAPI_MakeBox(4+q,7+q,12+q).Shape() for q in range(3)]
old=BRepPrimAPI_MakeBox(9,15,27).Shape()
new=BRepPrimAPI_MakeBox(9,16,27).Shape()
pos=rng.integers(100,8000,size=(80,3))
a=[make(stable[i%3] if i<30 else old,pos[i],i) for i in range(80)]
b=[make(stable[i%3] if i<30 else new,
        pos[i]+np.array([1100.,-2000.,300.]),i) for i in range(80)]
aligned,info=align_assembly(a,b,.01)
assert info['method']=='partial_world_brep_consensus',info
assert np.allclose(info['translation_B_to_A_mm'],[-1100,2000,-300]),info
support=frame_support(a,aligned,.01,proofs=12)
assert support['count']>=30 and support['proofs']==support['checked']==12,support
print('PASS R10: 80 parts, 30 unchanged, global XYZ translation')

a=[make(old,(i*31,i%7*49,0),i) for i in range(50)]
b=[make(new,(i*31+800,i%7*49,0),i) for i in range(50)]
try:align_assembly(a,b,.01)
except AlignmentUnavailable:pass
else:raise AssertionError('No common shape: registration should be unavailable')
print('PASS R10: insufficient B-Rep evidence does not invent translation')

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from dsac29.gui46 import Window
app=QApplication.instance() or QApplication([])
w=Window();w.show();w.navigate('mass');app.processEvents()
with TemporaryDirectory() as folder:
 paths=[]
 for n in range(4):
  p=Path(folder)/f'MASS_{n:02d}.step';p.write_text('test',encoding='utf8');paths.append(str(p))
 w._mass_add(paths);app.processEvents()
 lst=w.mass_input_list
 assert lst.count()==4 and lst.height()>=150
 def click(index,mods=Qt.NoModifier):
  holder=lst.itemWidget(lst.item(index))
  QTest.mouseClick(holder,Qt.LeftButton,mods)
  app.processEvents()
 click(0)
 assert [i.row() for i in lst.selectedIndexes()]==[0]
 click(0)
 assert not lst.selectedItems(), 'Click selected row again must deselect'
 click(0);click(2,Qt.ControlModifier)
 assert {i.row() for i in lst.selectedIndexes()}=={0,2}
 click(3,Qt.ShiftModifier)
 assert {i.row() for i in lst.selectedIndexes()}=={2,3}
 assert w.mass_remove_selected.isEnabled()
 w._mass_running_controls(True)
 assert not w.mass_drop.acceptDrops() and not w.mass_input_list.isEnabled()
 assert not w.mass_add_files.isEnabled() and not w.mass_add_folder.isEnabled()
 before=list(w.mass_inputs)
 w._mass_add([paths[0]])
 assert w.mass_inputs==before
 w._mass_running_controls(False)
 assert w.mass_drop.acceptDrops()
 assert w.mass_add_files.isEnabled() and w.mass_input_list.isEnabled()
 w.mass_remove_selected.click();app.processEvents()
 assert len(w.mass_inputs)==2
 assert all(Path(p).exists() for p in paths)
 print('PASS R10: Qt selection toggle, Ctrl/Shift, dimensions, remove and DnD busy lock')
 w.grab().save('R10_UI_MASS.png')
w.close()
