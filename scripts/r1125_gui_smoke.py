"""R11.25: new UX without old settings, list toggles or unsafe file deletion."""
from pathlib import Path
from tempfile import TemporaryDirectory
from PySide6.QtWidgets import QApplication,QFrame,QFormLayout
from dsac29.gui46 import Window
app=QApplication.instance() or QApplication([])
window=Window()
window.show()
app.processEvents()
window.navigate('settings')
app.processEvents()
assert hasattr(window,'test_run') and window.test_run.isEnabled()
assert hasattr(window,'test_save') and not window.test_save.isEnabled()
assert not hasattr(window,'zw3d_flat_output'),'Flat STEP switch should be removed'
assert not hasattr(window,'absr_test_output'),'Experimental ABSR switch should be removed'
assert window.cache_import is not None and window.clear_import_cache_button is not None
cards=[x for x in window.findChildren(QFrame,'settings-card')]
card_titles=[x.layout().itemAt(0).widget().text() for x in cards]
assert 'Testy' in card_titles,card_titles
assert 'Ogólne' not in card_titles,card_titles
assert 'Raport i eksport' in card_titles,card_titles
assert not any('Schemat STEP' in str(x) or 'Kontrola STEP' in str(x) for x in card_titles)
assert window.schema.currentText()=='AP214IS'
assert window.verify_mode.currentData()=='auto',window.verify_mode.currentData()
assert window._details_toggle.isHidden()
assert window._mass_toggle.isHidden()

window.navigate('mass')
app.processEvents()
assert window.mass_input_list.selectionMode()!=window.mass_input_list.SingleSelection
with TemporaryDirectory() as tmp:
    paths=[]
    for i in range(4):
        p=Path(tmp)/f'mock{i}.step'
        p.write_text('synthetic placeholder',encoding='utf8')
        paths.append(str(p))
    window._mass_add(paths)
    assert len(window.mass_inputs)==4
    window.mass_input_list.item(1).setSelected(True)
    window.mass_input_list.item(3).setSelected(True)
    app.processEvents()
    assert window.mass_remove_selected.isEnabled()
    window._mass_remove_selected()
    assert len(window.mass_inputs)==2,window.mass_inputs
    assert [x.name for x in window.mass_inputs]==['mock0.step','mock2.step']
    assert window.mass_input_list.count()==2
    assert window.mass_file.path.text().endswith('mock0.step')
    window.mass_input_list.selectAll()
    window._mass_remove_selected()
    assert len(window.mass_inputs)==0
    assert not window.mass_file.path.text()
    assert window.mass_input_list.isHidden()
    assert not window.mass_remove_selected.isEnabled()
window.close()
print('R11.25 UI PASS: minimal settings, diagnostic controls, permanently hidden toggles, safe multi-delete mass queue')
