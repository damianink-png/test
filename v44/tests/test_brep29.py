import math
from pathlib import Path
import numpy as np
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox,BRepPrimAPI_MakeCylinder
from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut
from OCP.gp import gp_Pnt, gp_Ax2, gp_Dir
from dsac29.geometry import describe,transform,equivalent_world,equivalent_rigid,candidate,difference
from dsac29.compare import compare
from dsac29.step_io import export_colored_step,load_step
from dsac29.report import produce
from dsac29.compare import Record


def box(x=0,y=0,z=0,sx=100,sy=60,sz=10):
    return BRepPrimAPI_MakeBox(gp_Pnt(x,y,z),sx,sy,sz).Shape()

def plate_with_hole(offset=0):
    base=box(0,0,0,120,80,10)
    bore=BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(25+offset,25,-2),gp_Dir(0,0,1)),8,14).Shape()
    result=BRepAlgoAPI_Cut(base,bore); result.Build();assert result.IsDone()
    return result.Shape()

def part(sh,name):return describe(sh,name,name)

def test_same_shape_renamed():
    a=[part(box(),'ABC')];b=[part(box(),'CBA')]
    result=compare(a,b)
    assert len(result)==1 and result[0].status=='RENAMED'

def test_identical_moved_and_rotated():
    a=part(box(),'profile')
    b=part(transform(box(),np.eye(3),np.array([100.,50.,0.])), 'renamed_profile')
    assert not equivalent_world(a,b)
    eq,_,_=equivalent_rigid(a,b)
    assert eq
    result=compare([a],[b]);assert result[0].status=='MOVED'

def test_moved_hole_equal_volume_but_not_equal_geometry():
    old=part(plate_with_hole(0),'PLYTA_08');new=part(plate_with_hole(4),'PLYTA_08')
    assert math.isclose(old.volume,new.volume,rel_tol=1e-9)
    assert not equivalent_world(old,new)
    assert not equivalent_rigid(old,new)[0]
    statuses=[r.status for r in compare([old],[new])]
    assert statuses==['CHANGED'],statuses

def test_removed_added_and_no_duplicate():
    a=[part(box(),'k1'),part(box(200,0,0),'k2')]
    b=[part(box(200,0,0),'nowe_nazwanie'),part(box(500,0,0,sx=30,sy=20,sz=10),'dodany')]
    rec=compare(a,b)
    assert set(r.status for r in rec)=={'RENAMED','REMOVED','ADDED'}
    assert sum(r.a_index is not None for r in rec)==2
    assert sum(r.b_index is not None for r in rec)==2

def test_two_overlapping_identical_parts_no_wrong_ghost():
    # Four occurrences (including overlap) must be paired distinctly.
    a=[part(box(0,0),'one'),part(box(0,0),'two'),part(box(100,0),'three')]
    b=[part(box(0,0),'A'),part(box(100,0),'B'),part(box(0,0),'C')]
    rec=compare(a,b)
    assert len(rec)==3
    assert all(r.status in ('RENAMED','SAME') for r in rec)

def test_color_export_roundtrip_names(tmp_path):
    a=[part(box(),'abc')]
    b=[part(box(),'cba')]
    records=compare(a,b)
    out=tmp_path/'model.step'
    export_colored_step(str(out),records,a,b)
    assert out.stat().st_size>500
    solids=load_step(str(out))
    assert len(solids)==1
    assert 'RENAMED' in solids[0].name

def test_reports(tmp_path):
    a=[part(box(),'one')];b=[part(box(),'two')]
    rec=compare(a,b)
    out,err=produce(tmp_path,a,b,rec,density=7850.)
    assert err is None
    assert (out/'RAPORT.html').is_file()
    assert (out/'BOM_A.csv').is_file()
    assert (out/'BOM_B.csv').is_file()
    assert 'one' in (out/'ZMIANY.csv').read_text(encoding='utf-8-sig')

if __name__=='__main__':
    import pytest
    raise SystemExit(pytest.main([__file__,'-v']))

def test_step_colors_survive_round_trip(tmp_path):
    from OCP.XCAFDoc import XCAFDoc_DocumentTool, XCAFDoc_ColorType
    from OCP.TDocStd import TDocStd_Document
    from OCP.TCollection import TCollection_ExtendedString
    from OCP.TDF import TDF_LabelSequence,TDF_Label
    from OCP.STEPCAFControl import STEPCAFControl_Reader
    from OCP.Quantity import Quantity_Color
    a=[part(box(),'old')];b=[part(box(),'new')]
    out=tmp_path/'colors.step'
    export_colored_step(str(out),compare(a,b),a,b)
    d=TDocStd_Document(TCollection_ExtendedString('BinXCAF'))
    rd=STEPCAFControl_Reader();rd.SetColorMode(True)
    assert rd.ReadFile(str(out)).name=='IFSelect_RetDone'
    assert rd.Transfer(d)
    ct=XCAFDoc_DocumentTool.ColorTool_s(d.Main())
    st=XCAFDoc_DocumentTool.ShapeTool_s(d.Main())
    sq=TDF_LabelSequence();st.GetFreeShapes(sq)
    assert sq.Length()==1
    col=Quantity_Color()
    components=TDF_LabelSequence();st.GetComponents_s(sq.Value(1),components)
    definition=TDF_Label();assert st.GetReferredShape_s(components.Value(1),definition)
    assert ct.GetColor(st.GetShape_s(definition),XCAFDoc_ColorType.XCAFDoc_ColorSurf,col)
    assert col.Green()>col.Red()
