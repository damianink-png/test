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
p.write_text(s,encoding='utf-8')
print('REGISTERED_WORLD_LOOKUP_PASS')
