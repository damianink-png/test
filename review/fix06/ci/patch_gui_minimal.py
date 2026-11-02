"""Apply verified minimal Qt GUI fixes to the frozen RC9 source bundle.

This patch is deliberately anchored to the source lines printed by
DS Compare UI source anchors CI. It refuses unknown source versions.
"""
from pathlib import Path
import sys

root=Path(sys.argv[1])
def change(filename,old,new):
    path=root/"dsac29"/filename
    data=path.read_text(encoding="utf-8")
    count=data.count(old)
    if count!=1:
        raise RuntimeError(f"UI patch anchor missing or duplicated: {filename}: {count}: {old[:80]!r}")
    path.write_text(data.replace(old,new),encoding="utf-8")

change("gui_modern.py",
       "   self.run_compare.setText('Porównaj');self.run_compare.setMinimumWidth(220)",
       "   self.run_compare.setText('Porównaj rewizje');self.run_compare.setMinimumWidth(220)")

# Reuse the EXISTING reset_button; move it under the comparison action,
# rather than creating a duplicate or leaving it below export results.
change("gui_modern.py",
       "   lay.addWidget(self._compare_run_host)\n",
       """   lay.addWidget(self._compare_run_host)
   self.reset_button.setText('Nowe porównanie');self.reset_button.setObjectName('text-button')
   try:self.reset_button.clicked.disconnect()
   except (TypeError,RuntimeError):pass
   self.reset_button.clicked.connect(self.new_comparison)
   lay.addWidget(self.reset_button,alignment=Qt.AlignCenter)
""")
change("gui_modern.py",
       """   self.reset_button.setText('Nowe porównanie');self.reset_button.setObjectName('text-button')
   try:self.reset_button.clicked.disconnect()
   except (TypeError,RuntimeError):pass
   self.reset_button.clicked.connect(self.new_comparison)
   lay.addWidget(self.reset_button,alignment=Qt.AlignCenter)
   self.reset_button.hide()
   self._details_toggle=QPushButton('Pokaż szczegółową listę zmian')""",
       """   self._details_toggle=QPushButton('Pokaż szczegółową listę zmian')""")

# Keep internal table objects for compatibility with existing summary and
# CSV code, but never place the table, search/filter or details toggle on
# the visible comparison page.
change("gui_modern.py",
       "   self._details_toggle.hide();lay.addWidget(self._details_toggle)",
       "   self._details_toggle.hide()")
change("gui_modern.py",
       "   dt.addWidget(self.compare_table);lay.addWidget(self._details);self._details.hide()",
       "   dt.addWidget(self.compare_table);self._details.hide()")
change("gui_modern.py",
       """   self.reset_button.setVisible(done)
   self._details_toggle.setVisible(done)
   if not done:self._details.hide()""",
       """   self.reset_button.show()
   self.reset_button.setEnabled(self.process is None)
   self._details_toggle.hide()
   self._details.hide()""")

# An older GUI must never block analysis on the partial-report modal.
# The worker already auto-approves safe partial reports, but this also
# protects the GUI if it encounters a legacy material_unverified request.
p=root/"dsac29"/"gui45.py"
s=p.read_text(encoding="utf-8")
start=s.index("        if data.get('material_unverified'):")
end=s.index("        delta=data.get('translation_mm',[0,0,0])",start)
old=s[start:end]
if "QMessageBox(self);box.setWindowTitle('Niepełna analiza geometrii')" not in old:
    raise RuntimeError("Unexpected material modal source; refusing unsafe patch")
s=s[:start]+"""        if data.get('material_unverified'):
            self.active_log.appendPlainText(
                'Zapisuję automatycznie raport częściowy; niepotwierdzone pary pozostają do sprawdzenia.')
            self._reply_coordinate_prompt(token,'review')
            return
"""+s[end:]
p.write_text(s,encoding="utf-8")
print("DSCOMPARE_MINIMAL_GUI_PATCH_PASS",root,flush=True)
