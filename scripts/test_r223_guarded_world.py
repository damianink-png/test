"""R22.3 guard regression: native crashes and timeout never mean SAME."""
import sys
import pytest
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCP.gp import gp_Pnt
from dsac29.geometry import describe
from dsac29.native_guard import guarded_world_reexport, NativeGeometryFailure

def solid(width=10, origin=0):
    return describe(BRepPrimAPI_MakeBox(
        gp_Pnt(float(origin),0,0), float(width), 10., 10.).Shape(),
        'piece', 'test')

def test_world_proof():
    assert guarded_world_reexport(solid(),solid(),.01) is True
    assert guarded_world_reexport(solid(),solid(11),.01) is False

def test_child_crash(tmp_path):
    script=tmp_path/'fail.py'
    script.write_text('import sys;sys.exit(77)',encoding='utf-8')
    with pytest.raises(NativeGeometryFailure,match='77'):
        guarded_world_reexport(solid(),solid(),.01,
                               process_args=[sys.executable,str(script)])

def test_timeout(tmp_path):
    script=tmp_path/'sleep.py'
    script.write_text('import time;time.sleep(15)',encoding='utf-8')
    with pytest.raises(NativeGeometryFailure,match='Timeout'):
        guarded_world_reexport(solid(),solid(),.01,
            process_args=[sys.executable,str(script)],timeout_s=.2)

def test_invalid_payload(tmp_path):
    script=tmp_path/'bad.py'
    script.write_text('import sys,json;open(sys.argv[-1],"w").write(json.dumps({"ok": True,"match":"yes"}))',encoding='utf-8')
    with pytest.raises(NativeGeometryFailure,match='Nieprawidłowy'):
        guarded_world_reexport(solid(),solid(),.01,
            process_args=[sys.executable,str(script)])
