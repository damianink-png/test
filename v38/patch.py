"""DS Compare V3.8 upgrade patch for the verified V3.7 source tree."""
from pathlib import Path

root = Path(__file__).resolve().parent
p = root / "dsac29" / "gui_qt37.py"
s = p.read_text(encoding="utf-8")

def change(old, new):
    global s
    if old not in s:
        raise RuntimeError("V3.8 source anchor missing: " + old[:90])
    s = s.replace(old, new)

change("'MOVED':'#6659D4'", "'MOVED':'#B47BDD'")
change("'ADDED':'#6659D4'", "'ADDED':'#4985EE'")
change("selection='#E2F2F1' if light else '#344E56'", "selection='#FFF0DC' if light else '#57422C'")
change("QPushButton:hover {{background:{hover};border:1px solid #56BDAD;", "QPushButton:hover {{background:{hover};border:1px solid #F4A340;")
change("'#206B68' if light else '#7AE4D2'", "'#99530A' if light else '#FFD5A0'")
change("QPushButton#primary {{background:#58C8B1;color:#102731;", "QPushButton#primary {{background:#F59E38;color:#241B11;")
change("QPushButton#primary:hover {{background:#87E5D0;", "QPushButton#primary:hover {{background:#FFB85F;")
change("QPushButton#teal {{background:#49B8AC;color:#142D33;", "QPushButton#teal {{background:#F59E38;color:#241B11;")
change("QPushButton#teal:hover {{background:#81DBCD;", "QPushButton#teal:hover {{background:#FFB85F;")
change("selection-background-color:#52B8AC", "selection-background-color:#F59E38")
change("border:1px solid #51BEB3", "border:1px solid #F59E38")
change("QProgressBar {{background:{inp};color:{text};border:none;border-radius:5px;height:8px;}}",
       "QProgressBar {{background:{inp};color:{text};border:1px solid {edge};border-radius:6px;min-height:17px;max-height:19px;text-align:center;font-weight:700;}}")
change("QProgressBar::chunk {{background:#58C8B1;border-radius:5px;}}",
       "QProgressBar::chunk {{background:#F59E38;border-radius:5px;}}")
change("QScrollBar:vertical {{background:transparent;width:9px;}}",
       "QComboBox::drop-down {{border:none;width:28px;}}\n    QScrollBar:vertical {{background:transparent;width:9px;}}")
change("color:#54BFAF;font-size:31px", "color:#F59E38;font-size:31px")
change("self.progress.setMaximumHeight(9);v.addWidget(self.progress)",
       "self.progress.setMinimumHeight(20);self.progress.setFormat('Gotowy  •  %p%');v.addWidget(self.progress)")
change("toolbar.addStretch()\n        v.addLayout(toolbar)",
       """toolbar.addStretch()
        toolbar.addWidget(_button('Dopasuj model',self.fit_model))
        v.addLayout(toolbar)
        legend=QHBoxLayout();self.legend_filters={}
        legend.addWidget(_label('Kolory:','muted'))
        for code,name in [('SAME','Bez zmian'),('CHANGED','Zmienione'),
                          ('ADDED','Nowe'),('MOVED','Przesunięte'),
                          ('REMOVED','Usunięte'),('UNCERTAIN','Niepewne')]:
            cb=QCheckBox(name);cb.setChecked(True)
            cb.toggled.connect(self.refresh_legend)
            self.legend_filters[code]=cb;legend.addWidget(cb)
        legend.addStretch();v.addLayout(legend)""")
change("self.mass_go=_button('◉  Oblicz masy',self.start_mass,'primary');row.addWidget(self.mass_go)",
       """self.mass_go=_button('◉  Oblicz masy',self.start_mass,'primary');row.addWidget(self.mass_go)
        self.mass_cancel=_button('Anuluj',self.cancel);self.mass_cancel.setEnabled(False);row.addWidget(self.mass_cancel)""")
change("v.addWidget(p)\n        self.mass_summary=",
       """v.addWidget(p)
        self.mass_progress=QProgressBar()
        self.mass_progress.setRange(0,100);self.mass_progress.setValue(0)
        self.mass_progress.setFormat('Gotowy  •  %p%')
        v.addWidget(self.mass_progress)
        self.mass_status=_label('Wybierz STEP i kliknij „Oblicz masy”.','muted')
        v.addWidget(self.mass_status)
        correction=QHBoxLayout()
        self.mass_edit=_button('Edytuj ilości',self.toggle_mass_edit,'subtle')
        self.mass_export=_button('Zapisz skorygowane CSV',self.export_corrected_mass,'subtle')
        self.mass_export.setEnabled(False)
        correction.addWidget(self.mass_edit);correction.addWidget(self.mass_export)
        correction.addStretch();v.addLayout(correction)
        self.mass_summary=""")
change("self.mass_table.setAlternatingRowColors(True);self.mass_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)",
       """self.mass_table.setAlternatingRowColors(True);self.mass_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.mass_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.mass_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.mass_editing=False
        self.mass_table.cellChanged.connect(self._mass_cell_changed)""")
start = s.index("        self.color_buttons={}")
end = s.index("        v.addWidget(p);v.addStretch()", start)
s = s[:start] + """        self.color_buttons={};self.color_labels={}
        grid=QGridLayout();grid.setHorizontalSpacing(12);grid.setVerticalSpacing(10)
        for idx,(status,name) in enumerate([
                ('SAME','Bez zmian'),('CHANGED','Zmienione'),('ADDED','Nowe'),
                ('MOVED','Przesunięte'),('REMOVED','Usunięte'),('UNCERTAIN','Do sprawdzenia')]):
            card=QFrame();card.setObjectName('colorcard')
            line=QHBoxLayout(card);line.setContentsMargins(12,8,12,8)
            swatch=QLabel('');swatch.setFixedSize(27,27);line.addWidget(swatch)
            labels=QVBoxLayout();labels.addWidget(_label(name))
            hex_label=_label('','muted');labels.addWidget(hex_label)
            line.addLayout(labels,1)
            btn=_button('Wybierz',lambda checked=False,k=status:self.change_color(k),'subtle')
            line.addWidget(btn)
            self.color_buttons[status]=swatch;self.color_labels[status]=hex_label
            grid.addWidget(card,idx//2,idx%2)
        pl.addLayout(grid)
        pl.addWidget(_button('Przywróć kolory domyślne',self.reset_colors,'subtle'))
""" + s[end:]
change("for key,b in self.color_buttons.items():\n            color=self.settings['kolory'].get(key,COLORS[key]);b.setStyleSheet(f'border-left:11px solid {color};')",
       """for key,b in self.color_buttons.items():
            color=self.settings['kolory'].get(key,COLORS[key])
            b.setStyleSheet(f'background:{color};border:1px solid #808693;border-radius:8px;')
            self.color_labels[key].setText(color.upper())""")
change("Wersja 3.7", "Wersja 3.8")
change("self.worker_kind=kind;self.worker_dir=folder;self.worker_position=0",
       "self.worker_kind=kind;self.worker_dir=folder;self.worker_position=0")
change("self.btn_cancel.setEnabled(True)\n        self.log.clear()",
       """self.btn_cancel.setEnabled(True);self.mass_cancel.setEnabled(True)
        self.progress.setFormat('Przetwarzanie…')
        if kind=='mass':
            self.mass_progress.setRange(0,0)
            self.mass_status.setText('Wczytywanie geometrii STEP…')
        self.log.clear()""")
change("self.log.append(msg);self.status.setText(msg)\n                if self.worker_kind=='mesh':self.viewer_message.setText(msg)",
       """if not msg.startswith('Siatka 3D:'):self.log.append(msg)
                self.status.setText(msg)
                if self.worker_kind=='mesh':self.viewer_message.setText(msg)
                if self.worker_kind=='mass':self.mass_status.setText(msg)""")
change("self.progress.setRange(0,100);self.progress.setValue(100 if code==0 else 0)",
       """self.progress.setRange(0,100);self.progress.setValue(100 if code==0 else 0)
        self.progress.setFormat('Ukończono' if code==0 else 'Błąd')
        self.mass_progress.setRange(0,100)
        self.mass_progress.setValue(100 if code==0 else 0)
        self.mass_progress.setFormat('Ukończono' if code==0 else 'Błąd')
        self.mass_cancel.setEnabled(False)
        if self.worker_kind=='mass':
            self.mass_status.setText('Ukończono' if code==0 else 'Błąd obliczania mas')""")
change("self.process.kill();self.status.setText('Przerwano — proces obliczeniowy zatrzymany')",
       """self.process.kill();self.status.setText('Przerwano — proces obliczeniowy zatrzymany')
            self.mass_status.setText('Anulowano analizę masy')""")
change("self.mass_table.setRowCount(len(rows))\n        keys=",
       "self.mass_table.blockSignals(True)\n        self.mass_table.setRowCount(len(rows))\n        keys=")
change("for j,k in enumerate(keys):self.mass_table.setItem(i,j,QTableWidgetItem(row.get(k,'')))",
       """for j,k in enumerate(keys):
                item=QTableWidgetItem(row.get(k,''))
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                if j:item.setTextAlignment(Qt.AlignRight|Qt.AlignVCenter)
                self.mass_table.setItem(i,j,item)
        self.mass_table.blockSignals(False)""")
anchor="    def open_result(self,name):"
insert="""    def toggle_mass_edit(self):
        self.mass_editing=not self.mass_editing
        self.mass_table.setEditTriggers(QAbstractItemView.DoubleClicked if self.mass_editing else QAbstractItemView.NoEditTriggers)
        self.mass_edit.setText('Zakończ edycję ilości' if self.mass_editing else 'Edytuj ilości')
        self.mass_export.setEnabled(self.mass_editing)
        for row in range(self.mass_table.rowCount()):
            for col in range(self.mass_table.columnCount()):
                cell=self.mass_table.item(row,col)
                if cell:
                    flags=cell.flags()
                    cell.setFlags(flags | Qt.ItemIsEditable if col==1 and self.mass_editing else flags & ~Qt.ItemIsEditable)

    def _mass_cell_changed(self,row,col):
        if col!=1 or not self.mass_editing:return
        try:
            count=int(self.mass_table.item(row,1).text().strip())
            if not 0<=count<=1000000:raise ValueError()
            unit=float(self.mass_table.item(row,3).text().replace(',','.'))
        except (ValueError,AttributeError):
            self.mass_status.setText('Nieprawidłowa ilość — wpisz liczbę od 0 do 1 000 000')
            return
        self.mass_table.blockSignals(True)
        self.mass_table.item(row,4).setText(f'{unit*count:.5f}'.replace('.',','))
        self.mass_table.blockSignals(False)
        total=0.
        for row in range(self.mass_table.rowCount()):
            try:total+=float(self.mass_table.item(row,4).text().replace(',','.'))
            except (ValueError,AttributeError):pass
        self.mass_summary.setText(f'Korekta ilości (bez zmian STEP) • Masa łączna: {total:.3f} kg'.replace('.',','))

    def export_corrected_mass(self):
        path,_=QFileDialog.getSaveFileName(self,'Zapisz skorygowane zestawienie',
                str(self.worker_dir/'MASY_CZESCI_SKORYGOWANE.csv'),'CSV (*.csv)')
        if not path:return
        import csv
        with open(path,'w',encoding='utf-8-sig',newline='') as f:
            writer=csv.writer(f,delimiter=';')
            writer.writerow([self.mass_table.horizontalHeaderItem(i).text() for i in range(self.mass_table.columnCount())])
            for row in range(self.mass_table.rowCount()):
                writer.writerow([self.mass_table.item(row,col).text() for col in range(self.mass_table.columnCount())])
        self.mass_status.setText('Zapisano skorygowany CSV — oryginalny BOM pozostawiono bez zmian')

    def fit_model(self):
        if self.viewer_ready:
            self.renderer.ResetCamera()
            self.vtk_widget.GetRenderWindow().Render()

    def refresh_legend(self,*_):
        if not self.viewer_ready:return
        for key,actors in self.viewer_actors.items():
            visible=any(checkbox.isChecked() for status,checkbox in self.legend_filters.items()
                 if self.settings['kolory'].get(status,COLORS[status]).lower()==key)
            for actor in actors:actor.SetVisibility(visible)
        self.vtk_widget.GetRenderWindow().Render()

"""
change(anchor,insert+anchor)
change("self.renderer.RemoveAllViewProps()\n            groups={}",
       "self.renderer.RemoveAllViewProps()\n            self.viewer_actors={}\n            groups={}")
change("self.renderer.AddActor(actor)\n            self.renderer.ResetCamera()",
       """self.renderer.AddActor(actor)
                hex_color='#'+''.join(f'{min(255,max(0,round(v*255))):02X}' for v in rgb)
                self.viewer_actors.setdefault(hex_color.lower(),[]).append(actor)
            self.refresh_legend()
            self.renderer.ResetCamera()""")
p.write_text(s,encoding="utf-8")
mesh=root/'dsac29/mesh_v37.py'
t=mesh.read_text(encoding="utf-8")
t=t.replace("solid_count%25==0","solid_count%100==0")
mesh.write_text(t,encoding="utf-8")
io=root/'dsac29/step_io.py'
t=io.read_text(encoding='utf-8')
t=t.replace("'pokolorowane_powierzchnie':colored_faces,",
     "'pokolorowane_powierzchnie':colored_faces,\n            'brak_kolorow_powierzchni':not bool(colored_faces),")
io.write_text(t,encoding='utf-8')
(root/'README_V38.txt').write_text(
 "DS Compare V3.8 — pomarańczowy motyw, legenda 3D, progress mas, edycja ilości i CSV.\\n"
 "STEP przechowuje kolory, ale wyświetlanie w ZW3D wymaga osobnego testu.\\n"
 "Automatycznego zapisu Z3 nie udostępniamy bez sprawdzonego API ZW3D 2019.\\n"
 "Autor: Szymczyk Damian.\\n",encoding='utf-8')
print("DS Compare V3.8 patch applied")
