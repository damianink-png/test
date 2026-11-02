"""Contain OCCT rigid Boolean segfaults in child processes for large assemblies.

The 2026-11-02 exact Trident run 41538362160 crashed at geometry.py:107
from compare.py:322 because use_native_guard was conditional on 40% certified
pairs, whereas normal revision comparison starts with zero certified pairs.

This patch changes *execution isolation*, not tolerance or matching verdicts.
A child crash yields NativeGeometryFailure => UNCERTAIN (never SAME).
"""
from pathlib import Path
import sys

def apply(path: Path):
    s = path.read_text(encoding='utf-8')
    replacements = [
        (
            "    use_native_guard = bool(len(a)>=600 and len(certified_pairs)>=max(100,int(len(a)*.40)))",
            "    # Exact Trident crash 41538362160: zero certified_pairs selected the\n"
            "    # in-process equivalent_rigid -> BRepAlgoAPI_Common -> SIGSEGV path.\n"
            "    # Isolate every rigid B-Rep check for large assemblies, regardless\n"
            "    # of whether initial matches were certified after alignment.\n"
            "    registered_native_mode = bool(len(a)>=600 and len(certified_pairs)>=max(100,int(len(a)*.40)))\\n"\n            "    use_native_guard = bool(len(a)>=600)"
        ),
        (
            "    native_guard_budget_s = 240.0",
            "    # Whole-stage budget (not per worker); still fail closed on exhaustion.\n"
            "    # Large assemblies need more than the old fixed 240 seconds.\n"
            "    native_guard_budget_s = max(600.0, min(2400.0, 1.5*len(a)))"
        ),
        (
            "lookup=(sorted(free_b) if use_native_guard else volume_index.query(s.volume,tolerance))",
            "lookup=(sorted(free_b) if registered_native_mode else volume_index.query(s.volume,tolerance))"
        ),
        (
            "(use_native_guard and world_candidate(s,b[j],tolerance))",
            "(registered_native_mode and world_candidate(s,b[j],tolerance))"
        ),
        (
            "guarded_rigid,s,b[j],tolerance,registered_reexport=True)",
            "guarded_rigid,s,b[j],tolerance,registered_reexport=registered_native_mode)"
        ),
    ]
    for before,after in replacements:
        if s.count(before)!=1:
            raise RuntimeError('Refusing unsafe rigid isolation patch; missing anchor: '+before[:100])
        s=s.replace(before,after,1)
    compile(s,str(path),'exec')
    path.write_text(s,encoding='utf-8')
    print('TRIDENT_RIGID_ISOLATION_PATCH_PASS',path,flush=True)

if __name__=='__main__':
    if len(sys.argv)!=2:
        raise SystemExit('usage: patch_trident_rigid_isolation.py <compare.py>')
    apply(Path(sys.argv[1]))
