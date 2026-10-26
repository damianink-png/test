from pathlib import Path
import sys,ast,shutil
root=Path(sys.argv[1]);here=Path(__file__).resolve().parents[1]
for p in (here/'overlay').glob('*.py'):shutil.copy2(p,root/'dsac29'/p.name)
def replace(name,old,new):
 p=root/'dsac29'/name;s=p.read_text(encoding='utf8');assert old in s,(name,old);s=s.replace(old,new);ast.parse(s);p.write_text(s,encoding='utf8')
replace('revision_overlap.py','    old_ids={r.a_index', '    from .residual_identity import recover\n    records=recover(a,b,records,tolerance,progress,cancelled)\n    old_ids={r.a_index')
# Candidate search after approved alignment must use the same permissive search
# as its verifier. Exact user tolerance remains in the final CAD proof.
replace('compare.py','    cells = _spatial_index(b, free_b, tolerance)','    from .step_reexport_tolerance import world_candidate\n    search_tol=search_radius(tolerance) if step_reexport_tolerance or certified_pairs else tolerance\n    cells = _spatial_index(b, free_b, search_tol)')
replace('compare.py','_nearby(cells, s, tolerance)','_nearby(cells, s, search_tol)')
replace('compare.py','and dist(s, b[j]) <= tolerance and\n                  (candidate(s,b[j],tolerance) or\n                   coarse_candidate(s,b[j],tolerance))','and dist(s, b[j]) <= search_tol and\n                  ((world_candidate(s,b[j],tolerance) if step_reexport_tolerance or certified_pairs else\n                   (candidate(s,b[j],tolerance) or coarse_candidate(s,b[j],tolerance))))')
# Reuse the isolated proof transport; each request still receives its own shapes.
replace('cli.py',"                with trace.phase('final_comparison_after_alignment',certified_pairs=len(certified_pairs)):","                from .native_session import world_session\n                with world_session(True), trace.phase('final_comparison_after_alignment',certified_pairs=len(certified_pairs)):")
replace('native_guard.py',"        common = operate(BRepAlgoAPI_Common,a_shape,b_shape,float(req['tolerance']))","        report('common_build_and_validity')\n        common = operate(BRepAlgoAPI_Common,a_shape,b_shape,float(req['tolerance']))\n        report('common_write')")
replace('native_guard.py',"        response = dict(ok=True, common_volume=float(volume(common)))","        report('common_volume')\n        response = dict(ok=True, common_volume=float(volume(common)))")
replace('native_guard.py',"if os.getenv('DSCOMPARE_SAVE_FAILED_BREP','0')!='1':return","if os.getenv('DSCOMPARE_SAVE_FAILED_BREP','1')!='1':return")
replace('native_guard.py',"trace.mark('native_common','TIMEOUT',timeout_s=timeout_s)","trace.mark('native_common','TIMEOUT',timeout_s=timeout_s,last_phase=reply.with_suffix('.phase').read_text(encoding='utf8') if reply.with_suffix('.phase').exists() else 'worker_start')")
print('RC10.1 residual identity and diagnostics installed')
replace('native_guard.py',"        common = operate(BRepAlgoAPI_Common,a_shape,b_shape,float(req['tolerance']))", "        import faulthandler\n        with Path(result_path).with_suffix('.stack.txt').open('w',encoding='utf8') as stack:\n            faulthandler.enable(file=stack,all_threads=True)\n            faulthandler.dump_traceback_later(20,repeat=True,file=stack)\n            try:\n                common = operate(BRepAlgoAPI_Common,a_shape,b_shape,float(req['tolerance']))\n            finally:\n                faulthandler.cancel_dump_traceback_later()\n                faulthandler.disable()")
replace('revision_overlap.py',"            stat['boolean_checks']+=1", "            trace.mark('revision_candidate','DETAIL',a_id=i,b_id=j,a_name=ref.name,b_name=b[j].name,a_volume=ref.volume,b_volume=b[j].volume,center_distance=float(np.linalg.norm(ref.center-b[j].center)),a_bounds=bounds.tolist(),b_bounds=bb[j].tolist())\n            stat['boolean_checks']+=1")
