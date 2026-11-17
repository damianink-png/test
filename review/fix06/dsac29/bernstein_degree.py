"""Exact rational Bernstein degree elevation; never geometric fitting."""
import numpy as np


def compatible_nets(left,right):
    p,w=map(np.asarray,left);q,v=map(np.asarray,right)
    if p.ndim!=q.ndim or p.ndim not in (2,3) or p.shape[-1]!=3 or q.shape[-1]!=3:
        raise ValueError('Unsupported control net')
    if p.shape[:-1]!=w.shape or q.shape[:-1]!=v.shape:
        raise ValueError('Invalid weights')
    if any(not np.isfinite(a).all() for a in (p,w,q,v)) or min(w.min(),v.min())<=0:
        raise ValueError('Invalid rational net')
    target=tuple(max(a,b) for a,b in zip(w.shape,v.shape))
    if max(target)>33 or np.prod(target)>4096:raise ValueError('Degree budget')
    def elevate(points,weights):
        h=np.concatenate((points*weights[...,None],weights[...,None]),axis=-1)
        for axis,size in enumerate(target):
            h=np.moveaxis(h,axis,0)
            while h.shape[0]<size:
                count=h.shape[0]
                out=np.empty((count+1,)+h.shape[1:]);out[0]=h[0];out[-1]=h[-1]
                for i in range(1,count):
                    alpha=i/count
                    out[i]=alpha*h[i-1]+(1-alpha)*h[i]
                h=out
            h=np.moveaxis(h,0,axis)
        weights=h[...,-1]
        return h[...,:3]/weights[...,None],weights
    return elevate(p,w),elevate(q,v)
