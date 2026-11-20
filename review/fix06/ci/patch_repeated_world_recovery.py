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
compile(s,str(p),'exec');p.write_text(s)
print('REPEATED_FIXED_WORLD_RECOVERY_PASS')
