"""R11.24 structural regression: native groups and optional ABSR-free flat twin."""
import json,os
from pathlib import Path
from tempfile import TemporaryDirectory
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCP.gp import gp_Trsf,gp_Vec
from OCP.TopLoc import TopLoc_Location
from dsac29.geometry import describe
from dsac29.compare import compare
from dsac29.step_io import export_revision_step,inspect_step_colors
from dsac29.step_diagnostics import inspect
from PySide6.QtWidgets import QApplication
from dsac29.gui46 import Window

def make(name,x):
    tr=gp_Trsf();tr.SetTranslation(gp_Vec(float(x),0,0))
    return describe(BRepPrimAPI_MakeBox(20,15,10).Shape().Located(TopLoc_Location(tr)),name,name)
a=[make('identyczna',0),make('usunieta',30)]
b=[make('identyczna',0),make('nowa',70)]
rows=compare(a,b,revision_only=True)
assert {'SAME','REMOVED','ADDED'}.issubset({r.status for r in rows}),rows
with TemporaryDirectory() as tmp:
    folder=Path(tmp)
    p=folder/'POROWNANIE_KOLORY.step'
    os.environ['DSCOMPARE_STEP_VERIFY']='full'
    os.environ['DSCOMPARE_ABSR_TEST_OUTPUT']='1'
    os.environ['DSCOMPARE_FLAT_FALLBACK']='0'
    diag=export_revision_step(str(p),rows,a,b)
    assert diag['grupowanie_zlozenia'] is True,diag
    assert p.is_file()
    report=p.with_name('POROWNANIE_KOLORY_DIAGNOSTYKA_STEP.json')
    assert report.is_file()
    root=json.loads(report.read_text(encoding='utf8'))
    assert root['liczba_produktow_step'] > root['realne_bryly_w_raporcie'],root
    assert root['wystapienia_manifold_solid_brep']>=root['realne_bryly_w_raporcie']
    assert root['produkty_z_nazwa_absr']==[]
    assert root['liczba_polaczen_podzlozen']>0
    twin=folder/'TEST_ABSR'/'STEP_BEZ_ABSR.step'
    assert twin.is_file(),diag
    twin_diag=inspect(twin)
    assert twin_diag['liczba_polaczen_podzlozen']==0,twin_diag
    assert twin_diag['liczba_produktow_step']==root['realne_bryly_w_raporcie'],twin_diag
    assert inspect_step_colors(str(twin))['elementy_bez_bryly']==0
    assert not (folder/'TEST_ABSR'/'BLAD_TESTU_ABSR.txt').exists()
    os.environ['DSCOMPARE_ABSR_TEST_OUTPUT']='0'
app=QApplication.instance() or QApplication([])
window=Window()
assert hasattr(window,'absr_test_output')
assert window.absr_test_output.isChecked() is False
window.close()
print('R11.24 PASS: native assembly intact; independent flat STEP has NO empty assembly products; diagnostic JSON and UI controls')
