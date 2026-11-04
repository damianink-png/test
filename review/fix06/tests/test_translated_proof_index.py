"""The cache index may accelerate lookup, never replace native proof."""
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCP.gp import gp_Trsf,gp_Vec
from OCP.TopLoc import TopLoc_Location
from dsac29.geometry import describe
from dsac29.revision_overlap import _TranslatedProofIndex


def _at(shape, shift, name):
    tr=gp_Trsf();tr.SetTranslation(gp_Vec(*shift))
    return describe(shape.Located(TopLoc_Location(tr)),name,name)


def test_translated_positive_proofs_only():
    a_shape=BRepPrimAPI_MakeBox(10,10,10).Shape()
    b_shape=BRepPrimAPI_MakeBox(11,10,10).Shape()
    x=_at(a_shape,(0,0,0),'A'); y=_at(b_shape,(0,0,0),'B')
    proofs=_TranslatedProofIndex()
    proofs.save(x,y,100.0)
    shifted_a=_at(a_shape,(40,0,0),'A');shifted_b=_at(b_shape,(40,0,0),'B')
    assert proofs.find(shifted_a,shifted_b)[2]==100.0
    assert proofs.find(_at(a_shape,(40,0,0),'A'),_at(b_shape,(41,0,0),'B')) is None
    # A separately exported STEP occurrence may have a different native
    # TShape while its entire LOCAL serialized B-Rep is byte identical.
    # Such an occurrence is safe ONLY with the same old/new relative pose.
    independent=_at(BRepPrimAPI_MakeBox(10,10,10).Shape(),(40,0,0),'A')
    assert not independent.shape.IsPartner(shifted_a.shape)
    assert proofs.find(independent,shifted_b)[2]==100.0
    assert proofs.saved==1 and proofs.candidates_checked==3


def test_never_store_failure_and_limit():
    a_shape=BRepPrimAPI_MakeBox(10,10,10).Shape()
    b_shape=BRepPrimAPI_MakeBox(11,10,10).Shape()
    x=_at(a_shape,(0,0,0),'A');y=_at(b_shape,(0,0,0),'B')
    proofs=_TranslatedProofIndex(limit=1)
    assert proofs.find(x,y) is None
    proofs.save(x,y,7.0)
    proofs.save(x,y,8.0)
    assert proofs.saved==1
    assert proofs.find(x,y) is None
