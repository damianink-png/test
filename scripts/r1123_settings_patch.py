"""R11.23: settings cards with stable row heights, centered text and no overlap."""
import os,json
from pathlib import Path
root=Path(os.environ['DS_COMPARE_SOURCE'])
p=root/'dsac29/gui_modern.py'
s=p.read_text(encoding='utf8')
start=s.index(' def _modern_settings(self):')
stop=s.index(' def create_zw3d_macro(self):',start)
replacement=""" def _modern_settings(self):
  _,lay=self._new_page('settings')
  title=QLabel('Ustawienia');title.setObjectName('hero')
  title.setAlignment(Qt.AlignCenter);lay.addWidget(title)
  grid=QGridLayout();grid.setSpacing(14)
  compare,cp=self._settings_card('Porównanie')
  cp.addRow('Tolerancja geometrii',self.tolerance)
  cp.addRow('Maksymalna liczba brył',self.solid_limit)
  cp.addRow(self.align)
  cp.addRow(self.full_bom)
  cp.addRow('Tryb BOM',self.bom_mode)
  report,rp=self._settings_card('Raport i eksport')
  folder=QWidget()
  folder.setStyleSheet('background:transparent;')
  folder_line=QHBoxLayout(folder)
  folder_line.setContentsMargins(0,0,0,0);folder_line.setSpacing(8)
  self.output.setMinimumWidth(120)
  folder_line.addWidget(self.output,1)
  self.output_button.setMinimumWidth(104)
  folder_line.addWidget(self.output_button,0)
  rp.addRow('Folder wyników',folder)
  rp.addRow('Schemat STEP',self.schema)
  rp.addRow('Kontrola STEP',self.verify_mode)
  rp.addRow('Kolory modeli',self.color_editor)
  self.zw3d_flat_output=QCheckBox('Płaski STEP bez podzłożeń — zgodność ZW3D')
  flat=str(self.store.value('zw3d_flat_output_r1122','false')).lower() in ('1','yes','true')
  self.zw3d_flat_output.setChecked(flat)
  self.zw3d_flat_output.toggled.connect(lambda v:self.store.setValue('zw3d_flat_output_r1122',v))
  self.zw3d_flat_output.setToolTip('W trybie płaskim nie ma pustych kontenerów ABSR, ale znikają też podzłożenia. Wyłączone: rzeczywiste podzłożenia STEP.')
  rp.addRow(self.zw3d_flat_output)
  warning=QLabel('Hierarchia podzłożeń wymaga kontenerów STEP. Nie można ich bezpiecznie usuwać z pliku po eksporcie.')
  warning.setObjectName('muted');warning.setWordWrap(True);rp.addRow(warning)
  rp.addRow(self.bom_csv)
  general,gp=self._settings_card('Ogólne')
  self.zw3d_macro_button=QPushButton('Utwórz makro startowe do ZW3D 2019')
  self.zw3d_macro_button.clicked.connect(self.create_zw3d_macro)
  gp.addRow('Integracja ZW3D',self.zw3d_macro_button)
  self._theme_select=QComboBox();self._theme_select.addItems(['Ciemny','Jasny'])
  self._theme_select.setCurrentText(self.theme.currentText())
  self._theme_select.currentTextChanged.connect(self.theme.setCurrentText)
  self.theme.currentTextChanged.connect(self._theme_select.setCurrentText)
  gp.addRow('Motyw',self._theme_select)
  gp.addRow('Język',QLabel('Polski'))
  gp.addRow(self.cache_import)
  gp.addRow(self.clear_import_cache_button)
  for form in (cp,rp,gp):
   form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
   form.setRowWrapPolicy(QFormLayout.WrapLongRows)
   form.setLabelAlignment(Qt.AlignLeft|Qt.AlignVCenter)
   form.setFormAlignment(Qt.AlignTop)
   form.setHorizontalSpacing(15)
   form.setVerticalSpacing(16)
  grid.addWidget(compare,0,0)
  grid.addWidget(report,0,1)
  grid.addWidget(general,1,0,1,2)
  grid.setColumnStretch(0,1);grid.setColumnStretch(1,1)
  lay.addLayout(grid)
  lay.addStretch(1)
  self._scroll_page('settings')
  self.safe_export.setChecked(True)
  self.safe_export.hide()
"""
s=s[:start]+replacement+s[stop:]
needle="  self._modern_topbar();self._modern_compare();self._modern_mass();self._modern_settings()\n"
assert s.count(needle)==1
s=s.replace(needle,needle+"  self._center_form_fields()\n",1)
needle=" def _scroll_page(self,key):\n"
assert s.count(needle)==1
s=s.replace(needle,""" def _center_form_fields(self):
  from PySide6.QtWidgets import QLineEdit,QAbstractSpinBox,QComboBox
  from PySide6.QtCore import Qt
  # Paths stay left aligned; numeric, switch and choice controls are centered.
  excluded=(self.output,self.mass_file.path,self.a.path,self.b.path)
  for field in self.findChildren(QLineEdit):
   if field not in excluded:field.setAlignment(Qt.AlignCenter)
  for spin in self.findChildren(QAbstractSpinBox):
   spin.setAlignment(Qt.AlignCenter)
  for choice in (self.schema,self.verify_mode,self.bom_mode,self._theme_select):
   choice.setEditable(True)
   choice.setInsertPolicy(QComboBox.NoInsert)
   choice.lineEdit().setReadOnly(True)
   choice.lineEdit().setAlignment(Qt.AlignCenter)
"""+needle,1)
assert "wrapper.setObjectName('page-scroll')" in s
s=s.replace("wrapper.setObjectName('page-scroll')","wrapper.setObjectName('page')",1)
p.write_text(s,encoding='utf8')
(root/'VERSION.txt').write_text('R11.23\n',encoding='utf8')
meta=root/'build_info.json'
if meta.exists():
 data=json.loads(meta.read_text('utf8'))
 data['version']='R11.23 · GitHub '+os.environ.get('GITHUB_SHA','')[:8]
 data['ui']='centered controls, wrapped settings cards, mass drag/drop, 5-column readable table'
 data['step_note']='Native assembly containers are necessary; cannot safely delete in exported STEP'
 meta.write_text(json.dumps(data,ensure_ascii=False),encoding='utf8')
# Update the packaged GUI smoke mode: responsive scroll panes are intentional.
entry=root/'DSCompareV3.py'
entry_text=entry.read_text(encoding='utf8')
old="assert not w.centralWidget().findChildren(QScrollArea), 'unexpected window scrollbars'"
assert entry_text.count(old)==1, 'packaged smoke compatibility anchor changed'
entry_text=entry_text.replace(old,"assert len(w.centralWidget().findChildren(QScrollArea))==2, 'mass and settings should have responsive scroll containers'",1)
entry.write_text(entry_text,encoding='utf8')
print('R11.23 stable settings forms installed')
