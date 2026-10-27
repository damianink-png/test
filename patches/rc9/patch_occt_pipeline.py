"""Apply integrated OCCT proof/repair and frame-matching patches to pinned RC9.

Fail closed on unexpected source: never silently drop a safety modification.
"""
from pathlib import Path
import ast,sys
root=Path(sys.argv[1])

def edit(name,old,new):
    path=root/name
    src=path.read_text(encoding='utf-8')
    if src.count(old)!=1:
        raise RuntimeError(f'RC9 interface changed: {name}: {old[:100]!r} count={src.count(old)}')
    src=src.replace(old,new)
    ast.parse(src)
    path.write_text(src,encoding='utf-8')

edit('step_reexport_tolerance.py',
     'def reexport_equivalent_world(a,b,tolerance=.01, *, allow_boolean=True, progress=None):',
     'def reexport_equivalent_world(a,b,tolerance=.01, *, allow_boolean=True, progress=None, _repair_boundary_only=False):')
edit('step_reexport_tolerance.py',
     '    if not shape_valid(a.shape) or not shape_valid(b.shape):return False',
     "    if not shape_valid(a.shape) or not shape_valid(b.shape):\n"
     "        if not _repair_boundary_only or allow_boolean:return False")
edit('step_reexport_tolerance.py',
     '    if prove(a.shape,b.shape,owner,fa,tolerance):return True\n'
     "    report('boolean_residual' if allow_boolean else 'inconclusive')",
     '    if prove(a.shape,b.shape,owner,fa,tolerance):return True\n'
     '    if _repair_boundary_only:return False  # No volume-based repair proof\n'
     "    report('boolean_residual' if allow_boolean else 'inconclusive')")

edit('native_guard.py',
     "    if req.get('operation') == 'world_reexport':\n"
     "        from .step_reexport_tolerance import reexport_equivalent_world\n"
     "        report('describe_shapes')",
     "    if req.get('operation') == 'world_reexport':\n"
     "        from .step_reexport_tolerance import reexport_equivalent_world\n"
     "        from .brep_safety import is_valid,validated_copy\n"
     "        original_invalid=not is_valid(a_shape) or not is_valid(b_shape)\n"
     "        if original_invalid:\n"
     "            report('validate_copy_repair')\n"
     "            validated_copy(a_shape,float(req['tolerance']))\n"
     "            validated_copy(b_shape,float(req['tolerance']))\n"
     "        report('describe_shapes')")
edit('native_guard.py',
     "            allow_boolean=bool(req.get('allow_boolean', False)), progress=report))",
     "            allow_boolean=(bool(req.get('allow_boolean', False)) and not original_invalid),\n"
     "            _repair_boundary_only=original_invalid,progress=report))")

# Optional Common must not execute in the GUI/coordinator process.
edit('compare.py',
     "                from .geometry import _common_volume\n"
     "                overlap_checks+=1",
     "                from .native_guard import guarded_common\n"
     "                from .material_deltas import volume\n"
     "                overlap_checks+=1")
edit('compare.py',
     "try:overlap=trace.brep_call('common_volume',i,j,_common_volume,s.shape,t.shape,tolerance)/min(s.volume,t.volume)",
     "try:overlap=volume(trace.brep_call('common_volume_isolated',i,j,guarded_common,s.shape,t.shape,tolerance))/min(s.volume,t.volume)")

# Repeated co-located occurrences need maximum 1:1 cardinality, not first-fit.
path=root/'registration_gate.py'
src=path.read_text(encoding='utf-8')
start=src.index(' occupied=set();pairs=[]\n',src.index('def _frame_support('))
end=src.index(' if not pairs:return',start)
replacement=""" options={}
 for j,part in enumerate(b):
  if cancelled and cancelled():raise Cancelled('Przerwano analizę')
  pos=np.asarray(part.center)
  base=tuple(floor(float(v)/cell_size) for v in pos)
  choices=[]
  for steps in product((-1,0,1),repeat=3):
   loc=tuple(x+y for x,y in zip(base,steps))
   for i in buckets.get(loc,()):
    distance=float(np.linalg.norm(a[i].center-pos))
    if distance<=radius and world_candidate(a[i],part,tol):
     choices.append((distance,i))
  if choices:options[j]=[i for _,i in sorted(set(choices))]
 # Iterative maximum-cardinality assignment; B-Rep proof before edge use.
 owner={};reverse={};checked_pairs={}
 for n,start in enumerate(sorted(options,key=lambda j:(len(options[j]),j))):
  if cancelled and cancelled():raise Cancelled('Przerwano analizę')
  if progress and n%25==0:progress(f'Weryfikacja przesunięcia B-Rep: {n}/{len(options)}; potwierdzono {len(owner)}')
  queue=[start];seen_left={start};seen_right=set();parent={};free=None
  for j in queue:
   for i in options[j]:
    if i in seen_right:continue
    if verify_all:
     pair=(i,j)
     if pair not in checked_pairs:checked_pairs[pair]=bool(proven(i,j))
     if not checked_pairs[pair]:continue
    seen_right.add(i);parent[i]=j
    if i not in owner:free=i;break
    next_j=owner[i]
    if next_j not in seen_left:seen_left.add(next_j);queue.append(next_j)
   if free is not None:break
  if free is None:continue
  while True:
   j=parent[free];old=reverse.get(j)
   owner[free]=j;reverse[j]=free
   if old is None:break
   free=old
 pairs=sorted((i,j) for i,j in owner.items())
"""
src=src[:start]+replacement+src[end:]
ast.parse(src)
path.write_text(src,encoding='utf-8')
print('RC9 integrated OCCT proof/repair gate, isolated Common and global 1:1 frame matching')
