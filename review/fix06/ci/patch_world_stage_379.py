"""Bound slow same-position CAD proofs without changing the geometry verdict.

The original medium-assembly (e.g. 379 parts) world-matching branch could
execute OCCT equivalent_world directly in the main process, with no watchdog.
All expensive comparisons for >=80 occurrences now use an isolated recyclable
native session, retaining the exact equivalent_world algorithm. Timeouts
become UNVERIFIED pairs, never false SAME or definite REMOVED.
"""
from pathlib import Path
import sys

root=Path(sys.argv[1])
native=root/'dsac29/native_guard.py'
compare=root/'dsac29/compare.py'
cli=root/'dsac29/cli.py'

def once(source,old,new,label):
    if source.count(old)!=1:
        raise RuntimeError(f'Unexpected CAD source anchor for {label}: {source.count(old)}')
    return source.replace(old,new)

s=native.read_text(encoding='utf-8')
s=once(s,
"    if req.get('operation') == 'world_reexport':",
"""    if req.get('operation') == 'world_equivalent':
        # Preserve the original exact world B-Rep algorithm and tolerance.
        # The ONLY change is native process isolation and a bounded timeout.
        report('describe_original_world_pair')
        left=describe(a_shape,'A','native-guard/world-A')
        right=describe(b_shape,'B','native-guard/world-B')
        from .geometry import equivalent_world
        report('original_equivalent_world')
        response=dict(ok=True,match=bool(equivalent_world(
            left,right,float(req['tolerance']))))
    elif req.get('operation') == 'world_reexport':""","native original-equivalent worker")
s=once(s,"allow_boolean=False, process_args=None, allow_solid_set_proof=False):",
       "allow_boolean=False, process_args=None, allow_solid_set_proof=False, operation='world_reexport'):",
       "native world API")
s=once(s,"            'operation': 'world_reexport',",
       "            'operation': str(operation),","native request operation")
s=once(s,"def guarded_registered_world(a,b,tolerance,**kwargs):",
"""def guarded_world_equivalent(a,b,tolerance,**kwargs):
    # Identical algorithm as former in-process equivalent_world, now isolated.
    return guarded_world_reexport(a,b,tolerance,operation='world_equivalent',**kwargs)


def guarded_registered_world(a,b,tolerance,**kwargs):""","native guarded world API")
compile(s,str(native),'exec')
native.write_text(s,encoding='utf-8')

s=compare.read_text(encoding='utf-8')
# Earlier exported STEP models with 80-599 parts used the strict 0.01 mm
# centroid prefilter; independently re-exported ZW3D 2019 solids can move
# their *integrated* center even if the actual CAD faces have not moved.
# Candidate lookup at 0.5 mm is NOT evidence of equality.
s=once(s,
"broad_world_lookup=len(a)>=600 or registered_lookup or step_reexport_tolerance",
"broad_world_lookup=(max(len(a),len(b))>=80 or registered_lookup or step_reexport_tolerance or exact_serialization)",
"same-world reexport candidate radius")
s=once(s,
"from .native_guard import NativeGeometryFailure,guarded_world_reexport,guarded_registered_world",
"from .native_guard import NativeGeometryFailure,guarded_world_reexport,guarded_registered_world,guarded_world_equivalent",
"compare native imports")
s=once(s,
"""    # Match exact names first GLOBALLY: repeated and overlapping occurrences
    # must not consume a counterpart that has an exact-name match elsewhere.""",
"""    # Only near-equidistant candidates use the existing CAD inertia/area
    # invariants as a SOFT priority. Do not change any native proof or filter.
    from .fingerprint_priority import FingerprintPriority
    fingerprint_rank=FingerprintPriority.shared(geometry_context)
    # Match exact names first GLOBALLY: repeated and overlapping occurrences
    # must not consume a counterpart that has an exact-name match elsewhere.""","fingerprint world-stage priority")
s=once(s,
"            js.sort(key=lambda j:(dist(s,b[j]),abs(s.volume-b[j].volume),j))",
"""            js.sort(key=lambda j:(dist(s,b[j]),abs(s.volume-b[j].volume),j))
            if len(js)>1:
                js=fingerprint_rank.world_ties(s,js,b,tolerance)""",
"ambiguous same-position priority")
s=once(s,
"    failed_groups = set()",
"""    failed_groups = set()
    # Preserve unknown native outcomes for identical definition pairs; never
    # restart the same hung OCCT operation on every duplicated occurrence.
    unknown_world_groups=set()
    # Native negative/incomplete proofs are not proof that 150 copies differ.
    # Probe independent occurrences a bounded number of times.
    world_probe_failures={}
    world_exhausted=set()
    world_probe_pairs={}
    # Only per-definition, placement-aware native timeouts are suppressed.
    # Unrelated definitions must always retain their opportunity for proof.
    def bounded_reexport(left,right,tol):
        # One native worker first checks oriented faces and trims, then may
        # verify TWO empty solid differences if re-export changed topology.
        # Names are never used to permit or deny geometric equivalence:
        # a renamed unchanged part must receive the same full proof.
        return guarded_world_reexport(left,right,tol,timeout_s=25,
            allow_solid_set_proof=True)
    def bounded_registered(left,right,tol):
        return guarded_registered_world(left,right,tol,timeout_s=25)
    def bounded_world(left,right,tol):
        return guarded_world_equivalent(left,right,tol,timeout_s=25)
""","world fallback guards")
s=once(s,
"                else:\n                    if checks >= max_checks: raise RuntimeError(f'Limit testów B-Rep ({max_checks}) — analiza niekompletna')",
"""                elif ((gs,gt) in world_exhausted and
                      any(_relative_location_is_same(s,a[aa],b[j],b[bb],tolerance)
                          for aa,bb in world_probe_pairs.get((gs,gt),()))):
                    # Never let failures at a DIFFERENT relative placement
                    # hide valid matches of a locally moved repeated part.
                    failed_a.add(i);failed_b.add(j);failed_pairs.add((i,j))
                    trace.mark('world_matching','UNVERIFIED_REPEATED_DEFINITION',
                               a_id=i,b_id=j,group_attempts=world_probe_failures.get((gs,gt),0))
                    continue
                else:
                    if checks >= max_checks: raise RuntimeError(f'Limit testów B-Rep ({max_checks}) — analiza niekompletna')""","skip duplicated native failures")
s=once(s,
"""                    checks += 1
                    try:
                        # In the verified STEP re-export registration branch,""",
"""                    checks += 1
                    if progress and max(len(a),len(b))>=80:
                        progress(f'Zgodność położenia: B-Rep A[{i+1}]/{len(a)} ↔ B[{j+1}]/{len(b)}; '
                                 f'test {checks}; ograniczenie 25 s na pojedynczą próbę.')
                    trace.mark('world_matching_pair','BEGIN',a_id=i,b_id=j,attempt=checks)
                    try:
                        # In the verified STEP re-export registration branch,""","per-pair progress")
s=once(s,"                                guarded_registered_world,s,b[j],tolerance)",
       "                                bounded_registered,s,b[j],tolerance)","registered stage world")
old="(guarded_world_reexport if len(a)>=80 else reexport_equivalent_world)"
if s.count(old)!=2:raise RuntimeError("Missing two broad reexport dispatches: "+str(s.count(old)))
s=s.replace(old,"(bounded_reexport if len(a)>=80 else reexport_equivalent_world)")
s=once(s,
"""                            same=trace.brep_call('equivalent_world',i,j,equivalent_world,s,b[j],tolerance)""",
"""                            same=trace.brep_call(
                                'equivalent_world_isolated' if max(len(a),len(b))>=80 else 'equivalent_world',
                                i,j,(bounded_world if max(len(a),len(b))>=80 else equivalent_world),
                                s,b[j],tolerance)""","medium isolated world equivalence")
old_native_errors="""                    except NativeGeometryFailure:
                        raise
                    except Exception as exc:"""
if s.count(old_native_errors)!=2:
    raise RuntimeError('Expected both stage-1 and rigid error handlers')
# Patch only the first occurrence: stage 2 keeps its existing error policy.
native_stage1_anchor=old_native_errors
s=s.replace(native_stage1_anchor, '___STAGE1_UNVERIFIED___',1)
s=once(s,
"___STAGE1_UNVERIFIED___",
"""                    except NativeGeometryFailure as exc:
                        # Timeout/crash is neither SAME nor a definitive
                        # mismatch. Keep this occurrence UNCERTAIN and continue
                        # to verify independent parts without replaying the
                        # same failed definition pair for every occurrence.
                        failed_a.add(i);failed_b.add(j);failed_pairs.add((i,j))
                        family=(gs,gt)
                        world_probe_failures[family]=world_probe_failures.get(family,0)+1
                        world_probe_pairs.setdefault(family,[]).append((i,j))
                        if world_probe_failures[family]>=2:
                            world_exhausted.add(family)
                        trace.mark('world_matching_pair','UNVERIFIED',a_id=i,b_id=j,
                                   operation=checks,error=str(exc))
                        if progress:
                            progress(f'Zgodność położenia: A[{i+1}] / B[{j+1}] niepotwierdzone '
                                     f'po izolowanej próbie B-Rep: {str(exc)[:300]}. '
                                     'Pozostałe bryły są nadal sprawdzane.')
                        # Native timeouts remain pair-local and never certify
                        # a different geometry. Continue with independent parts.
                        continue
                    except Exception as exc:""","world native error handling")
s=once(s,
"                            if not same and coarse_candidate(s,b[j],tolerance):",
"                            if not same and (coarse_candidate(s,b[j],tolerance) or (broad_world_lookup and world_candidate(s,b[j],tolerance))):",
"medium STEP fallback native proof")
s=once(s,
"""                if same:
                    geometry_context.remember_equivalence(s,b[j],tolerance)""",
"""                trace.mark('world_matching_pair','END',a_id=i,b_id=j,match=bool(same))
                if not same:
                    # The native routine finished, but did not prove equality.
                    # This is NOT an exception. It must never poison 150
                    # otherwise independent occurrences or mark the family
                    # as UNCERTAIN. Only real timeout/crash paths above may
                    # use the bounded unverified-family guard.
                    trace.mark('world_matching','NOT_PROVEN',
                               a_id=i,b_id=j,definition_a=gs,definition_b=gt)
                if same:
                    geometry_context.remember_equivalence(s,b[j],tolerance)""","world pair completed")
# Revisit previously inconclusive repeated occurrences only after an
# independent positive native world proof for the same CAD definitions.
s=once(s,
"    trace.mark('world_matching','END',matches=len(out),remaining_a=len(free_a),remaining_b=len(free_b),native_checks=checks)",
"""    if world_anchors and free_a and free_b:
        rescued=0
        for i in sorted(tuple(free_a)):
            s=a[i]
            candidates=sorted((j for j in _nearby(cells,s,lookup_radius)
                               if j in free_b and
                               (group_a[i],group_b[j]) in world_anchors and
                               dist(s,b[j])<=lookup_radius),
                              key=lambda j:(norm_a[i]!=norm_b[j],dist(s,b[j]),j))
            for j in candidates:
                gs,gt=group_a[i],group_b[j]
                ai,bj=world_anchors[gs,gt]
                if not _relative_location_is_same(s,a[ai],b[j],b[bj],tolerance):
                    continue
                renamed=genuine_rename(s,b[j])
                out.append(Record(i,j,'RENAMED' if renamed else 'SAME',
                                  'Wznowiony dowód powtarzalnej bryły B-Rep',
                                  name_changed=renamed))
                free_a.remove(i);free_b.remove(j)
                rescued+=1
                break
        if rescued:
            trace.mark('world_matching','RESCUED_OCCURRENCES',count=rescued)
            if progress:progress(f'Etap zgodności: odzyskano {rescued} wystąpień po pozytywnym dowodzie B-Rep.')
    trace.mark('world_matching','END',matches=len(out),remaining_a=len(free_a),remaining_b=len(free_b),native_checks=checks)""",
"recover repeats after positive world proof")

compile(s,str(compare),'exec')
compare.write_text(s,encoding='utf-8')

s=cli.read_text(encoding='utf-8')
s=once(s,
"        with world_session(registered_frame or (max(len(a),len(b))>=80 and bool(certified_pairs))):",
"        with world_session(max(len(a),len(b))>=80 or registered_frame):",
"medium native session reuse")
compile(s,str(cli),'exec')
cli.write_text(s,encoding='utf-8')
print('WORLD_STAGE_379_BOUNDED_NATIVE_PASS',root,flush=True)
