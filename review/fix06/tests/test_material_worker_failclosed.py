"""Regression: malformed material topology must never produce PyInstaller exception popup."""
import json
import pytest
from dsac29 import native_guard, material_guard
from dsac29.brep_safety import UnprovenRepair


def test_isolated_material_repair_failure_is_serialized(monkeypatch, tmp_path):
    request = tmp_path / 'request.json'
    response = tmp_path / 'reply.json'
    request.write_text(json.dumps({'operation':'material_regions','root':str(tmp_path)}))
    def bad_worker(req, path):
        raise UnprovenRepair('_shape_fix: Repaired topology still invalid; _wire_fix: No invalid wire could be repaired')
    monkeypatch.setattr(material_guard, 'worker', bad_worker)
    class ExitCalled(Exception):
        pass
    def exit_worker(code):
        assert code == 70
        raise ExitCalled()
    monkeypatch.setattr(native_guard.os, '_exit', exit_worker)
    with pytest.raises(ExitCalled):
        native_guard.worker(request, response)
    payload = json.loads(response.read_text(encoding='utf-8'))
    assert payload['ok'] is False
    assert payload['error_code'] == 'INVALID_BREP_AFTER_REPAIR'
    assert 'Repaired topology still invalid' in payload['error']


def test_isolated_material_invalid_input_never_passes_as_success(monkeypatch, tmp_path):
    request=tmp_path/'request.json';response=tmp_path/'reply.json'
    request.write_text(json.dumps({'operation':'material_regions','root':str(tmp_path)}))
    def bad_worker(req,path):
        raise ValueError('Corrupt input B-Rep')
    monkeypatch.setattr(material_guard,'worker',bad_worker)
    class ExitCalled(Exception): pass
    monkeypatch.setattr(native_guard.os,'_exit',lambda code: (_ for _ in ()).throw(ExitCalled()))
    with pytest.raises(ExitCalled): native_guard.worker(request,response)
    assert json.loads(response.read_text())['ok'] is False


def test_isolated_child_exits_70_without_traceback(tmp_path):
    import subprocess,sys,os
    request=tmp_path/'request.json';response=tmp_path/'reply.json'
    request.write_text(json.dumps({'operation':'material_regions','root':str(tmp_path)}))
    script="""from dsac29 import native_guard,material_guard
from dsac29.brep_safety import UnprovenRepair
def invalid(req,path):
    raise UnprovenRepair('_shape_fix: Repaired topology still invalid')
material_guard.worker=invalid
native_guard.worker(__import__('sys').argv[1],__import__('sys').argv[2])
"""
    p=subprocess.run([sys.executable,'-c',script,str(request),str(response)],
                     capture_output=True,text=True,timeout=20)
    assert p.returncode==70,(p.returncode,p.stderr)
    assert 'Traceback' not in p.stderr
    payload=json.loads(response.read_text(encoding='utf-8'))
    assert payload['ok'] is False and payload['error_code']=='INVALID_BREP_AFTER_REPAIR'
