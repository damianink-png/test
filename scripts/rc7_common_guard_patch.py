"""Safety hotfix for RC7: isolate every OCC Common in large assemblies.

RC7 used the count of *unmatched* parts to decide whether to isolate native
Boolean Common. Real Trident shifted tests leave 52/54 unresolved parts in a
1595-solid assembly, causing an unsafe in-process Common and 2400s CI timeout.
This patch only changes containment, not matching tolerances or verdicts.
"""
from pathlib import Path
import sys

root=Path(sys.argv[1]) if len(sys.argv)>1 else Path('src')
path=root/'dsac29'/'revision_overlap.py'
content=path.read_text(encoding='utf-8')
needle='guarded_large = len(a)>=600 and len(old_ids)+len(new_ids)>=80'
assert content.count(needle)==1, 'Expected exact RC7 guard condition not found'
content=content.replace(needle,'guarded_large = _should_guard_common(len(a),len(b))')
anchor='MAX_CHECKS=1400\n'
assert content.count(anchor)==1, 'Unexpected RC7 source layout'
content=content.replace(anchor,anchor+'''
def _should_guard_common(a_count,b_count):
    """A small unresolved tail does not make a large CAD Boolean safe."""
    return max(a_count,b_count)>=600

''')
path.write_text(content,encoding='utf-8')
print('RC7 native Common safety guard patched: large assemblies always isolated')
