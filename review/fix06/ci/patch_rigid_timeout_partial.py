"""Retain verified parts when an isolated rigid-pair proof times out."""
from pathlib import Path
import sys
p=Path(sys.argv[1])/'dsac29/compare.py';s=p.read_text()
a='    failed_groups = set()'
assert s.count(a)==1
s=s.replace(a,a+'\n    unknown_rigid_groups = set()')
a='''                elif pair in failed_groups:
                    match=False;memo_hits+=1'''
assert s.count(a)==1
s=s.replace(a,'''                elif pair in unknown_rigid_groups:
                    # Timeout is neither equality nor a negative geometry proof.
                    # Retain each unresolved occurrence without repeating the
                    # same definition search for every combination of copies.
                    failed_a.add(i);failed_b.add(j);failed_pairs.add((i,j))
                    continue
'''+a)
a='''                    except NativeGeometryFailure:
                        raise'''
assert s.count(a)==1
s=s.replace(a,'''                    except NativeGeometryFailure as exc:
                        unknown_rigid_groups.add(pair)
                        failed_a.add(i);failed_b.add(j);failed_pairs.add((i,j))
                        trace.mark('rigid_matching_pair','UNVERIFIED',a_id=i,b_id=j,error=str(exc))
                        if progress:progress(f'Ruch części: A[{i}] / B[{j}] niepotwierdzone: {exc}. Zachowuję pozostałe wyniki.')
                        continue''')
s=s.replace('stage; a crash must fail the entire job, never become a green match.',
            'stage; an incomplete pair remains uncertain without losing verified parts.')
compile(s,str(p),'exec');p.write_text(s)
