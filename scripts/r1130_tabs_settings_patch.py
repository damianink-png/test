"""R11.30: tabs, theme and About available during analysis; explicit settings Save.

The currently running worker has already received an immutable CLI option
snapshot; UI values edited meanwhile can only affect a later job. The Save
button stays disabled until that worker finishes.
"""
from pathlib import Path
import os,json
root=Path(os.environ['DS_COMPARE_SOURCE'])
p=root/'dsac29/gui_modern.py'
s=p.read_text('utf8')
def replace(a,b):
 global s
 n=s.count(a)
 if n!=1:raise RuntimeError(f'R11.30 tabs/settings anchor count {n}: {a[:100]!r}')
 s=s.replace(a,b,1)
a=s.index(" def _set_busy_ui(self,busy):")
b=s.index(" def _modern_compare(self):",a)
old=s[a:b]
assert ' def navigate(self,key)' in old
updated=""" def _set_busy_ui(self,busy):
  # Navigation and cosmetic actions remain available while worker computes.
  # Only operations that change or submit analysis inputs are disabled.
  self._analysis_busy_banner.setVisible(bool(busy))
  self._analysis_busy_banner.setText(
   'Trwa analiza — możesz przełączać zakładki i zmieniać motyw. '
   'Zapis ustawień oraz nowe obliczenia są dostępne po zakończeniu.'
   if busy else '')
  for button in self.nav.values():
   button.setEnabled(True)
   button.setToolTip('')
  self.theme_button.setEnabled(True)
  self.about_button.setEnabled(True)
  self._settings_save_button.setEnabled(not busy)
  self._settings_save_button.setToolTip(
   'Zapis ustawień jest wstrzymany do końca analizy.' if busy else
   'Zapisz ustawienia dla kolejnych analiz.')
  for control in (self.run_compare,self.run_mass,self.swap_button,
                  self.a.choose_button,self.b.choose_button):
   control.setEnabled(not busy)
  for card in (self.a,self.b):
   if hasattr(card,'_remove_model_button'):
    card._remove_model_button.setEnabled(not busy)
  for name in ('mass_add_files','mass_add_folder','mass_reset','mass_new_button',
               'reset_button','_add_material_button'):
   control=getattr(self,name,None)
   if control is not None:control.setEnabled(not busy)
  if hasattr(self,'mass_remove_selected'):
   self.mass_remove_selected.setEnabled(not busy and bool(self.mass_input_list.selectedItems()))
  if hasattr(self,'mass_input_list'):
   for index in range(self.mass_input_list.count()):
    holder=self.mass_input_list.itemWidget(self.mass_input_list.item(index))
    if holder is not None:
     for control in holder.findChildren(QPushButton):control.setEnabled(not busy)
  # The color editor writes its palette separately, so disable it while
  # running to avoid persisting mid-job changes behind the Save button.
  self.color_editor.setEnabled(not busy)

 def navigate(self,key):
  # Unlike R11.28, all tabs remain accessible during an active QProcess.
  return super().navigate(key)

 def save_settings(self,*args):
  # gui45 connects valueChanged/toggled directly to save_settings. Those
  # automatic callbacks must not persist unsaved edits.
  return None

 def _save_settings_explicit(self):
  if self.process is not None:return
  super().save_settings()
  for key,value in (
    ('solid_limit',self.solid_limit.value()),
    ('full_bom',self.full_bom.isChecked()),
    ('bom_mode',self.bom_mode.currentData()),
    ('bom_csv',self.bom_csv.isChecked()),
    ('output',self.output.text().strip()),
    ('import_cache',self.cache_import.isChecked()),
  ):
   self.store.setValue(key,value)
  self.store.sync()
  self._settings_save_feedback.setText('✓ Ustawienia zapisane. Będą użyte przy następnej analizie.')

"""
s=s[:a]+updated+s[b:]
replace("""  self.safe_export.setChecked(True);self.safe_export.hide()""",
"""  self.safe_export.setChecked(True);self.safe_export.hide()
  save_row=QHBoxLayout();save_row.setContentsMargins(0,8,0,0)
  save_row.addStretch(1)
  self._settings_save_feedback=QLabel('')
  self._settings_save_feedback.setObjectName('muted')
  self._settings_save_feedback.setWordWrap(True)
  save_row.addWidget(self._settings_save_feedback)
  self._settings_save_button=QPushButton('Zapisz ustawienia')
  self._settings_save_button.setObjectName('primary')
  self._settings_save_button.clicked.connect(self._save_settings_explicit)
  save_row.addWidget(self._settings_save_button)
  lay.insertLayout(lay.count()-1,save_row)
  self._settings_note=QLabel(
   'Podczas analizy możesz przeglądać ustawienia. Ich zapis będzie dostępny po zakończeniu.')
  self._settings_note.setObjectName('muted')
  self._settings_note.setWordWrap(True)
  lay.insertWidget(lay.count()-1,self._settings_note)""")
# Suppress autosaving on legacy GUI46 QSettings lambda hooks while
# retaining the checkbox/model visual state. Theme is intentionally exempt.
replace("""  self._center_form_fields()
  self._scroll_page('compare')""",
"""  self._center_form_fields()
  self._install_deferred_settings_signals()
  self._scroll_page('compare')""")
needle=" def _set_busy_ui(self,busy):"
add=""" def _install_deferred_settings_signals(self):
  # All currently visible settings persist only via the new Save button.
  # A few GUI46 controls were connected to QSettings via inline lambdas.
  for widget,signal in (
    (self.solid_limit,'valueChanged'),
    (self.full_bom,'toggled'),
    (self.bom_mode,'currentIndexChanged'),
    (self.bom_csv,'toggled'),
  ):
   try:getattr(widget,signal).disconnect()
   except (TypeError,RuntimeError):pass
  # Base GUI45 callbacks now call our no-op save_settings while editing.
  # Import cache is a runtime performance control and can be inspected;
  # its application will follow the explicit Save button.

"""
replace(needle,add+needle)
p.write_text(s,'utf8')
print('R11.30 parallel UX: navigation/theme/About remain active; saved settings + analysis starts disabled during worker')
