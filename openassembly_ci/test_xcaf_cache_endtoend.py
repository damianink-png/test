"""End-to-end proof that repeated XCAF occurrences reuse a single definition."""
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCP.XCAFDoc import XCAFDoc_DocumentTool
from OCP.STEPCAFControl import STEPCAFControl_Writer
from OCP.TopLoc import TopLoc_Location
from OCP.gp import gp_Trsf, gp_Vec
from OCP.IFSelect import IFSelect_RetDone
from openassembly import stepio

def test_shared_xcaf_definition_measured_once(tmp_path, monkeypatch):
    d = stepio.empty_doc()
    shapes = XCAFDoc_DocumentTool.ShapeTool_s(d.Main())
    assembly = shapes.NewShape()
    definition = shapes.AddShape(BRepPrimAPI_MakeBox(10., 20., 30.).Shape(), False)
    for x in (0., 100., 200.):
        tr = gp_Trsf()
        tr.SetTranslation(gp_Vec(x, 0., 0.))
        shapes.AddComponent(assembly, definition, TopLoc_Location(tr))
    shapes.UpdateAssemblies()
    path = tmp_path / 'repeated.step'
    writer = STEPCAFControl_Writer()
    assert writer.Transfer(d)
    assert writer.Write(str(path)) == IFSelect_RetDone
    calls = []
    original = stepio._local_measure
    def counted(shape):
        calls.append(shape)
        return original(shape)
    monkeypatch.setattr(stepio, '_local_measure', counted)
    parts = stepio.load_step(path)
    assert len(parts) == 3
    assert len(calls) == 1
    assert len({p.centroid for p in parts}) == 3
