"""Regression: failed native repair remains incomplete and exits promptly."""
import json,sys,tempfile
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'dscompare_rc9_manual'))
from dsac29 import native_guard,brep_safety
class ExitRequested(BaseException):
    def __init__(self,code):self.code=code
with tempfile.TemporaryDirectory(prefix='rc9_unproven_repair_') as td:
    root=Path(td);request=root/'request.json';reply=root/'reply.json'
    request.write_text(json.dumps({'operation':'world_reexport','a':str(root/'A.brep'),
        'b':str(root/'B.brep'),'tolerance':0.01,'allow_boolean':False}),encoding='utf8')
    with patch.object(native_guard,'_load_brep',side_effect=[object(),object()]), \
         patch.object(brep_safety,'is_valid',side_effect=[False,True]), \
         patch.object(brep_safety,'validated_copy',side_effect=brep_safety.UnprovenRepair('Repair increases stored vertex tolerance')), \
         patch.object(native_guard.os,'_exit',side_effect=lambda code: (_ for _ in ()).throw(ExitRequested(code))):
        try:native_guard.worker(str(request),str(reply))
        except ExitRequested as exc:assert exc.code==70,exc.code
        else:raise AssertionError('Unproven repair must not produce a successful result')
    data=json.loads(reply.read_text(encoding='utf8'))
    assert data['ok'] is False,data
    assert 'Repair increases stored vertex tolerance' in data['error'],data
    assert reply.with_suffix('.phase').read_text(encoding='utf8')=='repair_rejected'
    assert 'match' not in data
print('PASS: rejected repair cannot become SAME; isolated worker exits immediately')
