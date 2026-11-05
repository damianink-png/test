"""Retain broad, independently verified CAD lookup after sampled registration."""
from pathlib import Path
import sys

p=Path(sys.argv[1])
s=p.read_text(encoding='utf-8')
replacements={
    'broad_world_lookup=len(a)>=600':
        'broad_world_lookup=len(a)>=600 or bool(certified_pairs) or step_reexport_tolerance',
    'large_registered = len(a)>=600 and bool(certified_pairs)':
        'large_registered = len(a)>=80 and bool(certified_pairs)',
    '(guarded_world_reexport if len(a)>=600 else reexport_equivalent_world)':
        '(guarded_world_reexport if len(a)>=80 else reexport_equivalent_world)',
}
for old,new in replacements.items():
    expected=2 if old.startswith('(guarded') else 1
    if s.count(old)!=expected:raise RuntimeError('Registered lookup patch anchor changed: '+old)
    s=s.replace(old,new)
old='    out=[]; checks=0\n    for i,j in certified_pairs:'
new='''    out=[]; checks=0
    cad_a=cad_b=None
    if certified_pairs:
        from .cad_pose_search import landmarks
        cad_a,cad_b=landmarks(a,cancelled),landmarks(b,cancelled)
    for i,j in certified_pairs:'''
if s.count(old)!=1:raise RuntimeError('Registered proof map anchor changed')
s=s.replace(old,new)
old='if dist(a[i],b[j])>search_radius(tolerance):'
if s.count(old)!=1:raise RuntimeError('Registered proof placement anchor changed')
s=s.replace(old,'if np.linalg.norm(cad_a[i]-cad_b[j])>search_radius(tolerance):')
old='    cells = _spatial_index(b, free_b, lookup_radius)'
new='''    lookup_a,lookup_b=a,b
    if certified_pairs:
        # Integrated mass centroids are not geometric placement evidence.
        # After registration use original CAD landmarks for candidate lookup;
        # every unproven pair still needs its independent native B-Rep test.
        from types import SimpleNamespace
        lookup_a=[SimpleNamespace(center=p) for p in cad_a]
        lookup_b=[SimpleNamespace(center=p) for p in cad_b]
    cells = _spatial_index(lookup_b, free_b, lookup_radius)'''
if s.count(old)!=1:raise RuntimeError('Registered spatial index anchor changed')
s=s.replace(old,new)
old='for j in _nearby(cells, s, lookup_radius)'
if s.count(old)!=1:raise RuntimeError('Registered spatial query anchor changed')
s=s.replace(old,'for j in _nearby(cells, lookup_a[i], lookup_radius)')
old='and dist(s, b[j]) <= lookup_radius and'
if s.count(old)!=1:raise RuntimeError('Registered spatial distance anchor changed')
s=s.replace(old,'and np.linalg.norm(lookup_a[i].center-lookup_b[j].center) <= lookup_radius and')
p.write_text(s,encoding='utf-8')
print('REGISTERED_WORLD_LOOKUP_PASS')
