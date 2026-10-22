"""R11.31 automatic assembly-coordinate check and user approval protocol."""
import os
from pathlib import Path
root=Path(os.environ["DS_COMPARE_SOURCE"])
p=root/"dsac29/cli.py"
s=p.read_text(encoding="utf8")
def one(a,b):
 global s
 n=s.count(a)
 if n!=1:raise RuntimeError(f"R11.31 CLI anchor count {n}: {a[:85]!r}")
 s=s.replace(a,b,1)
one("bom_fast=False,bom_csv=True):","bom_fast=False,bom_csv=True,auto_align=False,alignment_approval=None):")
one("""        from .parallel_import import should_parallel, load_pair
        parallel, reason=should_parallel(a_path,b_path)""",
"""        from .parallel_import import should_parallel, load_pair
        # Large parallel importers in frozen EXE may exhaust RAM; prefer one
        # sequential OCC reader for interactive comparisons.
        parallel,reason=(False,'tryb bezpieczny: import sekwencyjny') if auto_align else should_parallel(a_path,b_path)""")
start=s.index("    alignment={'requested':bool(align),'enabled':False}")
stop=s.index("    # One shared, strictly in-memory geometry registry",start)
new="""    alignment={'requested':bool(align or auto_align),'enabled':False}
    (Path(output)/'OSTRZEZENIA.txt').unlink(missing_ok=True)
    if auto_align and not identical_sources:
        from .alignment import align_assembly,AlignmentUnavailable
        from .registration_gate import already_world_aligned
        if already_world_aligned(a,b,tolerance):
            alignment.update(enabled=False,status='already_aligned',
                             reason='Potwierdzono część wspólnych brył w oryginalnym układzie A/B.')
            if progress:progress('Wykrywanie położenia: modele mają wspólny układ odniesienia; bez przesuwania.')
        else:
            if progress:progress('Sprawdzanie wspólnego przesunięcia całego złożenia…')
            try:
                shifted,proposal=align_assembly(a,b,tolerance,progress)
            except AlignmentUnavailable as exc:
                raise RuntimeError(
                  'Nie da się bezpiecznie stwierdzić wspólnego przesunięcia modeli. '
                  'Przerwano analizę przed porównaniem i BOM, aby nie tworzyć błędnych kolorów. '
                  'Sprawdź układ współrzędnych w CAD. Szczegóły: '+str(exc)) from exc
            delta=proposal.get('translation_B_to_A_mm',(0,0,0))
            import numpy as np
            unchanged=(proposal.get('status')=='already_aligned' or
                       (np.linalg.norm(delta)<=tolerance and
                        np.allclose(proposal.get('rotation_B_to_A',np.eye(3)),np.eye(3),atol=1e-6)))
            if unchanged:
                alignment=proposal
            else:
                if alignment_approval is None:
                    raise RuntimeError('Wykryto przesunięcie; nie dostarczono obsługi pytania do użytkownika.')
                decision=alignment_approval(proposal)
                if decision!='align':
                    raise InterruptedError('Anulowano analizę — modele pozostały niezmienione.')
                b=shifted
                alignment=proposal
                alignment['approved_by_user']=True
                if progress:progress('Wyrównanie zaakceptowane — dalsze porównanie w jednym układzie współrzędnych.')
    elif align and not identical_sources:
        from .alignment import align_assembly, AlignmentUnavailable
        try:b,alignment=align_assembly(a,b,tolerance,progress)
        except AlignmentUnavailable as exc:
            raise RuntimeError('Wyrównanie całego złożenia nie jest wiarygodne: '+str(exc)) from exc
"""
s=s[:start]+new+s[stop:]
p.write_text(s,encoding='utf8')
p=root/"dsac29/registration_gate.py"
p.write_text('''"""Cheap, conservative B-Rep check for an already-common coordinate frame."""
from collections import defaultdict
from math import ceil
from .geometry import signature,candidate,equivalent_world
import numpy as np

def already_world_aligned(a,b,tolerance):
    if not a or not b:return False
    # Avoid expensive global alignment when even some stable world-space
    # reference parts prove the two revisions share their CAD origin.
    by_sig=defaultdict(list)
    for part in a:
        by_sig[signature(part)].append(part)
    required=1 if min(len(a),len(b))<=5 else max(2,ceil(.15*min(len(a),len(b))))
    count=0;used=set();checks=0
    for part in b:
        for base in by_sig.get(signature(part),[]):
            if id(base) in used:continue
            if np.linalg.norm(base.center-part.center)>tolerance:continue
            if not candidate(base,part,tolerance):continue
            checks+=1
            if equivalent_world(base,part,tolerance):
                used.add(id(base));count+=1;break
            if checks>20:break
        if count>=required:return True
        if checks>20:break
    return False
''',encoding='utf8')
print('R11.31 auto-align check installed: shared world anchors -> direct compare; otherwise request safe approval')
