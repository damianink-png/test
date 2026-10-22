"""DS Compare R11.25: minimal settings, local self-tests, visible lists and mass queue removal."""
from pathlib import Path
import os,json
root=Path(os.environ["DS_COMPARE_SOURCE"])
p=root/"dsac29/gui_modern.py"
s=p.read_text(encoding="utf8")
def replace(old,new,where="gui_modern"):
 global s
 n=s.count(old)
 if n!=1:raise RuntimeError(f"{where}: expected one match, got {n}: {old[:110]!r}")
 s=s.replace(old,new,1)

# Actual R11.24 settings are intentionally replaced in one location.
a=s.index(" def _modern_settings(self):")
b=s.index(" def create_zw3d_macro(self):",a)
new_settings=""" def _modern_settings(self):
  _,lay=self._new_page('settings')
  title=QLabel('Ustawienia');title.setObjectName('hero');title.setAlignment(Qt.AlignCenter)
  lay.addWidget(title)
  grid=QGridLayout();grid.setSpacing(14)
  compare,cp=self._settings_card('Porównanie i import')
  cp.addRow('Tolerancja geometrii',self.tolerance)
  cp.addRow('Maksymalna liczba brył',self.solid_limit)
  cp.addRow(self.align)
  cp.addRow(self.full_bom)
  cp.addRow('Tryb BOM',self.bom_mode)
  cp.addRow(self.cache_import)
  cp.addRow(self.clear_import_cache_button)

  report,rp=self._settings_card('Raport i eksport')
  folder=QWidget();folder.setStyleSheet('background:transparent;')
  folder_line=QHBoxLayout(folder);folder_line.setContentsMargins(0,0,0,0);folder_line.setSpacing(8)
  self.output.setMinimumWidth(120);folder_line.addWidget(self.output,1)
  self.output_button.setMinimumWidth(104);folder_line.addWidget(self.output_button,0)
  rp.addRow('Folder wyników',folder)
  rp.addRow('Kolory modeli',self.color_editor)
  rp.addRow(self.bom_csv)

  # Keep internal compatibility controls, but do not expose old settings.
  # Force a stable ZW3D compatible AP214 / automatic verification policy.
  self.schema.setCurrentText('AP214IS')
  auto=self.verify_mode.findData('auto')
  if auto>=0:self.verify_mode.setCurrentIndex(auto)
  self._theme_select=QComboBox()
  self._theme_select.addItems(['Ciemny','Jasny'])
  self._theme_select.setCurrentText(self.theme.currentText())
  self._theme_select.currentTextChanged.connect(self.theme.setCurrentText)
  self.theme.currentTextChanged.connect(self._theme_select.setCurrentText)

  testbox,tp=self._settings_card('Testy')
  note=QLabel('Wszystkie testy działają lokalnie na przykładowych bryłach. Żadne modele firmowe ani dane nie są wysyłane.')
  note.setObjectName('muted');note.setWordWrap(True);tp.addRow(note)
  self.test_run=QPushButton('Uruchom wszystkie testy')
  self.test_run.setMinimumHeight(42)
  self.test_run.clicked.connect(self._run_local_tests)
  tp.addRow(self.test_run)
  self.test_status=QLabel('Nie uruchomiono testów.')
  self.test_status.setObjectName('muted');self.test_status.setWordWrap(True);tp.addRow(self.test_status)
  tip=QLabel('Po uruchomieniu możesz zaimportować 3 syntetyczne STEP do ZW3D 2019 i wpisać liczbę ABSR.')
  tip.setObjectName('muted');tip.setWordWrap(True);tp.addRow(tip)
  from PySide6.QtWidgets import QSpinBox
  self.test_counts={};self.test_group_states={}
  for key,label in [('STANDARDOWY','Standardowy'),('BEZ_KORZENIA','Bez korzenia'),('PLASKI','Płaski')]:
   wrap=QWidget();r=QHBoxLayout(wrap);r.setContentsMargins(0,0,0,0);r.setSpacing(8)
   count=QSpinBox();count.setRange(-1,100000);count.setValue(-1)
   count.setSpecialValueText('Nie sprawdzono');count.setToolTip('Ile pustych elementów ABSR pokazuje ZW3D?')
   group=QComboBox();group.addItems(['Nie sprawdzono','Tak','Nie','Czesciowo'])
   group.setToolTip('Czy ZW3D zachował strukturę podzłożeń?')
   r.addWidget(count,1);r.addWidget(group,1)
   self.test_counts[key]=count;self.test_group_states[key]=group
   tp.addRow(label+' · ABSR / podzłożenia',wrap)
  actions=QWidget();actions_layout=QHBoxLayout(actions)
  actions_layout.setContentsMargins(0,0,0,0);actions_layout.setSpacing(8)
  self.test_save=QPushButton('Zapisz wyniki do TXT')
  self.test_save.setEnabled(False);self.test_save.clicked.connect(self._save_local_tests)
  self.test_folder=QPushButton('Otwórz folder testów')
  self.test_folder.setEnabled(False);self.test_folder.clicked.connect(self._open_local_test_folder)
  actions_layout.addWidget(self.test_save,1);actions_layout.addWidget(self.test_folder,1)
  tp.addRow(actions)

  for form in (cp,rp,tp):
   form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
   form.setRowWrapPolicy(QFormLayout.WrapLongRows)
   form.setLabelAlignment(Qt.AlignLeft|Qt.AlignVCenter)
   form.setFormAlignment(Qt.AlignTop)
   form.setHorizontalSpacing(15);form.setVerticalSpacing(16)
  grid.addWidget(compare,0,0);grid.addWidget(report,0,1)
  grid.addWidget(testbox,1,0,1,2)
  grid.setColumnStretch(0,1);grid.setColumnStretch(1,1)
  lay.addLayout(grid);lay.addStretch(1)
  self._scroll_page('settings')
  self.safe_export.setChecked(True);self.safe_export.hide()
  self.test_process=None;self.test_report=None

 def _run_local_tests(self):
  from pathlib import Path
  from datetime import datetime
  from PySide6.QtCore import QProcess
  from PySide6.QtWidgets import QMessageBox
  import sys
  if self.test_process is not None or self.process is not None:
   QMessageBox.information(self,'Testy','Najpierw zakończ bieżące obliczenia.');return
  base=Path(self.output.text()).expanduser()
  try:
   folder=base/('TESTY_LOKALNE_'+datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
   folder.mkdir(parents=True,exist_ok=False)
  except Exception as exc:
   QMessageBox.warning(self,'Testy','Nie można utworzyć folderu testów: '+str(exc));return
  self.test_report=None;self.test_save.setEnabled(False);self.test_folder.setEnabled(False)
  self.test_status.setText('Uruchomiono testy lokalne. Nie jest używana żadna geometria firmowa.')
  self.test_run.setEnabled(False)
  self.run_compare.setEnabled(False);self.run_mass.setEnabled(False)
  process=QProcess(self)
  process.setProcessChannelMode(QProcess.MergedChannels)
  args=['--worker','diagnostic','--output',str(folder)]
  if not getattr(sys,'frozen',False):
   args.insert(0,str(Path(__file__).resolve().parents[1]/'DSCompareV3.py'))
  self.test_process=process
  process.finished.connect(lambda code,status:self._local_tests_finished(code,folder))
  process.errorOccurred.connect(lambda code:self.test_status.setText('Błąd uruchamiania procesu testowego.'))
  process.start(sys.executable,args)

 def _local_tests_finished(self,code,folder):
  from pathlib import Path
  import json
  process=self.test_process;self.test_process=None
  if process is not None:process.deleteLater()
  self.test_run.setEnabled(True)
  if self.process is None:
   self.run_compare.setEnabled(True);self.run_mass.setEnabled(True)
  self.test_report=Path(folder)/'TESTY_DS_COMPARE_R1125.txt'
  if self.test_report.is_file():
   try:
    data=json.loads((Path(folder)/'_WYNIK_V37.json').read_text('utf8'))
    status=data.get('passed','?');total=data.get('total','?')
    self.test_status.setText(f'Zapisano raport TXT · PASS: {status}/{total}. Wyniki ZW3D możesz uzupełnić poniżej.')
   except Exception:
    self.test_status.setText('Zapisano raport TXT. Sprawdź wynik w folderze.')
   self.test_save.setEnabled(True);self.test_folder.setEnabled(True)
  else:
   self.test_status.setText('Testy przerwane lub bez wyniku TXT. Sprawdź lokalny log w folderze.')
   self.test_folder.setEnabled(True)

 def _save_local_tests(self):
  from PySide6.QtWidgets import QMessageBox
  from .local_tests import update_zw3d_results
  if self.test_report is None:return
  observations={key:{'absr':self.test_counts[key].value(),
                     'groups':self.test_group_states[key].currentText()}
                for key in self.test_counts}
  try:
   update_zw3d_results(self.test_report,observations)
   self.test_status.setText('Zapisano pełny TXT z testami oraz obserwacjami ZW3D 2019.')
  except Exception as exc:
   QMessageBox.warning(self,'Zapis wyników testu',str(exc))

 def _open_local_test_folder(self):
  if self.test_report is None:return
  from PySide6.QtGui import QDesktopServices
  from PySide6.QtCore import QUrl
  QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.test_report.parent)))

"""
s=s[:a]+new_settings+s[b:]

# Old toggles remain as invisible compatibility widgets, but content opens automatically.
replace("  lay.addWidget(self._details_toggle,alignment=Qt.AlignLeft)",
        "  self._details_toggle.hide()")
# The existing creation code may be in a one-line assignment, don't assume its layout.
replace("  lay.insertWidget(lay.indexOf(self._mass_details),self._mass_toggle,0,Qt.AlignLeft)",
        "  self._mass_toggle.hide()")

# Mass list: permit multi-selection; remove selected items only from queue.
replace("""  self.mass_input_list.hide();drop_layout.addWidget(self.mass_input_list)""",
"""  self.mass_input_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
  self.mass_input_list.itemSelectionChanged.connect(self._update_mass_remove_button)
  self.mass_input_list.hide();drop_layout.addWidget(self.mass_input_list)""")
replace("""  row.addWidget(self.run_mass,2);row.addWidget(self.cancel_mass,1)
  row.addWidget(self.mass_reset,1);row.addStretch()""",
"""  row.addWidget(self.run_mass,2);row.addWidget(self.cancel_mass,1)
  self.mass_remove_selected=QPushButton('Usuń zaznaczone')
  self.mass_remove_selected.setToolTip('Usuwa wskazane modele tylko z kolejki; nie usuwa plików z dysku.')
  self.mass_remove_selected.setEnabled(False)
  self.mass_remove_selected.clicked.connect(self._mass_remove_selected)
  row.addWidget(self.mass_remove_selected,1)
  row.addWidget(self.mass_reset,1);row.addStretch()""")
anchor=" def _mass_pick_files(self):"
method=""" def _update_mass_remove_button(self):
  self.mass_remove_selected.setEnabled(self.process is None and bool(self.mass_input_list.selectedItems()))
 def _mass_remove_selected(self):
  if self.process is not None:return
  indices={i.row() for i in self.mass_input_list.selectedIndexes()}
  if not indices:return
  self.mass_inputs=[model for j,model in enumerate(self.mass_inputs) if j not in indices]
  self.mass_input_list.clear()
  from PySide6.QtWidgets import QListWidgetItem
  for j,model in enumerate(self.mass_inputs,1):
   item=QListWidgetItem(f'{j}. {model.name}  ·  {model.parent.name}')
   item.setToolTip(str(model))
   self.mass_input_list.addItem(item)
  self.mass_file.path.setText(str(self.mass_inputs[0]) if self.mass_inputs else '')
  self.mass_input_count.setText(
   f'Wybrano {len(self.mass_inputs)} modeli STEP/STP' if self.mass_inputs else
   'Nie wybrano modeli · STEP / STP')
  self.mass_input_list.setVisible(bool(self.mass_inputs))
  self._mass_invalidate()
  self.mass_remove_selected.setEnabled(False)
"""
replace(anchor,method+anchor)
replace("""  for ctrl in (self.mass_add_files,self.mass_add_folder,self.mass_reset):
   ctrl.setEnabled(not busy)""",
"""  for ctrl in (self.mass_add_files,self.mass_add_folder,self.mass_reset):
   ctrl.setEnabled(not busy)
  self.mass_remove_selected.setEnabled(not busy and bool(self.mass_input_list.selectedItems()))""")

# Keep details out of the empty/running card and visible once results load.
replace("""   self._success.show();self._actions.show();self._refresh_outputs()""",
"""   self._success.show();self._actions.show();self._refresh_outputs()
   self._details.show()""")
replace("""   self._refresh_mass_summary(folder)
   self._format_mass_results()""",
"""   self._refresh_mass_summary(folder)
   self._format_mass_results()
   self._mass_details.show()""")

# Remove stale wording for previous controls (retained on screen? none).
replace("""  self._mass_toggle.setText('Pokaż listę części')
  self.mass_log.clear();self._mass_invalidate()""",
"""  self._mass_toggle.hide()
  self.mass_remove_selected.setEnabled(False)
  self.mass_log.clear();self._mass_invalidate()""")

# The compare widget already sets the old toggle text in start(); harmless while hidden.
p.write_text(s,encoding="utf8")

# Worker uses the same standalone EXE as all other workers.
p=root/"dsac29/worker_v37.py"
w=p.read_text("utf8")
old="choices=['compare','mass','mesh','detail','import']"
assert w.count(old)==1
w=w.replace(old,"choices=['compare','mass','mesh','detail','import','diagnostic']",1)
anchor="""        elif ns.worker=='compare':
"""
assert w.count(anchor)==1
w=w.replace(anchor,"""        elif ns.worker=='diagnostic':
            from .local_tests import run as run_local_diagnostics
            diagnostics=run_local_diagnostics(folder,progress=emit)
            payload={'ok':diagnostics['ok'],'folder':str(folder),
                     'passed':diagnostics['passed'],'total':diagnostics['total'],
                     'report':diagnostics['report']}
"""+anchor,1)
p.write_text(w,encoding="utf8")

(root/"VERSION.txt").write_text("R11.25\n",encoding="utf8")
meta=root/"build_info.json"
if meta.is_file():
    d=json.loads(meta.read_text("utf8"))
    d["version"]="R11.25 · GitHub "+os.environ.get("GITHUB_SHA","")[:8]
    d["ui"]="Single diagnostics section in settings; no exposed flat/ABSR/schema/verification/general toggles; remove selected mass inputs"
    meta.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding="utf8")
print("R11.25 simplified settings and confidential local diagnostics installed")
