"""R11.27 GUI regression: compare table gone, controls responsive across tabs."""
from pathlib import Path
import inspect
from tempfile import TemporaryDirectory
from PySide6.QtWidgets import QApplication,QScrollArea,QAbstractItemView
from dsac29.gui46 import Window
import dsac29.gui45 as legacy

app=QApplication.instance() or QApplication([])
w=Window();w.show();app.processEvents()
assert isinstance(w.pages['compare'],QScrollArea),type(w.pages['compare'])
assert isinstance(w.pages['mass'],QScrollArea)
assert isinstance(w.pages['settings'],QScrollArea)
assert w.compare_table.rowCount()==0
assert not w._details.isVisible()
assert w._details.parentWidget() is None,'Comparison result table container still attached to main page'
assert w._actions is not None and w.compare_open['POROWNANIE_KOLORY.step']
assert w.compare_open['RAPORT.html'] and w.compare_open['']
assert w.mass_actions and w.mass_open['RAPORT_MASY.html'] and w.mass_open['']
assert w.mass_add_files and w.mass_add_folder and w.mass_remove_selected and w.mass_reset
assert w.mass_input_list.selectionMode()==QAbstractItemView.ExtendedSelection
assert w.minimumWidth()>=560 and w.minimumHeight()>=420

# Comparison table remains as hidden legacy widget, but loading results
# must not read hundreds of MB of CSV or construct invisible result rows.
fn=inspect.getsource(legacy.Window.load_result)
assert 'self.compare_table.setRowCount(0)' in fn and "with (folder/'ZMIANY.csv').open" not in fn
assert 'buttons=self.compare_open' in fn

with TemporaryDirectory() as tmp:
    files=[]
    for n in range(3):
        f=Path(tmp)/f'PRIVATE_SAMPLE_{n}.step'
        f.write_text('dummy',encoding='utf8')
        files.append(str(f))
    w._mass_add(files)
    w.mass_input_list.item(1).setSelected(True)
    assert w.mass_remove_selected.isEnabled()
    w._mass_remove_selected()
    assert len(w.mass_inputs)==2

    for size in [(760,540),(800,600),(960,580),(1280,720)]:
        w.resize(*size)
        app.processEvents()
        for page in ('compare','mass','settings','compare','mass'):
            w.navigate(page);app.processEvents()
            scroll=w.pages[page]
            assert scroll.isVisible(),(size,page)
            assert scroll.verticalScrollBarPolicy()!=0
            assert scroll.horizontalScrollBarPolicy()!=0
            assert scroll.viewport().width()>350,(page,scroll.viewport().width())
            assert scroll.widget().width()<=scroll.viewport().width()+6,(page,scroll.widget().width(),scroll.viewport().width())
            assert all(b.isVisible() for b in w.nav.values()),(size,page)
        # This is the main failure mode: mass controls must all remain sized
        # after narrowing the compare page and navigating to mass.
        w.navigate('mass');app.processEvents()
        for control in [w.run_mass,w.cancel_mass,w.mass_remove_selected,w.mass_reset]:
            assert control.width()>=100,(size,control.text(),control.width())
            assert control.height()>=25,(size,control.text(),control.height())
            assert control.geometry().width()<=w.pages['mass'].widget().width()
        w.navigate('compare');app.processEvents()
        assert not w._details.isVisible()
        assert w.run_compare.width()>=160

    # Shrunk viewport must be able to reveal controls below the fold,
    # without a horizontal scrollbar clipping buttons.
    w.resize(760,540);w.navigate('mass');app.processEvents()
    assert w.pages['mass'].verticalScrollBar().maximum()>0, 'Mass page should scroll on a short window'
w.close()
print('R11.27 PASS: comparison results table removed; report buttons remain; auto-sized/scrolled 3 tabs; mass 2x2 grid works at 760x540')
