"""Regression guards: STEP AABB drift is not a move; in-place rotation is."""
import math
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCP.BRepAlgoAPI import BRepAlgoAPI_Fuse
from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
from OCP.gp import gp_Pnt, gp_Dir, gp_Ax1, gp_Trsf
from openassembly.model import Part, compare, _same_world_faces

def shape():
    a = BRepPrimAPI_MakeBox(gp_Pnt(0,0,0),6,3,2).Shape()
    b = BRepPrimAPI_MakeBox(gp_Pnt(5,2,0),2,4,2).Shape()
    fuse = BRepAlgoAPI_Fuse(a,b)
    fuse.Build()
    assert fuse.IsDone()
    return fuse.Shape()

def part(src,i):
    return Part(f'{src}{i}',f'Unique_{i}',f'/{src}/{i}',1000+i,2000+i,
                (float(i*12),0.,0.),(1000+i,2000+i,(i,),((0,1.),),((0,1.),)),
                pose=(1,0,0,0,1,0,0,0,1),extents=(10,20,20))

def scenario(rotated=False):
    a = [part('A',i) for i in range(150)]
    b = [part('B',i) for i in range(150)]
    a[100].shape = shape()
    b[100].shape = a[100].shape
    if rotated:
        tf = gp_Trsf()
        tf.SetRotation(gp_Ax1(gp_Pnt(3,2,1),gp_Dir(0,0,1)),math.pi/2)
        b[100].shape = BRepBuilderAPI_Transform(a[100].shape,tf,True).Shape()
    b[100].pose = (0,-1,0,1,0,0,0,0,1)
    b[100].extents = (10,20,30)
    return a,b

def test_roundtrip_same_world_faces_despite_aabb_pose_drift():
    a,b = scenario()
    assert _same_world_faces(a[100],b[100])
    c = compare(a,b,revision_overlap=lambda *_:{'ok':False})
    assert c.counts == {'unchanged':150},c.counts
    assert a[100].match_quality == 'world_faces_verified_roundtrip'

def test_genuine_in_place_rotation_remains_moved():
    a,b = scenario(rotated=True)
    assert not _same_world_faces(a[100],b[100])
    c = compare(a,b,revision_overlap=lambda *_:{'ok':False})
    assert c.counts == {'unchanged':149,'moved':1},c.counts

def test_world_face_proof_requires_real_geometry():
    a,b = scenario()
    b[100].shape = None
    assert not _same_world_faces(a[100],b[100])
