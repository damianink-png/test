"""Wire strict normalized STEP families into the already-shipped geometry engine.

Run only after earlier source overlays, not as an optional feature. Equality
requires complete exact local B-Rep serialization (SHA-256) or a native proof.
An XCAF key is trusted only within the SAME source file + shape label + solid.
"""
from pathlib import Path
import sys

root=Path(sys.argv[1])
registry=root/'dsac29/geometry_registry.py'
compare=root/'dsac29/compare.py'

def once(text,old,new,caption):
    if text.count(old)!=1:
        raise RuntimeError(f'STEP occurrence source drift: {caption}; matches={text.count(old)}')
    return text.replace(old,new)

s=registry.read_text(encoding='utf-8')
s=once(s,'        self._part_ids = {}',
"""        self._part_ids = {}
        self._trusted_occurrence_definitions = {}
""",'identity index')
s=once(s,
"""        cached=self._part_ids.get(identifier)
        if cached is not None and cached[1] is part:
            return cached[0]
        handle = part.shape.TShape()""",
"""        cached=self._part_ids.get(identifier)
        if cached is not None and cached[1] is part:
            return cached[0]
        # A complete translation-normalized B-Rep has exactly the same
        # surfaces, edges and trims. Its full digest is a STRICT proof,
        # unlike a rounded surface/volume/mesh signature.
        digest=getattr(part,'_dscompare_normalized_digest',None)
        xcaf=getattr(part,'step_definition_key',None)
        proof_key=(('brep',digest) if digest is not None else
                   ('xcaf',tuple(xcaf)) if xcaf is not None else None)
        if proof_key is not None:
            proven=self._trusted_occurrence_definitions.get(proof_key)
            if proven is not None:
                self._part_ids[identifier]=(proven,part)
                self.stats['trusted_occurrence_hits']+=1
                return proven
        handle = part.shape.TShape()""",'trusted repeated definitions')
s=once(s,
"""        self._part_ids[identifier] = (index, part)
        return index""",
"""        self._part_ids[identifier] = (index, part)
        if proof_key is not None:
            self._trusted_occurrence_definitions.setdefault(proof_key,index)
        return index""",'new registered definition')
compile(s,str(registry),'exec')
registry.write_text(s,encoding='utf-8')

s=compare.read_text(encoding='utf-8')
s=once(s,
"""    return np.array([[t.Value(i,j) for j in range(1,5)] for i in range(1,4)],dtype=float)""",
"""    matrix=np.array([[t.Value(i,j) for j in range(1,5)]
                     for i in range(1,4)],dtype=float)
    # Some STEP exporters bake each repeated component's translation into
    # face coordinates instead of TopLoc_Location. The exact normalized
    # B-Rep certificate defines its own local origin. This affine matrix
    # is the WORLD placement of that normalized complete B-Rep.
    local_origin=getattr(s,'_dscompare_local_origin',None)
    if local_origin is not None:
        matrix[:,3]+=matrix[:,:3]@np.asarray(local_origin,dtype=float)
    return matrix""",'canonical pose including baked STEP translation')
s=once(s,
"""    trace.mark('signature_cache','BEGIN',solids_a=len(a),solids_b=len(b))
    group_a=[geometry_context.definition(s) for s in a]""",
"""    trace.mark('signature_cache','BEGIN',solids_a=len(a),solids_b=len(b))
    if max(len(a),len(b))>=40:
        from .occurrence_identity import prepare_occurrence_identities
        occurrence_stats=prepare_occurrence_identities(a,b,progress=progress)
        trace.mark('step_occurrences','NORMALIZED',**occurrence_stats)
    group_a=[geometry_context.definition(s) for s in a]""",'prepare full geometry certificates before grouping')
s=once(s,
"""    def exact_same_definition(s,t,ga,gb):
        return ga == gb or geometry_context.same_definition(s,t)""",
"""    def exact_same_definition(s,t,ga,gb):
        return ga == gb or geometry_context.same_definition(s,t)
    def same_original_pose(s,t):
        pa=_location_matrix(s)
        pb=_location_matrix(t)
        return bool(np.allclose(pa[:,:3],pb[:,:3],rtol=0,atol=1e-10)
                    and np.linalg.norm(pa[:,3]-pb[:,3])
                    <=max(1e-8,min(float(tolerance),.01)))""",'exact local shape + original placement proof')
s=once(s,
"""exact_same_definition(s,b[j],gs,gt) and np.allclose(
                        _location_matrix(s),_location_matrix(b[j]),rtol=0,atol=1e-9):""",
"""exact_same_definition(s,b[j],gs,gt) and same_original_pose(s,b[j]):""",
'confirmed same world pose after STEP normalizing')
# Global assignment is applied only to copies of a PAIR OF DEFINITIONS
# already established equivalent by an original full B-Rep world proof.
# It cannot invent SAME edges for approximately similar raw geometries.
start="    if world_anchors and free_a and free_b:\n        rescued=0"
stop="    trace.mark('world_matching','END',matches=len(out),remaining_a=len(free_a)"
if s.count(start)!=1 or s.count(stop)!=1:
    raise RuntimeError('Verified anchor assignment drift')
i=s.index(start)
j=s.index(stop,i)
replacement="""    if world_anchors and free_a and free_b:
        from .assignment import assign as assign_confirmed
        proof_edges={}
        for i in sorted(free_a):
            s=a[i]
            for j in _nearby(cells,s,lookup_radius):
                if j not in free_b or dist(s,b[j])>lookup_radius:
                    continue
                key=(group_a[i],group_b[j])
                anchor=world_anchors.get(key)
                if anchor is None:
                    continue
                ai,bj=anchor
                if not _relative_location_is_same(s,a[ai],b[j],b[bj],tolerance):
                    continue
                distance=dist(s,b[j])
                proof_edges[i,j]=(distance/max(lookup_radius,1e-8)
                                  +.04*int(norm_a[i]!=norm_b[j]))
        rescued=0
        for i,j,ambiguous,gap in assign_confirmed(proof_edges):
            if i not in free_a or j not in free_b:
                continue
            changed_name=genuine_rename(a[i],b[j])
            out.append(Record(i,j,'RENAMED' if changed_name else 'SAME',
                'Pełny dowód B-Rep rodziny; globalne przypisanie wystąpień 1:1',
                name_changed=changed_name))
            free_a.remove(i)
            free_b.remove(j)
            rescued+=1
        if rescued:
            trace.mark('world_matching','RESCUED_OCCURRENCES',count=rescued)
            if progress:
                progress(f'Etap zgodności: przypisano globalnie {rescued} powtarzających się '
                         'wystąpień po potwierdzonym dowodzie B-Rep.')
"""
s=s[:i]+replacement+s[j:]
# A 1e-7 strict volume index is not a safe exclusion filter across STEP
# exporters. Open the 3% numeric-only proposal lane for medium assemblies;
# every NEW candidate still requires the original guarded B-Rep proof.
s=once(s,
"""    volume_index = _VolumeIndex(b, free_b)
    rigid_edges={}""",
"""    volume_index = _VolumeIndex(b, free_b)
    def exporter_volume_candidates(volume):
        if max(len(a),len(b))<80:
            return ()
        margin=max(tolerance**3,0.03*max(float(volume),1e-12))
        lo=bisect_left(volume_index.values,float(volume)-margin)
        hi=bisect_right(volume_index.values,float(volume)+margin)
        return (volume_index.sorted[k][1] for k in range(lo,hi))
    rigid_edges={}""",'broad but geometry-proven rigid candidate lane')
s=once(s,
"""            lookup=(sorted(free_b) if use_native_guard else volume_index.query(s.volume,tolerance))""",
"""            lookup=(sorted(free_b) if use_native_guard else
                    dict.fromkeys((*volume_index.query(s.volume,tolerance),
                                   *exporter_volume_candidates(s.volume))))""",
'bounded rigid lookup')
s=once(s,
"""and (rigid_candidate(i,j) or (use_native_guard and world_candidate(s,b[j],tolerance)))]""",
"""and (rigid_candidate(i,j) or
                       (max(len(a),len(b))>=80 and world_candidate(s,b[j],tolerance)))]""",
'exporter tolerant prefilter only')
# Do not hand untrusted, broad imported B-Rep candidates to an unbounded
# in-process rigid Boolean on medium STEP. The existing native guard is used
# for these additional candidates, with a per-pair 25-second deadline.
s=once(s,
"""                        if use_native_guard:
                            if perf_counter()-native_guard_started>native_guard_budget_s:
                                raise NativeGeometryFailure('Budżet izolowanych porównań B-Rep wyczerpany; analiza niekompletna')
                            from .native_guard import guarded_rigid
                            match,rotation,_=trace.brep_call('equivalent_rigid_guarded',i,j,guarded_rigid,s,b[j],tolerance,registered_reexport=True)""",
"""                        if use_native_guard or (max(len(a),len(b))>=80 and
                            not candidate(s,b[j],tolerance)):
                            if use_native_guard and perf_counter()-native_guard_started>native_guard_budget_s:
                                raise NativeGeometryFailure('Budżet izolowanych porównań B-Rep wyczerpany; analiza niekompletna')
                            from .native_guard import guarded_rigid
                            match,rotation,_=trace.brep_call('equivalent_rigid_guarded',i,j,
                                guarded_rigid,s,b[j],tolerance,registered_reexport=True,
                                timeout_s=25)""",
'guard new broad rigid candidates')
# The former 240-second limit was shared by the ENTIRE rigid stage,
# which was too short for 1600 occurrences even though each native call
# already has an independent timeout. Scale the aggregate watchdog only
# with input size; preserve both the global fail-closed and per-pair guards.
s=once(s,'def compare(a: list[SolidInfo]',
"""def native_rigid_stage_budget(solid_count):
    \"\"\"Bounded stage budget in seconds; source population controls scale.\"\"\"
    return max(240.0,0.5*max(0,int(solid_count)))


def compare(a: list[SolidInfo]""",
'rigid watchdog helper')
s=once(s,'    native_guard_budget_s = 240.0',
           '    native_guard_budget_s=native_rigid_stage_budget(max(len(a),len(b)))',
           'population-scaled registered rigid stage')
compile(s,str(compare),'exec')
compare.write_text(s,encoding='utf-8')
print('STEP_OCCURRENCE_FAMILY_AND_GLOBAL_ASSIGNMENT_PATCH_PASS',flush=True)
