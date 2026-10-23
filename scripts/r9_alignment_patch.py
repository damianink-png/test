from pathlib import Path
import json
root=Path(__file__).resolve().parents[1]/'source'
p=root/'dsac29'/'alignment.py'
s=p.read_text(encoding='utf-8')
def rep(old,new):
 global s
 assert s.count(old)==1,(s.count(old),old[:90])
 s=s.replace(old,new,1)
rep('    try:\n        aligned,info=_align_anchors(a,b,tolerance,progress)', '''    # When the existing frame has a B-Rep-confirmed majority, inspect
    # translations FIRST. Unique-anchor rigid checks can otherwise spend a
    # very long time solving a transform that is not needed at all.
    initial=frame_support(a,b,tolerance,proofs=12)
    if (initial['ratio']>=.60 and initial['checked']>=min(2,min(len(a),len(b)))
            and initial['proofs']==initial['checked']):
        try:
            aligned,info=_align_repeated_translation(a,b,tolerance,progress,
                                                     already_aligned=initial)
            if info.get('status')=='already_aligned':
                return b,info
            support=frame_support(a,aligned,tolerance,proofs=12)
            if (support['count']>initial['count'] and support['ratio']>=.60
                    and support['proofs']==support['checked']):
                info['whole_assembly_support']=support
                return aligned,info
        except AlignmentUnavailable:
            if progress:progress('Wyrównanie: zachowano potwierdzony aktualny układ CAD.')
            return b,{'requested':True,'enabled':True,'status':'already_aligned',
                      'method':'world_brep_consensus','votes':initial['count'],
                      'rotation_B_to_A':np.eye(3).tolist(),
                      'translation_B_to_A_mm':[0.,0.,0.]}
    try:
        aligned,info=_align_anchors(a,b,tolerance,progress)''')
rep('def _align_repeated_translation(a,b,tolerance,progress=None):',
    'def _align_repeated_translation(a,b,tolerance,progress=None,already_aligned=None):')
rep('    proposals={}\n    for key in common:', '''    proposals={}
    # Rare shared shapes make better candidate anchors. The bounded list
    # avoids repeatedly ranking hundreds of equivalent translations.
    limit=192
    for key in sorted(common,key=lambda k:(len(sig_a[k])*len(sig_b[k]),str(k))):''')
rep('                if len(proposals)>=900:break\n            if len(proposals)>=900:break\n        if len(proposals)>=900:break', '''                if len(proposals)>=limit:break
            if len(proposals)>=limit:break
        if len(proposals)>=limit:break
    if len(a)==len(b):
        mean_delta=np.mean([p.center for p in a],axis=0)-np.mean([p.center for p in b],axis=0)
        proposals[tuple(np.round(mean_delta,4))]=mean_delta
    proposals[(0.,0.,0.)]=np.zeros(3)''')
rep('    ranked=[]\n    for translation in proposals.values():', '''    ranked=[]
    from time import perf_counter
    ranked_start=perf_counter()
    for proposal_index,translation in enumerate(proposals.values()):''')
rep('        ranked.append((votes,tuple(float(x) for x in translation)))', '''        ranked.append((votes,tuple(float(x) for x in translation)))
        if progress and proposal_index and proposal_index%48==0:
            progress(f'Wyrównanie: sprawdzono {proposal_index+1}/{len(proposals)} ustawień w {perf_counter()-ranked_start:.1f} s')''')
rep('    ranked.sort(key=lambda x:(-x[0],x[1]))\n    candidates=[]', '''    ranked.sort(key=lambda x:(-x[0],x[1]))
    if already_aligned is not None:
        baseline=int(already_aligned['count'])
        if ranked[0][0]<=baseline:
            if progress:progress(f'Wyrównanie: już zgodne ({baseline} brył w układzie CAD), brak lepszego przesunięcia.')
            return b,{'requested':True,'enabled':True,'status':'already_aligned',
                      'method':'world_brep_consensus','votes':baseline,
                      'rotation_B_to_A':np.eye(3).tolist(),
                      'translation_B_to_A_mm':[0.,0.,0.]}
    candidates=[]''')
p.write_text(s,encoding='utf-8')
q=root/'dsac29'/'cli.py'
t=q.read_text(encoding='utf-8')
a='''            except AlignmentUnavailable as exc:
                raise RuntimeError(
                  'Nie da się bezpiecznie stwierdzić wspólnego przesunięcia modeli. '
                  'Przerwano analizę przed porównaniem i BOM, aby nie tworzyć błędnych kolorów. '
                  'Sprawdź układ współrzędnych w CAD. Szczegóły: '+str(exc)) from exc'''
b='''            except AlignmentUnavailable as exc:
                # Existing B-Rep-verified majority is not a failed alignment.
                if (initial['ratio']>=.60 and initial['checked']>=min(2,min(len(a),len(b)))
                        and initial['proofs']==initial['checked']):
                    shifted=b
                    proposal={'requested':True,'enabled':True,'status':'already_aligned',
                              'method':'world_brep_consensus','votes':initial['count'],
                              'translation_B_to_A_mm':[0.,0.,0.]}
                    if progress:progress('Nie znaleziono wiarygodnego lepszego przesunięcia; użyto zgodnego układu CAD.')
                else:
                    raise RuntimeError(
                      'Nie da się bezpiecznie stwierdzić wspólnego przesunięcia modeli. '
                      'Przerwano analizę przed porównaniem i BOM, aby nie tworzyć błędnych kolorów. '
                      'Sprawdź układ współrzędnych w CAD. Szczegóły: '+str(exc)) from exc'''
assert t.count(a)==1
q.write_text(t.replace(a,b),encoding='utf-8')
(root/'R9_ZMIANY.txt').write_text('DS Compare 1.0 R9\n- UI R8 zachowany w całości\n- Szybki test wspólnego układu CAD przed ciężkim wyrównaniem\n- Limit 192 hipotez i komunikaty postępu\n- Bez zmiany kryteriów B-Rep i kolorów\n',encoding='utf-8')
print('R9 engine patch PASS')
