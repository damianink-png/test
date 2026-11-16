from OCP.BRepPrimAPI import BRepPrimAPI_MakeCylinder
from OCP.BRepBuilderAPI import BRepBuilderAPI_NurbsConvert
from dsac29.boundary_descriptor import describe_boundary
from dsac29.geometry import describe


def test_cached_properties_do_not_require_any_native_shape_operation():
    marker=object()
    p=describe_boundary(marker,{'volume':12.,'area':23.})
    assert p.shape is marker and p.volume==12 and p.area==23


def test_bad_hints_fall_back_to_real_properties():
    shape=BRepPrimAPI_MakeCylinder(5.,10.).Shape()
    p=describe_boundary(shape,{'volume':float('nan'),'area':1})
    assert p.volume>780 and p.area>470


def test_forged_hints_cannot_prove_changed_geometry():
    from dsac29.nurbs_boundary import equivalent
    a=BRepPrimAPI_MakeCylinder(5.,10.).Shape()
    b=BRepBuilderAPI_NurbsConvert(BRepPrimAPI_MakeCylinder(6.,10.).Shape(),True).Shape()
    assert not equivalent(a,b,.01,properties=({'volume':1.,'area':1.},)*2)


def test_worker_returns_intermediate_proof_stages(monkeypatch):
    from dsac29.native_guard import guarded_registered_world
    from dsac29 import trace_r22
    a=BRepPrimAPI_MakeCylinder(5.,10.).Shape()
    b=BRepBuilderAPI_NurbsConvert(a,True).Shape()
    events=[]
    monkeypatch.setattr(trace_r22,'mark',lambda *args,**kw:events.append(kw))
    assert guarded_registered_world(describe(a,'a','a'),describe(b,'b','b'),.01)
    completed=[e for e in events if e.get('phase')=='nurbs_boundary_proven']
    assert completed and 'nurbs_boundary_accepted' in completed[0]['proof_stages']


def test_worker_timeout_retains_stages_before_boolean(monkeypatch):
    import json,subprocess,pytest
    from pathlib import Path
    from dsac29 import native_guard,native_session,trace_r22
    part=describe(BRepPrimAPI_MakeCylinder(5.,10.).Shape(),'a','a')
    events=[]
    monkeypatch.setattr(trace_r22,'mark',lambda *args,**kw:events.append(kw))
    monkeypatch.setattr(native_session,'current',lambda:None)
    def timeout(argv,**kwargs):
        reply=Path(argv[-1])
        reply.with_suffix('.stages.json').write_text(json.dumps(['nurbs_boundary_rejected_surface_or_trim','validated_solid_symmetric_difference']))
        raise subprocess.TimeoutExpired(argv,1)
    monkeypatch.setattr(native_guard.subprocess,'run',timeout)
    with pytest.raises(native_guard.NativeGeometryFailure):
        native_guard.guarded_registered_world(part,part,.01)
    assert any(e.get('proof_stages')==['nurbs_boundary_rejected_surface_or_trim','validated_solid_symmetric_difference'] for e in events)
