"""R22.3 RC3: fix Windows WinError 5 in reusable native B-Rep worker."""
from pathlib import Path
import sys

root=Path(sys.argv[1])
p=root/'dsac29/native_session.py'
s=p.read_text(encoding='utf-8')
old="""        command=root/'command.json'
        partial=root/'command.partial'
        partial.write_text(json.dumps({'sequence':self.sequence,'request':str(request),'reply':str(reply)}),encoding='utf-8')
        partial.replace(command)
"""
new="""        # Each request is immutable and has its own mailbox filename.
        # Replacing a shared command.json races the Windows reader (WinError 5).
        command=root/f'command_{self.sequence:08d}.json'
        partial=root/f'.command_{self.sequence:08d}.partial'
        try:
            partial.write_text(json.dumps({
                'sequence':self.sequence,'request':str(request),'reply':str(reply)
            }), encoding='utf-8')
            deadline=time.monotonic()+1.0
            while True:
                try:
                    partial.replace(command)
                    break
                except PermissionError as exc:
                    if time.monotonic()>=deadline:
                        raise NativeGeometryFailure(
                            'Nie mozna opublikowac polecenia B-Rep (WinError 5)'
                        ) from exc
                    time.sleep(.02)
        except BaseException:
            self.close()
            raise
"""
assert s.count(old)==1,'Original IPC writer differs from audited R22.3 RC2'
s=s.replace(old,new)
old2="""    command=Path(directory)/'command.json';last=0
    while True:
        try:payload=json.loads(command.read_text(encoding='utf-8'))
        except FileNotFoundError:
            time.sleep(.01);continue
        if payload['sequence']<=last:
            time.sleep(.01);continue
        worker(payload['request'],payload['reply'])
        last=payload['sequence']
"""
new2="""    # Read each immutable command once, in strict sequence order.
    root=Path(directory);last=0
    while True:
        next_number=last+1
        command=root/f'command_{next_number:08d}.json'
        try:
            payload=json.loads(command.read_text(encoding='utf-8'))
        except FileNotFoundError:
            time.sleep(.01)
            continue
        except PermissionError:
            time.sleep(.02)
            continue
        if payload.get('sequence') != next_number:
            raise ValueError('Nieprawidlowa kolejnosc zadan B-Rep')
        worker(payload['request'],payload['reply'])
        last=next_number
"""
assert s.count(old2)==1,'Original IPC reader differs from audited R22.3 RC2'
p.write_text(s.replace(old2,new2),encoding='utf-8')
test=root/'tests/test_r223_rc3_ipc.py'
test.write_text('''"""Windows-native B-Rep mailbox regression tests."""
from pathlib import Path
import pytest
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from dsac29.geometry import describe
from dsac29.native_guard import guarded_world_reexport, NativeGeometryFailure
from dsac29.native_session import world_session, WorldSession, current

def solid(x=8):
    return describe(BRepPrimAPI_MakeBox(x,11,17).Shape(),'x','x')

def test_many_requests_immutable_mailbox_and_recycle():
    a=solid();b=solid();different=solid(9)
    with world_session() as session:
        session.max_requests=22
        for i in range(52):
            assert guarded_world_reexport(a, b if i%3 else different,.01) is (i%3!=0)
        assert session.starts==3
        root=Path(session.directory.name)
        assert (root/'command_00000008.json').exists()
        assert not (root/'command.json').exists()
        child=session.process
    assert child.poll() is not None and current() is None

def test_no_overwrite_of_previous_commands(monkeypatch):
    original=Path.replace
    def reject_existing(self,target):
        if Path(target).exists():
            raise PermissionError('sharing violation')
        return original(self,target)
    monkeypatch.setattr(Path,'replace',reject_existing)
    with world_session() as session:
        a=solid()
        for _ in range(4):assert guarded_world_reexport(a,a,.01)
        assert (Path(session.directory.name)/'command_00000004.json').exists()

def test_bad_request_aborts_without_false_match(tmp_path):
    req=tmp_path/'request.json';req.write_text('{}',encoding='utf8')
    session=WorldSession()
    try:
        with pytest.raises(NativeGeometryFailure):
            session.execute(req,tmp_path/'reply.json',3)
        assert session.process is None
    finally:session.close()
''',encoding='utf-8')
runner=root/'TESTUJ.py'
t=runner.read_text(encoding='utf-8')
assert "tests=['test_r223_rc2.py'" in t,'Regression suite layout differs from audited R22.3 RC2'
runner.write_text(t.replace("tests=['test_r223_rc2.py'","tests=['test_r223_rc3_ipc.py','test_r223_rc2.py'"),encoding='utf-8')
print('Applied R22.3 RC3 WinError 5 IPC fix to',root)
