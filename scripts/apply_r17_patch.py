"""Patch exact GitHub R16 source after extraction; strict anchor checks."""
from pathlib import Path
root=Path(__file__).resolve().parents[1]/'source'/'dsac29'
def replace(fn,old,new):
 p=root/fn
 s=p.read_text(encoding='utf-8')
 if s.count(old)!=1:raise RuntimeError(f'R17 anchor {fn}: {s.count(old)} x {old[:80]!r}')
 p.write_text(s.replace(old,new,1),encoding='utf-8')
replace('cli.py',
 '    if revision_style:\n        from .revision_rules import classify_revisions',
 '    precomputed_regions={}\n    overlap_diagnostics=None\n    if revision_style:\n        from .revision_rules import classify_revisions')
replace('cli.py',
 '        rec=classify_revisions(a,b,rec,tolerance,progress=progress,geometry_context=geometry_context,geometry_first=True)\n        if progress:',
 '        rec=classify_revisions(a,b,rec,tolerance,progress=progress,geometry_context=geometry_context,geometry_first=True)\n        from .revision_overlap import merge_material_revisions\n        rec,precomputed_regions,overlap_diagnostics=merge_material_revisions(a,b,rec,tolerance,progress,cancelled)\n        if progress:')
replace('cli.py',
 '"manual_pairs":manual_review[\'pairs\'] if manual_review else []})',
 '"manual_pairs":manual_review[\'pairs\'] if manual_review else [],\n                        "revision_overlap":overlap_diagnostics},\n                       precomputed_material_regions=precomputed_regions)')
replace('material_deltas.py',
 'def all_changes(records,a,b,tolerance=0.01,progress=None):\n    out={};errors={}',
 'def all_changes(records,a,b,tolerance=0.01,progress=None,precomputed=None):\n    out=dict(precomputed or {});errors={}')
replace('material_deltas.py',
 '    for n,index in enumerate(indices,1):\n        r=records[index]',
 '    for n,index in enumerate(indices,1):\n        if index in out:continue\n        r=records[index]')
replace('report.py',
 'geometry_context=None,full_bom=True,report_context=None,bom_fast=False,bom_csv=True):',
 'geometry_context=None,full_bom=True,report_context=None,bom_fast=False,bom_csv=True,precomputed_material_regions=None):')
replace('report.py',
 'all_changes(records,a,b,tolerance,progress) if revision_style else ({},{})',
 'all_changes(records,a,b,tolerance,progress,precomputed_material_regions) if revision_style else ({},{})')
replace('report.py',
 "'NAZWY_TE_SAME_GEOMETRIE.csv','DIAGNOSTYKA_DOPASOWANIA.json'",
 "'NAZWY_TE_SAME_GEOMETRIE.csv','NAZWY_ZMIENIONA_GEOMETRIA.csv','DIAGNOSTYKA_DOPASOWANIA.json'")
replace('report.py',
 "    diagnostic={'bez_zmian_geometrii'",
 """    renamed_changed=[(a[r.a_index].name,b[r.b_index].name,a[r.a_index].path,b[r.b_index].path)
                     for r in records if r.status=='CHANGED' and r.name_changed
                     and r.a_index is not None and r.b_index is not None]
    if renamed_changed:
        write_csv(out/'NAZWY_ZMIENIONA_GEOMETRIA.csv',
                  ['Nazwa A','Nazwa B','Ścieżka A','Ścieżka B'],renamed_changed)
    diagnostic={'zmienione_rewizje':sum(r.status=='CHANGED' for r in records),
                'zmieniona_geometria_i_nazwa':len(renamed_changed),
                'dobor_podobnych_rewizji':(report_context or {}).get('revision_overlap'),
                'bez_zmian_geometrii'""")
replace('report.py',
 "'renamed_geometry_count':changed_names,",
 "'renamed_geometry_count':changed_names,'geometry_and_name_changed_count':len(renamed_changed),")
(root/'revision_overlap.py').write_text((Path(__file__).resolve().parent/'r17_revision_overlap.py').read_text(encoding='utf-8'),encoding='utf-8')
print('R17 patch PASS')
