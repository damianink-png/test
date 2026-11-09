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
"    failed_groups = set()",
"""    failed_groups = set()
    # Preserve unknown native outcomes for identical definition pairs; never
    # restart the same hung OCCT operation on every duplicated occurrence.
    unknown_world_groups=set()
    # Do not retry the same completed FALSE world result for each copy of
    # identical native definitions with the same relative CAD placement.
    # This is a negative memo only; native errors are never cached as FALSE.
    world_negative_anchors={}
    native_world_timeouts=0
    def bounded_reexport(left,right,tol):
        # One native worker first checks oriented faces and trims, then may
        # verify TWO empty solid differences if ZW3D changed face topology.
        # Native Cut is opt-in for the same named part and never substitutes
        # a numeric signature for a real B-Rep proof.
        same_name=bool(_normalized_name(left.name) and
            _normalized_name(left.name)==_normalized_name(right.name))
        return guarded_world_reexport(left,right,tol,timeout_s=25,
            allow_solid_set_proof=same_name)
    def bounded_registered(left,right,tol):
        return guarded_registered_world(left,right,tol,timeout_s=25)
    def bounded_world(left,right,tol):
        return guarded_world_equivalent(left,right,tol,timeout_s=25)
""","world fallback guards")
s=once(s,
"                else:\n                    if checks >= max_checks: raise RuntimeError(f'Limit testów B-Rep ({max_checks}) — analiza niekompletna')",
"""                elif ((gs,gt) in world_negative_anchors and
                      _relative_location_is_same(s,a[world_negative_anchors[(gs,gt)][0]],
                                                 b[j],b[world_negative_anchors[(gs,gt)][1]],
                                                 tolerance)):
                    same=False;memo_hits+=1
                elif (gs,gt) in unknown_world_groups:
                    failed_a.add(i);failed_b.add(j);failed_pairs.add((i,j))
                    trace.mark('world_matching','SKIP_UNVERIFIED_GROUP',a_id=i,b_id=j)
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
                        unknown_world_groups.add((gs,gt))
                        native_world_timeouts+=1
                        trace.mark('world_matching_pair','UNVERIFIED',a_id=i,b_id=j,
                                   operation=checks,error=str(exc))
                        if progress:
                            progress(f'Zgodność położenia: A[{i+1}] / B[{j+1}] niepotwierdzone '
                                     f'po izolowanej próbie B-Rep: {str(exc)[:300]}. '
                                     'Pozostałe bryły są nadal sprawdzane.')
                        if native_world_timeouts>=4:
                            raise NativeGeometryFailure(
                                'Etap zgodności położenia przerwany po 4 nieukończonych '
                                'operacjach OCCT. Nie opublikowano niepewnego porównania. '
                                'Sprawdź dziennik B-Rep; ostatni błąd: '+str(exc)) from exc
                        continue
                    except Exception as exc:""","world native error handling")
s=once(s,
"""                if same:
                    geometry_context.remember_equivalence(s,b[j],tolerance)""",
"""                trace.mark('world_matching_pair','END',a_id=i,b_id=j,match=bool(same))
                if not same:
                    world_negative_anchors.setdefault((gs,gt),(i,j))
                if same:
                    geometry_context.remember_equivalence(s,b[j],tolerance)""","world pair completed")
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
