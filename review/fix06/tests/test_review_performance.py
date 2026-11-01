"""Optimization regressions must preserve evidence and exact STEP checks."""
import re
from pathlib import Path
import numpy as np
import pytest
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCP.BRepBuilderAPI import BRepBuilderAPI_Copy
from OCP.TopLoc import TopLoc_Location
from OCP.gp import gp_Trsf,gp_Vec
from dsac29.geometry import describe
from dsac29.registration_gate import frame_support,FrameProofCache
from dsac29.step_structure import structure_counts,mapped_step


def repeated_pairs():
    bases=[BRepPrimAPI_MakeBox(width,12,14).Shape() for width in (10,10.0001)]
    arrays=[]
    for shape in bases:
        parts=[]
        for i in range(12):
            tr=gp_Trsf();tr.SetTranslation(gp_Vec(i*100.,0,0))
            independent=BRepBuilderAPI_Copy(shape,True,False).Shape().Moved(TopLoc_Location(tr))
            parts.append(describe(independent,'part','part'))
        arrays.append(parts)
    return arrays


def test_exact_topology_alias_reuses_only_completed_full_world_proof(monkeypatch):
    from dsac29 import step_reexport_tolerance as step
    a,b=repeated_pairs();calls=[];original=step.reexport_equivalent_world
    def proof(*args,**kw):calls.append(1);return original(*args,**kw)
    monkeypatch.setattr(step,'reexport_equivalent_world',proof)
    cache=FrameProofCache();r=frame_support(a,b,.01,verify_all=True,proof_cache=cache)
    assert r['count']==12 and len(calls)==1 and cache.exact_anchor_hits==11
    # A placement mismatch cannot inherit the proof, even for identical definitions.
    from dsac29.alignment import _relocate
    b[-1]=_relocate(b[-1],np.eye(3),np.array([.05,0,0]))
    r=frame_support(a,b,.01,verify_all=True,proof_cache=FrameProofCache())
    assert r['count']==11


def test_failed_or_inconclusive_proof_is_never_an_alias(monkeypatch):
    from dsac29 import step_reexport_tolerance as step
    from dsac29 import registration_gate as gate
    a,b=repeated_pairs();calls=[]
    monkeypatch.setattr(step,'reexport_equivalent_world',lambda *args,**kw:calls.append(1) or False)
    monkeypatch.setattr(gate,'equivalent_world',lambda *args:False)
    cache=FrameProofCache();r=frame_support(a,b,.01,verify_all=True,proof_cache=cache)
    assert r['count']==0 and len(calls)==12 and cache.exact_anchor_hits==0 and not cache.exact_anchors


def test_mapped_step_structure_retains_byte_count_and_regex_semantics(tmp_path,monkeypatch):
    data=b"ISO-10303-21;\n#1=PRODUCT('x','','',());\n#2 =\nNEXT_ASSEMBLY_USAGE_OCCURRENCE();\n#3=SHAPE_REPRESENTATION();\n#4=COLOUR_RGB('x',1.,0.,0.);\n#5=STYLED_ITEM();\n#6=SURFACE_STYLE_TRANSPARENT(.4);\n"*200
    file=tmp_path/'large.step';file.write_bytes(data)
    expected={'colors':data.count(b'COLOUR_RGB('),'styles':data.count(b'STYLED_ITEM('),'alpha':data.count(b'SURFACE_STYLE_TRANSPARENT(')}
    for key,token in [('products',b'PRODUCT'),('usages',b'NEXT_ASSEMBLY_USAGE_OCCURRENCE'),('representations',b'SHAPE_REPRESENTATION')]:expected[key]=len(re.findall(rb'(?m)^#\d+\s*=\s*'+token+rb'\(',data))
    def forbidden(*a,**k):raise AssertionError('Whole-file allocation')
    monkeypatch.setattr(Path,'read_bytes',forbidden)
    assert structure_counts(file)==expected
    file.rename(tmp_path/'renamed.step')  # Also checks closed mappings on Windows.


def test_mapped_empty_file_and_exception_release_handles(tmp_path):
    file=tmp_path/'empty.step';file.write_bytes(b'');assert not any(structure_counts(file).values())
    file.write_bytes(b'ISO-10303-21;')
    with pytest.raises(RuntimeError):
        with mapped_step(file):raise RuntimeError('test')
    file.unlink()


def test_ci_source_oracles_reject_changed_bytes_and_incomplete_exe_results():
    import sys
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'ci'))
    from fixture_oracles import expected_count,verify_counts,ORACLES
    revision='e47cc70edbdb0c36916885b54a5e1f30f52a717a'
    digest,count=ORACLES[revision]
    assert expected_count(revision,digest)==1707
    with pytest.raises(AssertionError):expected_count(revision,'0'*64)
    verify_counts({'solids_A':1707,'solids_B':1715},1707,1715)
    with pytest.raises(AssertionError):verify_counts({'solids_A':1706,'solids_B':1715},1707,1715)
    with pytest.raises(AssertionError):verify_counts({'solids_A':True,'solids_B':1715},1707,1715)
