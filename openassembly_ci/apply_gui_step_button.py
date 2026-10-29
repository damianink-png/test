"""Independent GUI convenience actions; never changes matching or CAD geometry."""
from pathlib import Path
import sys

def replace_once(s, old, new):
    assert s.count(old) == 1, f"Expected one GUI anchor, found {s.count(old)}"
    return s.replace(old, new, 1)

def apply(root):
    path = Path(root) / "src/openassembly/ui.py"
    s = path.read_text(encoding="utf-8")
    anchor = "        self.folder=ttk.Button(toolbar,text='Otwórz katalog',state='disabled',command=lambda:self.open('.'));self.folder.pack(side='left')"
    addition = (
        "\n        self.step_open=ttk.Button(toolbar,text='Otwórz STEP',state='disabled',command=lambda:self.open('POROWNANIE_KOLORY.step'));self.step_open.pack(side='left',padx=8)"
        "\n        self.bom_open=ttk.Button(toolbar,text='Otwórz BOM',state='disabled',command=lambda:self.open('BOM_PRZEGLAD.html'));self.bom_open.pack(side='left')"
    )
    s = replace_once(s, anchor, anchor + addition)
    anchor = "        self.go.configure(state='disabled');self.report.configure(state='disabled');self.folder.configure(state='disabled')"
    s = replace_once(s, anchor, anchor + ";self.step_open.configure(state='disabled');self.bom_open.configure(state='disabled')")
    anchor = "                    self.folder.configure(state='normal')"
    s = replace_once(s, anchor, anchor +
        "\n                    if (Path(self.out.get())/'POROWNANIE_KOLORY.step').is_file():self.step_open.configure(state='normal')" +
        "\n                    if (Path(self.out.get())/'BOM_PRZEGLAD.html').is_file():self.bom_open.configure(state='normal')")
    path.write_text(s, encoding="utf-8")
    print("OpenAssembly GUI STEP and expandable BOM actions installed")

if __name__ == "__main__":
    apply(sys.argv[1])
