"""Guardrails for STEP/B-Rep memory, geometry and source parameters."""
import hashlib
from pathlib import Path
from types import SimpleNamespace
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from dsac29.geometry import describe
from dsac29.geometry_registry import GeometryRegistry
from dsac29 import revision_overlap
from dsac29.step_io import ColoredDocument


def test_revision_score_rejects_impossible_positive_common():
    old=SimpleNamespace(volume=1000.0)
    new=SimpleNamespace(volume=1200.0)
    assert revision_overlap._score(1000.,old,new,True) is not None
    assert revision_overlap._score(1100.,old,new,True) is None
    assert revision_overlap._score(1000.00001,old,new,True) is not None
    assert revision_overlap._score(float('inf'),old,new,True) is None


def test_registry_streams_brep_digest_without_read_bytes(monkeypatch):
    original=Path.read_bytes
    def deny_brep_read_bytes(p):
        if p.suffix=='.brep':
            raise AssertionError('BRep must be hashed in bounded blocks')
        return original(p)
    monkeypatch.setattr(Path,'read_bytes',deny_brep_read_bytes)
    shape=BRepPrimAPI_MakeBox(4.,6.,8.).Shape()
    p=describe(shape,'part','part')
    registry=GeometryRegistry()
    expected=registry.exact_digest(p)
    assert isinstance(expected,bytes) and len(expected)==32
    assert registry.exact_digest(p)==expected
    assert registry.stats['serializations']==1
    assert registry.stats['digest_cache_hits']==1


def test_export_fingerprint_allows_large_exact_brep(monkeypatch):
    from OCP import BRepTools as native
    class Serializer:
        @staticmethod
        def Write_s(shape,path):
            with open(path,'wb') as output:
                for _ in range(5):output.write(b'X'*1024*1024)
            return True
    monkeypatch.setattr(native,'BRepTools',Serializer)
    size,digest=ColoredDocument._serialized_brep_signature(object())
    assert size==5*1024*1024
    assert digest==hashlib.sha256(b'X'*(5*1024*1024)).digest()


def test_export_fingerprint_refuses_unbounded_brep(monkeypatch):
    from OCP import BRepTools as native
    class Serializer:
        @staticmethod
        def Write_s(shape,path):
            with open(path,'wb') as output:
                for _ in range(33):output.write(b'X'*1024*1024)
            return True
    monkeypatch.setattr(native,'BRepTools',Serializer)
    assert ColoredDocument._serialized_brep_signature(object()) is None


def test_cli_rejects_nonfinite_inputs_before_touching_files(tmp_path):
    import pytest
    from dsac29.cli import process
    source=tmp_path/'does_not_exist.step'
    for option,value in [
        ('tolerance',float('nan')),('tolerance',float('inf')),
        ('tolerance',0.0),('density',float('nan')),
        ('density',-1.),('density',float('inf')),
        ('old_alpha',float('nan')),('old_alpha',1.5),
        ('max_solids',0),('max_solids',True),
    ]:
        with pytest.raises(ValueError):
            process(source,source,tmp_path/'results',progress=None,**{option:value})
    assert not (tmp_path/'results').exists()


def test_revision_proof_cache_is_real_function_local_not_commented_out():
    """Catch escaped-newline edits that hide the cache assignment in a comment.

    A syntax-only compilation passes even when a referenced local becomes an
    undefined global; this guard catches that packaging-wide regression early.
    Functional tests in test_revision_overlap_policy cover the actual path.
    """
    fn=revision_overlap._merge_material_revisions_strict
    assert 'common_cache' in fn.__code__.co_varnames
