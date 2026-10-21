"""DS Compare R11.22 - native subassemblies, batch mass and truthful completion controls.

Runs after the R11.21 patch on the restored sources in GitHub Actions.
"""
from pathlib import Path
import os,json
root=Path(os.environ['DS_COMPARE_SOURCE'])

def replace(path,old,new,n=1):
 f=root/path
 source=f.read_text(encoding='utf8')
 count=source.count(old)
 if count!=n:
  raise RuntimeError(f'{path}: expected {n} occurrences, found {count}: {old[:110]!r}')
 f.write_text(source.replace(old,new,n),encoding='utf8')

# XCAF subassemblies are intentionally restored. The opt-in flat mode is
# accurately described as NOT retaining native group hierarchy.
replace('dsac29/gui_modern.py',
 "  enabled=str(self.store.value('zw3d_flat_output_r1121','true')).lower() not in ('false','0','no')",
 "  enabled=str(self.store.value('zw3d_flat_output_r1122','false')).lower() in ('true','1','yes')")
replace('dsac29/gui_modern.py',
 "  self.zw3d_flat_output=QCheckBox('STEP bez pustych części ABSR (ZW3D 2019)')",
 "  self.zw3d_flat_output=QCheckBox('Płaski STEP bez podzłożeń — tryb zgodności ZW3D')")
replace('dsac29/gui_modern.py',
 "  self.zw3d_flat_output.setToolTip('Włączone: 1 STEP PRODUCT na 1 rzeczywistą bryłę, status w kolorach/nazwach/warstwach. Wyłączone: podzłożenia, które importer ZW3D może pokazywać jako ABSR.')",
 "  self.zw3d_flat_output.setToolTip('Wyłączone (domyślnie): rzeczywiste podzłożenia STEP według statusów i rewizji A/B. Włączone: brak węzłów złożenia, więc nie ma podzłożeń; statusy zachowane w nazwach i warstwach. W ZW3D 2019 węzły złożeń mogą wyglądać jak ABSR.')")
replace('dsac29/gui_modern.py',
 "self.store.setValue('zw3d_flat_output_r1121',checked)",
 "self.store.setValue('zw3d_flat_output_r1122',checked)")
replace('dsac29/gui_modern.py',
 "  rp.addRow(self.zw3d_flat_output)",
 "  rp.addRow(self.zw3d_flat_output)\n"
 "  warning=QLabel('Domyślnie: prawdziwe podzłożenia. ZW3D 2019 może wyświetlać ich kontenery jako ABSR. Tryb płaski usuwa kontenery, ale także podzłożenia.')\n"
 "  warning.setObjectName('muted');warning.setWordWrap(True);rp.addRow(warning)")

# Preserve single mass engine in the worker but add validated, batch input file.
replace('dsac29/gui45.py',
 "        else:args+=['--input',inputs[0],'--no-preview']",
 """        else:
            args+=['--input',inputs[0],'--no-preview']
            if kind=='mass' and getattr(self,'mass_inputs',None):
                input_file=folder/'_MASS_INPUTS.json'
                input_file.write_text(json.dumps([str(p) for p in self.mass_inputs],ensure_ascii=False,indent=2),encoding='utf8')
                args+=['--inputs-file',str(input_file)]""")
replace('dsac29/worker_v37.py',
 "    p.add_argument('--input',default='');p.add_argument('--output',required=True)",
 "    p.add_argument('--input',default='');p.add_argument('--output',required=True)\n"
 "    p.add_argument('--inputs-file',default='',help='JSON list of CAD model paths for batch mass')")
replace('dsac29/worker_v37.py',
 "            from .single_mass import analyze_single\n            output,s=analyze_single(ns.input,ns.output,ns.density,progress=emit,preview=not ns.no_preview,max_solids=ns.max_solids)",
 """            from .single_mass import analyze_single,analyze_many
            if ns.inputs_file:
                files=json.loads(Path(ns.inputs_file).read_text(encoding='utf8'))
                output,s=analyze_many(files,ns.output,ns.density,progress=emit,max_solids=ns.max_solids)
            else:
                output,s=analyze_single(ns.input,ns.output,ns.density,progress=emit,preview=not ns.no_preview,max_solids=ns.max_solids)""")

# New, visible user-facing input list; hidden compatibility FileCard supplies
# the first model path to existing validation and runner.
replace('dsac29/gui_modern.py',
 """  self._tile(self.mass_file,'do obliczenia masy')
  lay.addWidget(self.mass_file)""",
 """  self._tile(self.mass_file,'do obliczenia masy')
  self.mass_file.hide()
  from PySide6.QtWidgets import QListWidget
  self.mass_inputs=[]
  choices=QHBoxLayout();choices.setSpacing(9)
  self.mass_add_files=QPushButton('Dodaj pliki STEP')
  self.mass_add_folder=QPushButton('Dodaj folder')
  self.mass_reset=QPushButton('Resetuj dane')
  self.mass_add_files.clicked.connect(self._mass_pick_files)
  self.mass_add_folder.clicked.connect(self._mass_pick_folder)
  self.mass_reset.clicked.connect(self._mass_reset)
  choices.addWidget(self.mass_add_files,1)
  choices.addWidget(self.mass_add_folder,1)
  choices.addWidget(self.mass_reset,1)
  lay.addLayout(choices)
  self.mass_input_count=QLabel('Nie wybrano modeli. Dodaj pliki lub cały folder (STEP / STP).')
  self.mass_input_count.setObjectName('muted')
  self.mass_input_count.setWordWrap(True)
  lay.addWidget(self.mass_input_count)
  self.mass_input_list=QListWidget()
  self.mass_input_list.setMinimumHeight(66)
  self.mass_input_list.setMaximumHeight(120)
  self.mass_input_list.setAlternatingRowColors(True)
  lay.addWidget(self.mass_input_list)""")
replace('dsac29/gui_modern.py',
 """  btn_row=QHBoxLayout()
  for f in ('RAPORT_MASY.html',''):
   btn_row.addWidget(self.mass_open[f],1)
  lay.addLayout(btn_row);lay.addStretch(1)""",
 """  self.mass_done=QLabel('✓ Obliczenia zakończone — raport gotowy')
  self.mass_done.setObjectName('section')
  self.mass_done.setAlignment(Qt.AlignCenter)
  lay.addWidget(self.mass_done)
  self.mass_done.hide()
  self.mass_actions=QFrame();self.mass_actions.setObjectName('surface')
  btn_row=QHBoxLayout(self.mass_actions)
  btn_row.setContentsMargins(12,10,12,10)
  for f in ('RAPORT_MASY.html',''):
   b=self.mass_open[f];b.setMinimumWidth(0);btn_row.addWidget(b,1)
  lay.addWidget(self.mass_actions)
  self.mass_actions.hide()
  lay.addStretch(1)""")
replace('dsac29/gui_modern.py',
 " def _toggle_mass(self):\n",
 """ def _mass_invalidate(self):
  self.results.pop('mass',None)
  self.mass_done.hide();self.mass_actions.hide()
  self.mass_progress.hide();self.mass_progress.setRange(0,100);self.mass_progress.setValue(0)
  self.mass_table.setRowCount(0);self.mass_summary.setText('Wybierz modele i naciśnij „Oblicz masę”.')
  for action in self.mass_open.values():action.setEnabled(False)
 def _mass_add(self,paths):
  from pathlib import Path
  existing={str(p).casefold() for p in self.mass_inputs}
  incoming=[]
  for entry in paths:
   p=Path(entry).expanduser().resolve()
   if not p.is_file() or p.suffix.lower() not in ('.step','.stp'):continue
   if str(p).casefold() in existing:continue
   incoming.append(p);existing.add(str(p).casefold())
  if len(self.mass_inputs)+len(incoming)>500:
   QMessageBox.warning(self,'Za dużo plików','Limit: 500 modeli na jedną analizę. Wybierz mniejszy folder.')
   return
  if not incoming:return
  self.mass_inputs.extend(incoming)
  self.mass_input_list.clear()
  for i,p in enumerate(self.mass_inputs,1):
   self.mass_input_list.addItem(f'{i}. {p.name}   —   {p.parent}')
  self.mass_file.path.setText(str(self.mass_inputs[0]))
  n=len(self.mass_inputs)
  self.mass_input_count.setText(f'Wybrano {n} model' + ('e' if 2<=n<=4 else 'i' if n>=5 else '') + ' · STEP/STP · wyniki osobno i razem')
  self._mass_invalidate()
 def _mass_pick_files(self):
  from PySide6.QtWidgets import QFileDialog
  selected,_=QFileDialog.getOpenFileNames(self,'Dodaj modele do obliczenia masy',
    str(self.mass_inputs[-1].parent if self.mass_inputs else Path.home()),
    'Modele STEP (*.step *.stp);;Wszystkie pliki (*)')
  self._mass_add(selected)
 def _mass_pick_folder(self):
  from PySide6.QtWidgets import QFileDialog
  folder=QFileDialog.getExistingDirectory(self,'Wybierz folder modeli STEP/STP',
    str(self.mass_inputs[-1].parent if self.mass_inputs else Path.home()))
  if folder:
   base=Path(folder)
   files=sorted((p for p in base.rglob('*') if p.is_file() and p.suffix.lower() in ('.step','.stp')),
      key=lambda p:str(p).casefold())
   if len(files)>500:
    QMessageBox.warning(self,'Za dużo plików','Folder zawiera ponad 500 plików STEP/STP. Wybierz mniejszy folder.')
    return
   if not files:
    QMessageBox.information(self,'Brak modeli','Nie znaleziono plików STEP / STP.')
    return
   self._mass_add(files)
 def _mass_reset(self):
  if self.process is not None:return
  self.mass_inputs.clear();self.mass_input_list.clear();self.mass_file.path.clear()
  self.mass_input_count.setText('Nie wybrano modeli. Dodaj pliki lub cały folder (STEP / STP).')
  self.mass_log.clear();self._mass_invalidate()
 def _mass_running_controls(self,busy):
  for ctrl in (self.mass_add_files,self.mass_add_folder,self.mass_reset):
   ctrl.setEnabled(not busy)
 def _toggle_mass(self):
""")
replace('dsac29/gui_modern.py',
 """ def start(self,kind):
  if kind=='compare':
   self._success.hide();self._actions.hide();self._details.hide();self._bom_label.hide()
   self.report_progress.hide();self._details_toggle.setText('Pokaż szczegółową listę zmian')
  super().start(kind)""",
 """ def start(self,kind):
  if kind=='compare':
   self._success.hide();self._actions.hide();self._details.hide();self._bom_label.hide()
   self.report_progress.hide();self._details_toggle.setText('Pokaż szczegółową listę zmian')
  if kind=='mass':
   if not self.mass_inputs:
    QMessageBox.warning(self,'Brak modeli','Najpierw dodaj pliki STEP albo folder.')
    return
   self._mass_invalidate()
  super().start(kind)
  if kind=='mass' and self.process is not None:
   self._mass_running_controls(True)
   self.mass_summary.setText(f'Trwa obliczanie masy {len(self.mass_inputs)} modeli…')""")
replace('dsac29/gui_modern.py',
 """  self._bom_label.hide();self.reset_button.setEnabled(True)
  if self.task=='compare' and self.results.get('compare'):""",
 """  self._bom_label.hide();self.reset_button.setEnabled(True)
  if self.task=='mass':
   self._mass_running_controls(False)
   success=bool(getattr(self,'completion_ok',False) and self.results.get('mass'))
   self.mass_done.setVisible(success);self.mass_actions.setVisible(success)
   if success:
    self.mass_progress.setRange(0,100);self.mass_progress.setValue(100)
    self.mass_summary.setText(self.mass_summary.text()+'  ·  Zakończono ✓')
   else:
    self.mass_done.hide();self.mass_actions.hide()
  if self.task=='compare' and self.results.get('compare'):""")
replace('dsac29/gui_modern.py',
 """   detail='Masa: {:.3f} kg  ·  {} brył  ·  {} unikalnych pozycji'.format(s['masa_calosci_kg'],s.get('liczba_bryl',0),s.get('liczba_pozycji',0))""",
 """   detail='Masa: {:.3f} kg  ·  {} brył  ·  {} pozycji'.format(s['masa_calosci_kg'],s.get('liczba_bryl',0),s.get('liczba_pozycji',0))
   if s.get('liczba_plikow'):detail='Przeanalizowano {} modeli  ·  '.format(s['liczba_plikow'])+detail""")
replace('dsac29/gui_modern.py',
 """ def reset_session(self):
  super().reset_session();self._success.hide();self._actions.hide();self._details.hide();self.progress.hide();self.mass_progress.hide();self.report_progress.hide();self._bom_label.hide()""",
 """ def reset_session(self):
  super().reset_session();self._success.hide();self._actions.hide();self._details.hide();self.progress.hide();self.mass_progress.hide();self.report_progress.hide();self._bom_label.hide()
  self._mass_reset()""")

# Save a document-ready, intelligible version label without changing algorithms.
(root/'VERSION.txt').write_text('R11.22\n',encoding='utf8')
meta=root/'build_info.json'
if meta.is_file():
 data=json.loads(meta.read_text(encoding='utf8'))
 data['version']='R11.22 · GitHub '+os.environ.get('GITHUB_SHA','')[:8]
 data['step_mode']='hierarchical native STEP default; flat without subassemblies optional'
 data['mass']='multi-file, folder, reset and final-only report actions'
 meta.write_text(json.dumps(data,ensure_ascii=False),encoding='utf8')
print('R11.22 source patch installed')
