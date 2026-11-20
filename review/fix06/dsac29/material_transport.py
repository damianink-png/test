"""Exchange computed OCCT Boolean results without decimal conversion."""
from pathlib import Path
from OCP.BinTools import BinTools
from OCP.TopoDS import TopoDS_Shape
from .brep_transport import read_brep


def write_result(shape, path):
    if not BinTools.Write_s(shape, str(path)):
        raise ValueError('Nie udało się zapisać wyniku B-Rep')


def read_result(path):
    # Older diagnostic workers can still supply an ASCII BRepTools file.
    with Path(path).open('rb') as stream:
        binary = stream.read(64).lstrip().startswith(b'Open CASCADE Topology ')
    if not binary:
        return read_brep(path)
    shape = TopoDS_Shape()
    if not BinTools.Read_s(shape, str(path)) or shape.IsNull():
        raise ValueError('Nie udało się odczytać wyniku B-Rep')
    return shape
