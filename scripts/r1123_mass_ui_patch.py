"""R11.23 mass page: single input drop zone, reset near run, readable part list."""
from pathlib import Path
import os
root=Path(os.environ['DS_COMPARE_SOURCE'])
f=root/'dsac29/gui_modern.py'
s=f.read_text(encoding='utf8')
def change(a,b):
    global s
    n=s.count(a)
    assert n==1,(a[:90],n)
    s=s.replace(a,b,1)
change('  self.mass_file.hide()\n  from PySide6.QtWidgets import QListWidget',
       '  self.mass_file.hide()\n  from PySide6.QtWidgets import QListWidget\n  from .mass_drop import MassDropArea')
start=s.index('  choices=QHBoxLayout();choices.setSpacing(9)',s.index(' def _modern_mass(self):'))
stop=s.index("  controls=QFrame();controls.setObjectName('surface')",start)
s=s[:start]+"""  self.mass_drop=MassDropArea(self._mass_add)
  drop_layout=QVBoxLayout(self.mass_drop)
  drop_layout.setContentsMargins(18,15,18,14);drop_layout.setSpacing(9)
  heading=QLabel('Przeciągnij pliki STEP/STP lub cały folder')
  heading.setObjectName('section');heading.setAlignment(Qt.AlignCenter)
  drop_layout.addWidget(heading)
  hint=QLabel('Możesz dodać jeden model, kilka modeli naraz albo cały folder z podfolderami.')
  hint.setObjectName('muted');hint.setAlignment(Qt.AlignCenter);hint.setWordWrap(True)
  drop_layout.addWidget(hint)
  choices=QHBoxLayout();choices.setSpacing(12);choices.addStretch(1)
  self.mass_add_files=QPushButton('Wybierz pliki')
  self.mass_add_folder=QPushButton('Wybierz folder')
  self.mass_add_files.clicked.connect(self._mass_pick_files)
  self.mass_add_folder.clicked.connect(self._mass_pick_folder)
  choices.addWidget(self.mass_add_files,1);choices.addWidget(self.mass_add_folder,1)
  choices.addStretch(1);drop_layout.addLayout(choices)
  self.mass_input_count=QLabel('Nie wybrano modeli · STEP / STP')
  self.mass_input_count.setAlignment(Qt.AlignCenter);self.mass_input_count.setObjectName('muted')
  drop_layout.addWidget(self.mass_input_count)
  self.mass_input_list=QListWidget();self.mass_input_list.setMinimumHeight(72)
  self.mass_input_list.setMaximumHeight(110);self.mass_input_list.setAlternatingRowColors(True)
  self.mass_input_list.hide();drop_layout.addWidget(self.mass_input_list)
  lay.addWidget(self.mass_drop)
"""+s[stop:]
change("  row=QHBoxLayout();row.addStretch();self.run_mass.setText('Oblicz masę');self.run_mass.setMinimumWidth(200);row.addWidget(self.run_mass);row.addWidget(self.cancel_mass);row.addStretch();lay.addLayout(row)",
"""  row=QHBoxLayout();row.setSpacing(9);row.addStretch()
  self.run_mass.setText('Oblicz masę');self.run_mass.setMinimumWidth(175)
  self.mass_reset=QPushButton('Resetuj dane')
  self.mass_reset.setToolTip('Czyści listę modeli i bieżący wynik, nie usuwa plików.')
  self.mass_reset.clicked.connect(self._mass_reset)
  row.addWidget(self.run_mass,2);row.addWidget(self.cancel_mass,1)
  row.addWidget(self.mass_reset,1);row.addStretch()
  lay.addLayout(row)""")
change('  self.mass_table.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Expanding);md.addWidget(self.mass_table);lay.addWidget(self._mass_details,1);self._mass_details.hide()',
"""  from PySide6.QtWidgets import QHeaderView
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
  md.addWidget(self.mass_table);self._mass_details.setMinimumHeight(310)
  lay.addWidget(self._mass_details,1);self._mass_details.hide()""")
change('  lay.addWidget(self._mass_toggle,alignment=Qt.AlignLeft)',
       '  lay.insertWidget(lay.indexOf(self._mass_details),self._mass_toggle,0,Qt.AlignLeft)')
change('  lay.addWidget(self.mass_actions)\n  self.mass_actions.hide()\n  lay.addStretch(1)',
       "  lay.addWidget(self.mass_actions)\n  self.mass_actions.hide()\n  lay.addStretch(1)\n  self._scroll_page('mass')")
start=s.index(' def _mass_add(self,paths):')
stop=s.index(' def _mass_pick_files(self):',start)
s=s[:start]+""" def _mass_add(self,paths):
  from pathlib import Path
  from PySide6.QtWidgets import QListWidgetItem
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
   QMessageBox.warning(self,'Limit modeli','Maksymalnie 500 modeli STEP/STP na jedną analizę.')
   return
  if not fresh:return
  self.mass_inputs.extend(fresh)
  self.mass_input_list.clear()
  for i,model in enumerate(self.mass_inputs,1):
   item=QListWidgetItem(f'{i}. {model.name}  ·  {model.parent.name}')
   item.setToolTip(str(model))
   self.mass_input_list.addItem(item)
  self.mass_input_list.show()
  self.mass_file.path.setText(str(self.mass_inputs[0]))
  self.mass_input_count.setText(f'Wybrano {len(self.mass_inputs)} modeli STEP/STP')
  self._mass_invalidate()
"""+s[stop:]
change("  self.mass_input_count.setText('Nie wybrano modeli. Dodaj pliki lub cały folder (STEP / STP).')\n  self.mass_log.clear();self._mass_invalidate()",
       "  self.mass_input_count.setText('Nie wybrano modeli · STEP / STP')\n  self.mass_input_list.hide();self._mass_details.hide()\n  self._mass_toggle.setText('Pokaż listę części')\n  self.mass_log.clear();self._mass_invalidate()")
change("   self._refresh_mass_summary(folder)\n def _refresh_mass_summary",
"""   self._refresh_mass_summary(folder)
   self._format_mass_results()
 def _format_mass_results(self):
  for i in range(self.mass_table.rowCount()):
   for j in range(self.mass_table.columnCount()):
    item=self.mass_table.item(i,j)
    if item is None:continue
    content=item.text()
    if j==0 and '="' in content:
     content=content.replace('="','').rstrip('"')
     item.setText(content)
    item.setToolTip(content)
    if j>0:item.setTextAlignment(Qt.AlignCenter)
 def _refresh_mass_summary""")
change(" QTableWidget{background:SURFACE;",
       """ QScrollArea#page-scroll{background:BG;border:0;}
 QFrame#mass-drop{background:SURFACE;border:2px dashed LINE;border-radius:15px;}
 QFrame#mass-drop[dragActive="true"]{background:SOFT;border:2px dashed ACCENT;}
 QListWidget{background:FIELD;color:INK;border:1px solid LINE;border-radius:8px;}
 QTableWidget{background:SURFACE;""")
anchor=' def _settings_card(self,title):'
scroll=""" def _scroll_page(self,key):
  from PySide6.QtWidgets import QScrollArea,QLayout
  page=self.pages[key]
  index={'compare':0,'mass':1,'settings':2}[key]
  wrapper=QScrollArea(self.stack);wrapper.setObjectName('page-scroll')
  wrapper.setWidgetResizable(True);wrapper.setFrameShape(QFrame.NoFrame)
  wrapper.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
  wrapper.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
  page.layout().setSizeConstraint(QLayout.SetMinimumSize)
  self.stack.removeWidget(page)
  wrapper.setWidget(page)
  self.stack.insertWidget(index,wrapper)
  self.pages[key]=wrapper
"""
change(anchor,scroll+anchor)
f.write_text(s,encoding='utf8')
print('R11.23 mass drop/controls/table patch installed')
