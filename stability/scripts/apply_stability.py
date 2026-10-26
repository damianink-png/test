import ast, shutil, sys
from pathlib import Path
root=Path(sys.argv[1]);here=Path(__file__).resolve().parents[1]
for p in (here/'overlay').glob('*.py'):shutil.copy2(p,root/'dsac29'/p.name)
def change(name,old,new):
    p=root/'dsac29'/name;s=p.read_text(encoding='utf8');assert old in s,(name,old)
    s=s.replace(old,new);ast.parse(s);p.write_text(s,encoding='utf8')
change('native_guard.py',"    if req.get('operation') == 'world_session':","    if req.get('operation') == 'material_regions':\n        from .material_guard import worker as material_worker\n        return material_worker(req,result_path)\n    if req.get('operation') == 'world_session':")
change('revision_overlap.py','from .material_deltas import calculate,operate,volume','from .material_deltas import operate,volume\nfrom .material_guard import calculate_isolated as calculate')
change('revision_overlap.py','guarded_large = len(a)>=600 and len(old_ids)+len(new_ids)>=80','guarded_large = True  # every unresolved Common is isolated, including small assemblies')
change('revision_overlap.py','    ba={i:',"    if progress:progress(f'Zmiany materiału: {len(old_ids)} starych i {len(new_ids)} nowych elementów; sprawdzanie geometrii…')\n    ba={i:")
change('revision_overlap.py',"            stat['boolean_checks']+=1","            stat['boolean_checks']+=1\n            if progress:progress(f'Zmiany materiału: Common A[{i}] ↔ B[{j}], test {stat[\"boolean_checks\"]}; limit 35 s')")
change('revision_overlap.py','        try:\n            cached=best_common.get(i)',"        if progress:progress(f'Zmiany materiału: podział Common/Cut A[{i}] ↔ B[{j}]; limit 35 s')\n        try:\n            cached=best_common.get(i)")
change('revision_overlap.py',"        except Exception:\n            stat['invalid_boolean']+=1;continue","        except NativeGeometryFailure:\n            raise\n        except Exception:\n            stat['invalid_boolean']+=1;continue")
change('revision_overlap.py',"        if stat['budget_exceeded']:break","        if stat['budget_exceeded']:raise NativeGeometryFailure('Limit liczby testów materiału — analiza niekompletna')")
change('material_deltas.py','        try:out[index]=calculate(a[r.a_index],b[r.b_index],tolerance)',"        from .material_guard import calculate_isolated\n        from .native_guard import NativeGeometryFailure\n        try:out[index]=calculate_isolated(a[r.a_index],b[r.b_index],tolerance)\n        except NativeGeometryFailure:raise")
change('trace_r22.py',"_pair_enabled=os.getenv('DSCOMPARE_TRACE_BREP','0')=='1'","_pair_enabled=os.getenv('DSCOMPARE_TRACE_BREP','1')=='1'")
change('worker_v37.py','    try:\n        if ns.worker==',"    try:\n        from .process_lifetime import contain_children\n        contain_children()\n        if ns.worker==")
# Keep diagnostics useful even when no Python exception is raised.
change('diagnostics.py',"        faulthandler.enable(file=_log_file,all_threads=True)","        _log_file.write('Uruchomiono DS Compare. Postęp analizy: folder wyników / _ETAPY_DIAGNOSTYKA.jsonl\\n')\n        faulthandler.enable(file=_log_file,all_threads=True)")
print('Stability patch applied')
