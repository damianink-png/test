"""Exercise native B-Rep file transport alongside diagnostic heartbeat polling."""
import hashlib,threading
from pathlib import Path
from dsac29.brep_transport import write_brep,read_brep
from dsac29.geometry import describe
from dsac29.geometry_registry import GeometryRegistry
from dsac29.step_reexport_tolerance import reexport_equivalent_world
from dsac29.trace_r22 import memory_mib

ROOT=Path(__file__).parent/'fixtures/moved_reexport_insert'
def test_repeated_native_unicode_transport_keeps_original_boundaries(tmp_path):
    source=read_brep(ROOT/'A.brep');path=tmp_path/'Zażółć_模型.brep'
    stop=threading.Event();errors=[]
    def heartbeat():
        try:
            while not stop.wait(.002):memory_mib()
        except BaseException as exc:errors.append(exc)
    thread=threading.Thread(target=heartbeat);thread.start()
    try:
        write_brep(source,path);before=hashlib.sha256(path.read_bytes()).digest()
        for _ in range(40):
            write_brep(source,path)
            assert hashlib.sha256(path.read_bytes()).digest()==before
            restored=read_brep(path)
        assert reexport_equivalent_world(describe(source,'A','A'),describe(restored,'B','B'),.000001,allow_boolean=False,_original_boundary_only=True)
    finally:stop.set();thread.join(timeout=5)
    assert not thread.is_alive() and not errors

def test_definition_digest_is_local_and_geometry_sensitive():
    a=describe(read_brep(ROOT/'A.brep'),'A','A');b=describe(read_brep(ROOT/'B.brep'),'B','B')
    registry=GeometryRegistry()
    assert registry.exact_digest(a) is not None
    assert registry.exact_digest(a)!=registry.exact_digest(b)
