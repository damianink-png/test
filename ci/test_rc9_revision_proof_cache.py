"""RC9: only exact native partner pairs under shared translation may reuse proof."""
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCP.gp import gp_Trsf, gp_Vec
from OCP.TopLoc import TopLoc_Location
from dsac29.geometry import describe
from dsac29.compare import Record
from dsac29.revision_overlap import merge_material_revisions, _reuse_common_volume
from dsac29.material_deltas import _matching_regions


def at(shape, x, y=0):
    tr=gp_Trsf()
    tr.SetTranslation(gp_Vec(float(x),float(y),0.))
    return describe(shape.Located(TopLoc_Location(tr)), 'P', 'P')


def test_native_proof_cache_reuses_only_exact_partner_pose():
    old=BRepPrimAPI_MakeBox(17.,15.,9.).Shape()
    new=BRepPrimAPI_MakeBox(17.,16.,9.).Shape()
    a=[at(old,0),at(old,100)]
    b=[at(new,0),at(new,100)]
    assert _reuse_common_volume(a[1],b[1],a[0],b[0])
    assert not _reuse_common_volume(a[1],at(new,101),a[0],b[0])
    assert not _reuse_common_volume(a[1],at(BRepPrimAPI_MakeBox(17.,16.,9.).Shape(),100),a[0],b[0])
    assert not _reuse_common_volume(a[1],at(new,100),a[0],at(new,1))
    records=[Record(i,None,'REMOVED','') for i in range(2)]
    records += [Record(None,i,'ADDED','') for i in range(2)]
    result,precomputed,stat=merge_material_revisions(a,b,records,.01)
    assert [r.status for r in result]==['CHANGED','CHANGED']
    assert stat['common_proof_reuse']==1,stat
    assert stat['region_proof_reuse']==1,stat
    assert stat['boolean_checks']==1,stat
    for k,r in enumerate(result):
        assert _matching_regions(precomputed[k],a[r.a_index],b[r.b_index],.01)
        assert abs(precomputed[k].regions.added_mm3-153)<.001
        assert precomputed[k].regions.removed_mm3<.001


def test_native_proof_cache_rejects_different_relative_placement():
    old=BRepPrimAPI_MakeBox(17.,15.,9.).Shape()
    new=BRepPrimAPI_MakeBox(17.,16.,9.).Shape()
    a=[at(old,0),at(old,100)]
    b=[at(new,0),at(new,101)]
    records=[Record(i,None,'REMOVED','') for i in range(2)]
    records += [Record(None,i,'ADDED','') for i in range(2)]
    result,precomputed,stat=merge_material_revisions(a,b,records,.01)
    assert stat['common_proof_reuse']==0,stat
    assert stat['region_proof_reuse']==0,stat
    assert stat['boolean_checks']==2,stat
