"""R11.28: StageWriter progress telemetry must never crash the CAD analysis.

Windows may temporarily deny os.replace if Explorer, indexing, antivirus, or
an external file watcher holds _ETAPY.json open without FILE_SHARE_DELETE.
Use a process-unique temp file and retry. This is optional UX telemetry:
failed writes are reported as best effort without aborting geometry/export.
"""
from pathlib import Path
import os
src=Path(os.environ["DS_COMPARE_SOURCE"])/"dsac29/stage_fast.py"
text=src.read_text("utf8")
a=text.index("from __future__ import annotations")
text=text[:a]+'''from __future__ import annotations
import json, os, time, tempfile
from pathlib import Path


class StageWriter:
    def __init__(self,folder):
        self.path=Path(folder)/'_ETAPY.json'
        self.values={'step':'oczekuje','reports':'oczekuje','report_percent':0}
        self.errors=0

    def update(self,**changes):
        if all(self.values.get(k)==v for k,v in changes.items()):
            return
        self.values.update(changes)
        payload=json.dumps(self.values,ensure_ascii=False)
        # Never reuse a constant _ETAPY.json.tmp; two writers may collide.
        # tempfile.mkstemp creates a unique file in the same directory,
        # so os.replace stays atomic on Windows/NTFS.
        tmp=None
        try:
            fd,tmp=tempfile.mkstemp(prefix='_ETAPY_',suffix='.tmp',dir=str(self.path.parent))
            with os.fdopen(fd,'w',encoding='utf8') as stream:
                stream.write(payload)
            for attempt in range(5):
                try:
                    os.replace(tmp,self.path)
                    tmp=None
                    return
                except (PermissionError, OSError):
                    # A sharing violation is usually transient.
                    if attempt<4:time.sleep(0.035*(attempt+1))
            self.errors+=1
        except OSError:
            self.errors+=1
        finally:
            if tmp is not None:
                try:Path(tmp).unlink(missing_ok=True)
                except OSError:pass
        # No exception: early STEP status may not refresh, but the worker
        # still writes its real output and final report.
        return
'''
src.write_text(text,"utf8")
print("R11.28 telemetry: atomic unique temp, retries, no fatal PermissionError")
