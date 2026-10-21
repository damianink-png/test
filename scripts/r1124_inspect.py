"""Temporary R11.24 source introspection for safe, narrow patches."""
from pathlib import Path
import os,ast
root=Path(os.environ['DS_COMPARE_SOURCE'])
SPECS={
 'dsac29/step_io.py':('class','def'),
 'dsac29/worker_v37.py':('def',),
 'dsac29/gui45.py':('def',),
 'dsac29/gui_modern.py':('def',),
 'dsac29/compare.py':('def',),
}
for filename in SPECS:
 p=root/filename
 s=p.read_text('utf8')
 lines=s.splitlines()
 tree=ast.parse(s)
 print('\\n===== FILE',filename,'LINES',len(lines),'=====')
 for n in ast.walk(tree):
  if not isinstance(n,(ast.ClassDef,ast.FunctionDef,ast.AsyncFunctionDef)):continue
  if isinstance(n,ast.ClassDef):
   print('CLASS',n.name,n.lineno,n.end_lineno);continue
  print('METHOD',n.name,n.lineno,n.end_lineno)
  if filename.endswith('step_io.py') and n.name in ('__init__','add','write','_export_revision_step','export_revision_step','inspect_step_colors'):
   print('\\n'.join(f'{i+1:04} {lines[i]}' for i in range(n.lineno-1,min(n.end_lineno,n.lineno+145))))
  elif filename.endswith('worker_v37.py') and n.name in ('main','run','emit','save_step','do_compare'):
   print('\\n'.join(f'{i+1:04} {lines[i]}' for i in range(n.lineno-1,min(n.end_lineno,n.lineno+165))))
  elif filename.endswith('gui45.py') and n.name in ('start','_on_finished','on_finished','_read_result','_proc_finished','_finish','_new_job','_update_actions'):
   print('\\n'.join(f'{i+1:04} {lines[i]}' for i in range(n.lineno-1,min(n.end_lineno,n.lineno+150))))
  elif filename.endswith('compare.py') and n.name in ('compare','match','pair_moved','_pair_moved'):
   print('\\n'.join(f'{i+1:04} {lines[i]}' for i in range(n.lineno-1,min(n.end_lineno,n.lineno+105))))
