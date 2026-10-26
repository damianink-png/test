"""Integrate robust translation candidates into the ACTUAL RC9 --align-auto path.

deferred_alignment.propose_from_stage1 -> propose runs before the regular
compare finishes. The older alignment.align_assembly path is not sufficient
for automatic tests; this patch supplements its histogram, never its proofs.
"""
from pathlib import Path
import ast,sys
path=Path(sys.argv[1])
src=path.read_text(encoding='utf-8')
needle="    for j,p in enumerate(b):sb[signature(p)].append(j)"
if src.count(needle)!=1:raise SystemExit('Deferred alignment source changed; abort patch')
insertion="""    # Independent rare-shape consensus supplements the existing candidate
    # histogram. It does NOT classify parts or authorize relocation: the
    # original world B-Rep frame_support/ambiguity checks below remain intact.
    try:
        from .robust_translation import Anchor, propose_translation
        rare_a=[Anchor(i,signature(p),tuple(float(v) for v in p.center))
                for i,p in enumerate(a)]
        rare_b=[Anchor(j,signature(p),tuple(float(v) for v in p.center))
                for j,p in enumerate(b)]
        robust=propose_translation(
            rare_a,rare_b,tolerance=tolerance,
            min_support=max(3,min(12,minimum)),
            max_signature_multiplicity=4,
            max_hypotheses=192)
        if robust is not None:
            candidate_offset=np.asarray(robust.shift,dtype=float)
            add(candidate_offset,weight=min(96,robust.support*3))
            if progress:progress(
                f'Wyrównanie: {robust.support} par rzadkich sygnatur; '
                'potwierdzenie B-Rep nadal wymagane.')
    except (TypeError,ValueError,KeyError) as exc:
        if progress:progress(f'Wyrównanie: pominięto wstępny konsensus ({exc}).')
"""
src=src.replace(needle,needle+'\n'+insertion)
ast.parse(src)
path.write_text(src,encoding='utf-8')
print('RC9 automatic stage1 alignment: robust candidate injected; native B-Rep gate unchanged')
