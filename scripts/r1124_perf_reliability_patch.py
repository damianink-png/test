"""R11.24 detailed timing and durable worker crash report."""
from pathlib import Path
import os
root=Path(os.environ['DS_COMPARE_SOURCE'])
def replace(file,a,b):
 p=root/file;s=p.read_text('utf8')
 n=s.count(a)
 if n!=1:raise RuntimeError(f'{file} anchor occurred {n} times: {a[:80]!r}')
 p.write_text(s.replace(a,b,1),encoding='utf8')

replace('dsac29/cli.py',
 """    if progress:progress('Zapis raportów CSV/HTML i modelu porównawczego STEP...')
    folder,err=produce(output,a,b,rec,density,generate_step=step,colors=colors,""",
 """    if progress:progress('Zapis modelu STEP, raportu i BOM...')
    t_output=perf_counter()
    folder,err=produce(output,a,b,rec,density,generate_step=step,colors=colors,""")
replace('dsac29/cli.py',
 """                       diff_step=diff_step,tolerance=tolerance,progress=progress,preview3d=preview3d,revision_style=revision_style,old_alpha=old_alpha,geometry_context=geometry_context,full_bom=full_bom,bom_fast=bom_fast,bom_csv=bom_csv,report_context={"A":Path(a_path).name,"B":Path(b_path).name,"import":import_stats,"alignment":alignment,"tolerance_mm":tolerance})
    import json""",
 """                       diff_step=diff_step,tolerance=tolerance,progress=progress,preview3d=preview3d,revision_style=revision_style,old_alpha=old_alpha,geometry_context=geometry_context,full_bom=full_bom,bom_fast=bom_fast,bom_csv=bom_csv,report_context={"A":Path(a_path).name,"B":Path(b_path).name,"import":import_stats,"alignment":alignment,"tolerance_mm":tolerance})
    output_stage_s=perf_counter()-t_output
    if progress:progress(f'Zapis wyników (STEP + raport + BOM): {output_stage_s:.1f} s')
    import json""")
replace('dsac29/cli.py',
 """'matching_and_classification_s':matching_s,'bom_grouping_s':summary.get('bom_seconds',0),'total_s':perf_counter()-ts,""",
 """'matching_and_classification_s':matching_s,'bom_grouping_s':summary.get('bom_seconds',0),
         'step_and_reports_stage_s':output_stage_s,
         'total_s':perf_counter()-ts,""")
replace('dsac29/worker_v37.py',
 """    except Exception:
        emit('BŁĄD: '+traceback.format_exc().splitlines()[-1])
        payload={'ok':False,'error':traceback.format_exc()}""",
 """    except Exception:
        issue=traceback.format_exc()
        emit('BŁĄD: '+issue.splitlines()[-1])
        # Keep a full readable trace even when GUI/log collection is interrupted.
        try:
            (folder/'DIAGNOSTYKA_BLEDU.txt').write_text(issue,encoding='utf8')
        except OSError:pass
        payload={'ok':False,'error':issue}""")
print('R11.24 stage timing and durable diagnostics installed')
