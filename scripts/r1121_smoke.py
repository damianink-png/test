"""R11.21 regression: Windows DPI layout, color dialog and ABSR-free STEP."""
import os,re,tempfile
from pathlib import Path
from PySide6.QtCore import QTimer,Qt
from PySide6.QtWidgets import QApplication,QDialog,QScrollArea,QLabel
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from dsac29.gui46 import Window
from dsac29.step_io import ColoredDocument,inspect_step_colors

app=QApplication.instance() or QApplication([])
w=Window()
w.show()
for theme in ('Ciemny','Jasny'):
 w.apply_theme(theme)
 for width in (740,850,1100):
  w.resize(width,740);app.processEvents()
  host=w._navigation_host
  assert host.isVisible(),theme
  for key in ('compare','mass','settings'):
   btn=w.nav[key]
   assert btn.parentWidget() is host,key
   assert btn.width()>=btn.fontMetrics().horizontalAdvance(btn.text())+55,(theme,width,key,btn.width())
   assert host.rect().contains(btn.geometry().center()),(theme,width,key)
w.zw3d_flat_output.setChecked(True)
assert w.zw3d_flat_output.isChecked()
def inspect_dialog():
 dialogs=[t for t in QApplication.topLevelWidgets() if isinstance(t,QDialog) and 'Kolory elementów' in t.windowTitle() and t.isVisible()]
 assert len(dialogs)==1,dialogs
 dialog=dialogs[0]
 assert not dialog.findChildren(QScrollArea),'color dialog must not scroll'
 assert len([t for t in dialog.findChildren(QLabel) if t.text().startswith(('Przesunięte','Zmodyfikowane','Nierozstrzygnięte'))])>=6
 dialog.reject()
QTimer.singleShot(0,inspect_dialog)
w.edit_export_colors()
w.close()
with tempfile.TemporaryDirectory() as folder:
 p=Path(folder)/'POROWNANIE_KOLORY.step'
 d=ColoredDocument(group_by_status=True,reuse_definitions=False,flat_zw3d=True)
 d.add(BRepPrimAPI_MakeBox(11,13,17).Shape(),'Test_A',(0.12,0.75,0.35),group='SAME')
 d.add(BRepPrimAPI_MakeBox(9,14,16).Shape(),'Test_B',(0.12,0.43,0.95),group='ADDED')
 diag=d.write(p)
 data=p.read_text('utf8',errors='replace')
 assert len(re.findall(r'(?m)^#\d+\s*=\s*PRODUCT\(',data))==2
 assert 'NEXT_ASSEMBLY_USAGE_OCCURRENCE(' not in data
 assert diag['eksport_plaski_bez_absr'] and diag['bryly_wynikowe']==2
 assert inspect_step_colors(str(p))['elementy_bez_bryly']==0
print('R11.21 PASS: full nav, 9-color modal without scroll, ZW3D flat 2 solids / 2 products / 0 assembly links')
