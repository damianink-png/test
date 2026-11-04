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
    support=frame_support(a,aligned,tolerance,verify_all=True,progress=progress)
    if support['ratio']>=.60 and support['count']>=min(2,min(len(a),len(b))):"""
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
    target.write_text(revised.replace(old_message,new_message),encoding='utf8')
    print('DSCOMPARE_ALIGNMENT_2ANCHOR_GATE_PASS',target)


if __name__=='__main__':
    if len(sys.argv)!=2:raise SystemExit('usage: patch_alignment_stage2.py path/to/alignment.py')
    patch(sys.argv[1])
