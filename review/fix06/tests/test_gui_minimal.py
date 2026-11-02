"""Qt GUI regression for the actual packaged desktop source."""
from pathlib import Path

def test_frozen_gui_has_no_partial_report_modal():
    from dsac29 import gui45
    source=Path(gui45.__file__).read_text(encoding="utf-8")
    assert "box.setWindowTitle('Niepełna analiza geometrii')" not in source
    assert "self._reply_coordinate_prompt(token,'review')" in source

def test_existing_reset_button_is_below_compare_and_results_table_is_hidden():
    from PySide6.QtWidgets import QApplication
    # Import through the production entrypoint: gui46 installs its modern alias.
    from dsac29.gui46 import Window as ModernWindow
    app=QApplication.instance() or QApplication([])
    w=ModernWindow()
    try:
        assert w.run_compare.text()=="Porównaj rewizje"
        assert w.reset_button.text()=="Nowe porównanie"
        assert not w.reset_button.isHidden()
        assert w._details_toggle.isHidden()
        assert w._details.isHidden()
        w._set_compare_result_state(True)
        assert not w.reset_button.isHidden()
        assert w._details_toggle.isHidden()
        assert w._details.isHidden()
    finally:
        w.deleteLater()
