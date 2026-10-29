"""Regression checks for the XCAF local-definition cache."""
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from openassembly.stepio import _measure, _local_measure

def test_cached_measure_matches_uncached():
    shape = BRepPrimAPI_MakeBox(10., 20., 30.).Shape()
    local = _local_measure(shape)
    assert _measure(shape, shape) == _measure(shape, shape, local)

def test_repeated_definition_reuses_local_geometry(monkeypatch):
    from openassembly import stepio
    shape = BRepPrimAPI_MakeBox(10., 20., 30.).Shape()
    data = stepio._local_measure(shape)
    original = stepio._local_measure
    def forbidden(*args, **kwargs):
        raise AssertionError("local geometry recalculated for cached occurrence")
    monkeypatch.setattr(stepio, "_local_measure", forbidden)
    try:
        assert stepio._measure(shape, shape, data)[0] == 6000.
    finally:
        monkeypatch.setattr(stepio, "_local_measure", original)
