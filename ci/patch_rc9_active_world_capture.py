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

    Uses a complete-generation marker and already-serialized B-Rep bytes. This is
    evidence only; never returns a geometry verdict.
    """
    if os.getenv('DSCOMPARE_CAPTURE_ACTIVE_BREP','0')!='1':return
    from . import trace_r22 as trace
    if trace._path is None:return
    import shutil
    import tempfile
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
            # Publish a complete generation directory only after both inputs
            # and the metadata are durable. No reader can see mixed pairs.
            generation = destination / f'capture_{os.getpid()}_{count}'
            with tempfile.TemporaryDirectory(prefix='.capture_', dir=destination) as tmp:
                staging = Path(tmp)
                for name in ('A', 'B'):
                    shutil.copyfile(Path(root) / (name + '.brep'), staging / (name + '.brep'))
                metadata = {'sequence': count, 'pid': os.getpid(),
                            'a_path': str(a.path), 'b_path': str(b.path),
                            'tolerance_mm': float(tolerance)}
                (staging / 'metadata.json').write_text(
                    json.dumps(metadata, ensure_ascii=False), encoding='utf-8')
                # TemporaryDirectory cannot be renamed while its context owns
                # it on Windows; copy into a unique final generation instead.
                generation.mkdir(exist_ok=False)
                try:
                    for name in ('A.brep', 'B.brep', 'metadata.json'):
                        shutil.copyfile(staging / name, generation / name)
                    (generation / 'COMPLETE').write_text('1', encoding='ascii')
                except BaseException:
                    shutil.rmtree(generation, ignore_errors=True)
                    raise
            # The marker is written last, so incomplete generations are ignored.
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
