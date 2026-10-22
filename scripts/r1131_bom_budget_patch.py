"""R11.31 bounded, conservative BOM. Counts/masses remain exact.

Exact geometrical deduplication is too expensive for hundreds of independent
OCC definitions. When budget expires, leave still-unproven solids separate;
never merge just because names or dimensions match.
"""
from pathlib import Path
import os
root=Path(os.environ["DS_COMPARE_SOURCE"])
p=root/"dsac29/report.py"
s=p.read_text(encoding="utf8")
old="def geometry_groups(parts, progress=None, report_progress=None, context=None, tolerance=0.01, known_groups=None, fast_proven_only=False):"
new="def geometry_groups(parts, progress=None, report_progress=None, context=None, tolerance=0.01, known_groups=None, fast_proven_only=False, time_budget_s=28):"
assert s.count(old)==1
s=s.replace(old,new,1)
old="""    context = context if context is not None else GeometryRegistry()
    buckets = defaultdict(list)"""
new="""    context = context if context is not None else GeometryRegistry()
    deadline=perf_counter()+max(5,float(time_budget_s))
    budget_exceeded=False
    buckets = defaultdict(list)"""
assert s.count(old)==1
s=s.replace(old,new,1)
old="""        possible = [group_index for group_index in buckets.get(sig, ())
                    if candidate(parts[groups[group_index][0]], part, tolerance)]"""
new="""        if perf_counter()>deadline and not budget_exceeded:
            budget_exceeded=True
            context.stats['bom_budget_exhausted']+=1
            if progress:progress('BOM: przekroczono limit dokładnego grupowania; pozostałe unikalne definicje zachowano jako osobne pozycje.')
        possible = [] if budget_exceeded else [group_index for group_index in buckets.get(sig, ())
                    if candidate(parts[groups[group_index][0]], part, tolerance)]"""
assert s.count(old)==1
s=s.replace(old,new,1)
old="""    def safe_groups(parts,role,start,end,known_groups=None):
        before=len(geometry_context.bom_errors)"""
new="""    def safe_groups(parts,role,start,end,known_groups=None):
        before=len(geometry_context.bom_errors)
        before_budget=geometry_context.stats.get('bom_budget_exhausted',0)
        effective_fast=bom_fast or len(parts)>180
        if effective_fast and not bom_fast:
            warning=f'BOM {role}: duże złożenie ({len(parts)} brył); szybkie grupowanie wyłącznie po potwierdzonej geometrii. Liczba pozycji może być większa.'
            bom_warnings.append(warning)
            if progress:progress(warning)"""
assert s.count(old)==1
s=s.replace(old,new,1)
old="""context=geometry_context,tolerance=tolerance,fast_proven_only=bom_fast,**({'known_groups':known_groups} if known_groups else {}))
            if len(geometry_context.bom_errors)>before:"""
new="""context=geometry_context,tolerance=tolerance,fast_proven_only=effective_fast,time_budget_s=28,
                **({'known_groups':known_groups} if known_groups else {}))
            if geometry_context.stats.get('bom_budget_exhausted',0)>before_budget:
                bom_warnings.append(f'BOM {role}: przekroczono 28 s na grupowanie, niepotwierdzone duplikaty pokazano osobno. Masa całkowita i liczba brył nie zmieniły się.')
            if len(geometry_context.bom_errors)>before:"""
assert s.count(old)==1
s=s.replace(old,new,1)
p.write_text(s,encoding="utf8")
print('R11.31 BOM: bound grouping to 28s per assembly, fast identity for >180 solids, never invent duplicate groupings')
