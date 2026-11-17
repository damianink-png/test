"""Exact knot refinement and rational de Casteljau restriction, not sampling."""
import numpy as np
from itertools import product


def curves_equal(left,right,tolerance):
    from .parametric_identity import pole_bound
    def valid(data):
        k=np.asarray(data[2],float)
        return len(k)==len(data[1])+1 and np.isfinite(k).all() and np.all(np.diff(k)>0) and k[0]==0 and k[-1]==1
    if not valid(left) or not valid(right):return False
    union=sorted(set(left[2])|set(right[2]))
    if len(union)>20000:return False
    def split(h,t):
        a=[h[0]];b=[h[-1]]
        while len(h)>1:
            h=(1-t)*h[:-1]+t*h[1:];a.append(h[0]);b.append(h[-1])
        return np.array(a),np.array(b[::-1])
    def restrict(data,start,end):
        knots=data[2];i=min(len(knots)-2,max(0,int(np.searchsorted(knots,start,side='right'))-1))
        p,w=data[1][i];h=np.concatenate((p*w[:,None],w[:,None]),axis=1)
        lo,hi=knots[i:i+2];u=(start-lo)/(hi-lo);v=(end-lo)/(hi-lo)
        if not 0<=u<v<=1+1e-12:raise ValueError('Invalid interval')
        h,_=split(h,min(1.,v))
        if u>0:_,h=split(h,u/v)
        return h[:,:3]/h[:,3,None],h[:,3]
    try:
        return all(pole_bound(restrict(left,u,v),restrict(right,u,v))<=tolerance for u,v in zip(union,union[1:]))
    except (ValueError,IndexError,FloatingPointError):return False


def surfaces_equal(a,b,required_flip,tolerance):
    from OCP.TColStd import TColStd_Array1OfReal,TColStd_Array1OfInteger
    from OCP.GeomConvert import GeomConvert_BSplineSurfaceToBezierSurface
    from .parametric_identity import pole_bound
    if a.IsUPeriodic() or a.IsVPeriodic() or b.IsUPeriodic() or b.IsVPeriodic():return False
    def array(values,kind):
        result=kind(1,len(values))
        for i,x in enumerate(values,1):result.SetValue(i,x)
        return result
    def normalize(s):
        for axis in ('U','V'):
            values=[getattr(s,axis+'Knot')(i) for i in range(1,getattr(s,'Nb'+axis+'Knots')()+1)]
            span=values[-1]-values[0]
            if not np.isfinite(values).all() or span<=0:raise ValueError('Invalid knots')
            getattr(s,'Set'+axis+'Knots')(array([(v-values[0])/span for v in values],TColStd_Array1OfReal))
    def net(p):
        return (np.array([[p.Pole(i,j).Coord() for j in range(1,p.NbVPoles()+1)] for i in range(1,p.NbUPoles()+1)]),
                np.array([[p.Weight(i,j) for j in range(1,p.NbVPoles()+1)] for i in range(1,p.NbUPoles()+1)]))
    for swap,ru,rv in product((False,True),repeat=3):
        if bool(swap^ru^rv)!=required_flip:continue
        try:
            x,y=a.Copy(),b.Copy()
            if swap:y.ExchangeUV()
            if ru:y.UReverse()
            if rv:y.VReverse()
            normalize(x);normalize(y)
            unions={axis:sorted(set(getattr(s,axis+'Knot')(i) for s in (x,y) for i in range(1,getattr(s,'Nb'+axis+'Knots')()+1))) for axis in ('U','V')}
            if (len(unions['U'])-1)*(len(unions['V'])-1)>10000:continue
            for axis,values in unions.items():
                for s in (x,y):
                    degree=getattr(s,axis+'Degree')()
                    getattr(s,'Insert'+axis+'Knots')(array(values,TColStd_Array1OfReal),array([degree]*len(values),TColStd_Array1OfInteger),0.,False)
            xx,yy=GeomConvert_BSplineSurfaceToBezierSurface(x),GeomConvert_BSplineSurfaceToBezierSurface(y)
            if (xx.NbUPatches(),xx.NbVPatches())!=(yy.NbUPatches(),yy.NbVPatches()):continue
            if all(pole_bound(net(xx.Patch(i,j)),net(yy.Patch(i,j)))<=tolerance for i in range(1,xx.NbUPatches()+1) for j in range(1,xx.NbVPatches()+1)):return True
        except Exception:continue
    return False
