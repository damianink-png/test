"""Safe geometry fingerprint priority for CAD matching candidates.

Uses the same *existing* volume, face area and principal moments already
calculated by DS Compare. This is NOT a new proof of geometric equality:
never exclude a candidate, change native tolerance or return SAME.

The inexpensive descriptor is evaluated lazily only for ambiguous
world/overlap candidate *ties*. An unrelated candidate's failure never
suppresses any later positive whole-B-Rep proof.
"""
from math import isfinite

def _features(part):
    try:
        v=float(part.volume)
        a=float(part.area)
        moments=tuple(sorted(float(x) for x in part.eigenvalues))
        if len(moments)!=3 or not all(isfinite(x) for x in (v,a,*moments)):
            return None
        if v<=0 or a<=0:
            return None
        return (v,a,*moments)
    except (AttributeError,TypeError,ValueError,OverflowError):
        return None


def _ratio(x,y):
    # Relative, scale-free discrepancy. Noise is measured consistently for
    # very small as well as massive industrial CAD parts.
    return min(1.,abs(x-y)/max(abs(x),abs(y),1e-12))


class FingerprintPriority:
    """Per-comparison, immutable-part cache. Never cross-revision persistent."""
    def __init__(self):
        self._cache={}
        self._surface_cache={}
        self._surface_native=[]
        self._surface_shapes={}
        self.tie_groups=0
        self.descriptors_computed=0
        self.surface_analyses=0
        self.surface_reuses=0
        self.surface_pair_rankings=0
        self.surface_budget=64

    @classmethod
    def shared(cls,context):
        """Single comparison-scoped feature store; no stale global state."""
        if context is None:
            return cls()
        result=getattr(context,'_dscompare_fingerprint_priority',None)
        if result is None:
            result=cls()
            context._dscompare_fingerprint_priority=result
        return result

    def surface(self,part):
        """Analytical face features. NEVER a CAD equality certificate."""
        source=getattr(part,'step_definition_key',None)
        key=('XCAF',tuple(source)) if source is not None else ('occurrence',id(part))
        shape=getattr(part,'shape',None)
        if shape is None:
            return None
        # A reworked CAD part can preserve its imported XCAF label while
        # replacing the native geometry. Check IsPartner before serving a
        # cached surface fingerprint, to avoid stale data across revisions.
        if key in self._surface_cache:
            cached_shape=self._surface_shapes.get(key)
            if cached_shape is not None and shape.IsPartner(cached_shape):
                self.surface_reuses+=1
                return self._surface_cache[key]
        # The OCP Python wrapper returned by shape.TShape() is ephemeral:
        # hash(shape.TShape()) is NOT stable for the same native definition.
        # At most 64 definitions are retained. Check genuine native
        # IsPartner directly; it also works for translated occurrences.
        for saved,value in self._surface_native:
            if shape.IsPartner(saved):
                self._surface_cache[key]=value
                self._surface_shapes[key]=shape
                self.surface_reuses+=1
                return value
        if self.surface_analyses>=self.surface_budget:
            return None
        self.surface_analyses+=1
        value=None
        try:
            from OCP.TopExp import TopExp_Explorer
            from OCP.TopAbs import TopAbs_FACE
            from OCP.TopoDS import TopoDS
            from OCP.BRepAdaptor import BRepAdaptor_Surface
            from collections import Counter
            ex=TopExp_Explorer(shape,TopAbs_FACE)
            kinds=Counter();radii=[];faces=0
            while ex.More():
                faces+=1
                if faces>220:
                    kinds=None
                    break
                adaptor=BRepAdaptor_Surface(TopoDS.Face_s(ex.Current()))
                kind=str(adaptor.GetType()).split('.')[-1].replace('GeomAbs_','')
                kinds[kind]+=1
                if kind=='Cylinder':
                    radii.append(float(adaptor.Cylinder().Radius()))
                elif kind=='Torus':
                    tor=adaptor.Torus()
                    radii.extend((float(tor.MajorRadius()),float(tor.MinorRadius())))
                elif kind=='Sphere':
                    radii.append(float(adaptor.Sphere().Radius()))
                elif kind=='Cone':
                    radii.append(float(adaptor.Cone().RefRadius()))
                ex.Next()
            if kinds is not None:
                total=sum(kinds.values())
                curved=any(kinds.get(k,0)>0 for k in ('Cylinder','Cone','Torus','Sphere'))
                value=(tuple(sorted((k,n/total) for k,n in kinds.items())),
                       tuple(sorted(set(round(x,4) for x in radii))),
                       curved)
        except (ValueError,RuntimeError,TypeError,AttributeError,OverflowError):
            value=None
        self._surface_cache[key]=value
        self._surface_shapes[key]=shape
        self._surface_native.append((shape,value))
        return value

    @staticmethod
    def _surface_distance(left,right):
        if not left or not right or not left[2]:
            return None
        aa=dict(left[0]);bb=dict(right[0])
        topology_delta=sum(abs(aa.get(k,0.)-bb.get(k,0.))
                           for k in (aa.keys()|bb.keys()))/2
        ar,br=left[1],right[1]
        if not ar and not br:
            radius_delta=0.
        elif not ar or not br:
            radius_delta=1.
        else:
            radius_delta=sum(min(
                abs(v-u)/max(abs(v),abs(u),1.) for u in br)
                for v in ar)/len(ar)
        return min(1.,.45*topology_delta+.55*radius_delta)

    def candidate_compatible(self,a,b):
        """Unchanged permissive numerical window for unique CAD anchors."""
        import numpy as np
        av=self._of(a);bv=self._of(b)
        if av is None or bv is None or min((*av,*bv))<=0:
            return False
        a5=np.asarray(av,dtype=float);b5=np.asarray(bv,dtype=float)
        return bool(np.all(np.abs(a5-b5)<=np.maximum(
            [.01,.01,.001,.001,.001],
            np.maximum(a5,b5)*[.01,.01,.025,.025,.025])))


    def _of(self,part):
        key=id(part)
        if key not in self._cache:
            self._cache[key]=_features(part)
            self.descriptors_computed+=1
        return self._cache[key]

    def distance(self,a,b,*,with_surface=False):
        left=self._of(a);right=self._of(b)
        if left is None or right is None:
            return float('inf')
        # For a material revision, volume and moments can differ; these
        # components are soft priorities only, NEVER acceptance criteria.
        base=(.25*_ratio(left[0],right[0])
              +.30*_ratio(left[1],right[1])
              +.15*sum(_ratio(x,y) for x,y in zip(left[2:],right[2:])))
        if not with_surface:
            return base
        source_surface=self.surface(a)
        # No expensive target face reads for ordinary planar pieces.
        if source_surface is None or not source_surface[2]:
            return base
        extra=self._surface_distance(source_surface,self.surface(b))
        if extra is None:
            return base
        self.surface_pair_rankings+=1
        return .55*base+.45*extra

    def world_ties(self,source,ordered,targets,tolerance,distances=None):
        """Reorder only near-equidistant candidates; preserve every index."""
        if len(ordered)<2:return ordered
        ordered=list(ordered)
        dist=(lambda j:distances[j]) if distances is not None else (
            lambda j:float(__import__('numpy').linalg.norm(
                source.center-targets[j].center)))
        threshold=max(.005,min(.25,5.*float(tolerance)))
        out=[];start=0
        while start<len(ordered):
            end=start+1
            while end<len(ordered) and dist(ordered[end])-dist(ordered[start])<=threshold:
                end+=1
            group=ordered[start:end]
            if len(group)>1:
                self.tie_groups+=1
                group.sort(key=lambda j:(self.distance(source,targets[j]),
                                          abs(source.volume-targets[j].volume),j))
            out.extend(group);start=end
        assert len(out)==len(ordered)
        return out

    def common_ties(self,source,ordered,targets,gap=.025):
        """Reorder close-overlap pairs; never alter candidate set or scores."""
        if len(ordered)<2:return ordered
        ordered=list(ordered)
        out=[];start=0
        while start<len(ordered):
            end=start+1
            while end<len(ordered) and ordered[end][0]-ordered[start][0]<=gap:
                end+=1
            group=ordered[start:end]
            if len(group)>1:
                self.tie_groups+=1
                group.sort(key=lambda entry:(self.distance(
                    source,targets[entry[1]],with_surface=True),
                    entry[0],entry[1]))
            out.extend(group);start=end
        assert len(out)==len(ordered)
        return out
