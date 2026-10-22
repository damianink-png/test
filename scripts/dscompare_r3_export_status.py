"""R3: distinguish main colored STEP failure from OPTIONAL difference STEP failure.
Save summaries independently so GUI never hides a valid main output.
"""
from pathlib import Path
import os
root=Path(os.environ['DS_COMPARE_SOURCE'])
p=root/'dsac29/report.py'
s=p.read_text('utf8')
old="""    if details["errors"]:err=(err+"; " if err else "")+"Różnice materiału: "+"; ".join(details["errors"])"""
new="""    # Errors from optional ROZNICE_BREP.step must never invalidate the main
    # POROWNANIE_KOLORY.step, even when the optional exporter raises.
    if details["errors"] and progress:
        progress('UWAGA: opcjonalny STEP różnic materiałowych: '+'; '.join(details["errors"]))"""
assert s.count(old)==1
s=s.replace(old,new,1)
old="""'step_export_error':err,'step_ready':bool(generate_step and err is None and (out/'POROWNANIE_KOLORY.step').is_file()),'full_bom'"""
new="""'step_export_error':err,'optional_diff_errors':list(details['errors']),
                        'main_step_error':err,'main_step_ready':bool(generate_step and err is None and (out/'POROWNANIE_KOLORY.step').is_file()),
                        'step_ready':bool(generate_step and err is None and (out/'POROWNANIE_KOLORY.step').is_file()),'full_bom'"""
assert s.count(old)==1
s=s.replace(old,new,1)
p.write_text(s,'utf8')

p=root/'dsac29/worker_v37.py'
s=p.read_text('utf8')
old="""payload={'ok':True,'folder':str(output),'wyniki':len(recs),'blad_step':err,'step_ready':not bool(err) and (output/'POROWNANIE_KOLORY.step').is_file(),'alignment':json.loads((output/'PODSUMOWANIE.json').read_text(encoding='utf-8')).get('alignment',{})}"""
new="""summary=json.loads((output/'PODSUMOWANIE.json').read_text(encoding='utf-8'))
            main_ready=bool(summary.get('step_ready',False))
            payload={'ok':bool(not ns.generate_step or main_ready),
                     'folder':str(output),'wyniki':len(recs),'blad_step':err,
                     'step_ready':main_ready,
                     'optional_diff_errors':summary.get('optional_diff_errors',[]),
                     'alignment':summary.get('alignment',{})}"""
assert s.count(old)==1
s=s.replace(old,new,1)
p.write_text(s,'utf8')
print('R3 success reporting: main STEP independent from optional B-Rep changes; worker ok reflects requested main export')
