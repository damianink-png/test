"""V3.6 new theme support and offline B-Rep-colored preview contract."""
from pathlib import Path
from dsac29.cli import process
from dsac29.preview3d import create_preview
from dsac29.step_io import load_step
from dsac29.compare import compare
from dsac29 import gui

ROOT=Path(__file__).resolve().parents[1]

def test_offline_webgl_preview_contains_real_per_status_rgb(tmp_path):
    a=load_step(str(ROOT/'samples/MODEL_A.step'))
    b=load_step(str(ROOT/'samples/MODEL_B.step'))
    records=compare(a,b)
    result=create_preview(tmp_path/'preview.html',records,a,b,
             colors={'ADDED':(0.1,0.2,0.9),'REMOVED':(0.9,0.2,0.1)})
    assert result['elementy']>=4
    assert result['trojkaty']>40
    text=(tmp_path/'preview.html').read_text(encoding='utf-8')
    assert 'webgl' in text.lower() and 'file' not in text[:150]
    assert '0.1,0.2,0.9' in text and '0.9,0.2,0.1' in text
    assert 'Podgląd siatkowy' in text

def test_preview_added_to_full_process(tmp_path):
    folder, rows, err=process(str(ROOT/'samples/MODEL_A.step'),
         str(ROOT/'samples/MODEL_B.step'),str(tmp_path),
         step=False,diff_step=False,preview3d=True,progress=None)
    assert err is None
    assert (folder/'PODGLAD_KOLOROW_3D.html').exists()
    assert (folder/'PODSUMOWANIE.json').exists()

def test_theme_data_and_status_color_remains_separate():
    assert gui.DARK_THEME['BG'] != gui.LIGHT_THEME['BG']
    gui.use_ui_theme('jasny')
    assert gui.BG == gui.LIGHT_THEME['BG']
    assert gui._rgb(gui.COLORS['SAME']) == '#9199A6'
    gui.use_ui_theme('ciemny')
    assert gui.BG == gui.DARK_THEME['BG']
