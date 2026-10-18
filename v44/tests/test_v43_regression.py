import json,csv
import numpy as np
import pytest
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from dsac29.geometry import describe
from dsac29.compare import compare,_CenterAxisIndex
from dsac29.report import produce
from dsac29 import review43


def part(x=20,name='P',move=(0,0,0)):
    from OCP.gp import gp_Vec
    from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
    from OCP.gp import gp_Trsf
    shape=BRepPrimAPI_MakeBox(x,10,10).Shape()
    tr=gp_Trsf();tr.SetTranslation(gp_Vec(*move))
    return describe(BRepBuilderAPI_Transform(shape,tr,True).Shape(),name,name)


def test_index_never_loses_candidates_even_on_degenerate_axes():
    parts=[part(20,str(i),(i%13,0,i//13)) for i in range(150)]
    idx=_CenterAxisIndex(parts,range(len(parts)))
    for p in parts[::4]:
        for radius in (0.1,1.5,10.,55.):
            expected={i for i,b in enumerate(parts) if np.linalg.norm(p.center-b.center)<=radius}
            assert set(idx.query(p,radius))==expected


def fixture(tmp_path):
    a=[part(11,'A0'),part(14,'A1', (150,0,0)),part(18,'A2',(300,0,0))]
    b=[part(10,'B0'),part(25,'B1',(180,0,0)),part(18,'A2',(300,0,0))]
    # Fix decisions explicitly, independent of automatic matching implementation.
    from dsac29.compare import Record
    recs=[Record(0,0,'UNCERTAIN','Mogą być powiązane'),Record(1,None,'REMOVED','Brak'),
          Record(None,1,'ADDED','Brak'),Record(2,2,'SAME','Zgodne')]
    produce(tmp_path,a,b,recs,generate_step=False,diff_step=False,progress=None)
    return recs


def test_review_confirms_without_overwriting_original(tmp_path):
    fixture(tmp_path)
    original=(tmp_path/'PODSUMOWANIE.json').read_bytes()
    rows=(tmp_path/'ZMIANY.csv').read_bytes()
    doc=review43.confirm(tmp_path,0,0,'Sprawdzono na rysunku')
    assert len(doc['decisions'])==1
    doc=review43.confirm(tmp_path,1,1,'Porównano osie')
    assert doc['decisions'][-1]['kind']=='manual_pair'
    assert (tmp_path/'PODSUMOWANIE.json').read_bytes()==original
    assert (tmp_path/'ZMIANY.csv').read_bytes()==rows
    with (tmp_path/review43.CSVFILE).open(encoding='utf-8-sig',newline='') as f:
        reviewed=list(csv.DictReader(f,delimiter=';'))
    assert reviewed[1]['Ręczna para A/B']=='A#1 ↔ B#1'
    assert reviewed[2]['Decyzja użytkownika']
    assert len(reviewed)==4
    review43.revoke(tmp_path,1,1)
    assert len(review43.load(tmp_path)['decisions'])==1


def test_review_refuses_conflicts_wrong_inputs_and_stale_report(tmp_path):
    fixture(tmp_path)
    review43.confirm(tmp_path,1,1)
    for a,b in [(1,0),(0,1),(2,2),(-1,1),(0,2)]:
        with pytest.raises(review43.ReviewError):review43.confirm(tmp_path,a,b)
    s=tmp_path/'PODSUMOWANIE.json'
    doc=json.loads(s.read_text(encoding='utf-8'))
    doc['solids_A']=99;s.write_text(json.dumps(doc),encoding='utf-8')
    with pytest.raises(review43.ReviewError):review43.load(tmp_path)


def test_matching_automatic_still_covers_each_occurrence():
    a=[part(20,'X', (i*100,0,0)) for i in range(75)]
    b=[part(20,'X',(i*100,0,0)) for i in range(75)]
    b[27]=part(19,'Y',(2700,0,0))
    records=compare(a,b)
    assert {x.a_index for x in records if x.a_index is not None}==set(range(75))
    assert {x.b_index for x in records if x.b_index is not None}==set(range(75))
    assert len(records)<=77


def test_qt_manual_review_markers_and_no_source_mutation(tmp_path,monkeypatch):
    pytest.importorskip('PySide6')
    from PySide6.QtWidgets import QApplication
    from dsac29 import gui_qt37 as ui
    monkeypatch.setattr(ui,'_settings_path',lambda:tmp_path/'settings.json')
    app=QApplication.instance() or QApplication([])
    source=tmp_path/'compare';source.mkdir()
    fixture(source)
    w=ui.Window();w.result_dir=source;w.load_summary()
    assert w.table.rowCount()==4
    review43.confirm(source,0,0,'Zatwierdzone')
    w.load_summary()
    assert w.review_decisions and 'Potwierdzone' not in w.table.item(0,0).text()
    assert any('Powiązanie ręcznie potwierdzone' in w.table.item(j,4).text() for j in range(w.table.rowCount()))
    assert all(r['status'] in ('UNCERTAIN','REMOVED','ADDED','SAME') for r in w.result_records)
    w.close()
