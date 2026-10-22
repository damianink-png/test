"""R11.29 regression suite: no surplus STEP ABSR styling, compound wrapper and repeated-parts alignment."""
from pathlib import Path
import re
import numpy as np
import pytest
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCP.BRep import BRep_Builder
from OCP.TopoDS import TopoDS_Compound
from OCP.gp import gp_Trsf,gp_Vec
from OCP.TopLoc import TopLoc_Location
from dsac29.geometry import describe,equivalent_world
from dsac29.step_io import ColoredDocument,load_step
from dsac29.alignment import align_assembly
from dsac29.compare import compare
from dsac29.revision_rules import classify_revisions

def entities(path,name):
    data=Path(path).read_bytes()
    return len(re.findall(rb'(?m)^#\d+\s*=\s*'+name.encode()+rb'\(',data))

def part(name,x=0,y=0,length=17):
    shape=BRepPrimAPI_MakeBox(length,16,12).Shape()
    tr=gp_Trsf();tr.SetTranslation(gp_Vec(x,y,0))
    return describe(shape.Located(TopLoc_Location(tr)),name,name)

def test_no_surplus_anonymous_representations(monkeypatch,tmp_path):
    monkeypatch.setenv('DSCOMPARE_STEP_SCHEMA','AP214IS')
    monkeypatch.setenv('DSCOMPARE_STEP_VERIFY','full')
    doc=ColoredDocument(group_by_status=True,reuse_definitions=False)
    a=part('BEZ_ZMIAN');b=part('NOWA',55)
    doc.add(a.shape,a.name,(.1,.9,.3),group='SAME')
    doc.add(b.shape,b.name,(.2,.4,.9),group='ADDED')
    p=tmp_path/'colored.step';d=doc.write(p)
    assert d['puste_reprezentacje_step']==0
    assert d['kontrola_wstawien_bez_styli']
    assert entities(p,'SHAPE_REPRESENTATION')==d['podzlozenia_step']
    assert entities(p,'NEXT_ASSEMBLY_USAGE_OCCURRENCE')==d['powiazania_zlozenia']
    assert entities(p,'PRODUCT')==d['produkty_step']
    assert len(load_step(p))==2

def test_transparent_old_still_has_face_colors(tmp_path):
    doc=ColoredDocument(group_by_status=True,reuse_definitions=False)
    a=part('STARY',75)
    doc.add(a.shape,a.name,(.9,.2,.1),alpha=.4,group='REMOVED',revision='A')
    p=tmp_path/'old.step';d=doc.write(p)
    assert d['puste_reprezentacje_step']==0
    assert d['rekordy_przezroczystosci_step']>0
    assert d['powierzchnie_przezroczyste']>0
    assert entities(p,'SHAPE_REPRESENTATION')==d['podzlozenia_step']

def test_unwrap_single_solid_compound_keep_world_location(tmp_path):
    solid=BRepPrimAPI_MakeBox(29,13,9).Shape()
    comp=TopoDS_Compound();build=BRep_Builder();build.MakeCompound(comp);build.Add(comp,solid)
    shift=gp_Trsf();shift.SetTranslation(gp_Vec(96,33,10))
    located=comp.Located(TopLoc_Location(shift))
    original=describe(located,'KLIN','KLIN')
    doc=ColoredDocument(group_by_status=True)
    doc.add(located,'KLIN',(.3,.6,.7),group='SAME')
    p=tmp_path/'single.step';d=doc.write(p)
    out=load_step(p)
    assert d['puste_reprezentacje_step']==0
    assert len(out)==1 and equivalent_world(original,out[0],.01)
    assert np.linalg.norm(out[0].center-original.center)<1.e-5

def test_strict_multisolid_compound_rejected(monkeypatch):
    monkeypatch.setenv('DSCOMPARE_STRICT_SOLIDS','1')
    comp=TopoDS_Compound();build=BRep_Builder();build.MakeCompound(comp)
    build.Add(comp,BRepPrimAPI_MakeBox(10,11,12).Shape())
    build.Add(comp,BRepPrimAPI_MakeBox(13,14,15).Shape())
    doc=ColoredDocument(group_by_status=True)
    with pytest.raises(ValueError,match='DSCOMPARE_STRICT_SOLIDS'):
        doc.add(comp,'KILKA',(.1,.2,.3),group='SAME')

def test_align_repeated_identical_geometry_with_one_truly_moved():
    a=[part('POWTARZALNY',i*37,i*11,18) for i in range(8)]
    b=[part('POWTARZALNY',i*37+100,i*11+30+(6 if i==7 else 0),18) for i in range(8)]
    aligned,info=align_assembly(a,b,.01)
    assert info['enabled'] and info['method']=='repeated_translation_consensus'
    assert np.allclose(info['translation_B_to_A_mm'],[-100,-30,0],atol=.01)
    records=compare(a,aligned,.01,revision_only=True,exact_serialization=True)
    classified=classify_revisions(a,aligned,records,.01)
    assert sum(r.status=='SAME' for r in classified)==7,[(r.status,r.a_index,r.b_index) for r in classified]
    assert sum(r.status=='MOVED' for r in classified)==1
