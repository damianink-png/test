from pathlib import Path
import json
import numpy as np
from dsac29.mesh_v37 import make_mesh
from dsac29.worker_v37 import main as worker_main

ROOT=Path(__file__).resolve().parents[1]

def test_all_test_solids_are_meshed_without_global_cap(tmp_path):
    data=make_mesh(ROOT/'samples/MODEL_B.step',tmp_path/'all.npz','szybka')
    assert data['kompletne'] is True
    assert data['bryly']==4
    with np.load(tmp_path/'all.npz') as arr:
        assert len(arr['offsets'])==5
        assert len(arr['colors'])==4
        assert arr['offsets'][-1]==len(arr['vertices'])
        assert len(arr['vertices'])%3==0


def test_worker_step_color_roundtrip_ap214(tmp_path):
    output=tmp_path/'job'
    rc=worker_main(['--worker','compare','--a',str(ROOT/'samples/MODEL_A.step'),
      '--b',str(ROOT/'samples/MODEL_B.step'),'--output',str(output),
      '--generate-step','--schema','AP214IS'])
    assert rc==0
    diag=json.loads((output/'DIAGNOSTYKA_KOLOROW.json').read_text(encoding='utf-8'))
    assert diag['pokolorowane_etykiety']>=4
    assert diag['pokolorowane_powierzchnie']>0
    assert diag['rekordy_kolorow_step']>=3
    result=json.loads((output/'_WYNIK_V37.json').read_text(encoding='utf-8'))
    assert result['ok']
