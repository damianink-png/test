"""Independent GUI convenience patch; no geometry or comparison logic changed."""
from pathlib import Path
import sys

def apply(root):
    path=Path(root)/"src/openassembly/ui.py"
    s=path.read_text(encoding="utf-8")
    old="        self.folder=ttk.Button(toolbar,text='Otwórz katalog',state='disabled',command=lambda:self.open('.'));self.folder.pack(side='left')"
    new=old+"\n        self.step_open=ttk.Button(toolbar,text='Otwórz STEP',state='disabled',command=lambda:self.open('POROWNANIE_KOLORY.step'));self.step_open.pack(side='left',padx=8)"
    assert s.count(old)==1,"UI toolbar anchor changed"
    s=s.replace(old,new,1)
    old="        self.go.configure(state='disabled');self.report.configure(state='disabled');self.folder.configure(state='disabled')"
    new=old+";self.step_open.configure(state='disabled')"
    assert s.count(old)==1
    s=s.replace(old,new,1)
    old="                    self.folder.configure(state='normal')"
    new=old+"\n                    if (Path(self.out.get())/'POROWNANIE_KOLORY.step').is_file():self.step_open.configure(state='normal')"
    assert s.count(old)==1
    s=s.replace(old,new,1)
    path.write_text(s,encoding="utf-8")
    print("Independent OpenAssembly GUI: Open STEP button installed")

if __name__=="__main__":
    apply(sys.argv[1])
