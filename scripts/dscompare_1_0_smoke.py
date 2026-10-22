"""DS Compare 1.0 regression for ported GUI and exact safe assignment acceleration."""
import random,time
from pathlib import Path
from PySide6.QtWidgets import QApplication,QScrollArea,QMessageBox
from dsac29.gui46 import Window
from dsac29.gui_modern import AboutWindow
from dsac29.assignment import assign

# Stable 1:1 pairing, including the one-for-one hard case and ambiguities.
rng=random.Random(42)
for k in range(150):
 n=rng.randint(1,9);m=rng.randint(1,9)
 edges={(a,b):rng.random() for a in range(n) for b in range(m) if rng.random()<.3}
 if not edges:continue
 result=assign(edges)
 assert len({i for i,j,_,_ in result})==len(result)
 assert len({j for i,j,_,_ in result})==len(result)
 assert all((i,j) in edges for i,j,_,_ in result)
 if len(edges)==1:
  assert len(result)==1 and not result[0][2]

# Large sparse assemblies should finish quickly and all pairings remain exact.
edges={(i,i):.02 for i in range(1800)}
started=time.perf_counter()
selected=assign(edges)
elapsed=time.perf_counter()-started
assert len(selected)==1800 and all(not ambiguous for _,_,ambiguous,_ in selected)
assert elapsed<12.0, f'1800 deterministic components unexpectedly slow: {elapsed:.2f}s'
print(f'PASS assignment 1800 singleton pairs in {elapsed:.3f}s')

app=QApplication.instance() or QApplication([])
w=Window();w.show();app.processEvents()
about=AboutWindow(w);about.show();app.processEvents()
assert isinstance(about.findChild(QScrollArea),QScrollArea)
assert about.logo.isVisible()
assert about.version_label.text()=='Wersja 1.0'
assert about.minimumWidth()<=w.width() and about.width()<=w.width()+100
assert about.layout() is not None
about.close()
w.navigate('settings');app.processEvents()
assert w._settings_save_button is not None
assert not w._settings_dirty()
before=w.cache_import.isChecked()
w.cache_import.setChecked(not before);app.processEvents()
assert w._settings_dirty()
assert not bool(w.store.value('import_cache',before,type=bool))==bool(not before),'Unexpected cache autosave'
w._settings_cancel_button.click();app.processEvents()
assert not w._settings_dirty() and w.cache_import.isChecked()==before
w.navigate('mass');app.processEvents()
assert w._mass_materials_panel.isVisible()
w.close()
print('PASS 1.0 GUI: About responsive, cache saved only by Save, form layouts accessible')
