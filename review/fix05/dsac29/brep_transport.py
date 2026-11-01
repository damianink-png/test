"""Native filename B-Rep I/O; no C++ stream callbacks into Python buffers.

Transport never proves equality or repairs topology. Callers must independently
validate geometry after loading. Native APIs also retain Unicode path support.
"""
from pathlib import Path

def write_brep(shape,path):
    from OCP.BRepTools import BRepTools
    path=Path(path)
    if BRepTools.Write_s(shape,str(path)) is False or not path.is_file() or not path.stat().st_size:
        raise ValueError('Nie można zapisać geometrii B-Rep')

def read_brep(path):
    from OCP.BRepTools import BRepTools
    from OCP.TopoDS import TopoDS_Shape
    from OCP.BRep import BRep_Builder
    shape=TopoDS_Shape()
    if BRepTools.Read_s(shape,str(Path(path)),BRep_Builder()) is False or shape.IsNull():
        raise ValueError('Nie można odczytać bryły B-Rep w odizolowanym procesie')
    return shape
