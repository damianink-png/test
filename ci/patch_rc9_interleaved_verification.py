"""Interleave sample and full world-BRep proof to prune weak translation frames.

This is a scheduling optimization only. Candidate offsets and the strict
acceptance/ambiguity checks are unchanged. The sample is never a SAME proof.
"""
from pathlib import Path
import ast
root = Path(__file__).resolve().parents[1] / 'dscompare_rc9_manual'
path = root / 'dsac29' / 'deferred_alignment.py'
src = path.read_text(encoding='utf-8')
start = '    sampled=[];evaluated=[]\n'
end = "    if not winners:return {'status':'unresolved','reason':'Hipotezy nie przeszły kontroli geometrii.'}\n"
if src.count(start) != 1 or src.count(end) != 1:
    raise SystemExit('Expected two-stage alignment block missing; no source changed')
a=src.index(start); b=src.index(end,a)
old=src[a:b]
for required in ('frame_support(a,shifted,tolerance,proofs=24,', 'frame_support(a,shifted,tolerance,verify_all=True,', "support['pairs']", 'len(evaluated)>=16'):
    if required not in old: raise SystemExit('Safety anchor missing: '+required)
replacement = '''    # Verify the best-ranked candidate immediately. Once a fully proven frame
    # exists, apply the SAME existing coarse-score pruning heuristic before
    # sampling further candidates. This avoids spending 24 expensive native
    # checks on each of 16 weak hypotheses before starting any full proof.
    winners=[];evaluated=[]
    identity=np.eye(3)
    for coarse,offset in sorted(ranked,key=lambda v:-v[0]):
        if any(np.linalg.norm(offset-old)<=tolerance for old in evaluated):continue
        if len(evaluated)>=16:break
        if winners:
            best=max(w[0] for w in winners)
            margin=max(1,ceil(.10*best)) if low_overlap else 0
            if coarse<best-margin:continue
        evaluated.append(offset)
        check_cancel()
        # Each unique offset is evaluated once; retaining all shifted OCCT
        # shapes provides no cache hits and unnecessarily increases peak RAM.
        shifted=[_relocate(p,identity,offset) for p in b]
        preliminary=frame_support(a,shifted,tolerance,proofs=24,
                                  progress=progress,cancelled=cancelled)
        checked=preliminary['checked'];confirmed=preliminary['proofs']
        # A sample is ONLY a negative filter. Never classify from it.
        if (preliminary['count']>=minimum
                and preliminary['count']>baseline
                and checked>=min(8,preliminary['count'])
                and confirmed>=max(4,ceil(.65*checked))):
            # All accepted pairs must still be independently B-Rep proven.
            support=frame_support(a,shifted,tolerance,verify_all=True,
                                  progress=progress,cancelled=cancelled)
            if support['count']>=minimum and support['count']>baseline:
                winners.append((support['count'],offset,support['pairs']))
        if progress:
            progress(f'Przesunięcie: próbka B-Rep {confirmed}/{checked}, '
                     f'pełne dowody {len(winners)}, kandydaci {len(evaluated)}')
'''
out=src[:a]+replacement+src[b:]
ast.parse(out)
path.write_text(out,encoding='utf-8')
print('RC9 interleaved translation verification installed; full B-Rep gate retained')
