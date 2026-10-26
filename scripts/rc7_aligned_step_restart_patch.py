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
                # Fresh geometry requires full STEP surface/trim proof and
                # isolated native workers; this does not reuse old certificates.
                step_reexport_tol=True
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


# The original R13 regression expected reusing a certified in-memory comparison
# after alignment. That contradicts the newly requested STEP round-trip restart.
# Replace it with stronger proof of an independent second pass, a saved STEP,
# and fresh geometry context. Non-aligned assemblies still use only one pass.
test_file = root / 'tests' / 'test_r13_deferred_alignment.py'
test = test_file.read_text(encoding='utf-8')
old_assert = " assert len(contexts)==1  # reuse all proven pairs without repeating compare"
new_assert = """ assert len(contexts)==2  # stage 1 discovery followed by independent STEP reimport comparison
 assert contexts[0] is not contexts[1]  # no stale geometry certificates after round-trip
 aligned_step=other/'out'/'_WYROWNANY_STEP'/'B_WYROWNANY.step'
 assert aligned_step.is_file() and aligned_step.stat().st_size>500
 summary=json.loads((other/'out'/'PODSUMOWANIE.json').read_text())
 assert summary['alignment']['aligned_step_restart']['solids_reimported']==len(b)
 assert summary['statuses'].get('SAME',0)==len(a)"""
assert test.count(old_assert)==1, 'Unexpected original R13 regression assertion'
test_file.write_text(test.replace(old_assert,new_assert),encoding='utf-8')
ast.parse(test_file.read_text(encoding='utf-8'))
print('Updated R13 regression to require independent compare after saved/reimported STEP')

# A STEP round-trip changes integrated scalar descriptors. Search margins
# admit hypotheses only; the final proof still uses the user's tolerance.
compare = root / 'dsac29' / 'compare.py'
s = compare.read_text(encoding='utf-8')
s = s.replace('import coarse_candidate,reexport_equivalent_world,search_radius',
              'import coarse_candidate,reexport_equivalent_world,search_radius,world_candidate')
old = '    cells = _spatial_index(b, free_b, tolerance)'
assert s.count(old)==1
s = s.replace(old, '    world_radius = search_radius(tolerance) if step_reexport_tolerance else tolerance\n    cells = _spatial_index(b, free_b, world_radius)')
s = s.replace('_nearby(cells, s, tolerance)', '_nearby(cells, s, world_radius)')
s = s.replace('and dist(s, b[j]) <= tolerance and', 'and dist(s, b[j]) <= world_radius and')
s = s.replace('coarse_candidate(s,b[j],tolerance))]',
              'coarse_candidate(s,b[j],tolerance) or\n                   (step_reexport_tolerance and world_candidate(s,b[j],tolerance)))]')
ast.parse(s)
compare.write_text(s,encoding='utf-8')
