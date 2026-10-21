"""R11.23 test: drop folder/STEP, compact mass controls, settings and readable table."""
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from PySide6.QtWidgets import QApplication,QFormLayout,QScrollArea,QFrame
from PySide6.QtCore import Qt,QMimeData,QUrl
from dsac29.gui46 import Window
from dsac29.mass_drop import MassDropArea
app=QApplication.instance() or QApplication([])
w=Window();w.show();w.navigate('mass');app.processEvents()
assert isinstance(w.mass_drop,MassDropArea)
assert w.mass_drop.acceptDrops()
assert w.mass_reset.parentWidget() is not w.mass_drop
assert w.mass_table.minimumHeight()>=285
assert w.mass_table.columnCount()==5
assert w.mass_table.horizontalScrollBarPolicy()==Qt.ScrollBarAsNeeded
assert isinstance(w.pages['mass'],QScrollArea)
assert isinstance(w.pages['settings'],QScrollArea)
assert w.pages['mass'].objectName()=='page'
with TemporaryDirectory() as folder:
 root=Path(folder)
 (root/'nested').mkdir()
 (root/'a.step').write_text('placeholder',encoding='utf8')
 (root/'nested'/'b.stp').write_text('placeholder',encoding='utf8')
 (root/'nested'/'skip.pdf').write_text('skip',encoding='utf8')
 w._mass_add([str(root)])
 assert len(w.mass_inputs)==2,w.mass_inputs
 assert w.mass_input_list.count()==2
 assert w.mass_input_list.isVisible()
 assert w.mass_file.path.text()
 w._mass_add([str(root/'a.step')])
 assert len(w.mass_inputs)==2,'duplicate entries'
 w._mass_reset()
 assert w.mass_input_list.isHidden() and not w.mass_inputs
 assert w.mass_actions.isHidden()
 for name in ('Jasny','Ciemny'):
  w.apply_theme(name)
  for width in (800,1200):
   w.resize(width,750);app.processEvents()
   assert w.mass_reset.width()>=w.mass_reset.fontMetrics().horizontalAdvance('Resetuj dane')+20
   for card in w.findChildren(QFrame,'settings-card'):
    assert card.layout().rowWrapPolicy()==QFormLayout.WrapLongRows
   assert w.output_button.width()>0
 assert w.schema.isEditable() and w.schema.lineEdit().isReadOnly()
 assert w.schema.lineEdit().alignment() & Qt.AlignHCenter
w.close()
print('R11.23 PASS: single dropbox accepts folder+file, reset, scrollable forms, readable table, center controls')
