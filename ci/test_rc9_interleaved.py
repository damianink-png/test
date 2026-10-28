"""Synthetic regression: translation is not accepted from a sampled proof."""
from pathlib import Path
import sys
from types import SimpleNamespace
import numpy as np

root=Path(__file__).resolve().parents[1]/'dscompare_rc9_manual'
sys.path.insert(0,str(root))
from dsac29 import deferred_alignment as alignment


def scenario(full_pass):
    a=[SimpleNamespace(center=np.array([10.*i,0.,0.]),volume=float(i+1),name=str(i)) for i in range(40)]
    b=[SimpleNamespace(center=p.center+np.array([100.,25.,-2.]),volume=p.volume,name=p.name) for p in a]
    originals={name:getattr(alignment,name) for name in ('signature','candidate','world_candidate','_relocate','frame_support')}
    calls=[]
    try:
        alignment.signature=lambda p:p.name
        alignment.candidate=lambda left,right,t:left.name==right.name
        alignment.world_candidate=lambda left,right,t:left.name==right.name
        alignment._relocate=lambda p,r,offset:SimpleNamespace(center=p.center+offset,volume=p.volume,name=p.name)
        def proof(a,b,t,**kwargs):
            full=bool(kwargs.get('verify_all',False))
            pairs=[(i,i) for i in range(len(a)) if np.linalg.norm(a[i].center-b[i].center)<=t]
            calls.append((full,len(pairs)))
            if full and not full_pass:
                return dict(count=0,proofs=0,checked=0,pairs=[])
            n=len(pairs) if full else min(24,len(pairs))
            return dict(count=len(pairs),proofs=n,checked=n,pairs=pairs)
        alignment.frame_support=proof
        records=[SimpleNamespace(status='MOVED',a_index=i,b_index=i) for i in range(40)]
        result=alignment.propose(a,b,records,.01)
        assert any(full for full,count in calls), 'No strict full proof was attempted'
        if full_pass:
            assert result['status']=='registered',result
            assert result['votes']==40,result
            assert len(result['certified_pairs'])==40,result
            assert np.allclose(result['translation_B_to_A_mm'],[-100.,-25.,2.]),result
        else:
            assert result['status']=='unresolved',result
        return calls
    finally:
        for name,value in originals.items():setattr(alignment,name,value)

if __name__=='__main__':
    print('full positive',scenario(True))
    print('sample-only rejected',scenario(False))
    print('PASS: virtual offset requires full proof')
