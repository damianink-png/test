"""Isolate native rigid OCCT Booleans in large assemblies without changing matching.

Exact Trident run 41538362160 crashed in parent equivalent_rigid at
geometry._common_volume (SIGSEGV), because zero certified_pairs disabled the
existing subprocess guard. This patch preserves the original candidate search
for normal revisions; only the native execution boundary changes.
"""
from pathlib import Path
import sys

def apply(path: Path):
    s = path.read_text(encoding='utf-8')
    replacements = [
        (
            "    use_native_guard = bool(len(a)>=600 and len(certified_pairs)>=max(100,int(len(a)*.40)))",
            "    # Exact Trident crash 41538362160: no certified pairs selected\n"
            "    # in-process rigid BRepAlgoAPI_Common -> SIGSEGV.\n"
            "    # Preserve the original candidate search for normal revisions.\n"
            "    registered_native_mode = bool(len(a)>=600 and len(certified_pairs)>=max(100,int(len(a)*.40)))\n"
            "    # Isolate native rigid operations for every large assembly.\n"
            "    use_native_guard = bool(len(a)>=600)"
        ),
        (
            "    native_guard_budget_s = 240.0",
            "    # Whole-stage budget; still fail closed when exhausted.\n"
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
    for before, after in replacements:
        if s.count(before) != 1:
            raise RuntimeError('Refusing unsafe rigid isolation patch; missing anchor: '+before[:100])
        s = s.replace(before, after, 1)
    compile(s, str(path), 'exec')
    path.write_text(s, encoding='utf-8')
    print('TRIDENT_RIGID_ISOLATION_PATCH_PASS', path, flush=True)

if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('usage: patch_trident_rigid_isolation.py <compare.py>')
    apply(Path(sys.argv[1]))
