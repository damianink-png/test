"""R11.26 regression - two settings panels, no test controls or mass output grid."""
from pathlib import Path
from tempfile import TemporaryDirectory
from PySide6.QtWidgets import QApplication,QFrame,QPushButton,QFormLayout,QAbstractItemView
from dsac29.gui46 import Window

app=QApplication.instance() or QApplication([])
w=Window()
w.show()
w.navigate('settings')
app.processEvents()
settings=w.pages['settings']
cards=settings.findChildren(QFrame,'settings-card')
titles=[c.layout().itemAt(0).widget().text() for c in cards]
assert len(cards)==2,titles
assert titles==['Porównanie i import','Raport i eksport'],titles
assert not hasattr(w,'test_run') and not hasattr(w,'test_save') and not hasattr(w,'test_folder')
assert not hasattr(w,'test_counts') and not hasattr(w,'test_process')
texts=[b.text() for b in settings.findChildren(QPushButton)]
assert not any('test' in t.casefold() or 'ABSR' in t.upper() for t in texts),texts
assert w.cache_import and w.clear_import_cache_button
assert w.output_button and w.color_editor
assert w.schema.currentText()=='AP214IS'
assert w.verify_mode.currentData()=='auto'

w.navigate('mass')
app.processEvents()
assert not w._mass_details.isVisible()
# Data adapter remains for existing legacy report handlers but is removed
# completely from the screen layout and cannot consume space.
assert w._mass_details.parentWidget() is None
assert w._mass_details not in [x.widget() for x in w._mass_details.children() if hasattr(x,'widget')]
assert w.mass_table is not None and not w.mass_table.isVisible()
assert w.mass_actions is not None
assert w.mass_open['RAPORT_MASY.html'] is not None
assert w.mass_open[''] is not None
assert w.run_mass and w.cancel_mass and w.mass_reset
assert w.mass_add_files and w.mass_add_folder and w.mass_remove_selected
w.mass_actions.show()
app.processEvents()
assert w.mass_actions.isVisible()
assert not w._mass_details.isVisible()
w.mass_actions.hide()
with TemporaryDirectory() as root:
    paths=[]
    for idx in range(3):
        p=Path(root)/f'syntetyczny_{idx}.step'
        p.write_text('TEST',encoding='utf8')
        paths.append(str(p))
    w._mass_add(paths)
    assert w.mass_input_list.count()==3
    w.mass_input_list.item(1).setSelected(True)
    app.processEvents()
    assert w.mass_remove_selected.isEnabled()
    w._mass_remove_selected()
    assert w.mass_input_list.count()==2
    assert len(w.mass_inputs)==2
w.close()
print('R11.26 PASS: settings only comparison and export; no Testy, no mass table, all mass action buttons and queue removal remain')
