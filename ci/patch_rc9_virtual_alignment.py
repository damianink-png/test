"""Two-phase B-Rep verification for RC9 deferred global translation.

Cheap virtual centroid offsets already rank hypotheses. This patch uses a
bounded, geometrically proven sample as a *negative filter* before the original
verify_all=True gate. No candidate is accepted, certified or exported from the
sample alone. Full B-Rep proof and ambiguity checks remain authoritative.
"""
from pathlib import Path
import ast
root=Path(__file__).resolve().parents[1]/'dscompare_rc9_manual'
path=root/'dsac29'/'deferred_alignment.py'
src=path.read_text(encoding='utf-8')
start="    winners=[];evaluated=[]\n"
end="    if not winners:return {'status':'unresolved','reason':'Hipotezy nie przeszły kontroli geometrii.'}\n"
if src.count(start)!=1 or src.count(end)!=1:
    raise SystemExit('Unexpected deferred alignment source: abort')
a=src.index(start)
b=src.index(end,a)
old=src[a:b]
for required in ("verify_all=True","support['pairs']","len(evaluated)>=16","_relocate"):
    if required not in old:raise SystemExit('Missing safety anchor '+required)
replacement="""    # First test hypotheses using virtual center offsets (above) and a bounded
    # world-BRep sample. A sample is NEVER a proof of the whole assembly.
    # The expensive full proof runs only for viable top-ranked hypotheses.
    sampled=[];evaluated=[]
    for coarse,offset in sorted(ranked,key=lambda v:-v[0]):
        if any(np.linalg.norm(offset-old)<=tolerance for old in evaluated):continue
        if len(evaluated)>=16:break
        evaluated.append(offset)
        check_cancel()
        shifted=[_relocate(p,np.eye(3),offset) for p in b]
        preliminary=frame_support(a,shifted,tolerance,proofs=24,
                                  progress=progress,cancelled=cancelled)
        checked=preliminary['checked']
        confirmed=preliminary['proofs']
        # This is only a cheap reject gate; it does not certify SAME, MOVED,
        # a translation, or any of the output artifact pairs.
        if (preliminary['count']>=minimum
                and preliminary['count']>baseline
                and checked>=min(8,preliminary['count'])
                and confirmed>=max(4,ceil(.65*checked))):
            sampled.append((coarse,offset,shifted))
        if progress:
            progress(f'Przesunięcie: próbka B-Rep {confirmed}/{checked}, '
                     f'kandydaci {len(sampled)}/{len(evaluated)}')
    winners=[]
    for coarse,offset,shifted in sampled:
        check_cancel()
        if winners:
            best=max(w[0] for w in winners)
            margin=max(1,ceil(.10*best)) if low_overlap else 0
            if coarse<best-margin:continue
        # Original strict gate: every accepted pair is B-Rep verified.
        # Only these pairs may be reused as certified_pairs in final compare.
        support=frame_support(a,shifted,tolerance,verify_all=True,
                              progress=progress,cancelled=cancelled)
        if support['count']>=minimum and support['count']>baseline:
            winners.append((support['count'],offset,support['pairs']))
"""
out=src[:a]+replacement+src[b:]
ast.parse(out)
path.write_text(out,encoding='utf-8')
print('RC9 two-stage virtual-offset candidate rejection installed; full B-Rep proof retained')
