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
    if state.features is None:
        if progress:progress('Wyrównanie: wyznaczam punkty odniesienia z oryginalnej geometrii CAD…')
        state.features=(search.landmarks(a,cancelled),search.landmarks(b,cancelled))
    native=support or frame_support
    deadline=monotonic()+(120 if extended else 60)
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
            if seen(pose) or count<minimum or count<=baseline:continue
            if winners:
                best=max(w['votes'] for w in winners)
                if count<best and pose.volume<max(w['_volume'] for w in winners):continue
            if attempted>=budget or monotonic()>=deadline:
                return False
            attempted+=1
            if progress:progress(f'Wyrównanie: hipoteza {attempted}/{budget}, {count} kandydatów; {pose.source}.')
            placed=[_relocate(p,pose.rotation,pose.translation) for p in b]
            cache=FrameProofCache();cache.deadline=deadline;cache.pair_timeout=12.
            cache.lookup_points=(state.features[0],state.features[1]@pose.rotation.T+pose.translation)
            try:
                pre=native(a,placed,tolerance,proofs=24,progress=progress,cancelled=cancelled,proof_cache=cache)
                checked=int(pre['checked']);positive=int(pre['proofs'])
                best_sample=max(best_sample,(positive,checked,int(pre['count'])))
                if (pre['count']<minimum or pre['count']<=baseline or
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
                    accepted=votes>=minimum and votes>baseline
                if accepted:
                    total=sum(max(0.,p.volume) for p in a)
                    ratio=volume/max(total,1e-12)
                    weak=population>=40 and votes<ceil(.5*population) and ratio<.15
                    if weak and (sampled or len(certified)!=votes):
                        finish(pose);continue
                    winners.append({'status':'registered','method':'cad_global_consensus_trimmed_refinement',
                        'translation_B_to_A_mm':pose.translation.tolist(),'rotation_B_to_A':pose.rotation.tolist(),
                        'votes':votes,'previous_world_matches':baseline,'requested':True,'enabled':True,
                        'requires_confirmation':bool(weak),'support_ratio':round(votes/population,4),
                        'verified_volume_ratio':round(ratio,4),'certified_pairs':certified,
                        'verification_scope':'sample_then_final_compare' if sampled else 'full_brep',
                        'checked_sample_count':n,'verified_sample_count':positive,
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
    translations=search.hypotheses(a,b,tolerance,features=state.features,extended=extended,
                                  cancelled=cancelled,progress=progress)
    from .native_session import world_session
    with world_session(True):
        # Reserve native work for rotation even when many periodic-grid
        # translations have high descriptor support but fail real geometry.
        complete=verify(translations[:3])
        if complete and not winners:
            rotations=search.hypotheses(a,b,tolerance,features=state.features,extended=extended,
                                       rotations=True,cancelled=cancelled,progress=progress)
            complete=verify(rotations)
        if complete:
            complete=verify(translations[3:])
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
