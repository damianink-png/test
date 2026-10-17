import json
import numpy as np
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from dsac29.geometry import describe,transform
from dsac29.compare import compare,Record
from dsac29.scene42 import make_result_scene,make_detail,metadata

def part(x=20,name='P'):
    return describe(BRepPrimAPI_MakeBox(x,10,10).Shape(),name,name)

def test_shortened_renamed_profile_uses_overlap():
    a=part(100,'profile-old');b=part(90,'profile-new')
    r=compare([a],[b])[0]
    assert r.status=='CHANGED' and 'wspólna objętość' in r.note
    assert 'Heurystyka' in r.confidence

def test_ambiguous_overlap_never_confirmed_pair():
    r=compare([part(100,'A'),part(100,'B')],[part(90,'C'),part(90,'D')])
    assert all(x.status=='UNCERTAIN' for x in r)

def test_scene_has_old_and_new_and_lazy_difference(tmp_path):
    a=part(20);b=part(18)
    info=make_result_scene([a],[b],[Record(0,0,'CHANGED','test')],tmp_path)
    assert info['complete'] and info['bodies']==2 and info['rendered_records']==1
    with np.load(tmp_path/'SCENA_WYNIK.npz') as f:
        assert list(f['roles'])==['B','A']
        assert all(metadata(x)[1]==0 for x in f['names'])
    out=make_detail(tmp_path,0)
    with np.load(out/'SCENA_WYNIK.npz') as f:
        assert len(f['names'])==1 and metadata(f['names'][0])[0]=='REMOVED'
        assert f['vertices'][:,0].min()>=17.99

def test_missing_mesh_is_reported(tmp_path,monkeypatch):
    import dsac29.scene42 as scene
    monkeypatch.setattr(scene,'_faces_meshed',lambda *args:[])
    info=make_result_scene([],[part()],[Record(None,0,'ADDED','')],tmp_path)
    assert not info['complete'] and info['rendered_records']==0 and len(info['errors'])==1

def test_mass_mapping_matches_rows_and_scene(tmp_path):
    from dsac29.single_mass import analyze_single
    from pathlib import Path
    out,s=analyze_single(Path(__file__).resolve().parents[1]/'samples/MODEL_A.step',tmp_path)
    mapping=json.loads((out/'MASA_MAPA.json').read_text())
    assert len(mapping)==s['liczba_pozycji']
    assert sorted(i for group in mapping for i in group)==list(range(s['liczba_bryl']))
    with np.load(out/'SCENA_WYNIK.npz') as f:assert len(f['names'])==s['liczba_bryl']

def test_export_validated_once(tmp_path,monkeypatch):
    import dsac29.step_io as io
    from dsac29.report import produce
    original=io.inspect_step_colors;calls=[]
    def spy(*a,**kw):calls.append(a);return original(*a,**kw)
    monkeypatch.setattr(io,'inspect_step_colors',spy)
    p=part();produce(tmp_path,[p],[p],[Record(0,0,'SAME','')],diff_step=False)
    assert len(calls)==1

def test_gui_filters_preserve_records(tmp_path,monkeypatch):
    from PySide6.QtWidgets import QApplication
    import dsac29.gui_qt37 as ui
    from dsac29.cli import process
    from pathlib import Path
    monkeypatch.setattr(ui,'_settings_path',lambda:tmp_path/'settings.json')
    app=QApplication.instance() or QApplication([])
    source=Path(__file__).resolve().parents[1]/'samples'
    out,_,_=process(source/'MODEL_A.step',source/'MODEL_B.step',tmp_path/'result',step=False,diff_step=False,progress=None)
    w=ui.Window();w.result_dir=out;w.load_summary();n=w.table.rowCount()
    w.category_checks['CHANGED'].setChecked(False)
    assert w.table.rowCount()==n and not w.write_step.isChecked() and not w.make_diff.isChecked()
    for row in range(n):
        idx=w.table.item(row,0).data(ui.Qt.UserRole)
        if w.result_records[idx]['status']=='CHANGED':assert w.table.isRowHidden(row)
    w.close()

def test_mesh_worker_does_not_clear_analysis_log(tmp_path,monkeypatch):
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import QProcess
    import dsac29.gui_qt37 as ui
    monkeypatch.setattr(ui,'_settings_path',lambda:tmp_path/'settings.json')
    monkeypatch.setattr(QProcess,'start',lambda *a,**k:None)
    app=QApplication.instance() or QApplication([])
    w=ui.Window();w.log.setPlainText('Analiza A/B zakończona')
    w.result_records=[{'status':'SAME'}]
    w.launch_worker('mesh',[],tmp_path/'mesh')
    assert w.log.toPlainText()=='Analiza A/B zakończona'
    assert w.result_records==[{'status':'SAME'}]
    w.worker_timer.stop();w.close()
