"""STEP round-trip: count, names, positions and fail-closed negative controls."""
import numpy as np
import pytest
from dataclasses import replace
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from dsac29.geometry import describe
from dsac29.alignment import _relocate
from dsac29.aligned_step_restart import save_aligned_step_and_reload, _match_imported


def _assembly():
    parts=[]
    for i in range(5):
        shape=BRepPrimAPI_MakeBox(10.+i, 15., 7.).Shape()
        original=describe(shape, 'plate' if i<3 else 'gusset',
                          f'ROOT/item_{i}', 'original.step')
        parts.append(_relocate(original,np.eye(3),
                               np.array([float(i*40+1200),-400.,200.])))
    return parts


def test_roundtrip_reimports_and_restores_metadata(tmp_path):
    parts=_assembly()
    result,path,stats=save_aligned_step_and_reload(parts,tmp_path,0.01)
    assert path.is_file() and path.stat().st_size>500
    assert stats['solids_expected']==stats['solids_reimported']==len(parts)
    assert sorted(p.path for p in result)==sorted(p.path for p in parts)
    assert sorted(p.source for p in result)==sorted(p.source for p in parts)
    for a in parts:
        b=next(x for x in result if x.path==a.path)
        assert np.linalg.norm(a.center-b.center)<.001
        assert abs(a.volume-b.volume)<.001


def test_roundtrip_refuses_missing_occurrence():
    parts=_assembly()
    with pytest.raises(RuntimeError,match='liczba brył'):
        _match_imported(parts,parts[:-1],.01)


def test_roundtrip_refuses_wrong_geometry_metadata():
    parts=_assembly()
    changed=list(parts)
    changed[0]=replace(changed[0],volume=changed[0].volume+100)
    with pytest.raises(RuntimeError,match='brak jednoznacznie'):
        _match_imported(parts,changed,.01)
