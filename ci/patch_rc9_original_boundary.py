"""Separate original-to-original identity from the repair displacement budget."""
from pathlib import Path
import ast
import sys

root=Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parents[1]/'dscompare_rc9_manual'
def edit(name,replacements):
    path=root/'dsac29'/name
    source=path.read_text(encoding='utf-8')
    for old,new in replacements:
        if source.count(old)!=1:
            raise SystemExit(f'{name}: expected one anchor, got {source.count(old)}: {old[:70]}')
        source=source.replace(old,new)
    ast.parse(source)
    path.write_text(source,encoding='utf-8')

edit('step_reexport_tolerance.py',[
 ('progress=None, _repair_boundary_only=False):','progress=None, _repair_boundary_only=False, _original_boundary_only=False):'),
 ("    report=progress or (lambda phase: None)","""    # Original-to-original proof spends no budget on repair displacement.
    # It retains EVERY edge and uses the existing half-budget curve proof.
    # Repair proof keeps its separate, stricter budget and policy.
    if _original_boundary_only and (allow_boolean or _repair_boundary_only):
        raise ValueError('Original boundary proof cannot repair or use Booleans')
    report=progress or (lambda phase: None)"""),
 ('if not _repair_boundary_only or allow_boolean:return False','if not (_repair_boundary_only or _original_boundary_only) or allow_boolean:return False'),
 ("    report('surface_and_trim_proof')", """    report('surface_and_trim_proof')
    if _original_boundary_only:
        return bool(prove(a.shape,b.shape,owner,fa,tolerance,strict_repair=False))""")
])
edit('native_guard.py',[
 ('allow_boolean=False,_repair_boundary_only=True,progress=report)', 'allow_boolean=False,_original_boundary_only=True,progress=report)')
])
print('Original boundary identity separated from copy-repair proof; no Boolean or edge removal')
