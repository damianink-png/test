from pathlib import Path
import os,ast
root=Path(os.environ['DS_COMPARE_SOURCE'])
spec={
 'dsac29/cli.py':['process'],
 'dsac29/gui45.py':['poll','finished','load_result','filter_results'],
 'dsac29/gui_modern.py':['poll','finished','load_result','_modern_compare','_modern_settings','_settings_card'],
 'dsac29/compare.py':['compare'],
 'dsac29/step_io.py':['_assembly','_parent'],
}
for name,chosen in spec.items():
 text=(root/name).read_text('utf8'); lines=text.splitlines()
 print('=====DETAIL',name,len(lines),'=====')
 tree=ast.parse(text)
 for n in ast.walk(tree):
  if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name in chosen:
   print('----',n.name,n.lineno,n.end_lineno,'----')
   cap=n.end_lineno if n.name not in ('compare','process') else min(n.end_lineno,n.lineno+350)
   for i in range(n.lineno-1,cap):
    print('%04d '%(i+1)+lines[i])
