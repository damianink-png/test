"""GUI integration check for R11.18, run with Windows Qt offscreen."""
import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication,QDialog,QDialogButtonBox,QScrollArea,QCheckBox

from dsac29.gui46 import Window
from dsac29.gui_modern import skin
from dsac29.zw3d_launcher import create_macro

def main():
    app=QApplication.instance() or QApplication([])
    w=Window()
    assert hasattr(w,'zw3d_macro_button')
    assert 'ZW3D' in w.zw3d_macro_button.text()
    for name in ('Ciemny','Jasny','Ciemny'):
        w.apply_theme(name)
        style=w.styleSheet().replace(' ','')
        assert 'QCheckBox,QRadioButton{' in style
        assert 'background:transparent' in style
    seen=[]
    def inspect():
        dlg=app.activeModalWidget()
        assert isinstance(dlg,QDialog), 'Color dialog not visible'
        scroll=dlg.findChild(QScrollArea)
        actions=dlg.findChild(QDialogButtonBox)
        assert scroll is None and actions, 'R11.21: wszystkie próbki kolorów muszą się mieścić bez przewijania'
        assert actions.button(QDialogButtonBox.Cancel).text()=='Anuluj'
        assert actions.button(QDialogButtonBox.Ok).text()=='Zapisz'
        app.processEvents()
        assert dlg.findChildren(QCheckBox)==[], 'Color picker does not require extra toggles'
        assert dlg.layout().count()>=4, 'The full color grid and footer must be visible'
        seen.append(True)
        dlg.reject()
    QTimer.singleShot(200,inspect)
    w.edit_export_colors()
    assert seen, 'Could not inspect color dialog'
    with TemporaryDirectory() as tmp:
        exe=Path(tmp)/'DSCompare.exe'
        exe.write_bytes(b'EXE-test-placeholder')
        dest=create_macro(executable=exe,output_dir=Path(tmp)/'ZW3D')
        content=dest.read_text(encoding='cp1250')
        assert content.startswith('MACRO main\n')
        assert '[vxSend,"$tm=more"]' in content
        assert str(exe.resolve()).casefold() in content.casefold(), (str(exe.resolve()),repr(content))
        assert 'ENDMACRO' in content
        assert dest.is_file()
    w.close()
    print('R11.18 UI checked: matching background, Polish Anuluj, non-scrolling colors, ZW3D launcher macro created.')
if __name__=='__main__':main()
