import base64,json,re,time
import numpy as np
import pytest
from dsac29.robust_translation import Anchor,propose_translation
from dsac29.shared_mesh import SharedMesh
from dsac29.preview3d import _faces_meshed,create_preview
from dsac29.geometry import describe
from dsac29.compare import Record
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCP.gp import gp_Trsf,gp_Vec
from OCP.TopLoc import TopLoc_Location
from preview_decode import expand_scene

def test_one_supporting_family_is_insufficient():
    a=[Anchor(i,'bolt',(i*10.,0,0)) for i in range(4)]+[Anchor(8,'plate',(100.,0,0))]
    b=[Anchor(i,'bolt',(i*10.+50,0,0)) for i in range(4)]+[Anchor(8,'plate',(1000.,0,0))]
    assert propose_translation(a,b) is None

def test_thousands_of_anchors_single_shift():
    a=[Anchor(i,str(i),(i*10.,i*2.,i*3.)) for i in range(3000)]
    b=[Anchor(x.index,x.signature,tuple(v+d for v,d in zip(x.center,(100.,-30.,20.)))) for x in a]
    t=time.perf_counter();p=propose_translation(a,b)
    assert p.support==3000 and p.shift==(-100.,30.,-20.)
    print('3000 anchor consensus seconds:',time.perf_counter()-t)

def test_incompatible_equal_support_rejected():
    a=[Anchor(i,str(i),(i*10.,0.,0.)) for i in range(6)]
    b=[Anchor(x.index,x.signature,(x.center[0]+(100 if x.index<3 else 200),0.,0.)) for x in a]
    assert propose_translation(a,b) is None

def test_shared_preview_preserves_rotation_translation_and_occurrences(tmp_path):
    shape=BRepPrimAPI_MakeBox(10,20,30).Shape()
    tr=gp_Trsf();tr.SetTranslation(gp_Vec(100,200,300))
    other=shape.Moved(TopLoc_Location(tr))
    a=describe(shape,'old','root/old');b=describe(other,'new','root/new')
    path=tmp_path/'view.html';info=create_preview(path,[Record(0,None,'REMOVED',''),Record(None,0,'ADDED','')],[a],[b])
    raw=json.loads(re.search(r'const scene=(.*);',path.read_text()).group(1))
    assert info['elementy']==2 and info['pominiete']==0 and info['unique_meshes']==1
    assert sum('mesh_data' in p for p in raw)==1
    decoded=expand_scene(raw)
    pts=[np.frombuffer(base64.b64decode(p['data']),dtype='<f4').reshape(-1,3) for p in decoded]
    assert np.allclose(pts[1]-pts[0],(100,200,300))
    assert decoded[0]['alpha']==.4 and decoded[0]['status']=='REMOVED'
    assert decoded[0]['pair_id']!=decoded[1]['pair_id']

def test_distinct_definitions_are_not_merged():
    cache=SharedMesh()
    for n in (10,10.1):cache.pack(BRepPrimAPI_MakeBox(n,20,30).Shape(),.15,np.zeros(3),_faces_meshed)
    assert cache.definitions==2 and cache.hits==0

def test_600_occurrences_keep_all_ids_and_one_mesh(tmp_path):
    shape=BRepPrimAPI_MakeBox(10,20,30).Shape();parts=[]
    for i in range(600):
        tr=gp_Trsf();tr.SetTranslation(gp_Vec(i*20.,0,0))
        parts.append(describe(shape.Moved(TopLoc_Location(tr)),str(i),'root/'+str(i)))
    path=tmp_path/'large.html'
    info=create_preview(path,[Record(None,i,'ADDED','') for i in range(600)],[],parts)
    raw=json.loads(re.search(r'const scene=(.*);',path.read_text()).group(1))
    assert info['elementy']==600 and info['unique_meshes']==1 and info['mesh_cache_hits']==599
    assert len({p['part_index'] for p in raw})==600
    decoded=expand_scene(raw)
    centers=[np.frombuffer(base64.b64decode(p['data']),dtype='<f4').reshape(-1,3).mean(axis=0) for p in decoded]
    assert np.allclose(np.diff(centers,axis=0),[20,0,0])

def test_mesh_rotation_at_large_origin():
    from OCP.gp import gp_Ax1,gp_Pnt,gp_Dir
    shape=BRepPrimAPI_MakeBox(10,20,30).Shape()
    tr=gp_Trsf();tr.SetRotation(gp_Ax1(gp_Pnt(0,0,0),gp_Dir(0,0,1)),.7)
    tr.SetTranslationPart(gp_Vec(1e8,2e8,3e8));moved=shape.Moved(TopLoc_Location(tr))
    origin=np.array([1e8,2e8,3e8]);cache=SharedMesh()
    payload,count=cache.pack(moved,.15,origin,_faces_meshed)
    decoded=expand_scene([payload])[0]
    actual=np.frombuffer(base64.b64decode(decoded['data']),dtype='<f4').reshape(-1,3)
    expected=np.asarray(list(_faces_meshed(moved,.15))).reshape(-1,3)-origin
    assert np.allclose(actual,expected,atol=1e-5)
