"""Regression: AP203 is metadata; avoid repeated translation integration.

All SAME decisions still need independent native B-Rep evidence. The
original-frame certified stage-1 pairs are reused only when NOT relocated.
"""
from dataclasses import replace
import numpy as np
import pytest
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCP.gp import gp_Pnt
from dsac29 import cad_registration,cli,step_diagnostics
from dsac29.compare import Record
from dsac29.geometry import describe, equivalent_world
from dsac29.alignment import _relocate


@pytest.mark.parametrize('text,expected',[
    ("FILE_SCHEMA(('CONFIG_CONTROL_DESIGN'));",'AP203'),
    ("FILE_SCHEMA ( ( 'AP203_CONFIGURATION_CONTROLLED_3D_DESIGN_OF_MECHANICAL_PARTS_AND_ASSEMBLIES_MIM_LF' ));",'AP203'),
    ("FILE_SCHEMA(('AUTOMOTIVE_DESIGN'));",'AP214'),
    ("FILE_SCHEMA(('AP242_MANAGED_MODEL_BASED_3D_ENGINEERING_MIM_LF'));",'AP242'),
    ("FILE_SCHEMA(('UNRECOGNIZED'));",'unknown'),
])
def test_step_application_protocol_is_detected_only_from_header(tmp_path,text,expected):
    p=tmp_path/'zw3d.step'
    p.write_text("ISO-10303-21;\nHEADER;\n"+text+"\nENDSEC;\nDATA;",encoding='ascii')
    out=step_diagnostics.schema_header(p)
    assert out['application_protocol']==expected
    assert step_diagnostics._schema_from_bytes(p.read_bytes())==out


def test_zero_pose_does_not_copy_or_reintegrate_shape(monkeypatch):
    p=describe(BRepPrimAPI_MakeBox(10,20,30).Shape(),'PLATE','PLATE')
    def forbidden(*args,**kwargs):raise AssertionError('identity pose must not relocate')
    monkeypatch.setattr(cad_registration,'_relocate',forbidden)
    unchanged=cad_registration.place_for_proof(p,np.eye(3),np.zeros(3))
    assert unchanged is p


def test_many_pure_translations_skip_legacy_integral(monkeypatch):
    p=describe(BRepPrimAPI_MakeBox(10,20,30).Shape(),'PLATE','PLATE')
    def forbidden(*args,**kwargs):raise AssertionError('translation must not recompute integral')
    monkeypatch.setattr(cad_registration,'_relocate',forbidden)
    for shift in ([130,280,524],[-130,-280,-524],[0,0,0]):
        t=np.array(shift,float)
        placed=cad_registration.place_for_proof(p,np.eye(3),t)
        actual=_relocate(p,np.eye(3),t)
        assert np.allclose(placed.center,actual.center,atol=1e-6)
        assert placed.volume==pytest.approx(actual.volume,rel=1e-8)
        assert placed.area==pytest.approx(actual.area,rel=1e-8)
        assert equivalent_world(placed,actual,.01)
        if not np.any(t):assert placed is p


def test_original_frame_keeps_same_instances_and_carries_only_certified_world_proofs():
    entries=[object() for _ in range(150)]
    def forbidden(*args,**kwargs):raise AssertionError('already aligned must not relocate')
    result=cli._use_confirmed_frame(entries,{'status':'already_aligned'},forbidden)
    assert result is entries
    proven=[Record(i,i,'SAME','Native B-Rep') for i in range(149)]
    proven.append(Record(149,149,'UNCERTAIN','Face hint is not solid proof'))
    assert cli._reused_world_pairs([],proven,{'status':'already_aligned'})==[(i,i) for i in range(149)]
    assert cli._reused_world_pairs([],proven,{'status':'registered'})==[]
    assert cli._reused_world_pairs([(5,5)],proven,{'status':'already_aligned'})==[(i,i) for i in range(149)]


def test_nonzero_frame_still_calls_proper_relocation():
    p=object()
    calls=[]
    def relocate(part,r,t):
        calls.append((part,r.copy(),t.copy()))
        return object()
    a=cli._use_confirmed_frame([p],{'status':'registered',
        'rotation_B_to_A':np.eye(3).tolist(),
        'translation_B_to_A_mm':[-130,-280,-524]},relocate)
    assert a[0] is not p and len(calls)==1
    assert np.allclose(calls[0][2],[-130,-280,-524])
