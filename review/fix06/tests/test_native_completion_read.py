"""Windows completion mailbox retry is bounded and fail-closed."""
import json
import tempfile
from pathlib import Path
import pytest
from dsac29.native_session import WorldSession
from dsac29.native_guard import NativeGeometryFailure

class LiveChild:
    def poll(self): return None
    def terminate(self): pass
    def wait(self, **kwargs): return 0

@pytest.mark.parametrize("failures,expected", [(2,True),(1000,False)])
def test_completion_read_lock(tmp_path,monkeypatch,failures,expected):
    session=WorldSession()
    session.directory=tempfile.TemporaryDirectory(dir=tmp_path)
    session.process=LiveChild()
    root=Path(session.directory.name)
    request=tmp_path/"request.json";request.write_text("{}")
    reply=tmp_path/"reply.json";reply.write_text("{}")
    completion=root/"completed_00000001.json"
    completion.write_text(json.dumps({"sequence":1}))
    original=Path.read_text
    attempts=[0]
    def read(self,*args,**kwargs):
        if self==completion and attempts[0]<failures:
            attempts[0]+=1
            raise PermissionError(13,"Windows temporary sharing violation")
        return original(self,*args,**kwargs)
    monkeypatch.setattr(Path,"read_text",read)
    try:
        if expected:
            session.execute(request,reply,2)
            assert attempts[0]==failures
        else:
            with pytest.raises(NativeGeometryFailure,match="potwierdzenie"):
                session.execute(request,reply,2)
            assert session.process is None
    finally:
        session.close()
