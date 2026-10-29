"""RC9: reuse proven Common/Cut for repeated native definitions under one translation.

Only exact TopoDS TShape partners with the same orientation, rotation and
relative placement qualify. First occurrence is computed by the isolated OCCT
workers. Every reused region is relocated and validated against the current
pair by bind_regions; changed geometry/relative placement is never reused.
"""
from pathlib import Path
import ast

p = Path(__file__).resolve().parents[1] / "dscompare_rc9_manual" / "dsac29" / "revision_overlap.py"
s = p.read_text(encoding="utf-8")

def replace_one(old, new):
    global s
    if s.count(old) != 1:
        raise SystemExit(f"Revision proof-cache anchor mismatch ({s.count(old)}): {old[:100]}")
    s = s.replace(old, new)

replace_one("def merge_material_revisions(a,b,records,tolerance=0.01,progress=None,cancelled=None):",
'''def _reuse_common_volume(a, b, saved_a, saved_b):
    """Exact native definition + same relative pose: valid translated proof."""
    sa, sb = a.shape, b.shape
    ca, cb = saved_a.shape, saved_b.shape
    if not sa.IsPartner(ca) or not sb.IsPartner(cb):
        return False
    if sa.Orientation() != ca.Orientation() or sb.Orientation() != cb.Orientation():
        return False
    for new, old in ((sa, ca), (sb, cb)):
        tn = new.Location().Transformation()
        to = old.Location().Transformation()
        for i in (1, 2, 3):
            for j in (1, 2, 3):
                if abs(tn.Value(i, j) - to.Value(i, j)) > 1.e-12:
                    return False
    return bool(np.max(np.abs((a.center-saved_a.center)-(b.center-saved_b.center))) < 1.e-9)


def _translated_regions(regions, offset):
    """Only rigidly relocate independently verified Common/Cut results."""
    from OCP.gp import gp_Trsf, gp_Vec
    from OCP.TopLoc import TopLoc_Location
    from .material_deltas import MaterialRegions
    tr = gp_Trsf()
    tr.SetTranslation(gp_Vec(*map(float, offset)))
    loc = TopLoc_Location(tr)
    return MaterialRegions(regions.common.Moved(loc), regions.added.Moved(loc),
                           regions.removed.Moved(loc), regions.common_mm3,
                           regions.added_mm3, regions.removed_mm3)


def merge_material_revisions(a,b,records,tolerance=0.01,progress=None,cancelled=None):''')

replace_one("    best_common={}\n    guarded_large = True",
"""    best_common={}
    common_cache=[]
    stat['common_proof_reuse']=0
    guarded_large = True""")

replace_one('''            stat['boolean_checks']+=1
            if progress:progress(f'Zmiany materiału: Common A[{i}] ↔ B[{j}], test {stat["boolean_checks"]}; limit 90 s')
            try:
                if guarded_large:
                    if perf_counter()-guarded_started>=guarded_budget_s:
                        raise NativeGeometryFailure('Limit czasu bezpiecznej analizy wspólnego materiału — nieukończone porównanie')
                    from .native_guard import guarded_common
                    shape=trace.brep_call('revision_common_isolated',i,j,guarded_common,ref.shape,b[j].shape,tolerance)
                else:
                    shape=trace.brep_call('revision_common',i,j,operate,BRepAlgoAPI_Common,ref.shape,b[j].shape,tolerance)
                common=volume(shape)
''',
'''            if perf_counter()-guarded_started>=guarded_budget_s:
                raise NativeGeometryFailure('Limit czasu bezpiecznej analizy wspólnego materiału — nieukończone porównanie')
            cached=next((entry for entry in common_cache
                         if _reuse_common_volume(ref,b[j],entry[0],entry[1])),None)
            shape=None
            if cached is not None:
                common=cached[2]
                stat['common_proof_reuse']+=1
            else:
                stat['boolean_checks']+=1
                if progress:progress(f'Zmiany materiału: Common A[{i}] ↔ B[{j}], test {stat["boolean_checks"]}; limit 90 s')
            try:
                if cached is None and guarded_large:
                    from .native_guard import guarded_common
                    shape=trace.brep_call('revision_common_isolated',i,j,guarded_common,ref.shape,b[j].shape,tolerance)
                elif cached is None:
                    shape=trace.brep_call('revision_common',i,j,operate,BRepAlgoAPI_Common,ref.shape,b[j].shape,tolerance)
                if cached is None:
                    common=volume(shape)
                    if len(common_cache)<128:
                        common_cache.append((ref,b[j],common))
''')

replace_one("best_common[i]=(score,j,bind_common(shape,ref.shape,b[j].shape,tolerance))",
            "best_common[i]=(score,j,bind_common(shape,ref.shape,b[j].shape,tolerance)) if shape is not None else (score,j,None)")

replace_one("    accepted={};regions={}",
"""    accepted={};regions={};region_cache=[]
    stat['region_proof_reuse']=0""")

replace_one(
"""            reg=trace.brep_call('revision_material_regions',i,j,calculate,a[i],b[j],tolerance,common_shape=cached[2] if cached and cached[1]==j else None)
            if _score(reg.common_mm3,a[i],b[j],_name_eq(a[i],b[j])) is None:""",
"""            reuse=next((entry for entry in region_cache
                        if _reuse_common_volume(a[i],b[j],entry[0],entry[1])),None)
            if reuse is not None:
                reg=_translated_regions(reuse[2],a[i].center-reuse[0].center)
                stat['region_proof_reuse']+=1
            else:
                reg=trace.brep_call('revision_material_regions',i,j,calculate,a[i],b[j],tolerance,common_shape=cached[2] if cached and cached[1]==j else None)
                if len(region_cache)<128:
                    region_cache.append((a[i],b[j],reg))
            if _score(reg.common_mm3,a[i],b[j],_name_eq(a[i],b[j])) is None:""")

ast.parse(s, filename=str(p))
p.write_text(s, encoding="utf-8")
print("RC9 native Common/Cut proof reuse installed; independent first proof and pair-bound validation retained")
