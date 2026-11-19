"""Route mixed STEP representations to complete boundary proof at every size."""
from pathlib import Path
import sys
p=Path(sys.argv[1])/'dsac29/compare.py'
s=p.read_text()
a='    memo_hits = 0\n'
assert s.count(a)==1
s=s.replace(a,'    from .export_representation import RepresentationCache\n    representations = RepresentationCache()\n'+a)
a='    broad_world_lookup=(max(len(a),len(b))>=80 or registered_lookup or step_reexport_tolerance or exact_serialization)'
assert s.count(a)==1
s=s.replace(a,'''    # Exporter-dependent mass integration drift also affects small assemblies.
    # A wider candidate lookup never widens the subsequent geometry tolerance.
    broad_world_lookup=True''')
a='                        if large_registered:'
assert s.count(a)==1
s=s.replace(a,'''                        if representations.differs(s,b[j],gs,gt):
                            # Do not let coincident analytic/NURBS Common hang
                            # before the exporter-independent proof is reached.
                            same=trace.brep_call('mixed_export_boundary',i,j,
                                bounded_reexport,s,b[j],tolerance)
                        elif large_registered:''')
a='(bounded_reexport if len(a)>=80 else reexport_equivalent_world)'
assert s.count(a)==2
s=s.replace(a,'bounded_reexport')
compile(s,str(p),'exec');p.write_text(s)
print('MIXED_EXPORT_DISPATCH_PASS')
