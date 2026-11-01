"""Windows cleanup regression: requests must never own a live session logger."""
import json,subprocess,sys,tempfile
from pathlib import Path
import pytest
from dsac29.native_session import WorldSession,world_session
from dsac29.native_guard import NativeGeometryFailure


def test_real_worker_keeps_diagnostics_out_of_disposable_requests(tmp_path):
    from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
    from dsac29.brep_transport import write_brep
    shape=BRepPrimAPI_MakeBox(8,11,17).Shape()
    with world_session() as session:
        session.max_requests=40
        for i in range(24):
            with tempfile.TemporaryDirectory(dir=tmp_path) as name:
                root=Path(name);write_brep(shape,root/'A.brep');write_brep(shape,root/'B.brep')
                request=root/'request.json';reply=root/'reply.json'
                request.write_text(json.dumps({'operation':'world_reexport','a':str(root/'A.brep'),'b':str(root/'B.brep'),'tolerance':.01,'allow_boolean':False}))
                session.execute(request,reply,10)
                assert json.loads(reply.read_text())=={'ok':True,'match':True}
                assert not (root/'_ETAPY_DIAGNOSTYKA.jsonl').exists()
                assert not (root/'AWARIA_PYTHON_FAULTHANDLER.txt').exists()
            assert not root.exists()
        journal=Path(session.directory.name)/'_ETAPY_DIAGNOSTYKA.jsonl'
        events=[json.loads(line) for line in journal.read_text().splitlines()]
        assert sum(e['stage']=='worker' and e['event']=='BEGIN' for e in events)==1
        child=session.process;session_path=Path(session.directory.name)
    assert child.poll() is not None and not session_path.exists()


def test_parent_waits_for_request_completion_after_early_reply(tmp_path,monkeypatch):
    # A deterministic transport-only child publishes its reply, then performs
    # another request write. The parent must not return/delete the folder yet.
    script='''import json,time,sys
from pathlib import Path
from dsac29 import native_guard,trace_r22
from dsac29.native_session import serve
root=Path(sys.argv[1]);trace_r22.setup(root)
def late_write(request,reply,**kwargs):
 Path(reply).write_text(json.dumps({'ok':True,'match':False}))
 time.sleep(.2)
 Path(request).with_name('last_write_finished').write_text('finished')
native_guard.worker=late_write
serve(root)
'''
    def start(session):
        session.close();session.directory=tempfile.TemporaryDirectory(dir=tmp_path)
        session.process=subprocess.Popen([sys.executable,'-c',script,session.directory.name],stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
        session.sequence=0;session.starts+=1
    monkeypatch.setattr(WorldSession,'_start',start)
    session=WorldSession()
    try:
        with tempfile.TemporaryDirectory(dir=tmp_path) as name:
            root=Path(name);request=root/'request.json';request.write_text('{}')
            session.execute(request,root/'reply.json',5)
            assert (root/'last_write_finished').read_text()=='finished'
            assert json.loads((root/'reply.json').read_text())['match'] is False
        assert not root.exists()
    finally:session.close()


class DummyProcess:
    def __init__(self):self.returncode=None
    def poll(self):return self.returncode
    def terminate(self):self.returncode=0
    def wait(self,**kw):return self.returncode
    def kill(self):self.returncode=-1


@pytest.mark.parametrize('completion',[{'sequence':9},{'sequence':True},{},[]])
def test_bad_completion_cannot_commit_a_reply(tmp_path,completion):
    session=WorldSession();session.directory=tempfile.TemporaryDirectory(dir=tmp_path);session.process=DummyProcess()
    root=Path(session.directory.name);request=tmp_path/'request.json';request.write_text('{}');reply=tmp_path/'reply.json';reply.write_text('{"ok":true,"match":true}')
    (root/'completed_00000001.json').write_text(json.dumps(completion))
    try:
        with pytest.raises(NativeGeometryFailure,match='potwierdzenie'):session.execute(request,reply,1)
        assert session.process is None and session.directory is None
    finally:session.close()


def test_failed_child_preserves_journal_after_stopping(tmp_path):
    session=WorldSession();session.directory=tempfile.TemporaryDirectory(dir=tmp_path);process=DummyProcess();session.process=process
    root=Path(session.directory.name);(root/'_ETAPY_DIAGNOSTYKA.jsonl').write_text('failure evidence\n')
    request=tmp_path/'request.json';request.write_text('{}');reply=tmp_path/'reply.json'
    try:
        with pytest.raises(NativeGeometryFailure,match='Timeout'):session.execute(request,reply,.025)
        assert process.returncode==0 and session.process is None
        assert (tmp_path/'NATIVE_SESSION_DIAGNOSTYKA.jsonl').read_text()=='failure evidence\n'
        assert not root.exists()
    finally:session.close()
