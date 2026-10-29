"""Capture the last two native STEP proof inputs before an access violation.

Diagnostics only: no changes to B-Rep proofs, tolerance, or matching.
"""
from pathlib import Path
import ast

root=Path(__file__).resolve().parents[1]/'dscompare_rc9_manual'
path=root/'dsac29'/'native_guard.py'
s=path.read_text(encoding='utf-8')
anchor='\ndef _load_brep(path):\n'
assert s.count(anchor)==1, 'Unexpected native_guard anchor'
insert='''
_active_capture_counter=0
_active_capture_lock=__import__('threading').Lock()

def _capture_active_world(root,a,b,tolerance):
    """Durably keep the last two world-proof requests for native crash analysis.

    Uses locked two-slot updates and already-serialized B-Rep bytes. This is
    evidence only; never returns a geometry verdict.
    """
    if os.getenv('DSCOMPARE_CAPTURE_ACTIVE_BREP','0')!='1':return
    from . import trace_r22 as trace
    if trace._path is None:return
    import shutil
    global _active_capture_counter
    # Keep both B-Rep files and their metadata as one synchronized snapshot.
    # Without this lock another thread could overwrite a slot midway and
    # leave a mismatched A/B pair in the crash evidence.
    with _active_capture_lock:
        _active_capture_counter += 1
        count = _active_capture_counter
        slot = count % 2
        destination = trace._path.parent / 'FAILED_BREP' / 'active_world'
        try:
            destination.mkdir(parents=True, exist_ok=True)
            # Keep the existing two-slot evidence format for CI readers.
            # Remove the completion marker before overwriting either input.
            marker = destination / f'slot{slot}.complete'
            marker.unlink(missing_ok=True)
            for name in ('A', 'B'):
                temporary = destination / f'.slot{slot}_{name}_{count}.partial'
                try:
                    shutil.copyfile(Path(root) / (name + '.brep'), temporary)
                    os.replace(temporary, destination / f'slot{slot}_{name}.brep')
                finally:
                    temporary.unlink(missing_ok=True)
            metadata = {'sequence': count, 'slot': slot,
                        'a_path': str(a.path), 'b_path': str(b.path),
                        'tolerance_mm': float(tolerance)}
            temporary = destination / f'.current_{count}.partial'
            try:
                temporary.write_text(json.dumps(metadata, ensure_ascii=False), encoding='utf-8')
                os.replace(temporary, destination / 'current.json')
            finally:
                temporary.unlink(missing_ok=True)
            marker.write_text(str(count), encoding='ascii')
        except (OSError, ValueError, TypeError, AttributeError) as exc:
            trace.mark('native_world_capture', 'ERROR', reason=str(exc), sequence=count)
'''
s=s.replace(anchor,'\n'+insert+anchor)
anchor2="""        argv = process_args or (
            [sys.executable, '--native-brep-compare'] if getattr(sys, 'frozen', False)
            else [sys.executable, '-m', 'dsac29.native_guard'])
        trace.mark('native_world', 'BEGIN', timeout_s=timeout_s)"""
new2="""        # Save current B-Rep pair BEFORE a possible native access violation.
        _capture_active_world(root,a,b,tolerance)
        argv = process_args or (
            [sys.executable, '--native-brep-compare'] if getattr(sys, 'frozen', False)
            else [sys.executable, '-m', 'dsac29.native_guard'])
        trace.mark('native_world', 'BEGIN', timeout_s=timeout_s)"""
assert s.count(anchor2)==1, 'Unexpected world proof anchor'
s=s.replace(anchor2,new2)
ast.parse(s)
path.write_text(s,encoding='utf-8')
print('RC9 active native B-Rep ring installed; opt-in diagnostic only')
