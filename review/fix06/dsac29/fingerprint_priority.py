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
        self.tie_groups=0
        self.descriptors_computed=0

    def _of(self,part):
        key=id(part)
        if key not in self._cache:
            self._cache[key]=_features(part)
            self.descriptors_computed+=1
        return self._cache[key]

    def distance(self,a,b):
        left=self._of(a);right=self._of(b)
        if left is None or right is None:
            return float('inf')
        # For a material revision, volume and moments can differ; these
        # components are soft priorities only, NEVER acceptance criteria.
        return (.25*_ratio(left[0],right[0])
                +.30*_ratio(left[1],right[1])
                +.15*sum(_ratio(x,y) for x,y in zip(left[2:],right[2:])))

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
                group.sort(key=lambda entry:(self.distance(source,targets[entry[1]]),
                                             entry[0],entry[1]))
            out.extend(group);start=end
        assert len(out)==len(ordered)
        return out
