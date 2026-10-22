"""R11.30 UI regression: highlighted selections, per-row remove, and real result-only views."""
from pathlib import Path
from tempfile import TemporaryDirectory
from PySide6.QtWidgets import QApplication,QPushButton,QFrame
from PySide6.QtCore import Qt
from dsac29.gui46 import Window

app=QApplication.instance() or QApplication([])
w=Window();w.show();app.processEvents()
w.navigate('compare')
assert w._compare_selector_host.isVisible()
assert w._compare_run_host.isVisible()
assert not w._success.isVisible()
assert not w.reset_button.isVisible()
assert not w.a.property('hasFile')
assert not w.b._remove_model_button.isVisible()

with TemporaryDirectory() as folder:
 a=Path(folder)/'Model_A_TEST.step';a.write_text('dummy',encoding='utf8')
 b=Path(folder)/'Model_B_TEST.step';b.write_text('dummy',encoding='utf8')
 w.a.path.setText(str(a));w.b.path.setText(str(b))
 app.processEvents()
 assert w.a.property('hasFile') and w.b.property('hasFile')
 assert w.a._remove_model_button.isVisible()
 assert w.a.choose_button.text()=='Zmień'
 assert w.a._chosen_file_label.text()==a.name
 assert w.a.height()<=150
 w.a._remove_model_button.click()
 assert w.a.path.text()=='' and not w.a.property('hasFile')
 w.a.path.setText(str(a))

 for width,height in [(850,620),(980,720),(1240,850)]:
  w.resize(width,height);app.processEvents()
  w.navigate('compare');app.processEvents()
  assert w._compare_selector_host.isVisible()
  w._set_compare_result_state(True);app.processEvents()
  assert not w._compare_selector_host.isVisible()
  assert not w._compare_run_host.isVisible()
  assert not w._compare_progress_panel.isVisible()
  assert w._success.isVisible() and w._actions.isVisible()
  assert w.reset_button.isVisible()
  w.new_comparison();app.processEvents()
  assert w._compare_selector_host.isVisible() and w._compare_run_host.isVisible()
  assert not w.reset_button.isVisible()
  assert w.a.path.text()=='' and w.b.path.text()==''
  w.a.path.setText(str(a));w.b.path.setText(str(b))

 w.navigate('mass')
 app.processEvents()
 assert w._mass_form_host.isVisible()
 assert not w._mass_result_card.isVisible()
 assert not w.mass_new_button.isVisible()

 files=[]
 for i in range(4):
  p=Path(folder)/f'Czesc_{i}_TEST.step';p.write_text('dummy',encoding='utf8')
  files.append(str(p))
 w._mass_add(files);app.processEvents()
 assert len(w.mass_inputs)==4
 assert w.mass_drop.property('hasFiles')
 assert w._mass_drop_title.text()=='Pliki do obliczenia masy'
 assert w.mass_add_files.text()=='+ Dodaj pliki'
 assert w._mass_queue_buttons.isVisible()
 for i in range(4):
  holder=w.mass_input_list.itemWidget(w.mass_input_list.item(i))
  assert holder is not None
  assert any(x.text()=='×' for x in holder.findChildren(QPushButton))
 holder=w.mass_input_list.itemWidget(w.mass_input_list.item(1))
 delete=next(b for b in holder.findChildren(QPushButton) if b.text()=='×')
 delete.click();app.processEvents()
 assert len(w.mass_inputs)==3 and w.mass_input_list.count()==3
 assert not any(p.name=='Czesc_1_TEST.step' for p in w.mass_inputs)
 assert all(p.exists() for p in map(Path,files)),'Deleting an item must never delete a CAD file'
 w.mass_input_list.item(0).setSelected(True)
 assert w.mass_remove_selected.isEnabled()
 w._mass_remove_selected();app.processEvents()
 assert len(w.mass_inputs)==2
 w._set_mass_result_state(True);app.processEvents()
 assert not w._mass_form_host.isVisible()
 assert w._mass_result_card.isVisible()
 assert w.mass_done.isVisible()
 assert w.mass_actions.isVisible()
 assert w.mass_new_button.isVisible()
 assert not w.run_mass.isVisible() and not w.mass_add_files.isVisible()
 w.mass_new_button.click();app.processEvents()
 assert not w.mass_inputs and not w.mass_drop.property('hasFiles')
 assert w._mass_form_host.isVisible()
 assert not w._mass_result_card.isVisible()
 assert not w.mass_actions.isVisible()
 assert not w.mass_new_button.isVisible()
 assert w.mass_add_files.text()=='Wybierz pliki'
from PySide6.QtCore import QProcess
from dsac29.gui_modern import AboutWindow
w.navigate('settings');app.processEvents()
assert w._settings_save_button.isEnabled()
worker=QProcess(w)
w.process=worker;w.task='compare'
w._set_busy_ui(True)
assert w._analysis_busy_banner.isVisible()
assert all(button.isEnabled() for button in w.nav.values())
assert w.theme_button.isEnabled() and w.about_button.isEnabled()
assert not w._settings_save_button.isEnabled()
assert not w.run_compare.isEnabled() and not w.run_mass.isEnabled()
w.navigate('mass');app.processEvents()
assert w.stack.currentWidget() is w.pages['mass']
w.navigate('settings');app.processEvents()
assert w.stack.currentWidget() is w.pages['settings']
theme_before=w.theme.currentText()
w.theme_button.click();app.processEvents()
assert w.theme.currentText()!=theme_before
saved_before=float(w.store.value('tolerance',.01))
old_tolerance=w.tolerance.value()
w.tolerance.setValue(.0321 if old_tolerance!=.0321 else .0221)
assert abs(float(w.store.value('tolerance',.01))-saved_before)<1e-9,'Settings unexpectedly auto-saved during analysis'
observed=[]
old_exec=AboutWindow.exec
try:
 AboutWindow.exec=lambda self:observed.append('opened') or 0
 w.about_button.click()
 assert observed==['opened']
finally:
 AboutWindow.exec=old_exec
w.process=None
w._set_busy_ui(False)
assert w._settings_save_button.isEnabled()
assert w.run_compare.isEnabled() and w.run_mass.isEnabled()
w._settings_save_button.click()
assert abs(float(w.store.value('tolerance',.01))-w.tolerance.value())<1e-9
w.close()
print('R11.30 PASS: selected CAD cards, per-file x removal, no disk deletion, clean result-only compare/mass, new task resets')
