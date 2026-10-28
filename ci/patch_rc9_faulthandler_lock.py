"""Keep faulthandler's Windows file handle outside disposable test/work folders.

On Windows an open faulthandler log prevents TemporaryDirectory cleanup.
The crash log must survive a worker crash, so use a persistent per-process file.
This patch changes diagnostics only, never geometry or classification.
"""
from pathlib import Path
import os
import tempfile

target = Path(__file__).resolve().parents[1] / "dscompare_rc9_manual" / "dsac29" / "trace_r22.py"
src = target.read_text(encoding="utf-8")
old = """        _fault_log=open(output/'AWARIA_PYTHON_FAULTHANDLER.txt','a',encoding='utf-8',buffering=1)"""
new = """        # Keep the live Windows handle outside disposable output/test folders.
        # A running worker may outlive the session and lock TemporaryDirectory.
        if os.name == 'nt':
            from datetime import datetime
            diagnostic_dir = Path(os.environ.get('LOCALAPPDATA') or tempfile.gettempdir()) / 'DSCompare' / 'logs'
            diagnostic_dir.mkdir(parents=True, exist_ok=True)
            fault_path = diagnostic_dir / ('AWARIA_PYTHON_FAULTHANDLER_%s_%s.txt' %
                                           (os.getpid(), datetime.now().strftime('%Y%m%d_%H%M%S_%f')))
        else:
            fault_path = output / 'AWARIA_PYTHON_FAULTHANDLER.txt'
        _fault_log=open(fault_path,'a',encoding='utf-8',buffering=1)"""
if src.count(old) != 1:
    raise SystemExit("Unexpected trace_r22.py version: refusing to patch")
target.write_text(src.replace(old, new), encoding="utf-8")
print("Patched faulthandler log location:", target)
