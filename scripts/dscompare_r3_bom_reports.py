"""R3: avoid re-writing final HTML and summary; reuse report context once.

Keep optional difference STEP failure separate. Grouping budgets avoid further
slow B-Rep attempts once a single native comparison proves pathological.
"""
from pathlib import Path
import os
root=Path(os.environ["DS_COMPARE_SOURCE"])
p=root/"dsac29/report.py"
s=p.read_text('utf8')
old="""                    try:
                        if context.rigid_equivalent(first, part, tolerance):
                            matched = group_index
                            break
                    except Exception as exc:"""
new="""                    # One native OCC check can exceed the nominal group
                    # deadline. If it does, do not launch MORE such checks.
                    before_check=perf_counter()
                    try:
                        if context.rigid_equivalent(first, part, tolerance):
                            matched = group_index
                            break
                    except Exception as exc:"""
assert s.count(old)==1;s=s.replace(old,new,1)
old="""                        # A failure must never turn into an assumed match.
        if matched is None:"""
new="""                        # A failure must never turn into an assumed match.
                    finally:
                        if perf_counter()-before_check>3.0 or perf_counter()>deadline:
                            if not budget_exceeded:
                                budget_exceeded=True
                                context.stats['bom_budget_exhausted']+=1
                                if progress:progress(
                                  'BOM: wolne sprawdzanie B-Rep — pominięto dalsze niepotwierdzone grupowanie.')
                            break
        if matched is None:"""
assert s.count(old)==1;s=s.replace(old,new,1)
# Main report should already have all its context instead of CLI reopening it.
anchor="""    stage.update(reports='html',report_percent=89)
    final_report=out/'RAPORT.html'"""
replacement="""    # Import scope, provenance and registration warnings are inserted BEFORE
    # final write, rather than reopening and rewriting the whole HTML 1-3x.
    context_info=report_context or {}
    notices=[]
    omitted=sum(int(v.get('faces_outside_solids',0))
                for v in context_info.get('import',{}).values())
    if omitted:
        warning=f'Zakres porównania: tylko bryły SOLID. Pominięto {omitted} powierzchni poza bryłami (A+B).'
        (out/'ZAKRES_IMPORTU.txt').write_text(warning,encoding='utf8')
        notices.append('<p role="alert">'+html.escape(warning)+'</p>')
    if context_info.get('alignment',{}).get('warning'):
        warning=context_info['alignment']['warning']
        (out/'OSTRZEZENIA.txt').write_text(warning+'\\n',encoding='utf8')
        notices.append('<p role="alert"><strong>'+html.escape(warning)+'</strong></p>')
    if revision_style:
        note=(f'<div class="panel"><b>A — stara rewizja:</b> {html.escape(str(context_info.get("A","")))}'
              f'<br><b>B — nowa rewizja:</b> {html.escape(str(context_info.get("B","")))}'
              f'<br>Tolerancja: {tolerance} mm</div>')
        notices.append(note)
        if err:notices.append('<p role="alert"><b>Eksport STEP nie powiódł się:</b> '+html.escape(err)+'</p>')
    if notices:
        htmltxt=htmltxt.replace('<body>','<body>'+''.join(notices),1)
    stage.update(reports='html',report_percent=89)
    final_report=out/'RAPORT.html'"""
assert s.count(anchor)==1;s=s.replace(anchor,replacement,1)
anchor="""'step_ready':bool(generate_step and err is None and (out/'POROWNANIE_KOLORY.step').is_file()),'full_bom'"""
replacement="""'step_ready':bool(generate_step and err is None and (out/'POROWNANIE_KOLORY.step').is_file()),
                        'import_diagnostics':context_info.get('import',{}),
                        'source_fingerprints':context_info.get('fingerprints',{}),
                        'manual_pairs':context_info.get('manual_pairs',[]),
                        'alignment':context_info.get('alignment',{}),
                        'source_A':context_info.get('source_A',''),
                        'source_B':context_info.get('source_B',''),
                        'tolerance_mm':tolerance,
                        'export_style':'revision_A_B' if revision_style else 'standard',
                        'old_alpha':old_alpha,
                        'full_bom'"""
assert s.count(anchor)==1;s=s.replace(anchor,replacement,1)
p.write_text(s,'utf8')
p=root/"dsac29/cli.py"
s=p.read_text('utf8')
old="""bom_csv=bom_csv,report_context={"A":Path(a_path).name,"B":Path(b_path).name,"import":import_stats,"alignment":alignment,"tolerance_mm":tolerance})"""
new="""bom_csv=bom_csv,report_context={
                        "A":Path(a_path).name,"B":Path(b_path).name,
                        "source_A":str(Path(a_path).resolve()),
                        "source_B":str(Path(b_path).resolve()),
                        "import":import_stats,"alignment":alignment,"tolerance_mm":tolerance,
                        "fingerprints":fingerprints,
                        "manual_pairs":manual_review['pairs'] if manual_review else []})"""
assert s.count(old)==1;s=s.replace(old,new,1)
start=s.index("    summary_path=folder/'PODSUMOWANIE.json'")
end=s.index("    if thumbnails:",start)
replacement="""    # report.produce already wrote HTML and summary once using report_context.
    # Do not read/write multi-MB HTML again just to prepend the provenance.
    summary=json.loads((folder/'PODSUMOWANIE.json').read_text(encoding='utf8'))
"""
s=s[:start]+replacement+s[end:]
p.write_text(s,'utf8')
print("R3 reporting: one final HTML + JSON write, import/provenance already passed to producer; slow B-Rep cut-off between checks")
