"""R3 audit: dedupe geometry alignment hypotheses and STEP verification reads."""
import os
from pathlib import Path
root=Path(os.environ['DS_COMPARE_SOURCE'])

p=root/'dsac29/alignment.py'
s=p.read_text('utf8')
anchor="""    ranked=[]
    for method,R,t,i,j in candidates:
        supported=score(R,t)"""
replacement="""    # Several anchors routinely yield EXACTLY the same world-space transform.
    # Scoring each duplicates B-Rep transforms and equality checks.
    # Quantize at fractions of geometric tolerance; unlike merging actual
    # geometry, this only drops numerically equivalent hypotheses.
    unique={}
    quantum=max(1e-7,float(tolerance)*.01)
    for method,R,t,i,j in candidates:
        key=(tuple(np.round(np.asarray(R).flatten()/1e-8).astype('int64')),
             tuple(np.round(np.asarray(t)/quantum).astype('int64')))
        if key not in unique:
            unique[key]=(method,R,t,i,j)
    if progress and len(unique)<len(candidates):
        progress(f'Wyrównanie: {len(unique)} unikalnych transformacji zamiast {len(candidates)} powtarzanych hipotez.')
    ranked=[]
    for method,R,t,i,j in unique.values():
        # Cheap center checks before expensive transformed OCC B-Rep tests.
        coarse=sum(np.linalg.norm(a[ai].center-(R@b[bj].center+t))<=max(.0001,tolerance)
                   for ai,bj in pairs)
        if coarse<min_votes or coarse/len(pairs)<.6:
            continue
        supported=score(R,t)"""
if s.count(anchor)!=1:raise RuntimeError('alignment ranking insertion point changed')
s=s.replace(anchor,replacement,1)
p.write_text(s,'utf8')

p=root/'dsac29/step_io.py'
s=p.read_text('utf8')
anchor="""            if do_full:
                diag=inspect_step_colors(str(temporary))"""
replacement="""            # One lazy bytes buffer for structural checks (fast mode and/or
            # assembly tree), not a second whole-file read for each check.
            data=None
            if do_full:
                diag=inspect_step_colors(str(temporary))"""
if s.count(anchor)!=1:raise RuntimeError('STEP verification anchor changed')
s=s.replace(anchor,replacement,1)
anchor="""            if not self.flat_zw3d:
                import re
                data=temporary.read_bytes()"""
replacement="""            if not self.flat_zw3d:
                import re
                if data is None:data=temporary.read_bytes()"""
if s.count(anchor)!=1:raise RuntimeError('STEP duplicate-read anchor changed')
s=s.replace(anchor,replacement,1)
p.write_text(s,'utf8')

print('R3 geometry/STEP: deduplicated alignment hypotheses; STEP structure read once per export')
