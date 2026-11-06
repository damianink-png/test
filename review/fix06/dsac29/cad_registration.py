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
    if np.array_equal(r,np.eye(3)):return _relocate(part,r,t)
    return replace(part,shape=transform(part.shape,r,t),center=r@part.center+t,
                   inertia=r@part.inertia@r.T,axes=r@part.axes,
                   bbox=tuple(float(v) for v in np.abs(r)@np.asarray(part.bbox)))


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
    attempted=0;best_sample=(0,0,0);winners=state.pose_winners

    def seen(pose):
        return (any(search.pose_distance(pose.rotation,pose.translation,r,t,state.features[1],radius)<=tolerance
                    for r,t in state.poses_completed)
                or (np.linalg.norm(pose.rotation-np.eye(3))<1e-7 and
                    any(np.linalg.norm(pose.translation-t)<=tolerance for t in state.completed)))

    def finish(pose):
        state.poses_completed.append((pose.rotation.copy(),pose.translation.copy()))
        if np.linalg.norm(pose.rotation-np.eye(3))<1e-7:
            state.completed.append(pose.translation.copy())

    def verify(poses):
        nonlocal attempted,best_sample
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
            cache=FrameProofCache();cache.deadline=body_deadline;cache.pair_timeout=12.
            for pair in getattr(pose,'anchor_pairs',()):cache.results[pair]=True
            cache.lookup_points=(state.features[0],state.features[1]@pose.rotation.T+pose.translation)
            try:
                pre=native(a,placed,tolerance,proofs=24,progress=progress,cancelled=cancelled,proof_cache=cache)
                checked=int(pre['checked']);positive=int(pre['proofs'])
                best_sample=max(best_sample,(positive,checked,int(pre['count'])))
                if (pre['count']<required or pre['count']<=baseline or
                    checked<min(8,pre['count']) or positive<min(pre['count'],max(4,ceil(.65*checked)))):
                    finish(pose);continue
                sampled=population>=80 and pre['count']>=max(48,ceil(.55*population))
                if sampled:
                    proof=native(a,placed,tolerance,proofs=48,progress=progress,cancelled=cancelled,proof_cache=cache)
                    n=int(proof['checked']);positive=int(proof['proofs'])
                    accepted=n>=min(40,proof['count']) and positive>=max(24,ceil(.9*n))
                    certified=sorted(cache.results)
                    votes=int(proof['count']);volume=pose.volume
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
                            (np.asarray([p.center for p in a]),np.asarray([p.center for p in b])))
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
                    weak=population>=40 and (votes<8 or (votes<ceil(.5*population) and ratio<.15))
                    if weak and (sampled or len(certified)!=votes):
                        finish(pose);continue
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
                finish(pose)
            except NativeGeometryFailure as exc:
                # An unknown native outcome is not a negative geometry proof.
                finish(pose)
                state.failures.append({'offset':pose.translation.tolist(),'rotation':pose.rotation.tolist(),
                    'reason':str(exc),'count_upper_bound':count,'volume_upper_bound':pose.volume})
                if progress:progress('Wyrównanie: nieukończony dowód B-Rep; zachowuję diagnostykę i sprawdzam inną hipotezę.')
        return True

    # Pure translations get priority. If they cannot be proven, the SAME
    # coordinator, budget and state explore rotations rather than a second
    # legacy algorithm replaying all the failed translations.
    from .native_session import world_session
    from .unique_anchors import proven_translations
    with world_session(True):
        anchors=proven_translations(a,b,tolerance,state,body_deadline,extended=extended,
                                   progress=progress,cancelled=cancelled,clock=monotonic)
        if state.features is None:
            if progress:progress('Wyrównanie: wyznaczam punkty odniesienia z oryginalnej geometrii CAD…')
            state.features=(search.landmarks(a,cancelled),search.landmarks(b,cancelled))
        anchor_poses=[]
        mass=(np.asarray([p.center for p in a]),np.asarray([p.center for p in b]))
        for shift,pair in anchors:
            pairs=search.match_pose(a,b,*state.features,np.eye(3),shift,max(.05,5*tolerance),mass)
            pose=search.Pose(np.eye(3),shift,pairs,sum(a[i].volume for i,j in pairs),'unique_largest_inertia_anchor')
            pose.anchor_pairs=[pair];anchor_poses.append(pose)
        anchor_complete=verify(anchor_poses)
        translations=search.hypotheses(a,b,tolerance,features=state.features,extended=extended,
                                      cancelled=cancelled,progress=progress)
        # Reserve native work for rotation even when many periodic-grid
        # translations have high descriptor support but fail real geometry.
        complete=anchor_complete and verify(translations[:3])
        if complete and not winners:
            rotations=search.hypotheses(a,b,tolerance,features=state.features,extended=extended,
                                       rotations=True,cancelled=cancelled,progress=progress)
            complete=verify(rotations)
        if complete:
            complete=verify(translations[3:])
        if not winners and baseline<max(8,int(.2*population)) and monotonic()<deadline:
            from .surface_registration import propose as preserved_frame
            frame=preserved_frame(a,b,tolerance,state,extended=extended,progress=progress,
                                  cancelled=cancelled,deadline=deadline)
            if frame is not None:
                state.surface_diagnostics={k:v for k,v in frame.items() if k not in ('rotation_B_to_A',)}
                if frame.get('status') in ('registered','already_aligned'):
                    frame['search_diagnostics']=state.summary()
                    return frame
                if frame.get('status')=='unresolved':
                    frame['search_diagnostics']=state.summary()
                    return frame
    if not complete:
        return {'status':'unresolved','reason':'Osiągnięto limit czasu lub hipotez wyrównania; nie przyjęto niejednoznacznego wyniku.',
                'search_diagnostics':state.summary()}
    if not winners:
        if not attempted:return None
        return {'status':'unresolved','reason':f'Brak potwierdzonego położenia: najlepsza próbka {best_sample[0]}/{best_sample[1]} B-Rep, {best_sample[2]} kandydatów.',
                'search_diagnostics':state.summary()}
    winners.sort(key=lambda w:(-w['votes'],-w['_volume']))
    best=winners[0];t=np.asarray(best['translation_B_to_A_mm']);r=np.asarray(best['rotation_B_to_A'])
    margin=max(1,ceil(.1*best['votes'])) if best['votes']<ceil(.5*population) else 0
    def different(rr,tt):return search.pose_distance(rr,tt,r,t,state.features[1],radius)>tolerance
    if any(w['votes']>=best['votes']-margin and w['_volume']>=best['_volume']*.9 and
           different(w['rotation_B_to_A'],w['translation_B_to_A_mm']) for w in winners[1:]):
        return {'status':'unresolved','reason':'Kilka położeń ma podobne dowody B-Rep; nie wybrano arbitralnego wyrównania.'}
    if any(f['count_upper_bound']>=best['votes']-margin and f['volume_upper_bound']>=best['_volume']*.9 and
           different(f.get('rotation',np.eye(3)),f['offset']) for f in state.failures):
        return {'status':'unresolved','reason':'Niezweryfikowana konkurencyjna hipoteza B-Rep; nie zgadnięto położenia.'}
    result={k:v for k,v in best.items() if not k.startswith('_')}
    result['search_diagnostics']=state.summary()
    if progress:progress(f'Wyrównanie CAD: {best["votes"]}/{population} kandydatów, {best["verified_sample_count"]}/{best["checked_sample_count"]} dowodów B-Rep; B→A {t.tolist()} mm.')
    return result
