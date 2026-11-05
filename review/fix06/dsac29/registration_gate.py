"""Fast world-coordinate consensus with bounded B-Rep verification."""
from collections import defaultdict
from itertools import product
from math import floor
import numpy as np
from .geometry import signature,candidate,equivalent_world
from . import trace_r22 as trace

class FrameProofCache:
 """One immutable placement hypothesis, shared by its sample and full proof.

 Never reuse across transforms, input order or tolerances. Retain native shape
 snapshots as well as parts so that moved/replaced TopoDS values are detected.
 A native failure is never cached as a geometry result.
 """
 def __init__(self):
  from .geometry_registry import GeometryRegistry
  self.registry=GeometryRegistry();self.anchors={};self.results={}
  self.exact_anchors={};self.failed_pairs=set();self.exact_anchor_hits=0
  self.timed_out_pairs=set();self.skipped_timeouts=0
  self._binding=None
  self.hits=0;self.proof_calls=0

 def bind(self,a,b,tolerance):
  if self._binding is None:
   self._binding=(tuple(a),tuple(b),float(tolerance),
       tuple(p.shape.Located(p.shape.Location()) for p in a),
       tuple(p.shape.Located(p.shape.Location()) for p in b))
   return
  aa,bb,tol,sa,sb=self._binding
  if (float(tolerance)!=tol or len(a)!=len(aa) or len(b)!=len(bb)
      or any(p is not old or not p.shape.IsEqual(shape) for p,old,shape in zip(a,aa,sa))
      or any(p is not old or not p.shape.IsEqual(shape) for p,old,shape in zip(b,bb,sb))):
   raise ValueError('Frame proof cache belongs to a different placement or tolerance')

def _select_diverse_proof_pairs(pairs, parts, limit):
 """Choose independent geometry witnesses, not evenly spaced repeated screws.

 A centroid/descriptor match is a proposal only. This function neither
 verifies a solid nor changes the one-to-one assignment; every selected
 witness still requires the unchanged native B-Rep proof.
 """
 from collections import Counter
 total=len(pairs)
 n=min(max(0,int(limit)),total)
 if n==0:return []
 if n==total:return list(pairs)
 descriptors=[signature(parts[i]) for i,j in pairs]
 frequency=Counter(descriptors)
 def volume(k):
  value=float(getattr(parts[pairs[k][0]],'volume',0.))
  return value if np.isfinite(value) else 0.
 ranked=sorted(range(total),key=lambda k:(
  frequency[descriptors[k]],-volume(k),pairs[k]))
 selected=[];used=set();seen_keys=set()
 # Reserve half the proof budget for geometrically DISTINCT definitions.
 # The old uniform index sample could check 24 copies of one repeated part.
 for k in ranked:
  if descriptors[k] in seen_keys:continue
  selected.append(k);used.add(k);seen_keys.add(descriptors[k])
  if len(selected)>=max(1,n//2):break
 centers=np.asarray([parts[i].center for i,j in pairs],dtype=float)
 while len(selected)<n:
  best=max((k for k in range(total) if k not in used),
           key=lambda k:(min(float(np.sum((centers[k]-centers[j])**2))
                             for j in selected),
                         -frequency[descriptors[k]],volume(k),-k))
  selected.append(best);used.add(best)
 return [pairs[k] for k in selected]


def frame_support(a,b,tolerance,proofs=8,verify_all=False,progress=None,cancelled=None,proof_cache=None):
 from .native_session import world_session
 with world_session(max(len(a),len(b))>=80):
  return _frame_support(a,b,tolerance,proofs,verify_all,progress,cancelled,proof_cache)

def _frame_support(a,b,tolerance,proofs=8,verify_all=False,progress=None,cancelled=None,proof_cache=None):
 from .step_reexport_tolerance import coarse_candidate,reexport_equivalent_world,world_candidate,search_radius
 from .geometry_registry import GeometryRegistry
 from .compare import _relative_location_is_same,_location_matrix,Cancelled
 from . import native_guard
 if proof_cache is not None:
  proof_cache.bind(a,b,tolerance)
 registry=proof_cache.registry if proof_cache is not None else GeometryRegistry()
 anchors=proof_cache.anchors if proof_cache is not None else {}
 exact_anchors=proof_cache.exact_anchors if proof_cache is not None else {}
 # Failed native proofs are not matches. Bound failures to avoid false confidence.
 unverified=set();failed_groups=set()
 def prove_uncached(i,j):
  left,right=a[i],b[j]
  if left.shape.IsSame(right.shape):return True
  key=(registry.definition(left),registry.definition(right));old=anchors.get(key)
  if old and _relative_location_is_same(left,a[old[0]],right,b[old[1]],tolerance):return True
  # Exact local B-Rep equality and equal CAD placement are full proof.
  # Numerical descriptors and names by themselves are never proof.
  same=bool(registry.same_definition(left,right) and
      np.allclose(_location_matrix(left),_location_matrix(right),rtol=0,atol=1e-8))
  if same:
   anchors.setdefault(key,(i,j))
   return True
  # Independently exported occurrences can have different TShapes but
  # byte-identical local B-Reps. Reuse only an already completed WORLD
  # proof, with both exact digests and the same relative CAD placement.
  ld=registry.exact_digest(left);rd=registry.exact_digest(right)
  exact_key=(ld,rd) if ld is not None and rd is not None else None
  anchor=exact_anchors.get(exact_key) if exact_key is not None else None
  previously_failed=proof_cache is not None and (i,j) in proof_cache.failed_pairs
  if (not same and anchor and not previously_failed
     and registry.same_definition(left,a[anchor[0]])
     and registry.same_definition(right,b[anchor[1]])
     and _relative_location_is_same(left,a[anchor[0]],right,b[anchor[1]],tolerance)):
   same=True
   if proof_cache is not None:proof_cache.exact_anchor_hits+=1
  if not same:
   if max(len(a),len(b))>=80:
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
     if proof_cache is not None:
      proof_cache.failed_pairs.add((i,j))
      if 'timeout' in str(exc).casefold():proof_cache.timed_out_pairs.add((i,j))
     unverified.add((i,j));failed_groups.add(key)
     trace.mark('registration_proof','UNVERIFIED',a_id=i,b_id=j,
                error=str(exc),unverified_count=len(unverified))
     if len(unverified)>max(4,int(min(len(a),len(b))*.01)):
      raise native_guard.NativeGeometryFailure(
       'Zbyt wiele niezweryfikowanych bryl B-Rep podczas wyrownania '
       f'({len(unverified)}). Nie mozna bezpiecznie ustalic przesuniecia.') from exc
     return False
   else:
    same=trace.brep_call('verify_reexport',i,j,
        reexport_equivalent_world,left,right,tolerance,allow_boolean=False)
    if not same:same=trace.brep_call('verify_world',i,j,equivalent_world,left,right,tolerance)
  if same:
   anchors.setdefault(key,(i,j))
   if exact_key is not None:exact_anchors.setdefault(exact_key,(i,j))
  return same
 def proven(i,j):
  pair=(i,j)
  if proof_cache is not None and pair in proof_cache.timed_out_pairs:
   # Incomplete remains incomplete. Do not restart the same 90s native
   # operation in the larger sample or full pass of this immutable pose.
   unverified.add(pair);proof_cache.skipped_timeouts+=1
   return False
  if proof_cache is not None and pair in proof_cache.results:
   proof_cache.hits+=1
   return proof_cache.results[pair]
  if proof_cache is not None:proof_cache.proof_calls+=1
  same=bool(prove_uncached(i,j))
  # False can mean an inconclusive analytic proof, so retry it in the full
  # pass. Only completed positive proofs are transferable between passes.
  if proof_cache is not None and same and pair not in unverified:
   proof_cache.results[pair]=same
  return same
 if not a or not b:return dict(count=0,ratio=0.,proofs=0,checked=0,pairs=[])
 tol=max(tolerance,1.e-6);radius=search_radius(tol);cell_size=max(radius*2,.002)
 buckets=defaultdict(list)
 for i,part in enumerate(a):
  pos=tuple(floor(float(v)/cell_size) for v in part.center)
  buckets[pos].append(i)
 options={}
 for j,part in enumerate(b):
  if cancelled and cancelled():raise Cancelled('Przerwano analizę')
  pos=np.asarray(part.center)
  base=tuple(floor(float(v)/cell_size) for v in pos)
  choices=[]
  for steps in product((-1,0,1),repeat=3):
   loc=tuple(x+y for x,y in zip(base,steps))
   for i in buckets.get(loc,()):
    distance=float(np.linalg.norm(a[i].center-pos))
    if distance<=radius and world_candidate(a[i],part,tol):
     choices.append((distance,i))
  if choices:options[j]=[i for _,i in sorted(set(choices))]
 # Iterative maximum-cardinality assignment; B-Rep proof before edge use.
 owner={};reverse={};checked_pairs={}
 for n,start in enumerate(sorted(options,key=lambda j:(len(options[j]),j))):
  if cancelled and cancelled():raise Cancelled('Przerwano analizę')
  if progress and n%25==0:
   if verify_all:progress(f'Weryfikacja B-Rep: {n}/{len(options)}; zgodnych geometrii {len(owner)}')
   else:progress(f'Kandydaci położenia: {n}/{len(options)}; wstępnie sparowano {len(owner)} (B-Rep niepotwierdzony)')
  queue=[start];seen_left={start};seen_right=set();parent={};free=None
  for j in queue:
   for i in options[j]:
    if i in seen_right:continue
    if verify_all:
     pair=(i,j)
     if pair not in checked_pairs:checked_pairs[pair]=bool(proven(i,j))
     if not checked_pairs[pair]:continue
    seen_right.add(i);parent[i]=j
    if i not in owner:free=i;break
    next_j=owner[i]
    if next_j not in seen_left:seen_left.add(next_j);queue.append(next_j)
   if free is not None:break
  if free is None:continue
  while True:
   j=parent[free];old=reverse.get(j)
   owner[free]=j;reverse[j]=free
   if old is None:break
   free=old
 pairs=sorted((i,j) for i,j in owner.items())
 if not pairs:return dict(count=0,ratio=0.,proofs=0,checked=0,pairs=[],unverified=len(unverified))
 if verify_all:return dict(count=len(pairs),ratio=len(pairs)/max(1,min(len(a),len(b))),proofs=len(pairs),checked=len(pairs),pairs=pairs,unverified=len(unverified))
 n=min(proofs,len(pairs))
 selection=_select_diverse_proof_pairs(pairs,a,n)
 confirmed=0
 for number,(i,j) in enumerate(selection,1):
  if progress:progress(f'Dowód geometrii B-Rep {number}/{n}: A[{i}] ↔ B[{j}]…')
  confirmed+=bool(proven(i,j))
 if progress:progress(f'Próbka B-Rep: {confirmed}/{n} rzeczywistych dowodów; {len(pairs)} kandydatów położenia.')
 return dict(count=len(pairs),ratio=len(pairs)/max(1,min(len(a),len(b))),
             proofs=confirmed,checked=n)

def already_world_aligned(a,b,tolerance):
 r=frame_support(a,b,tolerance)
 return (r['ratio']>=.55 and r['proofs']==r['checked'] and
         r['checked']>=min(2,min(len(a),len(b))))


def original_frame_fastpath(a,b,tolerance,initial=None,progress=None):
    """Decide whether a verified shared CAD world frame can skip registration.

    A matching *subset* is sufficient if independent B-Rep samples agree,
    PROVIDED no stronger whole-assembly translation is suggested by the
    unchanged geometric definitions. No native geometry is moved here.

    Descriptor/centroid votes are only a cheap NEGATIVE gate; a nonzero
    translation is never accepted from these votes. That still requires
    align_assembly() and world B-Rep validation + user approval.
    """
    from collections import defaultdict,Counter
    from .compare import _spatial_index,_nearby
    from types import SimpleNamespace
    if initial is None:
        initial=frame_support(a,b,tolerance,proofs=8)
    population=min(len(a),len(b))
    if population==0:return False,'Brak brył'
    required=min(population,max(2,__import__('math').ceil(.35*population)))
    if (initial['count']<required or initial['checked']<min(2,population)
            or initial['proofs']!=initial['checked']):
        return False,f'Potwierdzono tylko {initial["count"]}/{population} pozycji'

    # A source exported one pitch away can overlap n-1 of n repeated
    # components. Detect that cheaply via centroid votes of equally sized
    # shape cohorts, then compare the number of placement candidates.
    sig_a=defaultdict(list);sig_b=defaultdict(list)
    for i,part in enumerate(a):sig_a[signature(part)].append(i)
    for i,part in enumerate(b):sig_b[signature(part)].append(i)
    possible=Counter();representatives={}
    threshold=max(.01,tolerance)
    for key in sig_a.keys() & sig_b.keys():
        ia,ib=sig_a[key],sig_b[key]
        if len(ia)!=len(ib):continue
        # Using centroids of SAME-MULTIPLICITY shape cohorts avoids a shift
        # estimate biased by changed parts which appear only in one revision.
        offset=(np.mean([a[i].center for i in ia],axis=0)
                -np.mean([b[i].center for i in ib],axis=0))
        if np.linalg.norm(offset)<=tolerance:continue
        k=tuple(int(round(float(c)/threshold)) for c in offset)
        possible[k]+=len(ia)
        representatives[k]=offset
    if possible:
        cell_size=max(tolerance,1.e-6)
        idx=_spatial_index(a,range(len(a)),cell_size)
        # Do not evaluate hundreds of candidates. Few high-support cohort
        # translations are sufficient as a veto, not proof of registration.
        for key,weight in possible.most_common(8):
            if weight<max(2,int(.04*population)):continue
            offset=representatives[key]
            used=set();votes=0
            for part in b:
                c=part.center+offset
                for i in _nearby(idx,SimpleNamespace(center=c),cell_size):
                    if i in used or np.linalg.norm(a[i].center-c)>tolerance:
                        continue
                    if signature(a[i])!=signature(part):continue
                    if not candidate(a[i],part,tolerance):continue
                    used.add(i);votes+=1;break
            if votes>initial['count']:
                if progress:progress(
                    f'Wstępna analiza: wykryto możliwe lepsze przesunięcie '
                    f'({votes} zamiast {initial["count"]} brył); pełna weryfikacja B-Rep.')
                return False,'Podejrzenie globalnego przesunięcia'
    if progress:progress(
        f'Wstępna analiza: potwierdzono {initial["count"]}/{population} brył '
        'w obecnym układzie CAD; pomijam szukanie przesunięcia.')
    return True,'Zgodność obecnego układu potwierdzona próbką B-Rep; brak lepszego przesunięcia'
