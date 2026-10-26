"""Recover identity omitted by integrated-property filters, never by heuristics.

Only isolated full CAD surface-and-oriented-trim proof can yield SAME.
A spatial candidate or a successful global alignment is not identity proof.
"""
import numpy as np
from .compare import Record
from .names import genuine_rename
from .native_guard import guarded_world_reexport
from .step_reexport_tolerance import world_candidate,search_radius
from . import trace_r22 as trace

def recover(a,b,records,tolerance,progress=None,cancelled=None):
    old=sorted(r.a_index for r in records if r.status=='REMOVED' and r.a_index is not None and r.b_index is None)
    new=sorted(r.b_index for r in records if r.status=='ADDED' and r.b_index is not None and r.a_index is None)
    if not old or not new:return list(records)
    radius=search_radius(tolerance)
    from collections import defaultdict
    from itertools import product
    buckets=defaultdict(list)
    for j in new:buckets[tuple(np.floor(b[j].center/radius).astype(int))].append(j)
    options={};reverse=defaultdict(list)
    for i in old:
        cell=np.floor(a[i].center/radius).astype(int);hits=[]
        for delta in product((-1,0,1),repeat=3):
            for j in buckets.get(tuple(cell+delta),()):
                if np.linalg.norm(a[i].center-b[j].center)<=radius and world_candidate(a[i],b[j],tolerance):hits.append(j)
        options[i]=hits
        for j in hits:reverse[j].append(i)
    proven={}
    for i in old:
        if cancelled and cancelled():raise InterruptedError('Anulowano analizę')
        hits=options[i]
        # Only unambiguous occurrence correspondence; duplicates keep existing path.
        if len(hits)!=1 or len(reverse[hits[0]])!=1:continue
        j=hits[0]
        if progress:progress(f'Weryfikacja pozostałych par CAD: A[{i}] ↔ B[{j}] — powierzchnie i granice, bez Boolean')
        if trace.brep_call('residual_identity',i,j,guarded_world_reexport,a[i],b[j],tolerance,allow_boolean=False):
            proven[i]=j
    if not proven:return list(records)
    used_b=set(proven.values())
    out=[r for r in records if not ((r.status=='REMOVED' and r.a_index in proven) or (r.status=='ADDED' and r.b_index in used_b))]
    for i,j in proven.items():
        out.append(Record(i,j,'SAME','Potwierdzona zgodność powierzchni CAD i wszystkich zorientowanych granic',name_changed=genuine_rename(a[i],b[j])))
    out.sort(key=lambda r:(r.b_index is None,r.b_index if r.b_index is not None else r.a_index))
    trace.mark('residual_identity','END',proven=len(proven),unresolved_old=len(old)-len(proven))
    return out
