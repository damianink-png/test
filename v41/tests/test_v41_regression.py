import csv
import numpy as np
import pytest
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from dsac29.geometry import describe,transform
from dsac29.compare import compare
from dsac29.report import _bill,write_csv,_fmt
from dsac29.names import technical

def part(name='Part',origin='explicit'):
    p=describe(BRepPrimAPI_MakeBox(10,20,30).Shape(),name,name)
    p.name_origin=origin
    return p

def test_exporter_name_is_not_engineering_rename():
    a=part('pedestal v2:1');b=part('base_plate.step','definition_fallback')
    assert compare([a],[b])[0].status=='SAME'
    assert compare([a],[part('new_design')])[0].status=='RENAMED'
    assert technical('NAUO528') and not technical('04244036')

def test_geometric_bill_preserves_all_occurrences():
    a=part('A');b=part('B')
    b=describe(transform(b.shape,np.eye(3),np.array([100.,0.,0.])),b.name,b.path)
    rows=_bill([a,b],7850)
    assert len(rows)==1 and rows[0][1]==2
    assert rows[0][4]==pytest.approx(2*6000*1e-9*7850,abs=1e-5)

def test_negative_measurement_is_numeric_but_names_are_escaped(tmp_path):
    f=tmp_path/'x.csv';write_csv(f,['delta','name'],[[_fmt(-12.3456),'=1+1']])
    rows=list(csv.reader(f.open(encoding='utf-8-sig'),delimiter=';'))
    assert rows[1]==['-12,3456',"'=1+1"]

def test_alignment_without_common_names():
    from dsac29.alignment import align_assembly
    a=[describe(transform(BRepPrimAPI_MakeBox(10+i,20,30).Shape(),np.eye(3),np.array([i*50.,i*i*30.,0.])),f'A{i}',f'A{i}') for i in range(3)]
    b=[describe(transform(p.shape,np.eye(3),np.array([100.,200.,300.])),f'B{i}',f'B{i}') for i,p in enumerate(a)]
    for p in b:p.name_origin='definition_fallback'
    aligned,info=align_assembly(a,b)
    assert info['votes']==3
    assert all(p.name_origin=='definition_fallback' for p in aligned)
    assert all(r.status=='SAME' for r in compare(a,aligned))

def test_unavailable_alignment_finishes_with_visible_warning(tmp_path,monkeypatch):
    import dsac29.cli as cli
    from dsac29.alignment import AlignmentUnavailable
    import dsac29.alignment as alignment
    def unavailable(*a,**kw):raise AlignmentUnavailable('Test niejednoznaczności')
    monkeypatch.setattr(alignment,'align_assembly',unavailable)
    monkeypatch.setattr(cli,'load_step',lambda *a,**kw:[part()])
    folder,recs,err=cli.process('a.step','b.step',tmp_path,step=False,diff_step=False,align=True,progress=None)
    assert err is None and recs[0].status=='SAME'
    assert 'Porównano oryginalne' in (folder/'RAPORT.html').read_text()
    assert (folder/'OSTRZEZENIA.txt').is_file()

def test_step_reader_uses_definition_instead_of_nauo(tmp_path):
    from dsac29.step_io import ColoredDocument,load_step
    from OCP.TDF import TDF_LabelSequence
    from OCP.TDataStd import TDataStd_Name
    from OCP.TCollection import TCollection_ExtendedString
    doc=ColoredDocument();doc.add(part().shape,'base_plate.step',(0.2,0.6,0.3))
    comps=TDF_LabelSequence();doc.tool.GetComponents_s(doc.root,comps)
    TDataStd_Name.Set_s(comps.Value(1),TCollection_ExtendedString('NAUO528'))
    f=tmp_path/'nauo.step';doc.write(f)
    imported=load_step(f)
    assert imported[0].name=='base_plate.step'
    assert imported[0].name_origin=='definition_fallback'

def test_identical_brep_definitions_group_without_repeated_boolean(monkeypatch):
    import dsac29.geometry as geometry
    from dsac29.report import geometry_groups
    from OCP.BRepBuilderAPI import BRepBuilderAPI_Copy
    a=part('A')
    b=describe(BRepBuilderAPI_Copy(a.shape).Shape(),'B','B')
    def unexpected(*args,**kwargs):raise AssertionError('Exact B-Rep must use the cache')
    monkeypatch.setattr(geometry,'equivalent_rigid',unexpected)
    assert geometry_groups([a,b])==[[0,1]]
