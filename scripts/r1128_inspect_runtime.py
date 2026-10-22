"""R11.28 retrieve complete actual relevant CAD/process source structure and code."""
from pathlib import Path
import ast,os
root=Path(os.environ['DS_COMPARE_SOURCE'])
targets={
'dsac29/alignment.py':None,
'dsac29/stage_fast.py':None,
'dsac29/report.py':['produce'],
'dsac29/worker_v37.py':['main','emit'],
'dsac29/gui45.py':['start','finished','poll','cancel','load_result','closeEvent','navigate','_choose','create_settings'],
'dsac29/gui46.py':['start','finished','poll','closeEvent','_fit_layout_to_monitor','navigate','apply_theme'],
'dsac29/gui_modern.py':['start','finished','poll','closeEvent','load_result','_refresh_outputs','_init_adaptive_window','_reflow_settings','_scroll_page'],
'dsac29/cli.py':['process']
}
for rel,methods in targets.items():
 p=root/rel
 if not p.is_file():continue
 lines=p.read_text('utf8').splitlines()
 print('====== SOURCE',rel,len(lines),'======',flush=True)
 try:tree=ast.parse('\n'.join(lines))
 except SyntaxError as e:print('SYNTAX ERROR',e,flush=True);continue
 if methods is None:
  for i,line in enumerate(lines):print(f'{i+1:04d} {line}',flush=True)
 else:
  for n in ast.walk(tree):
   if not isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) or n.name not in methods:continue
   print(f'----- {n.name} {n.lineno}-{n.end_lineno} -----',flush=True)
   for i in range(n.lineno-1,min(n.end_lineno,n.lineno+360)):
    print(f'{i+1:04d} {lines[i]}',flush=True)
