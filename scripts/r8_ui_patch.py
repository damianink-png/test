"""DS Compare R8 UI polish on top of the CURRENT R7 release source.
This script is deliberately strict: missing/changed anchors fail the build.
No CAD, alignment, classification, STEP exporter or worker logic is modified.
"""
from pathlib import Path
root=Path(__file__).resolve().parents[1]/"source"
p=root/"dsac29/gui_modern.py"
if not p.is_file():
    raise RuntimeError(f"Missing extracted R7 GUI: {p}")
s=p.read_text(encoding="utf-8")

def replace_once(a,b):
    global s
    n=s.count(a)
    if n!=1:
        raise RuntimeError(f"R8 GUI anchor found {n} times: {a[:110]!r}")
    s=s.replace(a,b,1)

# Important: QWidget has an opaque global background in both themes.
# The queue button container must be transparent, or a black rectangular band
# appears beneath the otherwise correctly rounded drop zone.
replace_once(
    ' QWidget#mass-file-row{background:FIELD;border:0;border-bottom:1px solid LINE;}',
    ' QWidget#mass-queue-actions{background:transparent;border:0;}\n'
    ' QWidget#mass-file-row{background:FIELD;border:1px solid transparent;border-radius:9px;}\n'
    ' QWidget#mass-file-row:hover{background:HOVER;border-color:LINE;}'
)
replace_once(
    ' QWidget#mass-file-row[selected="true"]{background:SOFT;}',
    ' QWidget#mass-file-row[selected="true"]{background:SOFT;border:1px solid ACCENT;border-radius:9px;}'
)
replace_once(
    ' QListWidget#mass-input-list{padding:0;border:1px solid LINE;border-radius:9px;background:FIELD;}',
    ' QListWidget#mass-input-list{padding:5px;border:1px solid LINE;border-radius:12px;background:FIELD;outline:0;}'
)
replace_once(
    ' QListWidget#mass-input-list::item{border:0;padding:0;margin:0;min-height:40px;}',
    ' QListWidget#mass-input-list::item{border:0;padding:0;margin:0;min-height:43px;background:transparent;}'
)
replace_once(
    ' QListWidget#mass-input-list::item:selected{background:SOFT;}',
    ' QListWidget#mass-input-list::item:selected{background:transparent;border:0;outline:0;}'
)
# Old unscoped text-button styling gave a barely noticeable hover in the
# light palette. A dedicated Mass "Wyczyść" button has obvious contrast.
replace_once(
    ' QPushButton#text-button:hover{color:ACCENT;background:HOVER;}',
    ' QPushButton#text-button:hover{color:ACCENT;background:HOVER;}\n'
    ' QPushButton#mass-clear{background:FIELD;color:INK;border:1px solid LINE;border-radius:9px;}\n'
    ' QPushButton#mass-clear:hover{background:ACCENT;color:#FFFFFF;border:1px solid ACCENT;font-weight:700;}\n'
    ' QPushButton#mass-clear:pressed{background:SOFT;color:INK;border-color:ACCENT;}'
)
replace_once(
    '  self._mass_queue_buttons=QWidget()\n  queue_row=QHBoxLayout(self._mass_queue_buttons)',
    "  self._mass_queue_buttons=QWidget()\n"
    "  self._mass_queue_buttons.setObjectName('mass-queue-actions')\n"
    "  queue_row=QHBoxLayout(self._mass_queue_buttons)"
)
replace_once(
    "  self.mass_input_list.setSpacing(0)",
    "  self.mass_input_list.setSpacing(3)\n"
    "  self.mass_input_list.setFrameShape(QFrame.NoFrame)"
)
replace_once(
    "  self.mass_reset.setObjectName('text-button')",
    "  self.mass_reset.setObjectName('mass-clear')"
)
replace_once(
    "   item.setToolTip(str(model));item.setSizeHint(QSize(20,42))",
    "   item.setToolTip(str(model));item.setSizeHint(QSize(20,45))"
)
replace_once(
    "   holder=QWidget();holder.setObjectName('mass-file-row')\n"
    "   holder.setMinimumHeight(40);holder.setProperty('selected',False)",
    "   holder=QWidget();holder.setObjectName('mass-file-row')\n"
    "   holder.setMinimumHeight(41);holder.setProperty('selected',False)"
)
replace_once(
    "  if self.task=='compare':\n"
    "   success=bool(getattr(self,'completion_ok',False) and self.results.get('compare'))\n"
    "   self._set_compare_result_state(success)\n"
    "   if not success:self.compare_summary.setText('Nie udało się zakończyć porównania — zobacz komunikat błędu.')",
    "  if self.task=='compare':\n"
    "   success=bool(getattr(self,'completion_ok',False) and self.results.get('compare'))\n"
    "   self._set_compare_result_state(success)\n"
    "   if not success:\n"
    "    # Keep the input cards available for retry, and make reset discoverable.\n"
    "    self.reset_button.setVisible(True)\n"
    "    self.reset_button.setEnabled(True)\n"
    "    self.reset_button.setToolTip('Wyczyść oba modele i rozpocznij nowe porównanie.')\n"
    "    self.compare_summary.setText('Nie udało się zakończyć porównania — zobacz komunikat błędu.')"
)
# Clear any legacy style duplication so later edits have unambiguous rules.
replace_once(
    ' QPushButton#delete-one{background:transparent;border:0;color:MUTED;min-width:28px;max-width:28px;min-height:28px;max-height:28px;padding:0;font-size:20px;}\n'
    ' QPushButton#delete-one:hover{background:HOVER;color:ACCENT;}\n',
    ''
)
p.write_text(s,encoding='utf-8')
build_info=root/'build_info.json'
if build_info.is_file():
    import json
    data=json.loads(build_info.read_text(encoding='utf-8'))
    data['ui_revision']='R8 (R7 engine; selected mass rows, clear hover, failed comparison reset)'
    build_info.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
(root/'R8_ZMIANY.txt').write_text(
    'DS Compare R8 na bazie R7\n'
    '- Nowe porównanie widoczne po nieudanej analizie.\n'
    '- Przezroczyste tło kontenera Usuń zaznaczone.\n'
    '- Zaokrąglone zaznaczenie plików STEP bez kwadratowej nakładki.\n'
    '- Wyraźne podświetlenie Wyczyść w jasnym motywie.\n'
    '- Silnik CAD, wyrównanie, BOM i STEP bez zmian względem R7.\n',
    encoding='utf-8')
print('R8 UI patch PASS: updated dsac29/gui_modern.py on top of extracted R7 source')
