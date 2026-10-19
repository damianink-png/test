"""Frozen Windows GUI integration smoke test.

The system file chooser is deliberately mocked in headless CI, because
a real native Windows common dialog cannot be dismissed by Qt timers.
The actual chooser code is checked separately in source-level tests.
"""
import json,time,sys
from pathlib import Path
from PySide6.QtWidgets import QApplication
from .gui46 import Window

def main(output):
    import dsac29.gui45 as picker
    dest=Path(output).resolve()
    dest.mkdir(parents=True,exist_ok=True)
    app=QApplication.instance() or QApplication([])
    app.setStyle('Fusion')
    w=Window()
    w.show()
    app.processEvents()
    sample=(Path(sys.executable).resolve().parent if getattr(sys,'frozen',False) else Path(__file__).resolve().parents[1])/'samples'
    old_dialog=picker.windows_explorer_dialog
    picked=str(sample/'MODEL_A.step')
    try:
        picker.windows_explorer_dialog=lambda directory,initial='',folder=False: picked
        w.a.choose()
    finally:
        picker.windows_explorer_dialog=old_dialog
    app.processEvents()
    assert w.a.path.text()==picked,'Selecting a STEP file did not populate path'
    assert not hasattr(w.a,'quick_menu'),'Quick access custom menu still present'
    w.b.path.setText(str(sample/'MODEL_B.step'))
    assert w.a.path.text().lower().endswith('.step')
    assert w.b.path.text().lower().endswith('.step')
    w.output.setText(str(dest))
    w.run_compare.click()
    deadline=time.monotonic()+150
    while w.process is not None and time.monotonic()<deadline:
        app.processEvents()
        time.sleep(.03)
    assert w.process is None,'Compare worker stalled'
    assert 'compare' in w.results, 'Compare result not loaded: '+w.log.toPlainText()[-1500:]
    assert w.isVisible(),'UI unexpectedly closed'
    assert (w.results['compare']/'PODSUMOWANIE.json').exists()
    assert (w.results['compare']/'POROWNANIE_KOLORY.step').exists()
    assert w.compare_table.rowCount()>0
    w.close()
    (dest/'UI_INTERACTIONS_PASS.json').write_text(json.dumps({
        'file_picker_mocked_in_headless_CI':True,
        'quick_access_removed':True,
        'selected_step':True,
        'compare_clicked':True,
        'worker_finished':True,
        'main_window_alive':True,
        'model_file_type':'.step',
        'native_z3':'requires STEP export'
    },indent=2),encoding='utf8')
    return 0
