"""Print only UI methods needed to make R11.27 responsive without guesswork."""
import ast,os
from pathlib import Path
root=Path(os.environ['DS_COMPARE_SOURCE'])
for rel,names in {
 'dsac29/gui_modern.py':['_modern_topbar','__init__','_new_page','_modern_compare','_reflow_compare','_modern_mass','new_comparison','reset_session','start','load_result','_refresh_outputs','_scroll_page','apply_theme'],
 'dsac29/gui45.py':['__init__','navigate'],
 'dsac29/gui46.py':['__init__','resizeEvent'],
}.items():
 p=root/rel
 if not p.exists():continue
 lines=p.read_text('utf8').splitlines()
 tree=ast.parse('\n'.join(lines))
 print(f'===== SOURCE R11.26 {rel} =====',flush=True)
 for cls in [n for n in ast.walk(tree) if isinstance(n,ast.ClassDef)]:
  if cls.name not in ('ModernWindow','Window'):continue
  for method in cls.body:
   if not isinstance(method,(ast.FunctionDef,ast.AsyncFunctionDef)) or method.name not in names:continue
   print(f'== {cls.name}.{method.name} {method.lineno}-{method.end_lineno} ==',flush=True)
   for i in range(method.lineno-1,method.end_lineno):
    print(f'{i+1:04d} {lines[i]}',flush=True)
