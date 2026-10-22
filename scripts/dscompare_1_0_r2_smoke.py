"""DS Compare 1.0 R2: practical Qt regression for cross-tab status and mass list geometry."""
import inspect
from pathlib import Path
from tempfile import TemporaryDirectory
from PySide6.QtCore import QProcess,Qt
from PySide6.QtWidgets import QApplication,QPushButton,QLabel,QScrollArea,QFormLayout
from dsac29.gui46 import Window
import dsac29.gui46 as legacy

app=QApplication.instance() or QApplication([])
w=Window();w.show();app.processEvents()
assert all(isinstance(w.pages[k],QScrollArea) for k in ('compare','mass','settings'))
assert w.minimumHeight()>=480
source=Path(legacy.__file__).read_text(encoding='utf8')
assert "if kind=='compare':" in source
assert "elif kind=='mass':" in source
assert "self.compare_summary.setText('Analiza trwa…' if kind=='compare' else 'Obliczanie masy…')" not in source

with TemporaryDirectory() as folder:
 files=[]
 for k in range(5):
  p=Path(folder)/f"PRZYKLADOWY_MODEL_{k:02d}.stp"
  p.write_text('test',encoding='utf8')
  files.append(str(p))
 w.navigate('mass');w._mass_add(files);app.processEvents()
 assert w.mass_input_list.count()==5
 assert w.mass_input_list.height()>=200 or w.mass_input_list.maximumHeight()>=170
 assert w._mass_materials_panel.isVisible()
 form=w._mass_materials_panel.layout()
 for i,control in enumerate((w.materials,w.density)):
  label=form.itemAt(i,QFormLayout.LabelRole).widget()
  assert isinstance(label,QLabel)
  assert label.alignment() & Qt.AlignVCenter
  assert label.minimumHeight()>=control.minimumHeight()
 for i in range(w.mass_input_list.count()):
  item=w.mass_input_list.item(i)
  holder=w.mass_input_list.itemWidget(item)
  assert holder is not None
  assert holder.objectName()=='mass-file-row'
  cross=next(b for b in holder.findChildren(QPushButton) if b.text()=='×')
  assert cross.height()==30 and holder.height()>=40,(i,cross.height(),holder.height())
  assert abs((cross.y()+cross.height()/2)-holder.height()/2)<=5,(i,cross.y(),holder.height())
 w.mass_input_list.item(2).setSelected(True);app.processEvents()
 holder=w.mass_input_list.itemWidget(w.mass_input_list.item(2))
 assert holder.property('selected') is True
 button=next(b for b in holder.findChildren(QPushButton) if b.text()=='×')
 button.click();app.processEvents()
 assert w.mass_input_list.count()==4 and len(w.mass_inputs)==4
 assert all(Path(p).exists() for p in files),'Remove from queue must not delete files'

 # View compare while MASS analysis is running.
 w.navigate('compare')
 w.compare_summary.setText('Wybierz dwa modele CAD')
 w.process=QProcess(w);w.task='mass'
 w._set_busy_ui(True);app.processEvents()
 assert w._global_status.isVisible()
 assert 'masy' in w._global_status.text().lower()
 assert w.compare_summary.text()=='Wybierz dwa modele CAD'
 w.navigate('settings');app.processEvents()
 assert w._global_status.isVisible()
 w.navigate('mass')
 w._set_busy_ui(False)
 assert not w._global_status.isVisible()
 w.process=None
 for size in ((960,720),(1000,810)):
  w.resize(*size);app.processEvents()
  w.navigate('mass')
  assert w.pages['mass'].verticalScrollBarPolicy()!=Qt.ScrollBarAlwaysOff
  assert w.pages['mass'].widget().minimumHeight()>0
 w.close()
print('R2 PASS: consistent file rows, 30px centered delete, vertical labels, all pages scroll, mass status never leaks to comparison')
