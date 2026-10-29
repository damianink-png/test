"""Keep original fail-closed behavior until an independently verified recovery exists."""
from pathlib import Path
import ast
root=Path(__file__).resolve().parents[1]/'dscompare_rc9_manual'/'dsac29'
a=(root/'compare.py').read_text(encoding='utf-8')
b=(root/'revision_overlap.py').read_text(encoding='utf-8')
ast.parse(a);ast.parse(b)
assert 'except NativeGeometryFailure:' in a
assert 'except NativeGeometryFailure:' in b
print('PASS: strict native failure propagation remains enabled')
