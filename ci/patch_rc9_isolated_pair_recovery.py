"""Exact serialized world B-Rep identity before repair of invalid solids.

This is a strict positive proof: identical complete serialized B-Rep inputs
represent identical world shapes. Nonidentical inputs use existing independent
oriented face/trim proof and fail-closed copy repair.
"""
from pathlib import Path
import ast
root=Path(__file__).resolve().parents[1]/'dscompare_rc9_manual'/'dsac29'
p=root/'native_guard.py'
s=p.read_text(encoding='utf-8')
old="""        direct_same=False
        if not valid_a and not valid_b:
            # Full original-oriented face AND trimming-wire identity is"""
new="""        direct_same=False
        if not valid_a and not valid_b:
            # Serialized full world B-Rep identity is exact, including
            # location, topology, trims and geometric definitions. No
            # bbox, mass or volume heuristic and no tolerance relaxation.
            from .exact_brep_identity import identical_serialized_brep
            if identical_serialized_brep(Path(req['a']),Path(req['b'])):
                report('exact_invalid_world_brep_proven')
                direct_same=True
        if not valid_a and not valid_b and not direct_same:
            # Full original-oriented face AND trimming-wire identity is"""
if s.count(old)!=1:raise RuntimeError('Unexpected invalid BRep proof anchor')
s=s.replace(old,new)
ast.parse(s)
p.write_text(s,encoding='utf-8')
helper=root/'exact_brep_identity.py'
helper.write_text('''"""Exact byte identity of two complete serialized world B-Reps."""
from pathlib import Path

def identical_serialized_brep(a,b):
    a,b=Path(a),Path(b)
    if not a.is_file() or not b.is_file():return False
    if a.stat().st_size!=b.stat().st_size:return False
    # Compare actual bytes, not merely a hash digest.
    with a.open('rb') as left,b.open('rb') as right:
        while True:
            x=left.read(1024*1024)
            y=right.read(1024*1024)
            if x!=y:return False
            if not x:return True
''',encoding='utf-8')
ast.parse(helper.read_text(encoding='utf-8'))
p.write_text(s,encoding='utf-8')
print('Exact invalid B-Rep identity fastpath installed')
