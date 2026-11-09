"""Use CAD comparison tolerance for already-proven repeated placements.

The previous 1e-5 mm cache threshold was 1000x smaller than the
user's normal 0.01 mm B-Rep tolerance. It prevented otherwise valid proof
reuse across 150 STEP occurrences with exporter placement rounding.

No numeric descriptors certify geometry: only a previously confirmed
original full B-Rep for the SAME two native definitions may be reused.
"""
from pathlib import Path
import sys
p=Path(sys.argv[1])/'dsac29/compare.py'
s=p.read_text(encoding='utf-8')
before="np.linalg.norm(ta-tb)<=min(tolerance*0.1,1e-5)"
after="np.linalg.norm(ta-tb)<=max(1e-8,min(tolerance,0.01))"
if s.count(before)!=1:
    raise RuntimeError(f'Unexpected same-definition relative placement policy: {s.count(before)}')
s=s.replace(before,after)
compile(s,str(p),'exec')
p.write_text(s,encoding='utf8')
print('ZW3D_OCCURRENCE_PLACEMENT_TOLERANCE_PASS',flush=True)
