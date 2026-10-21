# DS Compare R11.18 - Qt theme/dialog and ZW3D 2019 macro launch integration.
# Runs on restored 11.17 source before compiling PyInstaller.
from __future__ import annotations
import os,json
from pathlib import Path
root=Path(os.environ["DS_COMPARE_SOURCE"])
g=root/"dsac29"/"gui_modern.py"
text=g.read_text(encoding="utf-8")
def change(old,new,n=1):
    global text
    assert text.count(old)>=n, "Cannot find expected R11.17 GUI anchor: "+repr(old[:90])
    text=text.replace(old,new,n)

# Child checkable controls should not inherit the global dark QWidget background.
change(" QCheckBox{spacing:8px;padding:3px;}",
       " QCheckBox,QRadioButton{spacing:8px;padding:3px;background:transparent;color:INK;}\n QCheckBox:checked,QCheckBox:disabled,QRadioButton:checked{background:transparent;}")
# Add an actual ZW3D macro generator under Preferences, without requiring a separately distributed DLL.
change("  self._theme_select=QComboBox();self._theme_select.addItems(['Ciemny','Jasny'])",
       "  self.zw3d_macro_button=QPushButton('Utwórz makro startowe do ZW3D 2019')\n"
       "  self.zw3d_macro_button.setToolTip('Tworzy plik .mac, który uruchamia ten DSCompare.exe z ZW3D. Makro należy podłączyć w ZW3D.')\n"
       "  self.zw3d_macro_button.clicked.connect(self.create_zw3d_macro)\n"
       "  gp.addRow('Integracja ZW3D',self.zw3d_macro_button)\n"
       "  self._theme_select=QComboBox();self._theme_select.addItems(['Ciemny','Jasny'])")
anchor="  def apply_theme(self,name):\n"
assert anchor in text
fn="""  def create_zw3d_macro(self):
   from .zw3d_launcher import create_macro
   try:
    path=create_macro()
    QMessageBox.information(self,'Uruchamianie z ZW3D 2019',
      'Przygotowano makro:\\n'+str(path)+
      '\\n\\nWczytaj ten plik .mac w menedżerze makr ZW3D 2019 i przypisz do przycisku. '+
      'Makro wywołuje aktualną lokalizację DSCompare.exe. Po przeniesieniu EXE utwórz makro ponownie. '+
      'Działanie w ZW3D 2019 wymaga sprawdzenia na zainstalowanym programie.')
    if os.name=='nt':os.startfile(str(path.parent))
   except (OSError,ValueError,RuntimeError) as exc:
    QMessageBox.warning(self,'Integracja ZW3D','Nie udało się utworzyć makra: '+str(exc))
"""
text=text.replace(anchor,fn+anchor,1)
g.write_text(text,encoding="utf-8")

# Color dialog: protect last status swatch from footer at 125/150/200% DPI.
p=root/"dsac29"/"gui46.py"
t=p.read_text("utf8")
old="   dlg.setMinimumWidth(465)"
assert old in t
t=t.replace(old,"   dlg.setMinimumWidth(510);dlg.setMinimumHeight(435);dlg.resize(580,535)\n   dlg.setStyleSheet(self.styleSheet())",1)
old="   root=QVBoxLayout(dlg)"
assert old in t
t=t.replace(old,"   root=QVBoxLayout(dlg);root.setSpacing(12);root.setContentsMargins(18,18,18,18)",1)
old="   root.addLayout(grid)"
assert old in t
new="""   from PySide6.QtWidgets import QScrollArea,QWidget
   grid_host=QWidget(dlg)
   grid.setContentsMargins(4,4,4,4)
   grid.setVerticalSpacing(12)
   grid_host.setLayout(grid)
   scroll=QScrollArea(dlg)
   scroll.setWidgetResizable(True)
   scroll.setFrameShape(QFrame.NoFrame)
   scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
   scroll.setWidget(grid_host)
   root.addWidget(scroll,1)
"""
t=t.replace(old,new,1)
old="   actions=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel)"
assert old in t
t=t.replace(old,"   actions=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel)\n"
                "   actions.button(QDialogButtonBox.Ok).setText('Zapisz')\n"
                "   actions.button(QDialogButtonBox.Cancel).setText('Anuluj')",1)
p.write_text(t,encoding="utf8")

module=root/"dsac29"/"zw3d_launcher.py"
module.write_text('''"""Prepare optional ZW3D macro that opens standalone DS Compare EXE.

No native ZW3D API calls; ZW3D 2019 macro execution needs user verification.
The user receives only one EXE, which creates the .mac locally when asked.
"""
from __future__ import annotations
import os
from pathlib import Path
import sys

MACRO_NAME = "DS_COMPARE_START.mac"

def create_macro(executable=None, output_dir=None):
    exe=Path(executable or sys.executable).resolve()
    if not exe.is_file() or exe.suffix.casefold() != ".exe":
        raise ValueError("Wymagany istniejący plik programu DSCompare.exe")
    if any(x in str(exe) for x in ('"', "\\\\n", "\\\\r")):
        raise ValueError("Niepoprawna ścieżka do programu")
    target=Path(output_dir) if output_dir is not None else (
        Path(os.environ.get("APPDATA") or (Path.home()/"AppData"/"Roaming"))
        /"DSCompare"/"ZW3D2019")
    target.mkdir(parents=True,exist_ok=True)
    # ZW3D $tm=more file-open macro technique reported by community;
    # this is not guaranteed to be accepted by every ZW3D 2019 installation.
    data=('MACRO main\\\\n'
          '[vxSend,"$tm=more"]\\\\n'
          'BUFFER\\\\n'
          'BUFFER\\\\n'
          '[vxSend,"'+str(exe)+'"]\\\\n'
          'ENDBUFFER\\\\n'
          'ENDBUFFER\\\\n'
          'ENDMACRO\\\\n')
    dest=target/MACRO_NAME
    dest.write_bytes(data.encode("cp1250",errors="strict"))
    return dest
'''.replace('\\\\n','\\n'),encoding="utf8")
# Fix literal macro escapes: source text has escaped backslash-n in string literals.
assert "def create_macro(" in module.read_text("utf8")
version=root/"VERSION.txt"
version.write_text("R11.18\\n",encoding="utf8")
build=root/"build_info.json"
if build.is_file():
    data=json.loads(build.read_text("utf8"))
    data["version"]="R11.18 · GitHub "+os.environ.get("GITHUB_SHA","")[:8]
    data["zw3d_launcher"]="Macro VX via $tm=more, native ZW3D 2019 not verified"
    build.write_text(json.dumps(data,ensure_ascii=False),encoding="utf8")
print("DSCompare R11.18: dialog scroll/footer, Polish cancel, transparent checkbox styles, ZW3D macro helper installed.")
