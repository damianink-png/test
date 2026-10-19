"""Regression tests for R9 materials and result panel."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtCore import QSettings, QPoint
from PySide6.QtWidgets import QApplication
from dsac29.gui46 import Window, MATERIALS

def test_material_library_can_save_and_restore(tmp_path):
    QSettings.setDefaultFormat(QSettings.IniFormat)
    QSettings.setPath(QSettings.IniFormat,QSettings.UserScope,str(tmp_path/"settings"))
    app=QApplication.instance() or QApplication([])
    w=Window()
    assert w.material_combo.count() >= len(MATERIALS)+1
    steel=next(i for i in range(1,w.material_combo.count()) if w.material_combo.itemData(i)[0] == "Stal konstrukcyjna S235 / S355")
    w.material_combo.setCurrentIndex(steel)
    assert w.density.value()==7850
    w.save_custom_material("Stal testowa X",7744.5)
    assert w.material_combo.currentData() == ("Stal testowa X",7744.5)
    assert w.density.value()==7744.5
    assert "Stal testowa X" in str(w.store.value("custom_materials"))
    w.density.setValue(7777)
    assert w.material_combo.currentIndex()==0
    w.close()
    w2=Window()
    assert any(w2.material_combo.itemData(i)==("Stal testowa X",7744.5) for i in range(1,w2.material_combo.count()))
    w2.close()

def test_result_panel_actions_fit(tmp_path):
    QSettings.setDefaultFormat(QSettings.IniFormat)
    QSettings.setPath(QSettings.IniFormat,QSettings.UserScope,str(tmp_path/"settings"))
    app=QApplication.instance() or QApplication([])
    w=Window()
    w.resize(1120,740)
    w.show();app.processEvents()
    box=w.export_box
    assert box.width()>=296
    assert len(w.compare_open)==4
    for button in w.compare_open.values():
        point=button.mapTo(box,QPoint(button.width()//2,button.height()//2))
        assert box.rect().contains(point),f"Clipped result button: {button.text()}"
    assert not w.compare_help_text.isVisible()
    w.toggle_theme()
    w.navigate("mass")
    w.navigate("compare")
    app.processEvents()
    for button in w.compare_open.values():
        point=button.mapTo(box,QPoint(button.width()//2,button.height()//2))
        assert box.rect().contains(point),f"Clipped after theme toggle: {button.text()}"
    w.close()
