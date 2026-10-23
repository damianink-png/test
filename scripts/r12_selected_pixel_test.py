"""R12 Qt offscreen screenshot/pixel regression for the selected mass row."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from pathlib import Path
from tempfile import TemporaryDirectory
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication,QLabel,QPushButton
from dsac29.gui46 import Window

app=QApplication.instance() or QApplication([])
w=Window();w.show();w.navigate('mass');app.processEvents()
try:
 with TemporaryDirectory() as folder:
  files=[]
  for n in range(3):
   f=Path(folder)/f'R12_MASA_{n:02d}.step'
   f.write_text('synthetic entry',encoding='utf8');files.append(str(f))
  w._mass_add(files);app.processEvents()
  view=w.mass_input_list
  assert view.count()==3
  h0=view.itemWidget(view.item(0))
  h1=view.itemWidget(view.item(1))
  assert h0.height()==36 and h1.height()==36
  def pixel(holder):
   app.processEvents()
   image=holder.grab().toImage()
   return image.pixelColor(5,holder.height()//2)
  def close_color(actual,reference,tolerance=6):
   assert all(abs(v1-v2)<=tolerance for v1,v2 in
      zip(actual.getRgb()[:3],QColor(reference).getRgb()[:3])),(actual.name(),reference)
  for theme,accent in [('Ciemny','#1677F7'),('Jasny','#1268D8')]:
   w.apply_theme(theme);app.processEvents()
   # Unselected item should not look selected.
   unselected=pixel(h0)
   QTest.mouseClick(h0,Qt.LeftButton);app.processEvents()
   assert view.item(0).isSelected()
   assert h0.property('selected') is True
   selected=pixel(h0)
   close_color(selected,accent)
   assert selected.name()!=unselected.name(),(theme,selected.name(),unselected.name())
   text=h0.findChild(QLabel,'mass-row-label')
   delete=h0.findChild(QPushButton,'delete-one')
   assert text.property('massSelected') is True
   assert delete.property('massSelected') is True
   # Repeat click removes selection and restores ordinary theme field.
   QTest.mouseClick(h0,Qt.LeftButton);app.processEvents()
   assert not view.item(0).isSelected()
   assert h0.property('selected') is False
   assert text.property('massSelected') is False
   assert delete.property('massSelected') is False
   assert pixel(h0).name()!=accent.lower()
   # Multi-select must visibly highlight each selected row separately.
   QTest.mouseClick(h0,Qt.LeftButton);app.processEvents()
   QTest.mouseClick(h1,Qt.LeftButton,Qt.ControlModifier);app.processEvents()
   assert {x.row() for x in view.selectedIndexes()}=={0,1}
   close_color(pixel(h0),accent);close_color(pixel(h1),accent)
   assert w.mass_remove_selected.isEnabled()
   view.clearSelection();app.processEvents()
  w.apply_theme('Ciemny');app.processEvents()
  QTest.mouseClick(h0,Qt.LeftButton);app.processEvents()
  w.grab().save('R12_MASS_SELECTED_DARK.png')
  w.apply_theme('Jasny');app.processEvents()
  w.grab().save('R12_MASS_SELECTED_LIGHT.png')
finally:
 w.close()
print('R12 PASS: visually selected rows, colors dark/light, toggle, Ctrl, multi-selection')
