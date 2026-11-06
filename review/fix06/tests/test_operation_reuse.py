import numpy as np
import pytest
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from dsac29 import geometry,report,preview3d,cad_registration,cad_pose_search
from dsac29.geometry_registry import GeometryRegistry
from dsac29.compare import Record
from dsac29.material_deltas import calculate
from test_cad_pose_search import case


def test_bom_reuses_completed_rigid_proof_without_serializing_again(monkeypatch):
    a=geometry.describe(BRepPrimAPI_MakeBox(20,10,7).Shape(),'A','A')
    b=geometry.describe(BRepPrimAPI_MakeBox(20,10,7).Shape(),'B','B')
    ctx=GeometryRegistry();ctx.remember_equivalence(a,b,.01)
    monkeypatch.setattr(ctx,'exact_digest',lambda *a:pytest.fail('Completed proof must not require another B-Rep serialization'))
    assert report.geometry_groups([a,b],context=ctx,fast_proven_only=True)==[[0,1]]


def test_dual_common_preview_reuses_geometry_properties_but_keeps_both_names(tmp_path,monkeypatch):
    a=geometry.describe(BRepPrimAPI_MakeBox(20,10,7).Shape(),'OLD_NAME','old')
    b=geometry.describe(BRepPrimAPI_MakeBox(20,11,7).Shape(),'NEW_NAME','new')
    regions=calculate(a,b,.01);calls=[];original=geometry.describe
    def count(*args,**kwargs):calls.append(1);return original(*args,**kwargs)
    monkeypatch.setattr(geometry,'describe',count)
    path=tmp_path/'preview.html'
    info=preview3d.create_preview(path,[Record(0,0,'CHANGED','')],[a],[b],
        material_regions={0:regions},dual_revisions=True)
    assert len(calls)==2
    assert info['elementy']==3
    text=path.read_text();assert 'OLD_NAME' in text and 'NEW_NAME' in text


def test_expired_body_budget_does_not_build_unused_hypotheses(monkeypatch):
    from time import monotonic
    a,b,rows,_,_=case(n=18,rotated=False);clock=[monotonic()];place=cad_registration.place_for_proof
    monkeypatch.setattr(cad_registration,'monotonic',lambda:clock[0])
    def expire(*args):
        result=place(*args);clock[0]+=61;return result
    monkeypatch.setattr(cad_registration,'place_for_proof',expire)
    monkeypatch.setattr(cad_pose_search,'hypotheses',lambda *a,**kw:pytest.fail('Hypotheses generated after their verification budget expired'))
    result=cad_registration.propose(a,b,rows,.01)
    assert result['status']=='unresolved'


def test_surface_candidate_cache_keeps_surface_kinds_separate():
    from types import SimpleNamespace
    parts=[SimpleNamespace(area=10.,volume=10.,feature_kind=(kind,1,4),name='same')
           for kind in ('Plane','Cylinder')]
    points=np.array([[0.,0.,0.],[50.,20.,5.]])
    pairs=cad_pose_search.correspondences(parts,parts,points,points)
    assert set(pairs)=={(0,0),(1,1)}
