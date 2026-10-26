"""Inject robust signature-consensus proposal into RC9 sparse alignment.

Only changes candidate ordering. Existing native world B-Rep proof, frame
support, ambiguity gate and matching 1:1 remain authoritative.
"""
from pathlib import Path
import ast,sys
path=Path(sys.argv[1])
src=path.read_text(encoding='utf-8')
needle="    hints=sorted(histogram.values(),key=lambda val:-val[0])[:min(48,len(histogram))]"
if src.count(needle)!=1: raise SystemExit('RC9 alignment interface changed; refusing unsafe patch')
addition="""    # RC9 robust consensus: prioritize translation candidates supported by
    # independent rare signature families; do NOT infer SAME from this vote.
    try:
        from .robust_translation import Anchor, propose_translation
        aa=[Anchor(i,signature(p),tuple(float(v) for v in p.center))
            for i,p in enumerate(a)]
        bb=[Anchor(j,signature(p),tuple(float(v) for v in p.center))
            for j,p in enumerate(b)]
        proposal=propose_translation(
            aa,bb,tolerance=tolerance,
            min_support=max(3,min(12,required)),
            max_signature_multiplicity=4)
        if proposal is not None:
            t=np.asarray(proposal.shift,dtype=float)
            hints=[[proposal.support,t]] + [
                h for h in hints
                if np.linalg.norm(h[1]-t)>tolerance]
            hints=hints[:48]
            if progress: progress(
                f'Wyrównanie: odporny konsensus {proposal.support} par; '
                'weryfikacja B-Rep pozostaje obowiązkowa.')
    except (ValueError,TypeError,KeyError) as exc:
        if progress:progress(f'Wyrównanie: pominięto konsensus sygnatur ({exc}).')
"""
src=src.replace(needle,needle+'\n'+addition)
ast.parse(src)
path.write_text(src,encoding='utf-8')
print('RC9 robust translation proposal integrated before existing native B-Rep gate')
