"""DS Compare R11.20: restore light-theme visual depth, pill tabs and legible toggles.

The R11.19 XCAF grouped STEP exporter is deliberately unchanged here: do not
reintroduce the flat version and do not claim a ZW3D 2019 importer validation.
"""
from pathlib import Path
import os
import json

root=Path(os.environ["DS_COMPARE_SOURCE"])
file=root/"dsac29/gui_modern.py"
source=file.read_text(encoding="utf8")

def once(before,after):
    global source
    found=source.count(before)
    if found!=1:
        raise RuntimeError(f"Unexpected R11.19 Qt stylesheet version: {before[:80]!r}; found {found}")
    source=source.replace(before,after,1)

once("DARK={'bg':'#0B1017','surface':'#131B25','field':'#19232F','hover':'#223246','line':'#293646','ink':'#F3F7FD','muted':'#9AA8BB','accent':'#1677F7','soft':'#182D4B'}",
     "DARK={'bg':'#0B1119','surface':'#151D28','field':'#202B39','hover':'#283A50','line':'#344353','ink':'#F5F7FC','muted':'#ACB9CB','accent':'#1677F7','soft':'#183459'}")
once("LIGHT={'bg':'#F5F7FB','surface':'#FFFFFF','field':'#F5F7FA','hover':'#EAF2FE','line':'#DBE2EC','ink':'#162033','muted':'#64748B','accent':'#1677F7','soft':'#E3EEFF'}",
     "LIGHT={'bg':'#EBF0F7','surface':'#FFFFFF','field':'#F2F6FC','hover':'#E8F2FF','line':'#CED8E6','ink':'#162235','muted':'#65768C','accent':'#1677F7','soft':'#E6F0FF'}")
once(" QFrame#topbar{border:0;border-bottom:1px solid LINE;background:SURFACE;border-radius:0;}",
     " QFrame#topbar{border:0;border-bottom:1px solid LINE;background:SURFACE;border-radius:0;}"
     "\n QFrame#topbar QLabel{background:transparent;}"
     "\n QFrame#settings-card QLabel{background:transparent;}"
     "\n QFrame#settings-card,QFrame#file-card,QFrame#surface,QFrame#success{border:1px solid LINE;background:SURFACE;border-radius:15px;}")
# Theme-aware cards and the page background intentionally use different fills.
# Rounded nav chips replace old underlined flat-tabs; no special-casing screen/DPI.
once(" QPushButton#nav{background:transparent;border:0;border-bottom:2px solid transparent;border-radius:0;padding:10px 16px;min-height:26px;}",
     " QPushButton#nav{background:FIELD;border:1px solid LINE;border-radius:11px;padding:10px 17px;min-height:27px;}")
once(" QPushButton#nav:hover{background:HOVER;}",
     " QPushButton#nav:hover{background:HOVER;border:1px solid ACCENT;}")
once(" QPushButton#nav:checked{color:ACCENT;border-bottom:2px solid ACCENT;background:SOFT;}",
     " QPushButton#nav:checked{color:ACCENT;border:1px solid ACCENT;border-radius:11px;background:SOFT;font-weight:650;}")
# Explicit styled indicator is needed: Qt native checkmarks become effectively
# invisible on some Windows DPI/theme combinations when a global QSS is applied.
once(" QCheckBox,QRadioButton{spacing:8px;padding:3px;background:transparent;color:INK;}",
     " QCheckBox,QRadioButton{spacing:9px;padding:4px 2px;background:transparent;color:INK;}"
     "\n QCheckBox:hover,QRadioButton:hover{background:transparent;}"
     "\n QCheckBox::indicator,QRadioButton::indicator{width:17px;height:17px;border:2px solid MUTED;border-radius:5px;background:FIELD;}"
     "\n QRadioButton::indicator{border-radius:10px;}"
     "\n QCheckBox::indicator:checked,QRadioButton::indicator:checked{background:ACCENT;border:2px solid ACCENT;}"
     "\n QCheckBox::indicator:hover,QRadioButton::indicator:hover{border:2px solid ACCENT;}"
     "\n QCheckBox::indicator:disabled,QRadioButton::indicator:disabled{border:2px solid LINE;background:FIELD;}")
once(" QCheckBox:checked,QCheckBox:disabled,QRadioButton:checked{background:transparent;}",
     " QCheckBox:checked,QCheckBox:disabled,QRadioButton:checked{background:transparent;}")
# Qt popups (combo lists) need an explicit palette or the OS might leave black
# viewport rectangles under the bright theme.
once(" QComboBox QAbstractItemView{background:SURFACE;color:INK;border:1px solid LINE;selection-background-color:SOFT;}",
     " QComboBox QAbstractItemView{background:SURFACE;color:INK;border:1px solid LINE;outline:0;selection-background-color:SOFT;selection-color:INK;}"
     "\n QComboBox::drop-down{border:0;background:transparent;min-width:21px;}"
     "\n QComboBox QAbstractItemView::item{min-height:27px;padding:5px 8px;}")
file.write_text(source,encoding="utf8")
# Version embedded for About dialog in the one-file EXE.
(root/"VERSION.txt").write_text("R11.20\n",encoding="utf8")
info_file=root/"build_info.json"
if info_file.exists():
    data=json.loads(info_file.read_text(encoding="utf8"))
    data["version"]="R11.20 · GitHub "+os.environ.get("GITHUB_SHA","")[:8]
    data["ui"]="PySide6 - light/dark contrast and pill tabs"
    info_file.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf8")

# The existing R11.19 grouped STEP writer and worker defaults are intentionally
# left intact; this is not a speculative CAD algorithm rewrite.
step=(root/"dsac29/step_io.py").read_text(encoding="utf8")
assert "samodzielne_puste_produkty" in step
assert "podzlozenia_bez_pustych_lisci" in step
print("R11.20 UI palette, rounded tabs, visible checkbox indicators patched; R11.19 STEP groups retained.")
