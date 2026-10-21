"""Fast Qt smoke for R11.20 light/dark color contrast and rounded tabs."""
import os
from pathlib import Path
from PySide6.QtWidgets import QApplication,QCheckBox
from dsac29.gui46 import Window
from dsac29.gui_modern import DARK,LIGHT,skin

app=QApplication.instance() or QApplication([])
w=Window()
assert w.pages['compare'].objectName()=='page'
assert w.pages['settings'].objectName()=='page'
assert DARK['bg']!=DARK['surface']
assert LIGHT['bg']!=LIGHT['surface']
assert LIGHT['surface']!=LIGHT['field']
assert LIGHT['bg']!='#FFFFFF'
for name in ('Jasny','Ciemny','Jasny'):
    w.apply_theme(name)
    ss=w.styleSheet()
    assert 'QPushButton#nav:checked' in ss
    assert 'border-radius:11px' in ss
    assert 'QCheckBox::indicator:checked' in ss
    assert 'QCheckBox::indicator:hover' in ss
    assert 'border:2px solid' in ss
    assert 'QComboBox QAbstractItemView' in ss
    for key in ('compare','mass','settings'):
        assert w.nav[key].isCheckable()
    for box in (w.full_bom,w.align,w.cache_import,w.bom_csv):
        assert isinstance(box,QCheckBox)
        box.setChecked(not box.isChecked())
        app.processEvents()
        box.setChecked(not box.isChecked())
        app.processEvents()
    p=LIGHT if name=='Jasny' else DARK
    assert p['surface'] in ss and p['bg'] in ss
    print(name,'background',p['bg'],'cards',p['surface'],'fields',p['field'])
w.close()
print('PASS - separated pale background/white cards, pill navigation and legible checkbox indicator styles.')
