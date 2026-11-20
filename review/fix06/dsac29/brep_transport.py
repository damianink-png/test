"""Exchange OCCT shapes without decimal conversion."""
from pathlib import Path
import hashlib
from OCP.BinTools import BinTools
from OCP.TopoDS import TopoDS_Shape
from OCP.BRep import BRep_Builder
from OCP.BRepTools import BRepTools


def write_brep(shape, path):
    if not BinTools.Write_s(shape, str(path)):
        raise ValueError('Nie udało się zapisać wyniku B-Rep')


def read_brep(path):
    # Older diagnostic workers can still supply an ASCII BRepTools file.
    with Path(path).open('rb') as stream:
        binary = stream.read(64).lstrip().startswith(b'Open CASCADE Topology ')
    shape = TopoDS_Shape()
    ok = (BinTools.Read_s(shape, str(path)) if binary else
          BRepTools.Read_s(shape, str(path), BRep_Builder()))
    if not ok or shape.IsNull():
        raise ValueError('Nie udało się odczytać wyniku B-Rep')
    return shape


def brep_digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()
