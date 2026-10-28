"""Keep existing STEP topology tolerances inside original 0.01 mm budget."""
from pathlib import Path
import ast
root=Path(__file__).resolve().parents[1]/'dscompare_rc9_manual'
brep=root/'dsac29'/'brep_safety.py'
s=brep.read_text(encoding='utf-8')
a="def validated_copy(shape,tolerance=0.01):"
b="def validated_copy(shape,tolerance=0.01, *, max_source_tolerance=None):"
assert s.count(a)==1,s.count(a)
s=s.replace(a,b)
a='''    if shape.IsNull():raise UnprovenRepair('Null input B-Rep')
    if is_valid(shape):return shape,False
    from . import trace_r22 as trace
    before=topology_tolerances(shape);failures=[]'''
b='''    if shape.IsNull():raise UnprovenRepair('Null input B-Rep')
    if is_valid(shape):return shape,False
    # Source STEP may store tolerance > half-budget, but never > original
    # 0.01 mm budget. This is NOT permission to increase it during repair.
    source_cap=float(tolerance if max_source_tolerance is None else max_source_tolerance)
    if not float(tolerance)<=source_cap<=.01:
        raise ValueError('Source tolerance cap exceeds original CAD budget')
    from . import trace_r22 as trace
    before=topology_tolerances(shape)
    if any(value>source_cap+1e-12 for value in before.values()):
        raise UnprovenRepair('Original STEP stored tolerance exceeds CAD budget')
    failures=[]'''
assert s.count(a)==1,s.count(a)
s=s.replace(a,b)
a="if value>tolerance or value>before[kind]+1e-12:"
b="if value>source_cap+1e-12 or value>before[kind]+1e-12:"
assert s.count(a)==1,s.count(a)
s=s.replace(a,b)
ast.parse(s)
brep.write_text(s,encoding='utf-8')
p=root/'dsac29'/'native_guard.py';s=p.read_text(encoding='utf-8')
for suffix in ('A','B'):
 a=f'validated_copy({suffix.lower()}_shape,repair_tolerance)'
 b=f'validated_copy({suffix.lower()}_shape,repair_tolerance,max_source_tolerance=proof_tolerance)'
 assert s.count(a)==1,(a,s.count(a))
 s=s.replace(a,b)
ast.parse(s)
p.write_text(s,encoding='utf-8')
print('RC9: original STEP tolerances <=0.01 mm retained; independent boundary proof mandatory')
