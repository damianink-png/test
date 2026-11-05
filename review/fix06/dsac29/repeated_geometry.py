"""Full-revision occurrence populations for the automatic material policy.

Names, positions and descriptor equality do not prove a repeated definition.
Only native identity, exact local B-Rep or a completed rigid proof can group
occurrences. Unknown geometry is never silently declared equal.
"""
from collections import defaultdict
from .compare import _VolumeIndex, Cancelled
from .geometry import candidate
from .geometry_registry import GeometryRegistry


def geometry_populations(parts, tolerance=.01, geometry_context=None, cancelled=None):
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
    for i in representatives:
        for j in index.query(parts[i].volume,tolerance):
            if j<=i or find(i)==find(j):continue
            if cancelled and cancelled():raise Cancelled('Przerwano analizę')
            left,right=parts[i],parts[j]
            proven=context.has_rigid_proof(left,right,tolerance)
            if not proven and not candidate(left,right,tolerance):continue
            if not proven:
                proven=context.same_definition(left,right)
            if not proven and isinstance(context,GeometryRegistry):
                # Baked placements or independent STEP serializations can
                # differ bytewise. Keep this native operation crash-contained.
                from .native_guard import guarded_rigid,NativeGeometryFailure
                try:
                    proven=bool(guarded_rigid(left,right,tolerance)[0])
                except NativeGeometryFailure:
                    continue
                context.remember_equivalence(left,right,tolerance,proven)
            if proven:parent[find(j)]=find(i)
    populations=defaultdict(list)
    for i,ids in members.items():populations[find(i)].extend(ids)
    return [tuple(sorted(ids)) for ids in populations.values()]


def repeated_ids(parts, tolerance=.01, geometry_context=None, cancelled=None):
    return {i for ids in geometry_populations(parts,tolerance,geometry_context,cancelled)
            if len(ids)>1 for i in ids}


class RepeatedMaterialPolicy:
    """Whole-revision quantities and separated revision names gate Common.

Every admitted pair still requires the unchanged spatial and native Common/
Cut checks. Equal names or quantities never prove that geometry is unchanged.
"""
    def __init__(self,a,b,tolerance=.01,geometry_context=None,cancelled=None):
        from collections import Counter
        from .material_names import material_name_key
        self.keys_a=[material_name_key(p.name) for p in a]
        self.keys_b=[material_name_key(p.name) for p in b]
        totals_a=Counter(self.keys_a)
        totals_b=Counter(self.keys_b)
        self.sizes_a=[1]*len(a)
        self.sizes_b=[1]*len(b)
        for parts,sizes in ((a,self.sizes_a),(b,self.sizes_b)):
            for group in geometry_populations(parts,tolerance,geometry_context,cancelled):
                for i in group:sizes[i]=len(group)
        self.repeated_a={i for i,n in enumerate(self.sizes_a) if n>1}
        self.repeated_b={j for j,n in enumerate(self.sizes_b) if n>1}
        # Quantities use the entire model, including SAME/MOVED occurrences.
        # Both the geometric family and named family must keep their counts.
        self.tokens_a=[(n,k,totals_a[k]) if n>1 and k else None
                       for n,k in zip(self.sizes_a,self.keys_a)]
        self.tokens_b=[(n,k,totals_b[k]) if n>1 and k else None
                       for n,k in zip(self.sizes_b,self.keys_b)]

    def allows(self,i,j):
        if i not in self.repeated_a and j not in self.repeated_b:return True
        return self.tokens_a[i] is not None and self.tokens_a[i]==self.tokens_b[j]

    def eligible(self,old_ids,new_ids):
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
        return aa,bb
