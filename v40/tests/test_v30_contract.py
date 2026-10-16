"""Minimal source-level integration contracts, independent of Windows/GUI."""
from pathlib import Path
import inspect
from dsac29.cli import process
from dsac29 import gui
from dsac29.step_io import COLORS

ROOT = Path(__file__).resolve().parents[1]

def test_process_accepts_color_palette():
    params = inspect.signature(process).parameters
    assert 'colors' in params
    assert callable(gui.main)

def test_named_colors_and_green_rename():
    assert COLORS['SAME'] == COLORS['RENAMED']
    assert len({COLORS['ADDED'],COLORS['CHANGED'],COLORS['MOVED'],COLORS['UNCERTAIN']})==4
    assert all(key in COLORS for key in ('SAME','ADDED','REMOVED','UNCERTAIN'))

def test_dll_api_export_contract_and_no_file_mutations():
    source = (ROOT / 'bridge' / 'DSAssemblyCompare2019.cpp').read_text(encoding='utf-8')
    assert 'exportStep(6,buffer,&options)' in source
    assert 'DSAssemblyCompare2019Init' in source
    for command in ('DSCOMPARE','DSCOMPARE_A','DSCOMPARE_B','DSAC'):
        assert f'cmd("{command}"' in source
    for forbidden in ('cvxFileClose','cvxFileSave','cvxFileNew'):
        assert '"'+forbidden+'"' not in source

def test_workflow_builds_exe_and_dll():
    wf = (ROOT / '.github' / 'workflows' / 'build-dscompare-v30.yml').read_text(encoding='utf-8')
    assert '--collect-all OCP' in wf
    assert 'DSAssemblyCompare2019.dll' in wf
    assert 'DSCompareV3.exe' in wf
