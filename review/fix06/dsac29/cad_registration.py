"""Single stateful registration coordinator for translations and rigid poses.

Global landmark consensus -> trimmed refinement -> bounded native proofs ->
independent final comparison. Descriptor votes never become certified pairs.
"""
from math import ceil
from time import monotonic
import numpy as np
from . import cad_pose_search as search
from .alignment import _relocate
from .registration_gate import FrameProofCache


def _preserve_native_definition_evidence(original, moved):
    """Preserve only evidence still valid for the transformed TopoDS shape.

    A fresh dataclasses.replace does not copy dynamic XCAF metadata. The
    source-scoped XCAF definition is invariant under whole-frame motion.
    The translation-normalized digest and its local origin stay valid only
    when OCC preserves the original TShape (IsPartner). No derived Boolean
    verdict is transferred between frames.
    """
    source_key=getattr(original,'step_definition_key',None)
    if source_key is not None:
        moved.step_definition_key=source_key
    old_shape=getattr(original,'shape',None)
    new_shape=getattr(moved,'shape',None)
    if (old_shape is not None and new_shape is not None
            and new_shape.IsPartner(old_shape)):
        for attr in ('_dscompare_normalized_digest','_dscompare_local_origin'):
            value=getattr(original,attr,None)
            if value is not None:
                setattr(moved,attr,value)
    return moved

def place_for_proof(part,rotation,translation):
    """Place original B-Rep without reintegrating every candidate solid.

    Rigid placements preserve volume, area and principal moments; rotate the
    inertia tensor and axes algebraically. The AABB here is conservative and
    ONLY a search descriptor. Native proofs inspect the actual placed shape.
    The accepted final model still uses alignment._relocate/describe for its
    report dimensions. This shortcut never publishes a SAME verdict.
    """
    from dataclasses import replace
    from .geometry import transform
    r=np.asarray(rotation,dtype=float);t=np.asarray(translation,dtype=float)
    if (r.shape!=(3,3) or t.shape!=(3,) or not np.isfinite(r).all() or not np.isfinite(t).all()
            or not np.allclose(r.T@r,np.eye(3),rtol=0,atol=1e-10)
            or not np.isclose(np.linalg.det(r),1.,rtol=0,atol=1e-10)):
        raise ValueError('Hipoteza CAD wymaga obrotu właściwego i skończonej translacji')
    if np.array_equal(r,np.eye(3)):
        if not np.any(t):return part
        # Pure translation preserves intrinsic shape mass properties.
        # Do not recompute OCCT VolumeProperties/SurfaceProperties on every
        # body for every rival shift hypothesis. Native proofs use the
        # transformed TopoDS shape; these descriptors remain search-only.
        return _preserve_native_definition_evidence(
            part,replace(part,shape=transform(part.shape,r,t),
                         center=part.center+t))
    return _preserve_native_definition_evidence(
        part,replace(part,shape=transform(part.shape,r,t),center=r@part.center+t,
                     inertia=r@part.inertia@r.T,axes=r@part.axes,
                     bbox=tuple(float(v) for v in np.abs(r)@np.asarray(part.bbox))))



def _sampled_frame_decision(checked,positive,candidate_count,certified,a,tolerance,
                            pre_checked,pre_positive,baseline,population):
    """Distinguish changed parts from a false global frame without certifying
    any untested part. Strict 90% policy remains first choice. A bounded
    recovery needs independently proven, diverse, spatially spread solids
    and must be confirmed before the full per-part revision comparison.
    """
    strict_required=max(24,ceil(.90*checked))
    if checked<min(40,candidate_count):
        return False,False,f'Niepełna próbka: {positive}/{checked}, wymagane {min(40,candidate_count)} sprawdzeń'
    if positive>=strict_required:
        return True,False,f'Próg standardowy: {positive}/{checked}, wymagane {strict_required}'
    # The independent larger sample below is the decisive evidence. Allow
    # the preliminary sample to contain up to 20% changed/unknown pairs;
    # they are never certified, and this recovery always asks the user.
    if (checked<40 or pre_checked<20 or pre_positive<ceil(.80*pre_checked)
            or positive<max(32,ceil(.80*checked))):
        return False,False,f'Próbka poniżej progów: {positive}/{checked}, standard {strict_required}'
    pairs=sorted(set((int(i),int(j)) for i,j in certified))
    if len(pairs)<positive or len({i for i,j in pairs})<32 or len({j for i,j in pairs})<32:
        return False,False,'Za mało niezależnych par całych brył B-Rep'
    from .geometry import signature
    coords=np.asarray([a[i].center for i,j in pairs],dtype=float)
    diverse=len({signature(a[i]) for i,j in pairs})
    spread=(np.isfinite(coords).all() and
            np.linalg.matrix_rank(coords-coords.mean(axis=0),tol=tolerance)>=2)
    if not spread or diverse<4:
        return False,False,f'Niejednoznaczne kotwice: typy={diverse}, rozkład przestrzenny={bool(spread)}'
    projected=candidate_count*positive/checked
    if projected<=baseline+max(3,ceil(.05*population)):
        return False,False,f'Wzrost poparcia za mały wobec bazowych {baseline} części'
    return True,True,(f'Warunkowy konsensus: {positive}/{checked} pełnych B-Rep, '
                      f'{diverse} różnych geometrii; pozostałe części wymagają końcowego porównania')


def strong_incomplete_hypotheses(state,population):
    """Reuse native whole-body evidence before trying face extraction."""
    limit=max(24,int(.30*population))
    return [f for f in state.failures if f.get('pairs')
            and len(f.get('proven_pairs',()))>=12
            and int(f.get('count_upper_bound',0))>=limit]


def propose(a,b,records,tolerance,progress=None,cancelled=None,*,search_state=None,extended=False,support=None):
    from .registration_gate import frame_support
    from .registration_search import RegistrationSearch
    from .native_guard import NativeGeometryFailure
    if not np.isfinite(tolerance) or tolerance<=0 or tolerance>1:
        raise ValueError('Tolerancja B-Rep musi być w zakresie (0, 1] mm')
    state=search_state if search_state is not None else RegistrationSearch()
    state.bind(a,b,tolerance)
    population=min(len(a),len(b))
    if not population:return None
    baseline=sum(r.status in ('SAME','RENAMED') for r in records)
    minimum=1 if len(a)==len(b)==1 else max(2,ceil(.6*population)) if population<40 else 8
    if baseline==population:return None
    native=support or frame_support
    deadline=monotonic()+(120 if extended else 60)
    body_deadline=min(deadline,monotonic()+(60 if extended else 30))
    budget=32 if extended or population==1 else 12
    radius=max((float(np.linalg.norm(p.bbox)) for p in b),default=0.)
    mass=(np.asarray([p.center for p in a]),np.asarray([p.center for p in b]))
    attempted=0;best_sample=(0,0,0);winners=state.pose_winners;extra_time_given=False

    search_pass='extended' if extended else 'initial'

    def same_pending(pose,failure):
        return (np.array_equal(pose.rotation,np.asarray(failure.get('rotation',np.eye(3)))) and
                np.array_equal(pose.translation,np.asarray(failure['offset'])))

    def seen(pose):
        # At most one native retry of an unknown pose per search pass.
        # It remains eligible for the explicitly extended pass.
        if any(same_pending(pose,f) and f.get('last_pass')==search_pass for f in state.failures):return True
        if extended and any(same_pending(pose,f) and f.get('pairs') for f in state.failures):return False
        return (any(search.pose_distance(pose.rotation,pose.translation,r,t,state.features[1],radius)<=tolerance
                    for r,t in state.poses_completed)
                or (np.linalg.norm(pose.rotation-np.eye(3))<1e-7 and
                    any(np.linalg.norm(pose.translation-t)<=tolerance for t in state.completed)))

    def finish(pose):
        remaining=[]
        for failure in state.failures:
            if same_pending(pose,failure):
                state.resolved_failures.append(dict(translation_B_to_A_mm=failure['offset'],
                    attempts=failure.get('attempts',1),resolution='completed_native_evaluation',
                    previous_error=failure['reason']))
            else:remaining.append(failure)
        state.failures[:]=remaining
        state.poses_completed.append((pose.rotation.copy(),pose.translation.copy()))
        if np.linalg.norm(pose.rotation-np.eye(3))<1e-7:
            state.completed.append(pose.translation.copy())


    def incomplete(pose,cache,reason):
        old=next((f for f in state.failures if same_pending(pose,f)),None)
        entry=dict(offset=pose.translation.tolist(),rotation=pose.rotation.tolist(),
            reason=str(reason),count_upper_bound=len(pose.pairs),volume_upper_bound=pose.volume,
            pairs=[tuple(pair) for pair in pose.pairs],
            anchor_pairs=list(getattr(pose,'anchor_pairs',())),
            proof_rotation=pose.rotation.tolist(),proof_offset=pose.translation.tolist(),
            proven_pairs=[pair for pair,result in cache.results.items() if result is True],
            completed_negative_pairs=sorted(cache.completed_negative_pairs),
            native_errors=[dict(a=i,b=j,error=error) for (i,j),error in cache.native_errors.items()],
            attempts=(old.get('attempts',1)+1 if old else 1),
            last_pass=search_pass,pair_timeout_s=cache.pair_timeout)
        if old is not None:state.failures[state.failures.index(old)]=entry
        else:state.failures.append(entry)
        state.checkpoint()
        if progress:progress('Wyrównanie: dowód B-Rep nieukończony; hipoteza oczekuje na ponowne sprawdzenie, nie jest wynikiem negatywnym. '+str(reason)[:300])

    def close_or_defer(pose,cache):
        if cache.failed_pairs:
            incomplete(pose,cache,'Niepełna próba B-Rep: '+str(len(cache.failed_pairs))+' nieukończonych par. '+ '; '.join(list(cache.native_errors.values())[:3]))
        else:finish(pose)

    def verify(poses):
        nonlocal attempted,best_sample,body_deadline,deadline,extra_time_given
        for pose in poses:
            search.check_cancel(cancelled)
            count=len(pose.pairs)
            # A native-proven unique seed can have only six unchanged
            # witnesses while other anchors moved locally in this revision.
            required=min(minimum,6) if getattr(pose,'anchor_pairs',()) else minimum
            if seen(pose) or count<required or count<=baseline:continue
            if winners:
                best=max(w['votes'] for w in winners)
                if count<best and pose.volume<max(w['_volume'] for w in winners):continue
            if attempted>=budget or monotonic()>=body_deadline:
                return False
            attempted+=1
            if progress:progress(f'Wyrównanie: hipoteza {attempted}/{budget}, {count} kandydatów; {pose.source}.')
            placed=[]
            for number,p in enumerate(b):
                if number%32==0:
                    search.check_cancel(cancelled)
                    if monotonic()>=body_deadline:return False
                if progress and number%100==0:
                    progress(f'Przygotowanie położenia CAD: {number}/{len(b)} brył; bez ponownego całkowania geometrii.')
                placed.append(place_for_proof(p,pose.rotation,pose.translation))
            # Preparation can exhaust the search budget. Do not announce
            # five synthetic native failures when no proof has even started.
            if monotonic()>=body_deadline:return False
            cache=FrameProofCache();cache.deadline=body_deadline;cache.pair_timeout=24. if extended else 12.
            cache.deprioritized_pairs=set(getattr(pose,'retry_unverified_pairs',()))
            cache.completed_negative_pairs.update(getattr(pose,'retry_negative_pairs',()))
            for pair in [*getattr(pose,'anchor_pairs',()),*getattr(pose,'retry_proven_pairs',())]:cache.results[tuple(pair)]=True
            cache.lookup_points=(state.features[0],state.features[1]@pose.rotation.T+pose.translation)
            try:
                pre_started=monotonic()
                pre=native(a,placed,tolerance,proofs=24,progress=progress,cancelled=cancelled,proof_cache=cache)
                pre_elapsed=max(0.,monotonic()-pre_started)
                checked=int(pre['checked']);positive=int(pre['proofs'])
                state.sample_history.append(dict(translation_B_to_A_mm=pose.translation.tolist(),
                    rotation_B_to_A=pose.rotation.tolist(),search_pass=search_pass,source=pose.source,
                    candidate_count=int(pre['count']),checked=checked,world_proofs=positive,
                    unknown_pair_count=len(cache.failed_pairs)))
                best_sample=max(best_sample,(positive,checked,int(pre['count'])))
                if (pre['count']<required or pre['count']<=baseline or
                    checked<min(8,pre['count']) or positive<min(pre['count'],max(4,ceil(.65*checked)))):
                    close_or_defer(pose,cache);continue
                # A strong 24/24 preliminary sample of a 40-body bent STEP
                # can use almost the entire initial 30s frame budget; the
                # full per-body proof and the rival-pose check then fail due
                # to the expired clock, NOT due to CAD disagreement.
                # Apply the same measured proof-throughput extension to
                # medium-sized 40-79 body assemblies. This changes ONLY the
                # search time, never the required native CAD certificates.
                if (population>=40 and checked>=20 and
                    positive>=ceil(.80*checked) and not extra_time_given):
                    # Dynamic budget based on measured B-Rep throughput, not
                    # duplicated STEP occurrence count. Timeouts remain unknown.
                    reserve=min(105.,max(50.,3.*pre_elapsed))
                    body_deadline=max(body_deadline,monotonic()+reserve)
                    deadline=max(deadline,body_deadline+30.)
                    cache.deadline=body_deadline
                    extra_time_given=True
                    if progress:progress(
                        f'Wyrównanie: {positive}/{checked} pozytywnych B-Rep; '
                        f'rezerwuję czas na dalsze dowody B-Rep i kontrolę konkurencji.')
                sampled=population>=80 and pre['count']>=max(48,ceil(.55*population))
                recovered_sample=False
                if sampled:
                    proof=native(a,placed,tolerance,proofs=48,progress=progress,cancelled=cancelled,proof_cache=cache)
                    n=int(proof['checked']);positive=int(proof['proofs'])
                    certified=sorted(cache.results)
                    votes=int(proof['count']);volume=pose.volume
                    accepted,recovered_sample,sample_reason=_sampled_frame_decision(
                        n,positive,votes,certified,a,tolerance,checked,int(pre['proofs']),baseline,population)
                    state.sample_history[-1].update(
                        expanded_checked=n,expanded_proofs=positive,
                        accepted=bool(accepted),requires_confirmation=bool(recovered_sample),
                        decision=sample_reason,unknown_pair_count=len(cache.failed_pairs))
                    if progress:progress('Wyrównanie: '+sample_reason)
                else:
                    proof=native(a,placed,tolerance,verify_all=True,progress=progress,cancelled=cancelled,proof_cache=cache)
                    n=int(proof['checked']);positive=int(proof['proofs']);votes=int(proof['count'])
                    certified=list(proof['pairs']);volume=sum(max(0.,a[i].volume) for i,j in certified)
                    # Global frame support and individual part motion are
                    # different questions. Six complete native proofs supported by
                    # a unique anchor or a spatially independent consensus may establish a candidate frame even when
                    # two of eight geometric peers moved locally. Always ask
                    # for approval for this sparse, sub-eight frame evidence.
                    sparse_six=False
                    if population>=40 and votes>=6 and votes>baseline and len(certified)==votes:
                        coordinates=np.asarray([a[i].center for i,j in certified])
                        spread=np.linalg.matrix_rank(coordinates-coordinates.mean(axis=0),tol=tolerance)>=2
                        sparse_six=bool(getattr(pose,'anchor_pairs',()) or
                            (spread and int(pre['count'])>=8 and int(pre['proofs'])>=6 and
                             int(pre['proofs'])>=ceil(.75*int(pre['checked']))))
                    accepted=(votes>=minimum or sparse_six) and votes>baseline
                if (accepted and not sampled and 6<=votes<8 and
                    np.linalg.norm(pose.rotation-np.eye(3))<1e-9 and
                    not getattr(pose,'refined_from_world_pairs',False)):
                    # Remove locally moved candidates from the estimator as
                    # well as the certificate map. Re-check the corrected
                    # frame natively; old proofs never transfer to a new pose.
                    ii,jj=np.asarray(certified,dtype=int).T
                    refined=np.median(state.features[0][ii]-state.features[1][jj],axis=0)
                    delta=float(np.linalg.norm(refined-pose.translation))
                    if tolerance*.01<delta<=max(.05,5*tolerance):
                        pairs=search.match_pose(a,b,*state.features,np.eye(3),refined,max(.05,5*tolerance),
                            mass)
                        correction=search.Pose(np.eye(3),refined,pairs,sum(a[i].volume for i,j in pairs),'cad_inlier_translation_refinement')
                        correction.refined_from_world_pairs=True
                        before=len(winners)
                        if progress:progress(f'Wyrównanie: dopracowuję wektor z {votes} potwierdzonych części; pozostałe kandydatury nie wpływają na wyznaczanie wektora.')
                        verify([correction])
                        if any(w['votes']>=votes for w in winners[before:]):
                            finish(pose);continue
                if accepted:
                    total=sum(max(0.,p.volume) for p in a)
                    ratio=volume/max(total,1e-12)
                    weak=bool(recovered_sample) or (population>=40 and (votes<8 or (votes<ceil(.5*population) and ratio<.15)))
                    if weak and not recovered_sample and (sampled or len(certified)!=votes):
                        close_or_defer(pose,cache);continue
                    winners.append({'status':'registered','method':'cad_global_consensus_trimmed_refinement',
                        'translation_B_to_A_mm':pose.translation.tolist(),'rotation_B_to_A':pose.rotation.tolist(),
                        'votes':votes,'previous_world_matches':baseline,'requested':True,'enabled':True,
                        'requires_confirmation':bool(weak),'support_ratio':round(votes/population,4),
                        'verified_volume_ratio':round(ratio,4),'certified_pairs':certified,
                        'verification_scope':'sample_then_final_compare' if sampled else 'full_brep',
                        'checked_sample_count':n,'verified_sample_count':positive,
                        'independent_local_motion_allowed':True,
                        'initial_position_candidate_count':int(pre['count']),
                        'initial_checked_count':int(pre['checked']),
                        'initial_world_proof_count':int(pre['proofs']),
                        'full_pair_map':certified if not sampled and len(certified)==len(a)==len(b) else [],
                        'search_algorithm':pose.source,'_volume':volume})
                if accepted:finish(pose)
                else:close_or_defer(pose,cache)
            except NativeGeometryFailure as exc:
                # Unknown outcomes must not enter the completed-pose veto.
                incomplete(pose,cache,exc)
        return True

    # Pure translations get priority. If they cannot be proven, the SAME
    # coordinator, budget and state explore rotations rather than a second
    # legacy algorithm replaying all the failed translations.
    from .native_session import world_session
    from .unique_anchors import proven_translations
    with world_session(True):
        retry_complete=True
        if extended:
            pending=[f for f in state.failures if f.get('pairs') and f.get('last_pass')!=search_pass]
            pending.sort(key=lambda f:(-len(f.get('proven_pairs',())),-f['count_upper_bound']))
            retry_poses=[]
            for f in pending:
                pose=search.Pose(np.asarray(f.get('rotation',np.eye(3))),np.asarray(f['offset']),
                    [tuple(pair) for pair in f['pairs']],f['volume_upper_bound'],'retry_incomplete_brep')
                exact_proof_pose=(np.array_equal(pose.rotation,np.asarray(f.get('proof_rotation',[]))) and
                                  np.array_equal(pose.translation,np.asarray(f.get('proof_offset',[]))))
                pose.anchor_pairs=[tuple(pair) for pair in f.get('anchor_pairs',())] if exact_proof_pose else []
                pose.retry_proven_pairs=[tuple(pair) for pair in f.get('proven_pairs',())] if exact_proof_pose else []
                # Same immutable originals, exact pose, tolerance and native mode.
                # A finished non-proof is not a timeout and needs no replay.
                pose.retry_negative_pairs=[tuple(pair) for pair in f.get('completed_negative_pairs',())] if exact_proof_pose else []
                pose.retry_unverified_pairs=[(e['a'],e['b']) for e in f.get('native_errors',())
                                             if 'a' in e and 'b' in e] if exact_proof_pose else []
                retry_poses.append(pose)
            if retry_poses:
                if state.features is None:state.features=(search.landmarks(a,cancelled),search.landmarks(b,cancelled))
                if progress:progress(f'Wyrównanie: ponawiam {len(retry_poses)} nieukończonych hipotez; zachowuję ukończone wyniki dla dokładnie tego samego położenia.')
                retry_complete=verify(retry_poses)
        anchors=proven_translations(a,b,tolerance,state,body_deadline,extended=extended,
                                   progress=progress,cancelled=cancelled,clock=monotonic)
        if state.features is None:
            if progress:progress('Wyrównanie: wyznaczam punkty odniesienia z oryginalnej geometrii CAD…')
            state.features=(search.landmarks(a,cancelled),search.landmarks(b,cancelled))
        anchor_poses=[]
        for shift,pair in anchors:
            pairs=search.match_pose(a,b,*state.features,np.eye(3),shift,max(.05,5*tolerance),mass)
            pose=search.Pose(np.eye(3),shift,pairs,sum(a[i].volume for i,j in pairs),'unique_largest_inertia_anchor')
            pose.anchor_pairs=[pair];anchor_poses.append(pose)
        anchor_complete=verify(anchor_poses)
        # A finished budget cannot verify any new body hypotheses. Keep
        # the independent surface fallback below, without building unused
        # translation cohorts and correspondence pools first.
        translations=(search.hypotheses(a,b,tolerance,features=state.features,extended=extended,
                                      cancelled=cancelled,progress=progress)
                      if retry_complete and anchor_complete and monotonic()<body_deadline else [])
        # Reserve native work for rotation even when many periodic-grid
        # translations have high descriptor support but fail real geometry.
        complete=retry_complete and anchor_complete and monotonic()<body_deadline and verify(translations[:3])
        if complete and not winners:
            rotations=search.hypotheses(a,b,tolerance,features=state.features,extended=extended,
                                       rotations=True,cancelled=cancelled,progress=progress)
            complete=verify(rotations)
        if complete:
            complete=verify(translations[3:])
        if (not winners and not strong_incomplete_hypotheses(state,population)
                and baseline<max(8,int(.2*population)) and monotonic()<deadline):
            from .surface_registration import propose as preserved_frame
            frame=preserved_frame(a,b,tolerance,state,extended=extended,progress=progress,
                                  cancelled=cancelled,deadline=deadline)
            if frame is not None:
                state.surface_diagnostics={k:v for k,v in frame.items() if k not in ('rotation_B_to_A',)}
                state.checkpoint(frame)
                if frame.get('status') in ('registered','already_aligned'):
                    frame['search_diagnostics']=state.summary()
                    return frame
                if frame.get('status')=='unresolved':
                    frame['search_diagnostics']=state.summary()
                    return frame
    state.checkpoint()
    if not complete:
        return {'status':'unresolved','reason':'Osiągnięto limit czasu lub hipotez wyrównania; nie przyjęto niejednoznacznego wyniku.',
                'search_diagnostics':state.summary()}
    if not winners:
        if not attempted and not state.failures:return None
        if state.failures:
            f=state.failures[0]
            return {'status':'unresolved','reason':
                f'Nieukończona weryfikacja B-Rep dla B→A {f["offset"]} mm; '
                f'kandydaci {f["count_upper_bound"]}, próby {f.get("attempts",1)}. Przyczyna: {str(f["reason"])[:600]}',
                'search_diagnostics':state.summary()}
        return {'status':'unresolved','reason':f'Brak potwierdzonego położenia: najlepsza próbka {best_sample[0]}/{best_sample[1]} B-Rep, {best_sample[2]} kandydatów.',
                'search_diagnostics':state.summary()}
    winners.sort(key=lambda w:(-w['votes'],-w['_volume']))
    best=winners[0];t=np.asarray(best['translation_B_to_A_mm']);r=np.asarray(best['rotation_B_to_A'])
    margin=max(1,ceil(.1*best['votes'])) if best['votes']<ceil(.5*population) else 0
    def different(rr,tt):return search.pose_distance(rr,tt,r,t,state.features[1],radius)>tolerance
    if any(w['votes']>=best['votes']-margin and w['_volume']>=best['_volume']*.9 and
           different(w['rotation_B_to_A'],w['translation_B_to_A_mm']) for w in winners[1:]):
        return {'status':'unresolved','reason':'Kilka położeń ma podobne dowody B-Rep; nie wybrano arbitralnego wyrównania.'}
    rivals=[f for f in state.failures if f['count_upper_bound']>=best['votes']-margin and
            f['volume_upper_bound']>=best['_volume']*.9 and different(f.get('rotation',np.eye(3)),f['offset'])]
    if rivals:
        f=rivals[0]
        return {'status':'unresolved','reason':
            f'Niezweryfikowana konkurencyjna hipoteza B-Rep: B→A {f["offset"]} mm; '
            f'{f["count_upper_bound"]} kandydatów, {f.get("attempts",1)} prób. '
            f'Najlepszy potwierdzony wynik: {best["votes"]} par. Przyczyna: {str(f["reason"])[:600]}',
            'search_diagnostics':state.summary()}
    result={k:v for k,v in best.items() if not k.startswith('_')}
    result['search_diagnostics']=state.summary()
    if progress:progress(f'Wyrównanie CAD: {best["votes"]}/{population} kandydatów, {best["verified_sample_count"]}/{best["checked_sample_count"]} dowodów B-Rep; B→A {t.tolist()} mm.')
    return result
