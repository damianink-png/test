"""Full-revision occurrence populations for the automatic material policy.

Names, positions and descriptor equality do not prove a repeated definition.
Only native identity, exact local B-Rep or a completed rigid proof can group
occurrences. Unknown geometry is never silently declared equal.
"""
from collections import defaultdict
from .compare import _VolumeIndex, Cancelled
from .geometry import candidate
from .geometry_registry import GeometryRegistry


def repeated_ids(parts, tolerance=.01, geometry_context=None, cancelled=None):
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
    return {i for ids in populations.values() if len(ids)>1 for i in ids}
