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
    with patch.object(native_guard,'_load_brep',return_value=object()), \
         patch.object(material_deltas,'operate',side_effect=RuntimeError('invalid signed volume -122.58')), \
         patch.object(native_guard.os,'_exit',side_effect=lambda code: (_ for _ in ()).throw(ImmediateExit(code))):
        try:
            native_guard.worker(str(request),str(reply))
            raise AssertionError('Failed Common worker unexpectedly returned success')
        except ImmediateExit as exc:
            assert exc.code==70,exc.code
    data=json.loads(reply.read_text(encoding='utf-8'))
    assert data['ok'] is False,data
    assert 'invalid signed volume' in data['error'],data
    assert reply.with_suffix('.phase').read_text(encoding='utf-8')=='common_rejected'
    assert not (root/'common.brep').exists()
print('PASS: invalid Common fails closed and exits without native teardown')
