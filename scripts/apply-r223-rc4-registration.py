"""RC4: do not abort an entire registration on a single inconclusive B-Rep."""
from pathlib import Path
import sys
root=Path(sys.argv[1])
p=root/'dsac29/registration_gate.py'
s=p.read_text(encoding='utf-8')
old=" registry=GeometryRegistry();anchors={}\n def proven(i,j):\n"
new=""" registry=GeometryRegistry();anchors={}
 # Failed native proofs are not matches. Bound failures to avoid false confidence.
 unverified=set();failed_groups=set()
 def proven(i,j):
"""
assert s.count(old)==1
s=s.replace(old,new)
old="""  if not same:
   if max(len(a),len(b))>=600:
    # Crash-prone OCCT face/edge comparison MUST run in a child process.
    same=trace.brep_call('verify_reexport_guarded',i,j,
        native_guard.guarded_world_reexport,left,right,tolerance,allow_boolean=False)
   else:
"""
new="""  if not same:
   if max(len(a),len(b))>=600:
    # Inconclusive proofs are never SAME. A bounded number of isolated
    # failures can be skipped while independently verified pairs are retained.
    if key in failed_groups:
     unverified.add((i,j))
     if len(unverified)>max(4,int(min(len(a),len(b))*.01)):
      raise native_guard.NativeGeometryFailure(
       'Zbyt wiele niezweryfikowanych bryl B-Rep podczas wyrownania '
       f'({len(unverified)}). Nie mozna bezpiecznie ustalic przesuniecia.')
     return False
    try:
     same=trace.brep_call('verify_reexport_guarded',i,j,
         native_guard.guarded_world_reexport,left,right,tolerance,allow_boolean=False)
    except native_guard.NativeGeometryFailure as exc:
     unverified.add((i,j));failed_groups.add(key)
     trace.mark('registration_proof','UNVERIFIED',a_id=i,b_id=j,
                error=str(exc),unverified_count=len(unverified))
     if len(unverified)>max(4,int(min(len(a),len(b))*.01)):
      raise native_guard.NativeGeometryFailure(
       'Zbyt wiele niezweryfikowanych bryl B-Rep podczas wyrownania '
       f'({len(unverified)}). Nie mozna bezpiecznie ustalic przesuniecia.') from exc
     return False
   else:
"""
assert s.count(old)==1
s=s.replace(old,new)
old=""" if not pairs:return dict(count=0,ratio=0.,proofs=0,checked=0,pairs=[])
 if verify_all:return dict(count=len(pairs),ratio=len(pairs)/max(1,min(len(a),len(b))),proofs=len(pairs),checked=len(pairs),pairs=pairs)
"""
new=""" if not pairs:return dict(count=0,ratio=0.,proofs=0,checked=0,pairs=[],unverified=len(unverified))
 if verify_all:return dict(count=len(pairs),ratio=len(pairs)/max(1,min(len(a),len(b))),proofs=len(pairs),checked=len(pairs),pairs=pairs,unverified=len(unverified))
"""
assert s.count(old)==1
p.write_text(s.replace(old,new),encoding='utf-8')
p=root/'dsac29/native_session.py'
s=p.read_text(encoding='utf-8')
old='    def __init__(self, max_requests=32):'
assert s.count(old)==1
p.write_text(s.replace(old,'    def __init__(self, max_requests=16):'),encoding='utf-8')
print('RC4 fail-closed registration patch applied')
