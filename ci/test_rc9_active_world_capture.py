"""Regression: crash evidence is a ring of exact B-Rep bytes, not a proof."""
import json,os,sys,tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'dscompare_rc9_manual'))
from dsac29 import native_guard,trace_r22

with tempfile.TemporaryDirectory(prefix='rc9_active_world_') as td:
    root=Path(td);inputs=root/'input';inputs.mkdir()
    trace_r22._path=root/'comparison'/'_ETAPY_DIAGNOSTYKA.jsonl'
    trace_r22._path.parent.mkdir()
    target=trace_r22._path.parent/'FAILED_BREP'/'active_world'
    with patch.dict(os.environ,{'DSCOMPARE_CAPTURE_ACTIVE_BREP':'0'}):
        (inputs/'A.brep').write_bytes(b'untouched-A')
        (inputs/'B.brep').write_bytes(b'untouched-B')
        native_guard._capture_active_world(inputs,SimpleNamespace(path='a'),SimpleNamespace(path='b'),.01)
        assert not target.exists()
    with patch.dict(os.environ,{'DSCOMPARE_CAPTURE_ACTIVE_BREP':'1'}):
        for n in range(3):
            left=f'BRep A #{n}'.encode();right=f'BRep B #{n}'.encode()
            (inputs/'A.brep').write_bytes(left)
            (inputs/'B.brep').write_bytes(right)
            native_guard._capture_active_world(inputs,SimpleNamespace(path=f'A[{n}]'),SimpleNamespace(path=f'B[{n}]'),.01)
            meta=json.loads((target/'current.json').read_text(encoding='utf-8'))
            assert meta['tolerance_mm']==.01
            assert meta['a_path']==f'A[{n}]' and meta['b_path']==f'B[{n}]'
            slot=meta['slot']
            assert (target/f'slot{slot}_A.brep').read_bytes()==left
            assert (target/f'slot{slot}_B.brep').read_bytes()==right
        assert (target/'slot0_A.brep').read_bytes()==b'BRep A #1'
        assert (target/'slot1_A.brep').read_bytes()==b'BRep A #2'
print('PASS: latest native B-Rep pair preserved across crash; 0.01 mm unchanged')
