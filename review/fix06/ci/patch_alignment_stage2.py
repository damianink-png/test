"""Guard the legacy two-anchor registration before expensive full B-Rep."""
from pathlib import Path
import sys


def patch(path):
    target=Path(path)
    source=target.read_text(encoding='utf8')
    original="""    support=frame_support(a,aligned,tolerance,verify_all=True)
    if support['ratio']>=.60 and support['count']>=min(2,min(len(a),len(b))):"""
    replacement="""    # A translation supported by 2/2 selected anchors is still only a
    # hypothesis for an assembly with tens/hundreds of parts. Before
    # performing the expensive whole-model B-Rep verification, prove that
    # at least a useful population shares compatible placement/descriptors.
    population=min(len(a),len(b))
    if population>8:
        from math import ceil
        from .compare import _spatial_index,_nearby
        from .step_reexport_tolerance import world_candidate,search_radius
        from types import SimpleNamespace
        radius=search_radius(tolerance)
        spatial=_spatial_index(a,range(len(a)),radius)
        claimed=set()
        for part in aligned:
            center=part.center
            for i in _nearby(spatial,SimpleNamespace(center=center),radius):
                if i in claimed or np.linalg.norm(a[i].center-center)>radius:
                    continue
                if world_candidate(a[i],part,tolerance):
                    claimed.add(i);break
        required=max(8,ceil(.15*population)) if population>=40 else max(3,ceil(.35*population))
        if len(claimed)<required:
            if progress:
                progress(f'Wyrównanie: tylko {len(claimed)}/{population} wstępnie zgodnych pozycji po przesunięciu (wymagane {required}); odrzucono 2-bazową hipotezę bez pełnych, kosztownych testów B-Rep.')
            raise AlignmentUnavailable(
                f'Dwie bazy nie dowodzą przesunięcia złożenia: {len(claimed)}/{population} zgodnych położeń, wymagane {required}.')
        # The sample is a cheap positive gate, NOT a global registration proof.
        sample=frame_support(a,aligned,tolerance,proofs=min(8,required),
                             progress=progress)
        if sample['count']<required or sample['checked']<min(4,required) or sample['proofs']<min(4,sample['checked']):
            raise AlignmentUnavailable(
                f'Próbka B-Rep nie potwierdziła przesunięcia z baz: {sample["proofs"]}/{sample["checked"]} dowodów, {sample["count"]} kandydatów.')
    if population>=600:
        # Legacy 2-anchor rescue used to run >600 Boolean verifications
        # BEFORE the final comparison. Share only 48 positive proofs; leave
        # all other positions for the final, independently checked B-Rep pass.
        from .registration_gate import FrameProofCache
        cache=FrameProofCache()
        support=frame_support(a,aligned,tolerance,proofs=48,
                              progress=progress,proof_cache=cache)
        sampled_ok=(support['ratio']>=.60 and support['checked']>=40
                    and support['proofs']>=ceil(.90*support['checked']))
        if sampled_ok:
            info.update(votes=support['count'],
                        certified_pairs=sorted(cache.results),
                        full_pair_map=[],
                        verification_scope='sample_then_final_compare',
                        checked_sample_count=support['checked'],
                        verified_sample_count=support['proofs'])
    else:
        support=frame_support(a,aligned,tolerance,verify_all=True,progress=progress)
        sampled_ok=True
    if (sampled_ok and support['ratio']>=.60
            and support['count']>=min(2,min(len(a),len(b)))):"""
    if source.count(original)!=1:
        if source.count("A translation supported by 2/2 selected anchors") == 1:
            return
        raise RuntimeError('Unknown alignment.py; refusing unsafe patch')
    revised=source.replace(original,replacement)
    # This was displayed before verifying the full assembly, so its
    # past-tense wording incorrectly implied a successful registration.
    old_message="if progress:progress(f'Wyrównano B do A: {votes}/{len(pairs)} sprawdzonych baz; translacja [mm]: {np.round(t,3).tolist()}')"
    new_message="if progress:progress(f'Kandydat B do A: {votes}/{len(pairs)} wstępnie sprawdzonych baz; translacja [mm]: {np.round(t,3).tolist()}. Wyrównanie całego złożenia NIE jest jeszcze potwierdzone.')"
    if revised.count(old_message)!=1:
        raise RuntimeError('Unknown legacy alignment progress; refuse misleading output')
    revised=revised.replace(old_message,new_message)
    # If the initial two-base hypothesis is wrong, it does not rule out
    # every other translation. Continue with independently B-Rep-proven
    # repeated and sparse hypotheses instead of immediately failing.
    fallback_helper='''    def retry_other_shifts(anchor_error):
        if progress:
            progress('Wyrównanie: odrzucono jedną hipotezę bazową ('+str(anchor_error)+'). '
                     'Sprawdzam inne przesunięcia, bez uznawania niepotwierdzonych brył.')
        try:
            return _align_repeated_translation(a,b,tolerance,progress)
        except AlignmentUnavailable as repeated_error:
            try:
                return _align_sparse_translation(a,b,tolerance,progress,previous=repeated_error)
            except AlignmentUnavailable as sparse_error:
                raise AlignmentUnavailable('Nie znaleziono potwierdzonego przesunięcia; '
                    'bazy: '+str(anchor_error)+'; kolejne hipotezy: '+str(sparse_error)) from sparse_error

'''
    fallback_anchor='    # A translation supported by 2/2 selected anchors is still only a\n'
    if revised.count(fallback_anchor)!=1:
        raise RuntimeError('Missing verified two-base alignment fallback anchor')
    revised=revised.replace(fallback_anchor,fallback_helper+fallback_anchor)
    reject1="""            raise AlignmentUnavailable(
                f'Dwie bazy nie dowodzą przesunięcia złożenia: {len(claimed)}/{population} zgodnych położeń, wymagane {required}.')"""
    retry1="""            return retry_other_shifts(
                f'Dwie bazy nie dowodzą przesunięcia złożenia: {len(claimed)}/{population} zgodnych położeń, wymagane {required}.')"""
    reject2="""            raise AlignmentUnavailable(
                f'Próbka B-Rep nie potwierdziła przesunięcia z baz: {sample["proofs"]}/{sample["checked"]} dowodów, {sample["count"]} kandydatów.')"""
    retry2="""            return retry_other_shifts(
                f'Próbka B-Rep nie potwierdziła przesunięcia z baz: {sample["proofs"]}/{sample["checked"]} dowodów, {sample["count"]} kandydatów.')"""
    for old,new in [(reject1,retry1),(reject2,retry2)]:
        if revised.count(old)!=1:
            raise RuntimeError('Missing two-base rejection anchor: '+old[:65])
        revised=revised.replace(old,new)
    # Equal-count full-model translations have a strong, cheap hypothesis
    # based on ALL occurrence centroids, not two arbitrarily selected bases.
    centroid_preflight='''    # A complete coordinate-only shift changes every occurrence center
    # by the same vector. The mean-center delta is merely one hypothesis.
    # Full CAD B-Rep verification is still mandatory before classification.
    if initial['ratio']<.60 and len(a)==len(b) and len(a)>=8:
        try:
            return _align_global_centroid_translation(a,b,tolerance,progress,initial)
        except AlignmentUnavailable:
            pass
'''
    centroid_anchor='    # A fast partial B-Rep consensus is preferable to thousands of rigid\n'
    if revised.count(centroid_anchor)!=1:
        raise RuntimeError('Missing early registration anchor')
    revised=revised.replace(centroid_anchor,centroid_preflight+centroid_anchor)
    centroid_helper='''

def _align_global_centroid_translation(a,b,tolerance,progress=None,baseline=None):
    """One unambiguous global-shift hypothesis for equal-count assemblies.

    A mean-center delta is NEVER a geometry verdict: all accepted sampled
    pairs require independent B-Rep world proofs. Unproved pairs are compared
    in full after alignment, and final results are not emitted if too few pass.
    """
    from math import ceil
    from .registration_gate import frame_support, FrameProofCache
    count=min(len(a),len(b))
    if len(a)!=len(b) or count<8:
        raise AlignmentUnavailable('Global centroid shift requires equal occurrence counts (>=8).')
    shift=(np.mean([p.center for p in a],axis=0)
           -np.mean([p.center for p in b],axis=0))
    if np.linalg.norm(shift)<=tolerance:
        raise AlignmentUnavailable('Mean assembly center did not move.')
    shifted=[_relocate(p,np.eye(3),shift) for p in b]
    proof_cache=FrameProofCache()
    support=frame_support(a,shifted,tolerance,proofs=12,progress=progress,
                          proof_cache=proof_cache)
    required=max(8,ceil(.70*count))
    verified=int(support.get('proofs',0))
    checked=int(support.get('checked',0))
    matched=int(support.get('count',0))
    original=int((baseline or {}).get('count',0))
    if (matched<required or matched<=original or checked<min(8,count)
            or verified<ceil(.90*checked)):
        raise AlignmentUnavailable(
            f'Przesunięcie środka złożenia niepotwierdzone B-Rep: '
            f'{verified}/{checked} dowodów, {matched} kandydatów; '
            f'wymagane {required} zgodnych położeń.')
    if progress:
        progress('Wyrównanie: potwierdzono przesunięcie środka całego złożenia '
                 f'{shift.tolist()} mm, próba B-Rep {verified}/{checked}; '
                 'pozostałe bryły będą sprawdzone w końcowym porównaniu.')
    certified=sorted(proof_cache.results)
    return shifted,{
        'status':'registered','requested':True,'enabled':True,
        'method':'global_centroid_translation_brep_sample',
        'translation_B_to_A_mm':shift.tolist(),
        'rotation_B_to_A':np.eye(3).tolist(),
        'votes':matched,'previous_world_matches':original,
        'whole_assembly_support':support,
        'verification_scope':'sample_then_final_compare',
        'checked_sample_count':checked,'verified_sample_count':verified,
        'certified_pairs':certified,'full_pair_map':[],
        'requires_confirmation':True,
    }
'''
    if 'def _align_global_centroid_translation(' in revised:
        raise RuntimeError('Centroid helper already present unexpectedly')
    revised+=centroid_helper
    compile(revised,str(target),'exec')
    target.write_text(revised,encoding='utf8')
    print('DSCOMPARE_ALIGNMENT_2ANCHOR_GATE_PASS',target)


if __name__=='__main__':
    if len(sys.argv)!=2:raise SystemExit('usage: patch_alignment_stage2.py path/to/alignment.py')
    patch(sys.argv[1])
