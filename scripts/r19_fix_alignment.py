"""R19: recover global translation when STEP roundtrip changes numerical B-Rep signatures.

Applied to R17 sources already patched with R18. Exact B-Rep verification is
retained: coarse centroid/volume votes NEVER classify any part as unchanged.
"""
from pathlib import Path
root=Path("source/dsac29")
p=root/"deferred_alignment.py"
s=p.read_text(encoding="utf8")
anchor="\ndef _periodic_global_offset_possible(a,b,tolerance,population):"
assert anchor in s and "def propose_from_centroid_consensus(" not in s
helper=r'''

def propose_from_centroid_consensus(a,b,tolerance,baseline=0,progress=None,cancelled=None):
    """Secondary registration when STEP roundtrip perturbs strict descriptors."""
    from collections import Counter
    from math import ceil
    n=min(len(a),len(b))
    if n<5:return None
    sa=list(range(0,len(a),max(1,ceil(len(a)/150))))
    sb=list(range(0,len(b),max(1,ceil(len(b)/150))))
    scale=max(float(tolerance)*2.,.02)
    hist=Counter();offsets={}
    def loose(x,y):
        if x.volume<=0 or y.volume<=0:return False
        return (abs(x.volume-y.volume)/max(x.volume,y.volume)<=.005
                and abs(x.area-y.area)/max(x.area,y.area)<=.005)
    for i in sa:
        if cancelled and cancelled():raise Cancelled("Anulowano analizę")
        for j in sb:
            if not loose(a[i],b[j]):continue
            d=a[i].center-b[j].center
            if np.linalg.norm(d)<=max(tolerance,.01):continue
            key=tuple(int(round(float(v)/scale)) for v in d)
            hist[key]+=1
            offsets.setdefault(key,d)
    if not hist:return None
    index=_spatial_index(a,range(len(a)),max(tolerance,.02))
    plausible=[]
    for key,_ in hist.most_common(25):
        d=offsets[key];used=set()
        for p in b:
            target=p.center+d
            for i in _nearby(index,SimpleNamespace(center=target),max(tolerance,.02)):
                if i in used:continue
                if np.linalg.norm(a[i].center-target)>max(tolerance,.02):continue
                if not loose(a[i],p):continue
                used.add(i);break
        score=len(used)
        if score>=max(5,ceil(.80*n)) and score>baseline:
            plausible.append((score,d))
    if not plausible:return None
    plausible.sort(key=lambda x:-x[0])
    best,best_offset=plausible[0]
    if any(score>=best-max(1,ceil(.10*n))
           and np.linalg.norm(other-best_offset)>scale
           for score,other in plausible[1:]):
        return {"status":"unresolved",
                "reason":"Niejednoznaczne globalne przesunięcie centrów części."}
    shifted=[_relocate(p,np.eye(3),best_offset) for p in b]
    verified=frame_support(a,shifted,tolerance,verify_all=True)
    proof=int(verified["count"])
    required=2 if best==n and n<=40 else max(3,ceil(.10*n))
    if proof<required:return None
    if progress:
        progress(f"Przesunięcie grupy: {best}/{n} centrów, "
                 f"{proof} niezależnych potwierdzeń B-Rep. "
                 "Pozostałe bryły będą sklasyfikowane oddzielnie.")
    return {"status":"registered","method":"centroid_consensus_brep_anchors",
            "translation_B_to_A_mm":best_offset.tolist(),
            "rotation_B_to_A":np.eye(3).tolist(),
            "votes":proof,"center_votes":best,
            "previous_world_matches":baseline,
            "support_ratio":round(proof/max(1,n),4),
            "requested":True,"enabled":True}
'''
s=s.replace(anchor,helper+anchor)
old="    return propose(a,b,records,tolerance,progress,cancelled)\n"
assert s.count(old)==1
s=s.replace(old,'''    first=propose(a,b,records,tolerance,progress,cancelled)
    if first is not None and first.get("status")=="registered":return first
    recovered=propose_from_centroid_consensus(a,b,tolerance,baseline,progress,cancelled)
    return recovered if recovered is not None else first
''')
p.write_text(s,encoding="utf8")
p=root/"cli.py";s=p.read_text(encoding="utf8")
old='''                if (votes>=max(2*original,original+ceil(.30*pop))
                    and votes>=max(8,ceil(.50*pop))):
'''
assert s.count(old)==1
new='''                strong_centroid=(proposal.get("method")=="centroid_consensus_brep_anchors"
                                 and int(proposal.get("center_votes",0))>=ceil(.85*pop)
                                 and votes>=max(2,ceil(.10*pop)) and votes>original)
                if ((votes>=max(2*original,original+ceil(.30*pop))
                     and votes>=max(8,ceil(.50*pop))) or strong_centroid):
'''
s=s.replace(old,new)
p.write_text(s,encoding="utf8")
print("R19 stage-1 centroid fallback and guarded automatic registration applied")
