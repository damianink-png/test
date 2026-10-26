"""RC7: apply native Common isolation ONLY after verified global alignment.

Prevents unbounded in-process OCC Common on residual shifted solids without
regressing original-frame authentic revision comparisons. Fail closed:
a timeout is an incomplete comparison, NEVER a SAME/CHANGED proof.
"""
from pathlib import Path
import ast
import sys

root=Path(sys.argv[1])
cli=root/"dsac29/cli.py"
s=cli.read_text(encoding="utf-8")
old="rec,precomputed_regions,overlap_diagnostics=merge_material_revisions(a,b,rec,tolerance,progress,cancelled)"
new="rec,precomputed_regions,overlap_diagnostics=merge_material_revisions(a,b,rec,tolerance,progress,cancelled,alignment_applied=bool(alignment.get('applied')))"
assert s.count(old)==1,"Unexpected Work RC7 CLI source"
s=s.replace(old,new)
ast.parse(s)
cli.write_text(s,encoding="utf-8")

overlap=root/"dsac29/revision_overlap.py"
s=overlap.read_text(encoding="utf-8")
old="def merge_material_revisions(a,b,records,tolerance=0.01,progress=None,cancelled=None):"
new="def merge_material_revisions(a,b,records,tolerance=0.01,progress=None,cancelled=None,alignment_applied=False):"
assert s.count(old)==1,"Unexpected Work RC7 revision overlap signature"
s=s.replace(old,new)
old="guarded_large = len(a)>=600 and len(old_ids)+len(new_ids)>=80"
new="""# Only newly aligned large assemblies require the guarded path even when
    # residual parts are few. Original-frame revision-only retains its
    # previously passing Common behavior (no regression from broad guard).
    guarded_large = len(a)>=600 and (len(old_ids)+len(new_ids)>=80 or alignment_applied)"""
assert s.count(old)==1,"Unexpected Work RC7 revision overlap guard"
s=s.replace(old,new)
old="trace.mark('revision_overlap_guard','BEGIN',guarded=guarded_large,unresolved=len(old_ids)+len(new_ids))"
new="trace.mark('revision_overlap_guard','BEGIN',guarded=guarded_large,unresolved=len(old_ids)+len(new_ids),alignment_applied=bool(alignment_applied))"
assert s.count(old)==1,"Unexpected Work RC7 overlap diagnostics"
s=s.replace(old,new)
ast.parse(s)
overlap.write_text(s,encoding="utf-8")
print("Alignment-only native Common guard applied; original-frame revision path unchanged")
