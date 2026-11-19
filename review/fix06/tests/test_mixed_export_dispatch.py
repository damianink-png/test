from collections import Counter
from dataclasses import replace
import numpy as np
from OCP.BRepPrimAPI import BRepPrimAPI_MakeCylinder
from OCP.BRepBuilderAPI import BRepBuilderAPI_NurbsConvert
from dsac29.geometry import describe, transform
from dsac29 import compare as comparator
from dsac29.original_boundary import equivalent


def family(shape, count=8):
    return [describe(transform(shape,np.eye(3),np.array([i*30.,0.,0.])),
                     'PART_afm0',str(i)) for i in range(count)]


def test_mixed_repeats_prove_once_before_common(monkeypatch):
    a=BRepPrimAPI_MakeCylinder(5,10).Shape()
    b=BRepBuilderAPI_NurbsConvert(a,True).Shape()
    calls=[]
    def full(left,right,tol,**kwargs):
        calls.append(1)
        assert kwargs['allow_solid_set_proof']
        return equivalent(left.shape,right.shape,tol)
    def forbidden(*args,**kwargs):
        raise AssertionError('Mixed representations must reach boundary proof before Common')
    monkeypatch.setattr(comparator,'guarded_world_reexport',full)
    monkeypatch.setattr(comparator,'equivalent_world',forbidden)
    result=comparator.compare(family(a),family(b),revision_only=True)
    assert Counter(r.status for r in result)=={'SAME':8}
    assert len(calls)==1


def test_small_mixed_export_centroid_drift_is_only_lookup_hint(monkeypatch):
    a=BRepPrimAPI_MakeCylinder(5,10).Shape()
    b=BRepBuilderAPI_NurbsConvert(a,True).Shape()
    left,right=family(a,1),family(b,1)
    # Different STEP integrations change centroid, not the actual surfaces.
    right=[replace(right[0],center=right[0].center+np.array([.15,0.,0.]))]
    monkeypatch.setattr(comparator,'guarded_world_reexport',
                        lambda x,y,t,**kw:equivalent(x.shape,y.shape,t))
    result=comparator.compare(left,right,revision_only=True)
    assert [r.status for r in result]==['SAME']


def test_mixed_export_does_not_hide_local_move(monkeypatch):
    a=BRepPrimAPI_MakeCylinder(5,10).Shape()
    b=BRepBuilderAPI_NurbsConvert(a,True).Shape()
    left,right=family(a),family(b)
    right[-1]=describe(transform(right[-1].shape,np.eye(3),np.array([.2,0.,0.])),
                       right[-1].name,right[-1].path)
    monkeypatch.setattr(comparator,'guarded_world_reexport',
                        lambda x,y,t,**kw:equivalent(x.shape,y.shape,t))
    result=comparator.compare(left,right,revision_only=True)
    assert sum(r.status=='SAME' for r in result)==7
    assert not any(r.status=='SAME' and r.a_index==7 for r in result)


def test_real_isolated_mixed_pair():
    from dsac29.native_guard import guarded_world_reexport
    a=BRepPrimAPI_MakeCylinder(5,10).Shape()
    b=BRepBuilderAPI_NurbsConvert(a,True).Shape()
    assert guarded_world_reexport(family(a,1)[0],family(b,1)[0],.01,
                                  allow_solid_set_proof=True,timeout_s=25)


def test_changed_mixed_repeats_keep_common_material():
    from dsac29.geometry_registry import GeometryRegistry
    from dsac29.revision_rules import classify_revisions
    from dsac29.revision_overlap import merge_material_revisions
    old=family(BRepPrimAPI_MakeCylinder(5,10).Shape())
    new=family(BRepBuilderAPI_NurbsConvert(BRepPrimAPI_MakeCylinder(5,11).Shape(),True).Shape())
    context=GeometryRegistry()
    records=comparator.compare(old,new,revision_only=True,geometry_context=context)
    records=classify_revisions(old,new,records,geometry_first=True,geometry_context=context)
    result,regions,stats=merge_material_revisions(old,new,records,geometry_context=context,
                                                review_approval=lambda _:'review')
    assert Counter(r.status for r in result)=={'CHANGED':8}
    assert stats['accepted']==8
    assert regions


def test_nurbs_properties_match_analytic_mass_center_and_inertia():
    import pytest
    analytic=BRepPrimAPI_MakeCylinder(5,11).Shape()
    a=describe(analytic,'analytic','a')
    b=describe(BRepBuilderAPI_NurbsConvert(analytic,True).Shape(),'nurbs','b')
    assert b.volume==pytest.approx(np.pi*25*11,rel=1e-7)
    assert b.volume==pytest.approx(a.volume,rel=1e-7)
    assert b.area==pytest.approx(a.area,rel=1e-7)
    assert b.center==pytest.approx(a.center,abs=1e-6)
    assert b.eigenvalues==pytest.approx(a.eigenvalues,rel=1e-6)


def test_mixed_common_cut_volume_balance():
    import pytest
    from dsac29.material_deltas import calculate
    a=describe(BRepPrimAPI_MakeCylinder(5,10).Shape(),'part','a')
    b=describe(BRepBuilderAPI_NurbsConvert(BRepPrimAPI_MakeCylinder(5,11).Shape(),True).Shape(),'part','b')
    regions=calculate(a,b,.01)
    assert regions.common_mm3==pytest.approx(np.pi*250,rel=1e-7)
    assert regions.added_mm3==pytest.approx(np.pi*25,rel=1e-6)
    assert regions.removed_mm3==pytest.approx(0,abs=1e-7)
