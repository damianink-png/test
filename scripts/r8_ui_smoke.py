"""R8 focused Qt regression on exact R7 archive (offscreen Windows)."""
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from PySide6.QtCore import Qt,QProcess
from PySide6.QtWidgets import QApplication,QPushButton
from dsac29.gui46 import Window
from dsac29.gui_modern import skin

app=QApplication.instance() or QApplication([])
w=Window();w.show();app.processEvents()
assert w.mass_reset.objectName()=='mass-clear'
assert w._mass_queue_buttons.objectName()=='mass-queue-actions'
light=skin(False)
dark=skin(True)
for css in (light,dark):
    assert 'QWidget#mass-queue-actions{background:transparent' in css
    assert 'QListWidget#mass-input-list::item:selected{background:transparent' in css
    assert 'QWidget#mass-file-row[selected="true"]{background:' in css
    assert 'border-radius:9px;' in css
    assert 'QPushButton#mass-clear:hover{background:' in css
assert '#mass-clear:hover{background:#1268D8' in light
print('PASS R8: queue-footer clear background, rounded selected rows, visible clear hover for light/dark')

with TemporaryDirectory() as folder:
    paths=[]
    for n in range(3):
        p=Path(folder)/f'R8_ELEMENT_{n:02d}.step'
        p.write_text('synthetic entry, never delete disk file',encoding='utf-8')
        paths.append(str(p))
    w.navigate('mass')
    w._mass_add(paths);app.processEvents()
    assert w.mass_input_list.count()==3 and w._mass_queue_buttons.isVisible()
    item=w.mass_input_list.item(1)
    item.setSelected(True);app.processEvents()
    holder=w.mass_input_list.itemWidget(item)
    assert holder.property('selected') is True
    delete=next(x for x in holder.findChildren(QPushButton) if x.text()=='×')
    assert delete.objectName()=='delete-one'
    assert abs((delete.y()+delete.height()/2)-holder.height()/2)<=6
    delete.click();app.processEvents()
    assert len(w.mass_inputs)==2 and all(Path(f).exists() for f in paths)

    w.navigate('compare')
    w._set_compare_result_state(True)
    app.processEvents()
    assert w.reset_button.isVisible(),'Missing reset after successful compare'

    # Emulate the actual R7 completed callback, but isolate the engine/
    # worker superclass (this test is purely about UI transitions).
    base=type(w).__mro__[1]
    assert hasattr(base,'finished')
    w._set_compare_result_state(False)
    w.task='compare';w.completion_ok=False
    w.results.pop('compare',None)
    with patch.object(base,'finished',lambda *args,**kwargs:None):
        w.finished(1,QProcess.NormalExit)
    app.processEvents()
    assert w.reset_button.isVisible(),'New comparison hidden after failed analysis'
    assert w.reset_button.isEnabled()
    assert w._compare_selector_host.isVisible(),'Retry form must remain accessible'
    assert 'Nie udało' in w.compare_summary.text()
    w.a.path.setText(paths[0]);w.b.path.setText(paths[2])
    w.reset_button.click();app.processEvents()
    assert w.a.path.text()=='' and w.b.path.text()==''
    assert not w.reset_button.isVisible()
    w.navigate('mass')
    w.grab().save('R8_UI_MASS.png')
w.close()
print('R8 UI SMOKE PASS: success/error new comparison, clear models, mass list rows and light/dark styling')
