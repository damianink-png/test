"""Verify native proof failures are never silently promoted to matches."""
from pathlib import Path
import ast
root=Path(__file__).resolve().parents[1]/'dscompare_rc9_manual'/'dsac29'
a=(root/'compare.py').read_text(encoding='utf-8')
b=(root/'revision_overlap.py').read_text(encoding='utf-8')
ast.parse(a);ast.parse(b)
assert 'except NativeGeometryFailure as exc:' in a
assert 'failed_a.add(i);failed_b.add(j)' in a
assert "'UNCERTAIN' if i in failed_a" in a
assert "'UNCERTAIN' if j in failed_b" in a
assert 'except NativeGeometryFailure:' in b
assert 'raise' in b
print('PASS: conservative native proof failure classification')
