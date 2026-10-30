"""Regression: invalid Common must terminate isolated worker with explicit error.

This exercises the child error path without performing a dangerous OCCT
Boolean or changing any SAME/MOVED/material classification.
"""
import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'dscompare_rc9_manual'))
from dsac29 import native_guard
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox

class ImmediateExit(BaseException):
    def __init__(self, code):
        self.code=code

with tempfile.TemporaryDirectory(prefix='rc9_common_failfast_test_') as td:
    root=Path(td)
    request=root/'request.json'
    reply=root/'reply.json'
    request.write_text(json.dumps({
        'operation':'common','a':str(root/'A.brep'),'b':str(root/'B.brep'),
        'tolerance':0.01,'common_shape':str(root/'common.brep')
    }),encoding='utf-8')
    from dsac29 import material_deltas
    # Exercise the real analytic pre-check with valid OCCT shapes, rather than
    # passing Python objects that the BRepCheck_Analyzer cannot inspect.
    # The identical solids must not qualify for the changed-bore fast path.
    valid_shape=BRepPrimAPI_MakeBox(10,10,10).Shape()
    with patch.object(native_guard,'_load_brep',return_value=valid_shape), \
         patch.object(material_deltas,'operate',side_effect=RuntimeError('invalid signed volume -122.58')) as mocked_operate, \
         patch.object(native_guard.os,'_exit',side_effect=lambda code: (_ for _ in ()).throw(ImmediateExit(code))):
        try:
            native_guard.worker(str(request),str(reply))
            raise AssertionError('Failed Common worker unexpectedly returned success')
        except ImmediateExit as exc:
            assert exc.code==70,exc.code
    mocked_operate.assert_called_once()
    data=json.loads(reply.read_text(encoding='utf-8'))
    assert data['ok'] is False,data
    assert 'invalid signed volume' in data['error'],data
    assert reply.with_suffix('.phase').read_text(encoding='utf-8')=='common_rejected'
    assert not (root/'common.brep').exists()
print('PASS: invalid Common fails closed and exits without native teardown')
