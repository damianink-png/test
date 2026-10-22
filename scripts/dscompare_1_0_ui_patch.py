"""Finish the Oct 22 DS Compare 1.0 GUI changes on the verified R11.32 source.

Do not replace the geometry/STEP engine; this is a focused UI-only patch.
"""
from pathlib import Path
import os,json
root=Path(os.environ['DS_COMPARE_SOURCE'])
p=root/'dsac29/gui_modern.py'
s=p.read_text('utf8')
def replace(old,new):
 global s
 if s.count(old)!=1:
  raise RuntimeError(f'1.0 GUI anchor count={s.count(old)}: {old[:90]!r}')
 s=s.replace(old,new,1)
replace('    QAbstractItemView,QMessageBox)','    QAbstractItemView,QMessageBox,QScrollArea)')
replace("dark=self.parent().property('ds_dark') is True","dark=self.window().property('ds_dark') is True")
replace("p.translate(w/2,6);p.scale(scale,scale)",
        "p.translate(w/2,max(6,(self.height()-322*scale)/2));p.scale(scale,scale)")
start=s.index("  self.setWindowTitle('O programie');self.setObjectName('about-window')")
end=s.index(" def showEvent(self,event):",start)
updated="""  self.setWindowTitle('O programie — DS Compare 1.0');self.setObjectName('about-window')
  self.setStyleSheet(skin(bool(self.property('ds_dark'))))
  self.setMinimumSize(340,360)
  screen=parent.screen() or QGuiApplication.primaryScreen()
  area=screen.availableGeometry() if screen else None
  self.resize(min(540,area.width()-32) if area else 540,
              min(700,area.height()-48) if area else 700)
  layout=QVBoxLayout(self);layout.setContentsMargins(0,0,0,0)
  scroll=QScrollArea(self);scroll.setWidgetResizable(True);scroll.setFrameShape(QFrame.NoFrame)
  scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
  body=QWidget();content=QVBoxLayout(body)
  content.setContentsMargins(28,20,28,24);content.setSpacing(12)
  heading=QLabel('O programie');heading.setObjectName('section');heading.setAlignment(Qt.AlignCenter)
  content.addWidget(heading)
  self.logo=CompareLogo(self);content.addWidget(self.logo)
  caption=QLabel('Porównywanie geometrii CAD');caption.setAlignment(Qt.AlignCenter)
  caption.setWordWrap(True);caption.setObjectName('section');content.addWidget(caption)
  self.version_label=QLabel('Wersja 1.0');self.version_label.setAlignment(Qt.AlignCenter)
  self.version_label.setObjectName('muted');content.addWidget(self.version_label)
  details=QFrame();details.setObjectName('surface');grid=QVBoxLayout(details)
  grid.setContentsMargins(18,16,18,16);grid.setSpacing(7)
  for key,value in (('Autor','Damian Szymczyk'),('Technologia','Python · PySide6 · Open CASCADE (OCP)'),('Formaty','STEP / STP · eksport z ZW3D 2019')):
   lhs=QLabel(key);lhs.setObjectName('muted');lhs.setAlignment(Qt.AlignCenter)
   rhs=QLabel(value);rhs.setAlignment(Qt.AlignCenter);rhs.setWordWrap(True)
   grid.addWidget(lhs);grid.addWidget(rhs)
   if key!='Formaty':grid.addSpacing(8)
  content.addWidget(details)
  cr=QLabel('© 2026 Damian Szymczyk');cr.setObjectName('muted')
  cr.setAlignment(Qt.AlignCenter);content.addWidget(cr)
  content.addStretch(1);scroll.setWidget(body);layout.addWidget(scroll)
"""
s=s[:start]+updated+s[end:]
replace("""    (self.bom_mode,'currentIndexChanged'),
    (self.bom_csv,'toggled'),
  ):
   try:getattr(widget,signal).disconnect()""",
"""    (self.bom_mode,'currentIndexChanged'),
    (self.bom_csv,'toggled'),
    (self.cache_import,'toggled'),
  ):
   try:getattr(widget,signal).disconnect()""")
# One single cache checkbox connection, unlike the earlier 1.0 draft.
replace("""  self.store.sync()
  self._settings_saved=self._settings_snapshot()""",
"""  self.store.sync()
  if self.store.status()!=self.store.Status.NoError:
   QMessageBox.warning(self,'Ustawienia','Nie udało się zapisać ustawień. Sprawdź uprawnienia do zapisu.')
   return
  os.environ['DSCOMPARE_IMPORT_CACHE']='auto' if self.cache_import.isChecked() else 'off'
  self._settings_saved=self._settings_snapshot()""")
replace("""  self._settings_save_feedback.setText('✓ Zapisano.')
 def _modern_compare(self):""",
"""  self._settings_save_feedback.setText('✓ Zapisano.')
 def choose_output(self):
  from PySide6.QtWidgets import QFileDialog
  selected=QFileDialog.getExistingDirectory(self,'Folder wyników',self.output.text())
  if selected:self.output.setText(selected)
 def closeEvent(self,event):
  if self.process is None and self._settings_dirty():
   answer=QMessageBox.question(self,'Niezapisane ustawienia','Zapisać zmiany ustawień przed zamknięciem?',
       QMessageBox.Save|QMessageBox.Discard|QMessageBox.Cancel,QMessageBox.Cancel)
   if answer==QMessageBox.Cancel:
    event.ignore();return
   if answer==QMessageBox.Save:
    self._save_settings_explicit()
    if self._settings_dirty():
     event.ignore();return
  super().closeEvent(event)
 def _modern_compare(self):""")
replace("material_form.setContentsMargins(17,12,17,12);material_form.setSpacing(9)",
"""material_form.setContentsMargins(20,18,20,18);material_form.setSpacing(14)
  material_form.setLabelAlignment(Qt.AlignRight|Qt.AlignVCenter)
  material_form.setRowWrapPolicy(QFormLayout.WrapLongRows)
  material_form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)""")
replace("heading=QLabel(title);heading.setObjectName('section');layout.addRow(heading)",
        "heading=QLabel(title);heading.setObjectName('section');heading.setAlignment(Qt.AlignCenter);layout.addRow(heading)")
replace("cp.addRow('Maksymalna liczba brył',self.solid_limit)",
        "cp.addRow('Limit brył / plik',self.solid_limit)")
replace("""  cp.addRow(self.full_bom)
  cp.addRow('Tryb BOM',self.bom_mode)""",
"""  self.full_bom.setText('Twórz pełny BOM A i B')
  self.cache_import.setText('Przyspiesz ponowny import')
  self.bom_csv.setText('Zapisuj BOM także jako CSV')
  if self.bom_mode.count()>1:
   self.bom_mode.setItemText(0,'Dokładny — kontrola geometrii')
   self.bom_mode.setItemText(1,'Szybki — pewne duplikaty')
  cp.addRow(self.full_bom)
  cp.addRow('Tryb BOM',self.bom_mode)""")
replace("""   form.setLabelAlignment(Qt.AlignLeft|Qt.AlignVCenter)
   form.setFormAlignment(Qt.AlignTop)
   form.setHorizontalSpacing(15);form.setVerticalSpacing(16)""",
"""   form.setLabelAlignment(Qt.AlignRight|Qt.AlignVCenter)
   form.setFormAlignment(Qt.AlignTop)
   form.setHorizontalSpacing(18);form.setVerticalSpacing(16)
   for row in range(form.rowCount()):
    item=form.itemAt(row,QFormLayout.LabelRole)
    if item and isinstance(item.widget(),QLabel):
     label=item.widget();label.setAlignment(Qt.AlignRight|Qt.AlignVCenter)
     label.setMinimumHeight(40);label.setMinimumWidth(140)
     label.setWordWrap(True)""")
p.write_text(s,encoding='utf8')
meta=root/'build_info.json'
if meta.exists():
 d=json.loads(meta.read_text('utf8'))
 d['version']='1.0 · R11.32 geometry · GitHub '+os.environ.get('GITHUB_SHA','')[:8]
 d['ui']='Finished 1.0 centered fields, about responsive layout, settings cache/output atomic save'
 meta.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf8')
print('DS Compare 1.0 UI ported onto R11.32 engine, only one cache signal, no STEP changes')
