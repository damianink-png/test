"""Recover one repeated world witness before marking its occurrences unknown."""
from pathlib import Path
import sys
p=Path(sys.argv[1])/'dsac29/compare.py';s=p.read_text()
a="    trace.mark('signature_cache','END',definitions_a=len(set(group_a)),definitions_b=len(set(group_b)))"
assert s.count(a)==1
s=s.replace(a,a+'''
    from .repeated_world_recovery import RepeatedWorldRecovery
    repeated_world_recovery=RepeatedWorldRecovery(a,b,group_a,group_b,tolerance,geometry_context)''')
start=s.index('                    except NativeGeometryFailure as exc:',s.index("trace.mark('world_matching_pair','BEGIN'"))
end=s.index('                    except Exception as exc:',start)
old=s[start:end]
body=old.split('\n',1)[1]
new='''                    except NativeGeometryFailure as exc:
                        recovered=repeated_world_recovery.recover(i,j,exc,progress)
                        if recovered is True:
                            same=True
                        else:
'''+''.join('    '+l+'\n' for l in body.splitlines())
s=s[:start]+new+s[end:]
s=s.replace("if world_probe_failures[family]>=2:",
            "if world_probe_failures[family]>=2 or (i,j) in repeated_world_recovery.exhausted_pairs:")
# Allow one independent copy after the first expensive proof failed.
# Keep the existing per-pose guard once that bounded alternative is consumed.
anchor="for aa,bb in world_probe_pairs.get((gs,gt),()))):"
assert s.count(anchor)==1
s=s.replace(anchor,"""for aa,bb in world_probe_pairs.get((gs,gt),()))
                      and not (retry_pair := repeated_world_recovery.alternative(
                          i,j,world_probe_pairs[(gs,gt)]))):""")
anchor="                gs, gt = group_a[i], group_b[j]"
assert s.count(anchor)==1
s=s.replace(anchor,anchor+"\n                retry_pair = None")
anchor="                    except NativeGeometryFailure as exc:"
i=s.index(anchor,s.index("trace.mark('world_matching_pair','BEGIN'"))
s=s[:i]+"""                        if retry_pair == (i,j) and not same:
                            raise NativeGeometryFailure('Druga para reprezentatywna: brak dowodu B-Rep')
"""+s[i:]
anchor="                        if representations.differs(s,b[j],gs,gt):"
assert s.count(anchor)==1
s=s.replace(anchor,"""                        if retry_pair == (i,j):
                            same=repeated_world_recovery.verify_alternative(i,j)
                        elif representations.differs(s,b[j],gs,gt):""")
compile(s,str(p),'exec');p.write_text(s)
print('REPEATED_FIXED_WORLD_RECOVERY_PASS')

native=p.with_name('native_guard.py')
s=native.read_text()
changes=[
    ('process_args=None, registered_reexport=False):',
     'process_args=None, registered_reexport=False, repeated_cells=False):'),
    ("'operation':'registered_rigid' if registered_reexport else 'rigid',",
     "'operation':'repeated_cells' if repeated_cells else ('registered_rigid' if registered_reexport else 'rigid'),"),
    ("    elif req.get('operation') == 'common':",
     """    elif req.get('operation') == 'repeated_cells':
        from .shared_cells import same_material_cells
        match=bool(same_material_cells(a_shape,b_shape,float(req['tolerance'])))
        response=dict(ok=True,match=match,
                      rotation=[[1,0,0],[0,1,0],[0,0,1]] if match else None,
                      translation=[0,0,0] if match else None)
    elif req.get('operation') == 'common':""")]
for old,new in changes:
    assert s.count(old)==1
    s=s.replace(old,new)
compile(s,str(native),'exec')
native.write_text(s)
