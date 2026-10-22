"""R11.31 GUI: remove alignment checkbox, show explicit Align/Cancel prompt."""
from pathlib import Path
import os,json
root=Path(os.environ['DS_COMPARE_SOURCE'])
p=root/"dsac29/gui45.py"
s=p.read_text(encoding="utf8")
old="            if self.align.isChecked():args+=['--align']"
assert s.count(old)==1
s=s.replace(old,"            args+=['--align-auto']  # every comparison checks coordinates before STEP/BOM",1)
anchor="    def poll(self):"
assert s.count(anchor)==1
new="""    def _coordinate_prompt(self):
        if self.task!='compare' or self.process is None or self.current_folder is None:return
        request=self.current_folder/'_WYROWNANIE_PYTANIE.json'
        if not request.is_file():return
        try:data=json.loads(request.read_text(encoding='utf8'))
        except (OSError,ValueError):return
        token=str(data.get('token',''))
        if not token or token==getattr(self,'_last_coordinate_token',None):return
        self._last_coordinate_token=token
        delta=data.get('translation_mm',[0,0,0])
        try:translation=', '.join(f'{float(x):+.2f}' for x in delta)
        except (TypeError,ValueError):translation='nieznane'
        self.active_log.appendPlainText('Wykryto różnicę położenia: oczekiwanie na potwierdzenie.')
        box=QMessageBox(self)
        box.setWindowTitle('Wykryto przesunięcie modeli')
        box.setIcon(QMessageBox.Question)
        box.setText('Modele nie są ustawione w tym samym układzie współrzędnych.')
        box.setInformativeText(
            'Program wyznaczył przesunięcie modelu B względem A [mm]: '
            +translation+'\\n'
            'Potwierdź wyrównanie B do A przed porównaniem geometrii i kolorowaniem STEP. '
            'Jeśli to nie jest zamierzone przesunięcie całego złożenia, wybierz Anuluj.')
        confirm=box.addButton('Wyrównaj modele',QMessageBox.AcceptRole)
        box.addButton('Anuluj',QMessageBox.RejectRole)
        box.setDefaultButton(confirm)
        box.exec()
        selected='align' if box.clickedButton() is confirm else 'cancel'
        if selected=='cancel':self.was_cancelled=True
        response={'token':token,'decision':selected}
        try:
            dest=self.current_folder/'_WYROWNANIE_ODPOWIEDZ.json'
            temp=self.current_folder/'_WYROWNANIE_ODPOWIEDZ.tmp'
            temp.write_text(json.dumps(response,ensure_ascii=False),encoding='utf8')
            temp.replace(dest)
        except OSError as exc:
            self.active_log.appendPlainText('Nie można przekazać decyzji: '+str(exc))
            if self.process:self.cancel()

"""
s=s.replace(anchor,new+anchor,1)
s=s.replace("    def poll(self):\n        file=self.current_folder/'_POSTEP_V37.jsonl'",
            "    def poll(self):\n        self._coordinate_prompt()\n        if self.current_folder is None:return\n        file=self.current_folder/'_POSTEP_V37.jsonl'",1)
p.write_text(s,encoding='utf8')

p=root/"dsac29/gui_modern.py"
s=p.read_text(encoding='utf8')
old="  cp.addRow(self.align)"
assert s.count(old)==1
s=s.replace(old,"  # Alignment is automatic for all comparisons; no manual setting.\n  self.align.setChecked(False)\n  self.align.hide()\n  info=QLabel('Po imporcie program sam sprawdza położenie modeli. Jeśli potrzeba wyrównania, zapyta o zgodę.')\n  info.setObjectName('muted');info.setWordWrap(True);cp.addRow(info)",1)
p.write_text(s,encoding="utf8")

(root/"VERSION.txt").write_text("R11.31\\n",encoding="utf8")
m=root/"build_info.json"
if m.exists():
 d=json.loads(m.read_text(encoding="utf8"))
 d["version"]="R11.31 · GitHub "+os.environ.get("GITHUB_SHA","")[:8]
 d["ui"]="automatic B-to-A registration question, no manual align checkbox"
 m.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding="utf8")
print("R11.31 UI: auto alignment and explicit user permission before actual comparison, legacy option hidden")
