"""Full-revision occurrence populations for the automatic material policy.

Names, positions and descriptor equality do not prove a repeated definition.
Only native identity, exact local B-Rep or a completed rigid proof can group
occurrences. Unknown geometry is never silently declared equal.
"""
from collections import defaultdict
from time import perf_counter
from .compare import _VolumeIndex, Cancelled
from .geometry import candidate
from .geometry_registry import GeometryRegistry


def geometry_populations(parts, tolerance=.01, geometry_context=None, cancelled=None, *, relevant_ids=None, progress=None):
    context=geometry_context if geometry_context is not None else GeometryRegistry()
    # Native groups need no serialization or Boolean, irrespective of count.
    groups=defaultdict(list)
    for i,p in enumerate(parts):
        if cancelled and cancelled():raise Cancelled('Przerwano analizę')
        key=context.definition(p) if hasattr(context,'definition') else i
        groups[key].append(i)
    representatives=[ids[0] for ids in groups.values()]
    members={ids[0]:ids for ids in groups.values()}
    index=_VolumeIndex(parts,representatives)
    parent={i:i for i in representatives}
    def find(i):
        while parent[i]!=i:
            parent[i]=parent[parent[i]]
            i=parent[i]
        return i
    # Count full-revision populations, but only explore components touching
    # requested Common operands. Unrelated SAME/MOVED families need no tests.
    relevant=None if relevant_ids is None else set(relevant_ids)
    if relevant is not None and not relevant.issubset(range(len(parts))):
        raise ValueError('Nieprawidłowy zakres części do liczenia wystąpień')
    queue=list(representatives) if relevant is None else [i for i in representatives if relevant.intersection(members[i])]
    scheduled=set(queue);processed=set();native_checks=0;started=perf_counter();last=started
    if progress:progress(f'Zmiany materiału: liczby wystąpień — {len(queue)} rodzin wymagających kontroli w modelu z {len(parts)} częściami.')
    for i in queue:
        for j in index.query(parts[i].volume,tolerance):
            if j in processed or find(i)==find(j):continue
            if cancelled and cancelled():raise Cancelled('Przerwano analizę')
            left,right=parts[i],parts[j]
            known=(context.rigid_result(left,right,tolerance) if hasattr(context,'rigid_result') else None)
            if known is False:continue
            proven=known is True or context.has_rigid_proof(left,right,tolerance)
            if not proven and not candidate(left,right,tolerance):continue
            if not proven:proven=context.same_definition(left,right)
            if not proven and isinstance(context,GeometryRegistry):
                from .native_guard import guarded_rigid,NativeGeometryFailure
                native_checks+=1
                if progress and (native_checks==1 or perf_counter()-last>=.75):
                    progress(f'Zmiany materiału: liczby wystąpień — test B-Rep {native_checks}, definicje {i}/{j}; {perf_counter()-started:.1f} s.')
                    last=perf_counter()
                try:proven=bool(guarded_rigid(left,right,tolerance)[0])
                except NativeGeometryFailure:continue
                context.remember_equivalence(left,right,tolerance,proven)
            if proven:
                parent[find(j)]=find(i)
                if j not in scheduled:queue.append(j);scheduled.add(j)
        processed.add(i)
        if progress and perf_counter()-last>=.75:
            progress(f'Zmiany materiału: liczby wystąpień — sprawdzono {len(processed)}/{len(queue)} definicji; testy B-Rep {native_checks}.')
            last=perf_counter()
    if progress:progress(f'Zmiany materiału: liczby wystąpień — ukończono w {perf_counter()-started:.2f} s; testy B-Rep {native_checks}.')
    populations=defaultdict(list)
    for i,ids in members.items():populations[find(i)].extend(ids)
    return [tuple(sorted(ids)) for ids in populations.values() if relevant is None or relevant.intersection(ids)]


def repeated_ids(parts, tolerance=.01, geometry_context=None, cancelled=None):
    return {i for ids in geometry_populations(parts,tolerance,geometry_context,cancelled)
            if len(ids)>1 for i in ids}


class RepeatedMaterialPolicy:
    """Whole-revision quantities and separated revision names gate Common.

Every admitted pair still requires the unchanged spatial and native Common/
Cut checks. Equal names or quantities never prove that geometry is unchanged.
"""
    def __init__(self,a,b,tolerance=.01,geometry_context=None,cancelled=None,*,old_ids=None,new_ids=None,progress=None):
        from collections import Counter
        from .material_names import material_name_key
        self.keys_a=[material_name_key(p.name) for p in a]
        self.keys_b=[material_name_key(p.name) for p in b]
        totals_a=Counter(self.keys_a)
        totals_b=Counter(self.keys_b)
        self.scope_a=set(range(len(a))) if old_ids is None else set(old_ids)
        self.scope_b=set(range(len(b))) if new_ids is None else set(new_ids)
        self.sizes_a=[1]*len(a)
        self.sizes_b=[1]*len(b)
        for parts,sizes,scope in ((a,self.sizes_a,self.scope_a),(b,self.sizes_b,self.scope_b)):
            for group in geometry_populations(parts,tolerance,geometry_context,cancelled,relevant_ids=scope,progress=progress):
                for i in group:sizes[i]=len(group)
        self.repeated_a={i for i,n in enumerate(self.sizes_a) if n>1}
        self.repeated_b={j for j,n in enumerate(self.sizes_b) if n>1}
        # Quantities use the entire model, including SAME/MOVED occurrences.
        # Both the geometric family and named family must keep their counts.
        self._parts_a=a
        self._parts_b=b
        self.tokens_a=[(n,k,totals_a[k]) if n>1 and k else None
                       for n,k in zip(self.sizes_a,self.keys_a)]
        self.tokens_b=[(n,k,totals_b[k]) if n>1 and k else None
                       for n,k in zip(self.sizes_b,self.keys_b)]
        # Unequal whole-family quantities may still leave ONE old and ONE new
        # candidate after all verified stationary occurrences are consumed.
        # Admit only that unambiguous residual name family to a real native
        # Common/Cut comparison; a name alone never certifies CHANGED.
        self._residual_singletons=set()
        # eligible() is called twice during Common preparation, often with
        # overlapping operand sets. Topological bounds are immutable within
        # one comparison, so compute them at most once per occurrence.
        self._bbox_cache_a={}
        self._bbox_cache_b={}

    def allows(self,i,j):
        if i not in self.scope_a or j not in self.scope_b:return False
        if i not in self.repeated_a and j not in self.repeated_b:return True
        return ((self.tokens_a[i] is not None and self.tokens_a[i]==self.tokens_b[j])
                or (i,j) in self._residual_singletons)

    def eligible(self,old_ids,new_ids):
        if not set(old_ids).issubset(self.scope_a) or not set(new_ids).issubset(self.scope_b):
            raise ValueError('Nieprzeliczona rodzina geometrii poza zakresem Common')
        tokens_a={self.tokens_a[i] for i in old_ids if self.tokens_a[i] is not None}
        tokens_b={self.tokens_b[j] for j in new_ids if self.tokens_b[j] is not None}
        unique_a=bool(old_ids-self.repeated_a)
        unique_b=bool(new_ids-self.repeated_b)
        aa={i for i in old_ids if
            (i not in self.repeated_a and unique_b) or
            (self.tokens_a[i] is not None and self.tokens_a[i] in tokens_b)}
        bb={j for j in new_ids if
            (j not in self.repeated_b and unique_a) or
            (self.tokens_b[j] is not None and self.tokens_b[j] in tokens_a)}
        # A mixed revision can contain e.g. 10 old and 8 new copies:
        # after the stationary pairs are consumed, some residual copies
        # still have a UNIQUE physical position and a genuine material change.
        # Only admit a mutually UNIQUE overlap in the SAME engineering-name
        # family, before the actual native Common/Cut proof. Never infer
        # CHANGED from this bbox/name hint alone.
        by_old=defaultdict(list);by_new=defaultdict(list)
        for i in sorted(old_ids):
            if self.keys_a[i]:by_old[self.keys_a[i]].append(i)
        for j in sorted(new_ids):
            if self.keys_b[j]:by_new[self.keys_b[j]].append(j)
        self._residual_spatial_checks=0
        self._residual_spatial_ambiguous=0
        from .geometry import _precise_world_bounds
        import numpy as np
        bbox_a,bbox_b=self._bbox_cache_a,self._bbox_cache_b
        def world_bbox(part,index,cache):
            if index not in cache:
                box=np.asarray(_precise_world_bounds(part.shape),dtype=float)
                cache[index]=box if box.shape==(6,) and np.isfinite(box).all() else None
            return cache[index]
        for name,ids in by_old.items():
            others=by_new.get(name,())
            if not others or not (any(i in self.repeated_a for i in ids)
                                  or any(j in self.repeated_b for j in others)):
                continue
            # 30k nearby-name candidates is already far too ambiguous to
            # justify a new Cartesian Boolean search.
            if len(ids)*len(others)>30000:
                self._residual_spatial_ambiguous+=len(ids)+len(others)
                continue
            deg_a=defaultdict(list);deg_b=defaultdict(list)
            for i in ids:
                x=world_bbox(self._parts_a[i],i,bbox_a)
                if x is None:continue
                vol_x=float(np.prod(np.maximum(0.,x[3:]-x[:3])))
                if vol_x<=0:continue
                for j in others:
                    y=world_bbox(self._parts_b[j],j,bbox_b)
                    if y is None:continue
                    vol_y=float(np.prod(np.maximum(0.,y[3:]-y[:3])))
                    if vol_y<=0:continue
                    common=float(np.prod(np.maximum(
                        0.,np.minimum(x[3:],y[3:])-np.maximum(x[:3],y[:3]))))
                    self._residual_spatial_checks+=1
                    if common<.25*min(vol_x,vol_y):continue
                    deg_a[i].append(j);deg_b[j].append(i)
            for i,js in deg_a.items():
                if len(js)!=1:continue
                j=js[0]
                if len(deg_b[j])!=1:continue
                self._residual_singletons.add((i,j))
                aa.add(i);bb.add(j)
            self._residual_spatial_ambiguous+=sum(
                len(js)>1 for js in deg_a.values())
        return aa,bb
