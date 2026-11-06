"""R14: shifted revisions whose unchanged part count is below former 15% gate."""
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from test_r7_alignment_preview import occurrence
from dsac29.compare import Record
from dsac29.deferred_alignment import propose
from dsac29.alignment import _relocate
from dsac29.registration_gate import frame_support
import numpy as np


def case(delta=(1500,-200), coherent=True):
    n=80; stable=8
    common=BRepPrimAPI_MakeBox(17,11,9).Shape()
    old=BRepPrimAPI_MakeBox(17,15,9).Shape()
    new=BRepPrimAPI_MakeBox(17,16,9).Shape()
    coordinates=[(i*110+i*i%17,i*i*13%800) for i in range(n)]
    a=[occurrence(common if i<stable else old,'P',*coordinates[i]) for i in range(n)]
    b=[]
    for i in range(n):
        x,y=coordinates[i];dx,dy=delta
        if i<stable and not coherent:dx+=i*7;dy+=i*11
        b.append(occurrence(common if i<stable else new,'P',x+dx,y+dy))
    rec=[Record(i,i,'MOVED','identical local geometry') for i in range(stable)]
    rec.extend(Record(i,None,'REMOVED','changed geometry') for i in range(stable,n))
    rec.extend(Record(None,i,'ADDED','changed geometry') for i in range(stable,n))
    return a,b,rec


def test_sparse_global_translation_now_detected_and_brep_verified():
    a,b,records=case()
    proposal=propose(a,b,records,.01)
    assert proposal is not None and proposal['status']=='registered',proposal
    assert proposal['translation_B_to_A_mm']==[-1500.,200.,0.]
    assert proposal['votes']==8 and proposal['support_ratio']==.1
    offset=np.asarray(proposal['translation_B_to_A_mm'])
    aligned=[_relocate(part,np.eye(3),offset) for part in b]
    assert frame_support(a,aligned,.01,verify_all=True)['count']==8


def test_individual_local_moves_are_not_global_shift():
    # The old fixture also translated all 72 changed bodies by (1500,-200).
    # Use ZERO global delta to test only the eight independent local moves.
    a,b,records=case(delta=(0,0),coherent=False)
    proposal=propose(a,b,records,.01)
    assert proposal is None or proposal['status'] in ('unresolved','already_aligned'),proposal


def test_changed_majority_can_prove_frame_despite_local_moves_in_unchanged_subset():
    a,b,records=case(coherent=False)
    proposal=propose(a,b,records,.01)
    assert proposal['status']=='registered'
    assert proposal['method']=='preserved_native_faces'
    assert proposal['requires_confirmation'] and proposal['certified_pairs']==[]
    assert np.allclose(proposal['translation_B_to_A_mm'],[-1500,200,0])
