"""Recover one repeated world witness before marking its occurrences unknown."""
from pathlib import Path
import sys
p=Path(sys.argv[1])/'dsac29/compare.py';s=p.read_text()
a="    trace.mark('signature_cache','END',definitions_a=len(set(group_a)),definitions_b=len(set(group_b)))"
assert s.count(a)==1
s=s.replace(a,a+'''
    from .repeated_world_recovery import RepeatedWorldRecovery
    repeated_world_recovery=RepeatedWorldRecovery(a,b,group_a,group_b,tolerance)''')
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
compile(s,str(p),'exec');p.write_text(s)
print('REPEATED_FIXED_WORLD_RECOVERY_PASS')

native=p.with_name('native_guard.py')
s=native.read_text()
changes=[
    ('process_args=None, registered_reexport=False):',
     'process_args=None, registered_reexport=False, repeated_cells=False):'),
    ("'operation':'registered_rigid' if registered_reexport else 'rigid',",
     "'operation':'registered_rigid' if registered_reexport else 'rigid', 'repeated_cells':repeated_cells,"),
    ("        if req.get('operation') == 'registered_rigid':",
     """        cells_match=False
        if req.get('repeated_cells'):
            from .shared_cells import same_material_cells
            try:
                cells_match=same_material_cells(a_shape,b_shape,float(req['tolerance']))
            except (ValueError, RuntimeError):
                pass
        if cells_match:
            import numpy
            match,r,t=True,numpy.eye(3),numpy.zeros(3)
        elif req.get('operation') == 'registered_rigid':""")]
for old,new in changes:
    assert s.count(old)==1
    s=s.replace(old,new)
compile(s,str(native),'exec')
native.write_text(s)
