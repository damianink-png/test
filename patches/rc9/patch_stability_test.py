"""Update RC9's fail-closed regression for the conservative optional-overlap policy.

Native material proof must still raise on timeout. An OPTIONAL Common timeout
must not abort the complete comparison or silently classify unproven SAME/CHANGED.
"""
from pathlib import Path
import sys

path = Path(sys.argv[1])
src = path.read_text(encoding="utf-8")
old = """def test_small_overlap_is_guarded(monkeypatch):
    import dsac29.native_guard as ng
    from dsac29.revision_overlap import merge_material_revisions
    from dsac29.compare import Record
    def fail(*args,**kwargs):raise NativeGeometryFailure('injected timeout')
    monkeypatch.setattr(ng,'guarded_common',fail)
    a,b=parts()
    with pytest.raises(NativeGeometryFailure):
        merge_material_revisions([a],[b],[Record(0,None,'REMOVED',''),Record(None,0,'ADDED','')])
"""
new = """def test_small_overlap_failure_keeps_removed_added(monkeypatch):
    import dsac29.native_guard as ng
    from dsac29.revision_overlap import merge_material_revisions
    from dsac29.compare import Record
    def fail(*args,**kwargs):raise NativeGeometryFailure('injected timeout')
    monkeypatch.setattr(ng,'guarded_common',fail)
    a,b=parts()
    records, regions, stats = merge_material_revisions(
        [a],[b],[Record(0,None,'REMOVED',''),Record(None,0,'ADDED','')])
    assert sorted(r.status for r in records)==['ADDED','REMOVED']
    assert not regions
    assert stats['accepted']==0
    assert stats['native_failures']==1
    assert stats['invalid_boolean']>=1
"""
if src.count(old)!=1:
    raise SystemExit("RC9 stability test patch mismatch: original test not found exactly once")
path.write_text(src.replace(old,new),encoding="utf-8")
print("RC9 optional Common fallback test updated; strict native proof tests unchanged")
