"""Do not carry failed speculative pair errors past independently matched parts."""
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCP.gp import gp_Pnt
from dsac29.geometry import describe
from dsac29 import compare as compare_module


def shape(length=10,x=0):
    return BRepPrimAPI_MakeBox(gp_Pnt(x,0,0),length,10,10).Shape()


def test_failed_speculative_pair_is_discarded_after_other_occurrence_matched(monkeypatch):
    first=describe(shape(),'old-label','first')
    stable=shape()
    survivor=describe(stable,'old-label','survivor')
    # Same geometry, but potentially renamed and duplicated in both STEP files.
    counterpart=describe(stable,'old-label','new-survivor')
    separate=describe(shape(12,100),'different-label','new-other')
    attempts=[]
    def transient_failure(a,b,tol):
        attempts.append((a.path,b.path))
        raise RuntimeError('Synthetic ambiguous candidate B-Rep failure')
    monkeypatch.setattr(compare_module,'equivalent_world',transient_failure)
    result=compare_module.compare([first,survivor],[counterpart,separate],revision_only=True)
    assert ('first','new-survivor') in attempts
    assert {(r.a_index,r.b_index,r.status) for r in result} == {
        (0,None,'REMOVED'),(1,0,'SAME'),(None,1,'ADDED')}


def test_genuinely_unresolved_candidate_is_still_uncertain(monkeypatch):
    old=describe(shape(),'same','old')
    new=describe(shape(),'same','new')
    monkeypatch.setattr(compare_module,'equivalent_world',
                        lambda *args: (_ for _ in ()).throw(RuntimeError('OCCT failure')))
    monkeypatch.setattr(compare_module,'equivalent_rigid',lambda *a,**k:(False,None,None))
    out=compare_module.compare([old],[new],revision_only=True)
    assert len(out)==2 and all(r.status=='UNCERTAIN' for r in out)
