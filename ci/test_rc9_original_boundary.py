"""Original boundary identity: real failure replay and negative CAD controls."""
import sys
from pathlib import Path
from unittest.mock import patch
import tempfile,json,hashlib
root=Path(__file__).resolve().parents[1]/'dscompare_rc9_manual'
sys.path.insert(0,str(root))
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox,BRepPrimAPI_MakeCylinder
from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut
from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
from OCP.gp import gp_Trsf,gp_Vec,gp_Pnt
from dsac29.geometry import describe
from dsac29.step_reexport_tolerance import reexport_equivalent_world
from dsac29 import native_guard,brep_safety

def move(shape,dx):
    tr=gp_Trsf();tr.SetTranslation(gp_Vec(dx,0,0))
    return BRepBuilderAPI_Transform(shape,tr,True).Shape()
def same(a,b,**extra):
    return reexport_equivalent_world(describe(a,'A','A'),describe(b,'B','B'),.01,
        allow_boolean=False,_original_boundary_only=True,**extra)

box=BRepPrimAPI_MakeBox(10.,10.,10.).Shape()
assert same(box,move(box,.003))
assert not same(box,move(box,.02))
assert not same(box,BRepPrimAPI_MakeBox(10.,10.,10.02).Shape())
def hole(x):
    tool=BRepPrimAPI_MakeCylinder(1.,12.).Shape()
    tr=gp_Trsf();tr.SetTranslation(gp_Vec(x,5,-1))
    tool=BRepBuilderAPI_Transform(tool,tr,True).Shape()
    return BRepAlgoAPI_Cut(box,tool).Shape()
assert not same(hole(3),hole(7))  # Same volume, bounds and outer surfaces.
assert not same(box,hole(3))
try:same(box,box,_repair_boundary_only=True)
except ValueError:pass
else:raise AssertionError('Repair policy must remain separate')
# A failed original-boundary proof must still proceed to strict repair.
class ExitRequested(BaseException):pass
with tempfile.TemporaryDirectory() as td:
    p=Path(td);req=p/'request.json';reply=p/'reply.json'
    req.write_text(json.dumps(dict(operation='world_reexport',a='missing-A',b='missing-B',tolerance=.01)))
    with patch.object(native_guard,'_load_brep',side_effect=[box,box]), \
         patch.object(brep_safety,'is_valid',return_value=False), \
         patch('dsac29.step_reexport_tolerance.reexport_equivalent_world',return_value=False), \
         patch.object(brep_safety,'validated_copy',side_effect=brep_safety.UnprovenRepair('unproven')), \
         patch.object(native_guard.os,'_exit',side_effect=ExitRequested):
        try:native_guard.worker(str(req),str(reply))
        except ExitRequested:pass
        else:raise AssertionError('Unproven repair must fail')
    assert json.loads(reply.read_text())['ok'] is False
print('PASS: 7 original-boundary regression controls',flush=True)

if len(sys.argv)>1:
    p=Path(sys.argv[1])
    a,b=[native_guard._load_brep(p/(n+'.brep')) for n in ['A','B']]
    assert not brep_safety.is_valid(a) and not brep_safety.is_valid(b)
    with tempfile.TemporaryDirectory() as td:
        req=Path(td)/'request.json';out=Path(td)/'reply.json'
        req.write_text(json.dumps(dict(operation='world_reexport',a=str((p/'A.brep').resolve()),b=str((p/'B.brep').resolve()),tolerance=.01)))
        with patch.object(brep_safety,'validated_copy',side_effect=AssertionError('Must prove originals without repair')):
            assert native_guard.worker(str(req),str(out))==0
        assert json.loads(out.read_text())==dict(ok=True,match=True)
    assert not same(a,move(b,.02))
    print('PASS: captured Trident A273/B273 native worker and displaced negative control',flush=True)
