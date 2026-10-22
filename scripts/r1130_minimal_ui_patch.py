"""R11.30 minimal CAD/parts workflow, with two clear UI states.

The CAD engine and R11.29 exporter remain unchanged.
"""
from pathlib import Path
import os,json
root=Path(os.environ['DS_COMPARE_SOURCE'])
p=root/'dsac29/gui_modern.py'
s=p.read_text('utf8')
def method(name,source):
    global s
    anchor=' def '+name+'('
    a=s.index(anchor)
    b=s.find('\n def ',a+len(anchor))
    if b<0:raise RuntimeError('No successor method for '+name)
    s=s[:a]+source.rstrip()+ '\n'+s[b:]
def change(a,b):
    global s
    if s.count(a)!=1:raise RuntimeError(f'R11.30 anchor count {s.count(a)}: {a[:120]!r}')
    s=s.replace(a,b,1)

change(" QFrame#file-card:hover{border:1px solid ACCENT;background:FIELD;}",
       """ QFrame#file-card:hover{border:1px solid ACCENT;background:FIELD;}
 QFrame#file-card[hasFile="true"]{border:1px solid ACCENT;background:SURFACE;}
 QFrame#mass-drop[hasFiles="true"]{border:1px solid ACCENT;background:SURFACE;}
 QFrame#success{border:1px solid LINE;background:SURFACE;}
 QLabel#chosen-file{font-size:14px;font-weight:650;color:INK;}
 QLabel#result-figure{font-size:16px;font-weight:650;color:INK;}
 QPushButton#delete-one{background:transparent;border:0;color:MUTED;min-width:28px;max-width:28px;min-height:28px;max-height:28px;padding:0;font-size:20px;}
 QPushButton#delete-one:hover{background:HOVER;color:ACCENT;}""")

method('_tile',""" def _tile(self,tile,number):
  # Keep the original FileCard and choose button, but replace its giant tile
  # with a concise, visually distinct selected/empty state.
  from PySide6.QtCore import QSize
  tile.setObjectName('file-card')
  tile.setMinimumHeight(104)
  tile.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Fixed)
  choose=getattr(tile,'choose_button',None)
  if choose is None:
   choose=next((b for b in tile.findChildren(QPushButton) if 'Wybierz' in b.text()),None)
  if choose is None:raise RuntimeError('Missing CAD file picker')
  tile.choose_button=choose
  layout=tile.layout()
  while layout.count():
   it=layout.takeAt(0)
   if it.layout():
    nested=it.layout()
    while nested.count():
     sub=nested.takeAt(0)
     if sub.widget():sub.widget().setParent(tile)
   elif it.widget():it.widget().hide()
  layout.setContentsMargins(17,13,17,13);layout.setSpacing(5)
  row=QHBoxLayout();row.setSpacing(12)
  emblem=QLabel();emblem.setPixmap(vector_icon('file','#8DA6C9').pixmap(28,28))
  emblem.setFixedSize(32,34);row.addWidget(emblem)
  textcol=QVBoxLayout();textcol.setSpacing(4)
  heading=QLabel('Model '+str(number));heading.setObjectName('section');textcol.addWidget(heading)
  filename=QLabel('Nie wybrano pliku');filename.setObjectName('muted')
  filename.setSizePolicy(QSizePolicy.Ignored,QSizePolicy.Preferred)
  filename.setToolTip('Przeciągnij plik STEP / STP / Z3')
  textcol.addWidget(filename);row.addLayout(textcol,1)
  choose.setText('Wybierz')
  choose.setMinimumWidth(88);choose.setMaximumWidth(112)
  choose.setObjectName('text-button')
  row.addWidget(choose,0,Qt.AlignVCenter)
  clear=QPushButton('×');clear.setObjectName('delete-one')
  clear.setToolTip('Usuń wybrany model z porównania')
  clear.setAccessibleName('Usuń model '+str(number))
  clear.clicked.connect(lambda:tile.path.clear() if self.process is None else None)
  row.addWidget(clear,0,Qt.AlignVCenter)
  layout.addLayout(row)
  def refresh(path):
   present=bool(path)
   filename.setText(Path(path).name if present else 'Nie wybrano pliku · STEP / STP / Z3')
   filename.setObjectName('chosen-file' if present else 'muted')
   filename.setToolTip(path or 'Przeciągnij plik STEP / STP / Z3')
   choose.setText('Zmień' if present else 'Wybierz')
   clear.setVisible(present)
   tile.setProperty('hasFile',present)
   tile.style().unpolish(tile);tile.style().polish(tile)
   filename.style().unpolish(filename);filename.style().polish(filename)
  tile.path.textChanged.connect(refresh)
  tile._remove_model_button=clear
  tile._chosen_file_label=filename
  tile._file_refresh=refresh
  tile.path.hide()
  refresh(tile.path.text())
""")

method('_modern_compare',""" def _modern_compare(self):
  _,lay=self._new_page('compare')
  title=QLabel('Porównanie rewizji');title.setObjectName('hero')
  title.setAlignment(Qt.AlignCenter);lay.addWidget(title)
  self._compare_hint=QLabel('Wybierz dwa modele CAD')
  self._compare_hint.setObjectName('muted')
  self._compare_hint.setAlignment(Qt.AlignCenter);lay.addWidget(self._compare_hint)
  self._tile(self.a,'A');self._tile(self.b,'B')
  self._compare_selector_host=QWidget()
  self.source_grid=QGridLayout(self._compare_selector_host)
  self.source_grid.setContentsMargins(0,0,0,0);self.source_grid.setSpacing(12)
  self.swap_button.setText('');self.swap_button.setObjectName('info-btn')
  self.swap_button.setFixedSize(38,38)
  self.source_grid.addWidget(self.a,0,0)
  self.source_grid.addWidget(self.swap_button,0,1,Qt.AlignCenter)
  self.source_grid.addWidget(self.b,0,2)
  self.source_grid.setColumnStretch(0,1);self.source_grid.setColumnStretch(2,1)
  lay.addWidget(self._compare_selector_host)
  self._compare_run_host=QWidget()
  row=QHBoxLayout(self._compare_run_host)
  row.setContentsMargins(0,0,0,0);row.setSpacing(9);row.addStretch()
  self.run_compare.setText('Porównaj');self.run_compare.setMinimumWidth(220)
  row.addWidget(self.run_compare)
  self.cancel_compare.setText('Anuluj');row.addWidget(self.cancel_compare);row.addStretch()
  lay.addWidget(self._compare_run_host)
  self._compare_progress_panel=QFrame();self._compare_progress_panel.setObjectName('surface')
  pp=QVBoxLayout(self._compare_progress_panel);pp.setContentsMargins(16,11,16,12)
  self.compare_summary.setAlignment(Qt.AlignLeft);self.compare_summary.setObjectName('muted')
  self.compare_summary.setText('Wybierz dwa modele, aby rozpocząć.')
  pp.addWidget(self.compare_summary)
  self.progress.setRange(0,100);self.progress.setValue(0);pp.addWidget(self.progress)
  self.progress.hide()
  self._bom_label=QLabel('Raport i BOM');self._bom_label.setObjectName('muted');pp.addWidget(self._bom_label)
  self._bom_label.hide()
  self.report_progress.setRange(0,100);self.report_progress.setValue(0)
  pp.addWidget(self.report_progress);self.report_progress.hide()
  lay.addWidget(self._compare_progress_panel)
  self._success=QFrame();self._success.setObjectName('success')
  content=QVBoxLayout(self._success);content.setContentsMargins(20,19,20,19);content.setSpacing(13)
  self._success_title=QLabel('✓  Porównanie zakończone')
  self._success_title.setObjectName('section');content.addWidget(self._success_title)
  self._summary_stats=QLabel('')
  self._summary_stats.setWordWrap(True);self._summary_stats.setObjectName('result-figure')
  content.addWidget(self._summary_stats)
  lay.addWidget(self._success);self._success.hide()
  self._actions=QFrame();self._actions.setObjectName('surface')
  actions=QHBoxLayout(self._actions);actions.setContentsMargins(12,10,12,10);actions.setSpacing(9)
  for file in ('POROWNANIE_KOLORY.step','RAPORT.html',''):
   button=self.compare_open[file];button.setMinimumWidth(0);actions.addWidget(button,1)
  lay.addWidget(self._actions);self._actions.hide()
  self.reset_button.setText('Nowe porównanie');self.reset_button.setObjectName('text-button')
  try:self.reset_button.clicked.disconnect()
  except (TypeError,RuntimeError):pass
  self.reset_button.clicked.connect(self.new_comparison)
  lay.addWidget(self.reset_button,alignment=Qt.AlignCenter)
  self.reset_button.hide()
  self._details_toggle=QPushButton('Pokaż szczegółową listę zmian')
  self._details_toggle.setObjectName('text-button')
  self._details_toggle.clicked.connect(self._toggle_details)
  self._details_toggle.hide()
  self._details=QFrame();self._details.setObjectName('details')
  dt=QVBoxLayout(self._details);dt.setContentsMargins(0,0,0,0)
  search_row=QHBoxLayout();search_row.addWidget(self.search,1)
  search_row.addWidget(self.filter_selector);dt.addLayout(search_row)
  dt.addWidget(self.compare_table);self._details.hide()
  lay.addStretch(1)
  self._source_stacked=False;self._metric_columns=6

 def _set_compare_result_state(self,done):
  self._compare_selector_host.setVisible(not done)
  self._compare_run_host.setVisible(not done)
  self._compare_hint.setVisible(not done)
  self._compare_progress_panel.setVisible(not done)
  self._success.setVisible(done)
  self._actions.setVisible(done)
  self.reset_button.setVisible(done)
  if done:
   self.progress.hide();self.report_progress.hide();self._bom_label.hide()
  else:
   self._success.hide();self._actions.hide()
""")

# The Qt template was refactored after 2019; preserve existing new_comparison
# but make sure that state is reset in one place.
change("  self.log.clear();self.navigate('compare')",
       "  self.log.clear();self._set_compare_result_state(False);self.navigate('compare')")

method('_modern_mass',""" def _modern_mass(self):
  _,lay=self._new_page('mass')
  title=QLabel('Masa części');title.setObjectName('hero')
  title.setAlignment(Qt.AlignCenter);lay.addWidget(title)
  self._tile(self.mass_file,'do obliczenia masy');self.mass_file.hide()
  from PySide6.QtWidgets import QListWidget,QHeaderView
  from .mass_drop import MassDropArea
  self.mass_inputs=[]
  self._mass_form_host=QWidget()
  form_root=QVBoxLayout(self._mass_form_host)
  form_root.setContentsMargins(0,0,0,0);form_root.setSpacing(11)
  self.mass_drop=MassDropArea(self._mass_add)
  self.mass_drop.setProperty('hasFiles',False)
  drop_layout=QVBoxLayout(self.mass_drop)
  drop_layout.setContentsMargins(16,12,16,12);drop_layout.setSpacing(7)
  self._mass_drop_title=QLabel('Przeciągnij pliki STEP/STP lub folder')
  self._mass_drop_title.setObjectName('section')
  self._mass_drop_title.setAlignment(Qt.AlignCenter);drop_layout.addWidget(self._mass_drop_title)
  self._mass_drop_hint=QLabel('Możesz dodać kilka modeli naraz.')
  self._mass_drop_hint.setObjectName('muted');self._mass_drop_hint.setAlignment(Qt.AlignCenter)
  drop_layout.addWidget(self._mass_drop_hint)
  choices=QHBoxLayout();choices.setSpacing(9)
  self.mass_add_files=QPushButton('Wybierz pliki')
  self.mass_add_folder=QPushButton('Wybierz folder')
  self.mass_add_files.clicked.connect(self._mass_pick_files)
  self.mass_add_folder.clicked.connect(self._mass_pick_folder)
  choices.addStretch(1);choices.addWidget(self.mass_add_files,1)
  choices.addWidget(self.mass_add_folder,1);choices.addStretch(1)
  drop_layout.addLayout(choices)
  self.mass_input_count=QLabel('Nie wybrano modeli')
  self.mass_input_count.setObjectName('muted')
  self.mass_input_count.setAlignment(Qt.AlignCenter)
  drop_layout.addWidget(self.mass_input_count)
  self.mass_input_list=QListWidget()
  self.mass_input_list.setMinimumHeight(50);self.mass_input_list.setMaximumHeight(170)
  self.mass_input_list.setAlternatingRowColors(False)
  self.mass_input_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
  self.mass_input_list.itemSelectionChanged.connect(self._update_mass_remove_button)
  self.mass_input_list.hide();drop_layout.addWidget(self.mass_input_list)
  self._mass_queue_buttons=QWidget()
  queue_row=QHBoxLayout(self._mass_queue_buttons)
  queue_row.setContentsMargins(0,0,0,0);queue_row.addStretch(1)
  self.mass_remove_selected=QPushButton('Usuń zaznaczone')
  self.mass_remove_selected.setObjectName('text-button')
  self.mass_remove_selected.setEnabled(False)
  self.mass_remove_selected.setToolTip('Usuwa pozycje z listy, nie z dysku.')
  self.mass_remove_selected.clicked.connect(self._mass_remove_selected)
  queue_row.addWidget(self.mass_remove_selected)
  drop_layout.addWidget(self._mass_queue_buttons)
  self._mass_queue_buttons.hide()
  form_root.addWidget(self.mass_drop)
  self._mass_materials_panel=QFrame();self._mass_materials_panel.setObjectName('surface')
  material_form=QFormLayout(self._mass_materials_panel)
  material_form.setContentsMargins(17,12,17,12);material_form.setSpacing(9)
  material_form.addRow('Materiał',self.materials)
  material_form.addRow('Gęstość [kg/m³]',self.density)
  form_root.addWidget(self._mass_materials_panel)
  self._mass_material_actions=QWidget()
  more=QHBoxLayout(self._mass_material_actions)
  more.setContentsMargins(0,0,0,0);more.addStretch()
  self._add_material_button=QPushButton('Dodaj materiał')
  self._add_material_button.setObjectName('text-button')
  self._add_material_button.clicked.connect(self.add_material)
  more.addWidget(self._add_material_button);more.addStretch()
  form_root.addWidget(self._mass_material_actions)
  self._mass_run_host=QWidget()
  run_row=QHBoxLayout(self._mass_run_host)
  run_row.setContentsMargins(0,0,0,0);run_row.setSpacing(9)
  self.run_mass.setText('Oblicz masę')
  self.run_mass.setMinimumWidth(150)
  self.mass_reset=QPushButton('Wyczyść')
  self.mass_reset.setObjectName('text-button')
  self.mass_reset.setToolTip('Czyści listę modeli, nie usuwa plików.')
  self.mass_reset.clicked.connect(self._mass_reset)
  run_row.addWidget(self.run_mass,3)
  run_row.addWidget(self.cancel_mass,1)
  run_row.addWidget(self.mass_reset,1)
  form_root.addWidget(self._mass_run_host)
  lay.addWidget(self._mass_form_host)
  self.mass_progress.setRange(0,100);self.mass_progress.setValue(0)
  self.mass_progress.hide();lay.addWidget(self.mass_progress)
  self._mass_result_card=QFrame();self._mass_result_card.setObjectName('success')
  result_layout=QVBoxLayout(self._mass_result_card)
  result_layout.setContentsMargins(20,19,20,19);result_layout.setSpacing(12)
  self.mass_done=QLabel('✓  Obliczenia zakończone')
  self.mass_done.setObjectName('section')
  result_layout.addWidget(self.mass_done)
  self.mass_summary.setObjectName('result-figure')
  self.mass_summary.setWordWrap(True)
  result_layout.addWidget(self.mass_summary)
  lay.addWidget(self._mass_result_card)
  self._mass_result_card.hide()
  # Historical Qt table remains in memory for backward compatibility,
  # but is intentionally not attached to the window.
  self._mass_details=QFrame();self._mass_details.setObjectName('details')
  md=QVBoxLayout(self._mass_details);md.setContentsMargins(0,0,0,0)
  self.mass_table.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Expanding)
  self.mass_table.setMinimumHeight(290)
  self.mass_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
  self.mass_table.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
  self.mass_table.setTextElideMode(Qt.ElideMiddle)
  self.mass_table.setWordWrap(False)
  self.mass_table.setSelectionBehavior(QAbstractItemView.SelectRows)
  self.mass_table.verticalHeader().setDefaultSectionSize(36)
  hdr=self.mass_table.horizontalHeader()
  hdr.setSectionResizeMode(QHeaderView.Interactive)
  hdr.setMinimumSectionSize(80)
  hdr.setSectionResizeMode(0,QHeaderView.Stretch)
  for col,width in ((1,85),(2,148),(3,135),(4,145)):
   hdr.setSectionResizeMode(col,QHeaderView.Fixed)
   self.mass_table.setColumnWidth(col,width)
  md.addWidget(self.mass_table);self._mass_details.hide()
  self._mass_toggle=QPushButton('Pokaż listę części')
  self._mass_toggle.setObjectName('text-button')
  self._mass_toggle.clicked.connect(self._toggle_mass)
  self._mass_toggle.hide()
  self.mass_actions=QFrame();self.mass_actions.setObjectName('surface')
  actions=QHBoxLayout(self.mass_actions)
  actions.setContentsMargins(12,10,12,10);actions.setSpacing(9)
  for key in ('RAPORT_MASY.html',''):
   b=self.mass_open[key];b.setMinimumWidth(0);actions.addWidget(b,1)
  lay.addWidget(self.mass_actions);self.mass_actions.hide()
  self.mass_new_button=QPushButton('Nowe obliczenia')
  self.mass_new_button.setObjectName('text-button')
  self.mass_new_button.clicked.connect(self._mass_reset)
  lay.addWidget(self.mass_new_button,alignment=Qt.AlignCenter)
  self.mass_new_button.hide()
  lay.addStretch(1)
  self._scroll_page('mass')
  self._update_mass_file_visual()

 def _set_mass_result_state(self,done):
  self._mass_form_host.setVisible(not done)
  self.mass_done.setVisible(done)
  self._mass_result_card.setVisible(done)
  self.mass_actions.setVisible(done)
  self.mass_new_button.setVisible(done)
  if done:self.mass_progress.hide()

 def _update_mass_file_visual(self):
  count=len(self.mass_inputs)
  ready=count>0
  self._mass_drop_title.setText('Pliki do obliczenia masy' if ready else 'Przeciągnij pliki STEP/STP lub folder')
  self._mass_drop_hint.setVisible(not ready)
  self.mass_add_files.setText('+ Dodaj pliki' if ready else 'Wybierz pliki')
  self.mass_add_folder.setText('+ Dodaj folder' if ready else 'Wybierz folder')
  self.mass_input_count.setText(
   f'✓  {count} wybranych modeli STEP/STP' if ready else 'Nie wybrano modeli')
  self.mass_input_count.setObjectName('chosen-file' if ready else 'muted')
  self.mass_input_count.style().unpolish(self.mass_input_count)
  self.mass_input_count.style().polish(self.mass_input_count)
  self._mass_queue_buttons.setVisible(ready)
  self.mass_input_list.setVisible(ready)
  self.mass_drop.setProperty('hasFiles',ready)
  self.mass_drop.style().unpolish(self.mass_drop);self.mass_drop.style().polish(self.mass_drop)
  if ready:
   self.mass_input_list.setFixedHeight(min(170,max(45,count*37+6)))

 def _render_mass_file_rows(self):
  from PySide6.QtWidgets import QListWidgetItem
  from PySide6.QtCore import QSize
  self.mass_input_list.clear()
  for model in self.mass_inputs:
   item=QListWidgetItem(self.mass_input_list)
   item.setToolTip(str(model));item.setSizeHint(QSize(20,34))
   holder=QWidget()
   line=QHBoxLayout(holder)
   line.setContentsMargins(8,1,3,1);line.setSpacing(8)
   label=QLabel(model.name);label.setToolTip(str(model))
   label.setSizePolicy(QSizePolicy.Ignored,QSizePolicy.Preferred)
   line.addWidget(label,1)
   delete=QPushButton('×');delete.setObjectName('delete-one')
   delete.setToolTip('Usuń '+model.name+' z listy')
   delete.setAccessibleName('Usuń '+model.name)
   delete.clicked.connect(lambda checked=False,item=item:self._mass_remove_one(item))
   line.addWidget(delete)
   self.mass_input_list.setItemWidget(item,holder)
  self.mass_file.path.setText(str(self.mass_inputs[0]) if self.mass_inputs else '')
  self._update_mass_file_visual()

 def _mass_remove_one(self,item):
  if self.process is not None:return
  index=self.mass_input_list.row(item)
  if index<0 or index>=len(self.mass_inputs):return
  del self.mass_inputs[index]
  self._render_mass_file_rows()
  self._mass_invalidate()
""")

# Replace the repeated old list creation with the common renderer.
method('_mass_add',""" def _mass_add(self,paths):
  known={str(p).casefold() for p in self.mass_inputs}
  fresh=[]
  try:
   for raw in paths:
    p=Path(raw).expanduser().resolve()
    candidates=sorted((x for x in p.rglob('*') if x.is_file() and x.suffix.lower() in ('.step','.stp')),
                      key=lambda x:str(x).casefold()) if p.is_dir() else (p,)
    for model in candidates:
     if model.is_file() and model.suffix.lower() in ('.step','.stp'):
      key=str(model).casefold()
      if key not in known:
       known.add(key);fresh.append(model)
       if len(fresh)+len(self.mass_inputs)>500:break
    if len(fresh)+len(self.mass_inputs)>500:break
  except (OSError,ValueError) as exc:
   QMessageBox.warning(self,'Wybór modeli',str(exc));return
  if len(fresh)+len(self.mass_inputs)>500:
   QMessageBox.warning(self,'Limit modeli','Maksymalnie 500 modeli STEP/STP na analizę.')
   return
  if not fresh:return
  self.mass_inputs.extend(fresh)
  self._render_mass_file_rows()
  self._mass_invalidate()
""")
method('_mass_remove_selected',""" def _mass_remove_selected(self):
  if self.process is not None:return
  indices={i.row() for i in self.mass_input_list.selectedIndexes()}
  if not indices:return
  self.mass_inputs=[m for index,m in enumerate(self.mass_inputs) if index not in indices]
  self._render_mass_file_rows()
  self._mass_invalidate()
  self.mass_remove_selected.setEnabled(False)
""")
method('_mass_reset',""" def _mass_reset(self):
  if self.process is not None:return
  self.mass_inputs.clear()
  self._render_mass_file_rows()
  self.mass_log.clear()
  self._mass_invalidate()
  self.mass_remove_selected.setEnabled(False)
  self._set_mass_result_state(False)
""")
change("""  self.mass_progress.hide();self.mass_progress.setRange(0,100);self.mass_progress.setValue(0)
  self.mass_table.setRowCount(0);self.mass_summary.setText('Wybierz modele i naciśnij „Oblicz masę”.')""",
"""  self.mass_progress.hide();self.mass_progress.setRange(0,100);self.mass_progress.setValue(0)
  self.mass_table.setRowCount(0)
  self._set_mass_result_state(False)""")

# R11.28 busy disables all edit/new controls, including compact 'X' buttons.
change("""  if hasattr(self,'mass_reset'):self.mass_reset.setEnabled(not busy)""",
"""  if hasattr(self,'mass_reset'):self.mass_reset.setEnabled(not busy)
  for card in (self.a,self.b):
   if hasattr(card,'_remove_model_button'):
    card._remove_model_button.setEnabled(not busy)
   card.choose_button.setEnabled(not busy)
  if hasattr(self,'mass_new_button'):self.mass_new_button.setEnabled(not busy)
  if hasattr(self,'mass_input_list'):
   for index in range(self.mass_input_list.count()):
    holder=self.mass_input_list.itemWidget(self.mass_input_list.item(index))
    if holder is not None:
     for b in holder.findChildren(QPushButton):b.setEnabled(not busy)""")

# Make the result view the only active page content once the worker completed.
change("""   self._mass_invalidate()
  super().start(kind)""",
"""   self._mass_invalidate()
  super().start(kind)""")
change("""  self.progress.hide();self.mass_progress.hide();self.report_progress.hide()
  self._bom_label.hide();self.reset_button.setEnabled(True)""",
"""  self.progress.hide();self.mass_progress.hide();self.report_progress.hide()
  self._bom_label.hide();self.reset_button.setEnabled(True)""")
change("""   self.mass_done.setVisible(success);self.mass_actions.setVisible(success)
   if success:
    self.mass_progress.setRange(0,100);self.mass_progress.setValue(100)
    self.mass_summary.setText(self.mass_summary.text()+'  ·  Zakończono ✓')
   else:
    self.mass_done.hide();self.mass_actions.hide()
  if self.task=='compare' and self.results.get('compare'):
   self._actions.show()
  self._refresh_outputs()""",
"""   self._set_mass_result_state(success)
   if success:
    self.mass_progress.setRange(0,100);self.mass_progress.setValue(100)
  if self.task=='compare':
   success=bool(getattr(self,'completion_ok',False) and self.results.get('compare'))
   self._set_compare_result_state(success)
  self._refresh_outputs()""")
change("""   self._summary_stats.setText('Bez zmian: {same}   ·   Nowe: {new}   ·   Usunięte: {old}   ·   Przesunięte: {move}'.format(same=c.get('SAME',0)+c.get('RENAMED',0),new=c.get('ADDED',0),old=c.get('REMOVED',0),move=c.get('MOVED',0)))""",
"""   self._summary_stats.setText('A: {a} brył    →    B: {b} brył\\nBez zmian: {same}    ·    Nowe: {new}    ·    Usunięte: {old}    ·    Przesunięte: {move}'.format(
    a=s.get('solids_A',0),b=s.get('solids_B',0),
    same=c.get('SAME',0)+c.get('RENAMED',0),
    new=c.get('ADDED',0),old=c.get('REMOVED',0),move=c.get('MOVED',0)))""")
change("""   self._success.show();self._actions.show();self._refresh_outputs()
   self._details.hide()""",
"""   self._refresh_outputs();self._details.hide()""")
change("""   self._refresh_mass_summary(folder)
   self._format_mass_results()""",
"""   self._refresh_mass_summary(folder)
   self._format_mass_results()""")
change("""  self._mass_reset()
 def invalidate_comparison""",
"""  self._mass_reset()
  self._set_compare_result_state(False)
 def invalidate_comparison""")
change("""   self._success.hide();self._actions.hide()
  if not hasattr(self,'compare_table'):return""",
"""   self._set_compare_result_state(False)
  if not hasattr(self,'compare_table'):return""")

# Clear the old status card whenever 'New comparison' is chosen.
p.write_text(s,encoding='utf8')
(root/'VERSION.txt').write_text('R11.30\n',encoding='utf8')
build=root/'build_info.json'
if build.exists():
 obj=json.loads(build.read_text('utf8'))
 obj['version']='R11.30 · GitHub '+os.environ.get('GITHUB_SHA','')[:8]
 obj['ui']='Minimal file selection, per-file remove and dedicated post-analysis results'
 build.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf8')
print('R11.30 UI: selected file cards, per-row queue delete, compact done states, no CAD engine edits')
