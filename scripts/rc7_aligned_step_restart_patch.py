"""Install STEP round-trip restart into unpacked Work RC7.

Fail closed if the exact RC7 integration points changed. The original-frame
path and all geometry matching tolerances remain untouched.
"""
from pathlib import Path
import ast
import sys

root = Path(sys.argv[1])
cli = root / 'dsac29' / 'cli.py'
s = cli.read_text(encoding='utf-8')
anchor = "            proven=proposal.get('full_pair_map') or []"
assert s.count(anchor) == 1, 'RC7 CLI proof/restart anchor changed'
replacement = '''            # Restart in the verified A frame from an actual STEP round-trip.
            # This is not a geometry proof; the standard compare must run anew.
            import os
            restart_from_aligned_step = bool(alignment.get('applied')) and (
                os.environ.get('DSCOMPARE_REIMPORT_ALIGNED_STEP', '1').strip().lower()
                not in ('0', 'false', 'off', 'no'))
            if restart_from_aligned_step:
                from .aligned_step_restart import save_aligned_step_and_reload
                with trace.phase('aligned_step_write_reimport'):
                    b,aligned_step_path,reimport_diagnostics=save_aligned_step_and_reload(
                        b,output,tolerance,max_solids=max_solids,progress=progress)
                alignment['aligned_step_path']=str(aligned_step_path)
                alignment['aligned_step_restart']=reimport_diagnostics
                # Old indices and shape certificates refer to pre-STEP shapes.
                # Do not reuse them after reimport, even if counts are equal.
                certified_pairs=[]
                step_reexport_tol=False
                geometry_context=GeometryRegistry()
            proven=proposal.get('full_pair_map') or []'''
s=s.replace(anchor,replacement)
anchor2="            if alignment.get('applied') and len(proven)==len(a)==len(b):"
assert s.count(anchor2) == 1, 'RC7 CLI full proof shortcut anchor changed'
s=s.replace(anchor2,"""            if restart_from_aligned_step:
                with trace.phase('fresh_comparison_from_aligned_step'):
                    rec=do_compare()
            elif alignment.get('applied') and len(proven)==len(a)==len(b):""")
ast.parse(s)
cli.write_text(s,encoding='utf-8')
module = root / 'dsac29' / 'aligned_step_restart.py'
assert module.is_file(), 'Copy aligned_step_restart.py into source tree first'
ast.parse(module.read_text(encoding='utf-8'))
print('STEP aligned round-trip restart installed; default on after verified alignment')
