import pytest
from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut
from OCP.BRepPrimAPI import BRepPrimAPI_MakeCylinder, BRepPrimAPI_MakeBox
from OCP.BRepTools import BRepTools
from OCP.TopAbs import TopAbs_FACE
from OCP.gp import gp_Pnt, gp_Trsf, gp_Vec
from OCP.TopLoc import TopLoc_Location
from dsac29.same_domain import equivalent, normalize, _count
from test_registered_solid_sets import shapes


def test_split_planes_proven_without_boolean_and_without_modifying_inputs(tmp_path, monkeypatch):
    from dsac29 import step_reexport_tolerance
    a, b = shapes()
    before = tmp_path/'before.brep'; after = tmp_path/'after.brep'
    BRepTools.Write_s(b, str(before))
    def forbidden(*args, **kwargs):
        raise AssertionError('Normalization proof must not invoke Boolean difference')
    monkeypatch.setattr(step_reexport_tolerance, '_verified_difference_empty', forbidden)
    assert equivalent(a, b, .01)
    assert _count(normalize(b, .01), TopAbs_FACE) == 6
    BRepTools.Write_s(b, str(after))
    assert before.read_bytes() == after.read_bytes()


def test_normalization_does_not_align_locally_moved_part():
    a, b = shapes()
    tr = gp_Trsf(); tr.SetTranslation(gp_Vec(0., 0., 1.))
    assert not equivalent(a, b.Moved(TopLoc_Location(tr)), .01)


def test_normalization_preserves_holes_and_material_change():
    a, b = shapes()
    drill = BRepPrimAPI_MakeCylinder(2., 10.).Shape()
    tr = gp_Trsf(); tr.SetTranslation(gp_Vec(10., 15., -2.))
    changed = BRepAlgoAPI_Cut(b, drill.Moved(TopLoc_Location(tr))).Shape()
    assert not equivalent(a, changed, .01)
    assert equivalent(changed, changed, .01)


def test_equal_volume_is_not_boundary_proof():
    a = BRepPrimAPI_MakeBox(10., 12., 5.).Shape()
    b = BRepPrimAPI_MakeBox(12., 10., 5.).Shape()
    assert not equivalent(a, b, .01)


def test_tiny_tolerance_does_not_enable_normalization():
    a, b = shapes()
    assert normalize(a, 1e-8) is None
    assert not equivalent(a, b, 1e-8)


@pytest.mark.parametrize('schema', ['AP203', 'AP214IS'])
def test_step_roundtrip_split_faces_at_translated_coordinates(tmp_path, schema):
    from OCP.STEPControl import STEPControl_Writer, STEPControl_AsIs
    from OCP.Interface import Interface_Static
    from OCP.IFSelect import IFSelect_RetDone
    from dsac29.step_io import load_step
    from dsac29.native_guard import guarded_registered_world
    a, b = shapes()
    tr = gp_Trsf(); tr.SetTranslation(gp_Vec(130., 280., 410.))
    old_schema = Interface_Static.CVal_s('write.step.schema')
    parts = []
    try:
        Interface_Static.SetCVal_s('write.step.schema', schema)
        for index, shape in enumerate((a, b)):
            writer = STEPControl_Writer()
            assert writer.Transfer(shape.Moved(TopLoc_Location(tr)), STEPControl_AsIs) == IFSelect_RetDone
            path = tmp_path/f'{index}.step'
            assert writer.Write(str(path)) == IFSelect_RetDone
            imported = load_step(str(path))
            assert len(imported) == 1
            parts.append(imported[0])
    finally:
        Interface_Static.SetCVal_s('write.step.schema', old_schema)
    assert equivalent(parts[0].shape, parts[1].shape, .01)
    assert guarded_registered_world(parts[0], parts[1], .01)
