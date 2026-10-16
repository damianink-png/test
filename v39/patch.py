from pathlib import Path
p=Path("dsac29/gui_qt37.py")
s=p.read_text(encoding="utf-8")
def change(a,b):
 global s
 if a not in s:
  # Differences between released V3.8 and local prototype are handled below.
  return
 s=s.replace(a,b)
change("'MOVED':'#B47BDD'","'MOVED':'#6659D4'")
change("'ADDED':'#4985EE'","'ADDED':'#6659D4'")
change("'UNCERTAIN':'#99A3B2'","'UNCERTAIN':'#6659D4'")
change("self.settings.setdefault('kolory',dict(COLORS))","self.settings.setdefault('kolory',dict(COLORS))\n        self._sync_status_colors()")
change("    def build_sidebar(self):","""    def _sync_status_colors(self):
        p=self.settings['kolory']
        for key in ('SAME','CHANGED','REMOVED'):
            if not isinstance(p.get(key),str) or not QColor(p[key]).isValid():
                p[key]=COLORS[key]
        p['RENAMED']=p['SAME']
        for key in ('MOVED','ADDED','UNCERTAIN'):p[key]=p['CHANGED']

    def build_sidebar(self):""")
change("('CHANGED','Zmienione','#6659D4'),('ADDED','Nowe','#4B80EC')","('CHANGED','Nowe / zmienione','#6659D4')")
change("('CHANGED','Zmienione'),('ADDED','Nowe'),('MOVED','Przesunięte'),('REMOVED','Usunięte'),('UNCERTAIN','Do sprawdzenia')","('CHANGED','Nowe / zmienione'),('REMOVED','Usunięte')")
change("('CHANGED','Zmienione'),('ADDED','Nowe'),('MOVED','Przesunięte'),('REMOVED','Usunięte')","('CHANGED','Nowe / zmienione'),('REMOVED','Usunięte')")
change("bar.addStretch();bar.addWidget(_button('⇄ Zamień A i B',self.swap_models))","bar.addStretch();bar.addWidget(_button('📁  Otwórz folder wyników',self.open_folder,'subtle'))\n        bar.addWidget(_button('⇄ Zamień A i B',self.swap_models))")
change("self.progress.setFormat('Gotowy  •  %p%')","self.progress.setTextVisible(False)")
change("self.mass_progress.setFormat('Gotowy  •  %p%')","self.mass_progress.setTextVisible(False)")
change("self.viewer_model.addItems(['Wynik kolorowy','Model A','Model B','Wybierz STEP…'])","self.viewer_model.addItems(['Własny STEP','Wynik kolorowy','Model A','Model B'])")
change("        v.addLayout(toolbar)\n        self.viewer_legend=QHBoxLayout()","""        v.addLayout(toolbar)
        row=QHBoxLayout()
        row.addWidget(_label('Własny STEP:','muted'))
        self.viewer_custom_path=QLineEdit(self.settings.get('ostatni_podglad',''))
        self.viewer_custom_path.setPlaceholderText('Dowolny STEP/STP do podglądu, bez porównania')
        self.viewer_custom_path.textEdited.connect(lambda _:self.viewer_model.setCurrentIndex(0))
        row.addWidget(self.viewer_custom_path,1)
        row.addWidget(_button('Przeglądaj STEP…',self.choose_viewer_file,'subtle'))
        v.addLayout(row)
        self.viewer_progress=QProgressBar()
        self.viewer_progress.setTextVisible(False)
        self.viewer_progress.hide()
        v.addWidget(self.viewer_progress)
        self.viewer_legend=QHBoxLayout()""")
change("    def start_mesh(self):","""    def choose_viewer_file(self):
        start=self.viewer_custom_path.text().strip() or str(Path.home())
        selected=QFileDialog.getOpenFileName(self,'Wybierz dowolny STEP',start,'STEP (*.step *.stp)')[0]
        if selected:
            self.viewer_custom_path.setText(selected)
            self.viewer_model.setCurrentIndex(0)
            self.settings['ostatni_podglad']=selected
            save_settings(self.settings)

    def start_mesh(self):""")
change("""if idx==0:step=self.result_dir/'POROWNANIE_KOLORY.step'
        elif idx==1:step=Path(self.file_a.text())
        elif idx==2:step=Path(self.file_b.text())
        else:step=Path(QFileDialog.getOpenFileName(self,'Wskaż plik STEP','','STEP (*.step *.stp)')[0])""","""if idx==0:
            text=self.viewer_custom_path.text().strip()
            if not text:
                self.choose_viewer_file()
                text=self.viewer_custom_path.text().strip()
                if not text:return
            step=Path(text)
        elif idx==1:step=self.result_dir/'POROWNANIE_KOLORY.step'
        elif idx==2:step=Path(self.file_a.text())
        else:step=Path(self.file_b.text())""")
change("folder=self.result_dir/'_sceny_3d'/identifier","folder=_settings_path().parent/'Cache_3D'/identifier")
change("self.status.setText('Trwa zadanie: '+kind);self.progress.setRange(0,0)","""self.status.setText({'compare':'Porównywanie B-Rep…','mass':'Obliczanie mas…','mesh':'Tworzenie podglądu 3D…'}.get(kind,kind))
        if kind=='compare':self.progress.setRange(0,0)
        if kind=='mesh':
            self.viewer_progress.show()
            self.viewer_progress.setRange(0,0)""")
change("self.progress.setFormat('Przetwarzanie…');self.mass_progress.setFormat('Przetwarzanie…')","self.progress.setTextVisible(False);self.mass_progress.setTextVisible(False)")
change("""self.progress.setRange(0,100);self.progress.setValue(100 if code==0 else 0)
        self.progress.setFormat('Ukończono' if code==0 else 'Niepowodzenie')
        self.mass_progress.setRange(0,100);self.mass_progress.setValue(100 if code==0 else 0)
        self.mass_progress.setFormat('Ukończono' if code==0 else 'Niepowodzenie')""","""if self.worker_kind=='compare':
            self.progress.setRange(0,100);self.progress.setValue(100 if code==0 else 0)
        if self.worker_kind=='mass':
            self.mass_progress.setRange(0,100);self.mass_progress.setValue(100 if code==0 else 0)
        if self.worker_kind=='mesh':
            self.viewer_progress.hide()
            self.viewer_progress.setRange(0,100)""")
change("""('CHANGED',statuses.get('CHANGED',0)+statuses.get('MOVED',0)),
                          ('ADDED',statuses.get('ADDED',0)),('REMOVED',statuses.get('REMOVED',0))""","""('CHANGED',sum(statuses.get(x,0) for x in ('CHANGED','MOVED','ADDED','UNCERTAIN'))),
                          ('REMOVED',statuses.get('REMOVED',0))""")
change("lbl.setText(str(statuses.get(key,0)+(statuses.get('RENAMED',0) if key=='SAME' else 0)))","""value=(statuses.get('SAME',0)+statuses.get('RENAMED',0) if key=='SAME'
                   else sum(statuses.get(x,0) for x in ('CHANGED','MOVED','ADDED','UNCERTAIN')) if key=='CHANGED'
                   else statuses.get('REMOVED',0))
            lbl.setText(str(value))""")
change("if key=='SAME':self.settings['kolory']['RENAMED']=color.name().upper()","self._sync_status_colors()")
change("self.settings['kolory']=dict(COLORS);self.update_color_buttons()","self.settings['kolory']=dict(COLORS);self._sync_status_colors();self.update_color_buttons()")
change("Wersja 3.8","Wersja 3.9")
change("""active=any(v.isChecked() for k,v in self.legend_filters.items()
                       if self.settings['kolory'].get(k,COLORS[k]).lower()==key)
            if key.startswith('rgb:'):active=True""","""matching=[v for k,v in self.legend_filters.items()
                      if self.settings['kolory'].get(k,COLORS[k]).lower()==key]
            active=any(v.isChecked() for v in matching) if matching else True""")
change("    def open_folder(self):QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.result_dir)))","""    def open_folder(self):
        folder=(Path(self.worker_dir) if self.worker_kind=='compare' and self.process
                and self.process.state()!=QProcess.NotRunning
                else Path(self.file_out.text().strip() or str(self.result_dir)))
        try:folder.mkdir(parents=True,exist_ok=True)
        except OSError as exc:
            QMessageBox.warning(self,'Folder wyników',str(exc));return
        if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder))):
            QMessageBox.warning(self,'Folder wyników','Nie można otworzyć folderu: '+str(folder))""")
# V3.8 release patch leaves a few multiline layouts from its V3.7 base.
import re
s=re.sub(r"for k,name,color in \[\('SAME','Bez zmian'.*?\)\]:",
         "for k,name,color in [('SAME','Bez zmian','#26AD42'),('CHANGED','Nowe / zmienione','#6659D4'),('REMOVED','Usunięte','#E68F3D')]:",s,count=1)
s=re.sub(r"for code,name in \[\('SAME','Bez zmian'\).*?\]:\n            cb=QCheckBox",
         "for code,name in [('SAME','Bez zmian'),('CHANGED','Nowe / zmienione'),('REMOVED','Usunięte')]:\n            cb=QCheckBox",s,count=1,flags=re.S)
s=re.sub(r"for idx,\(status,name\) in enumerate\(\[\s*\('SAME','Bez zmian'\).*?\]\):",
         "for idx,(status,name) in enumerate([('SAME','Bez zmian'),('CHANGED','Nowe / zmienione'),('REMOVED','Usunięte')]):",s,count=1,flags=re.S)
# V3.8 source sometimes spells QProgressBar setup differently. Remove all placeholder percentages.
s=s.replace("self.progress.setFormat('Gotowy  •  %p%')","self.progress.setTextVisible(False)")
s=s.replace("self.mass_progress.setFormat('Gotowy  •  %p%')","self.mass_progress.setTextVisible(False)")
s=s.replace("self.progress.setFormat('Przetwarzanie…')","self.progress.setTextVisible(False)")
s=s.replace("self.mass_progress.setFormat('Przetwarzanie…')","self.mass_progress.setTextVisible(False)")
# Never hide imported neutral STEP mesh if it does not match a status color.
s=s.replace("""visible=any(checkbox.isChecked() for status,checkbox in self.legend_filters.items()
                 if self.settings['kolory'].get(status,COLORS[status]).lower()==key)""",
"""match=[v for kind,v in self.legend_filters.items()
                    if self.settings['kolory'].get(kind,COLORS[kind]).lower()==key]
            visible=any(v.isChecked() for v in match) if match else True""")
# Verify that all required UI controls were injected.
for required in ('viewer_custom_path=QLineEdit','def choose_viewer_file(self):',
                 'Otwórz folder wyników','viewer_progress=QProgressBar'):
    if required not in s:raise RuntimeError("V3.9 failed to provide "+required)

p.write_text(s,encoding="utf-8")
p=Path("dsac29/step_io.py");s=p.read_text(encoding="utf-8")
s=s.replace("'UNCERTAIN':(0.6,0.64,0.7)","'UNCERTAIN':(0.40,0.35,0.83)")
p.write_text(s,encoding="utf-8")
p=Path("dsac29/report.py");s=p.read_text(encoding="utf-8")
s=s.replace('<span><i class="dot" style="background:{hex_color("UNCERTAIN")}"></i>Niepewne</span>','')
p.write_text(s,encoding="utf-8")
p=Path("tests/test_v38_ui_static.py");s=p.read_text(encoding="utf-8")
s=s.replace('len(w.legend_filters)==6','len(w.legend_filters)==3')
p.write_text(s,encoding="utf-8")
Path("README_V39.txt").write_text("DS Compare V3.9. Podgląd 3D otwiera dowolny STEP bez porównania. Trzy kolory; raporty zachowują szczegółowe zmiany. Paski postępu bez sztucznego procentu. Folder wyników na ekranie porównania. Eksport STEP w rzeczywistych dużych złożeniach nadal wymaga sprawdzenia w ZW3D. DLL eksperymentalna. Autor: Szymczyk Damian.",encoding="utf-8")
