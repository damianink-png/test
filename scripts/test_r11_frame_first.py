"""R11: CAD frame first, periodic pitch protection, integration."""
import json
import numpy as np
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCP.gp import gp_Trsf,gp_Vec
from OCP.TopLoc import TopLoc_Location
from dsac29.geometry import describe
from dsac29.registration_gate import frame_support,original_frame_fastpath

def make(shape,pos,i):
 t=gp_Trsf();t.SetTranslation(gp_Vec(*map(float,pos)))
 return describe(shape.Located(TopLoc_Location(t)),f'PART{i}',f'PART{i}')

def test_normal_frame_partial_assembly():
 rng=np.random.default_rng(777)
 pos=rng.integers(100,9000,size=(80,3))
 common=BRepPrimAPI_MakeBox(20,11,9).Shape()
 old=BRepPrimAPI_MakeBox(13,14,15).Shape()
 new=BRepPrimAPI_MakeBox(13,14,16).Shape()
 a=[make(common if i<30 else old,pos[i],i) for i in range(80)]
 b=[make(common if i<30 else new,pos[i],i) for i in range(80)]
 initial=frame_support(a,b,.01,proofs=8)
 assert initial['count']==30 and initial['proofs']==8,initial
 assert original_frame_fastpath(a,b,.01,initial)[0]

def test_periodic_pitch_requires_registration():
 shape=BRepPrimAPI_MakeBox(17,11,9).Shape()
 a=[make(shape,(i*40,0,0),i) for i in range(30)]
 b=[make(shape,(i*40+40,0,0),i) for i in range(30)]
 initial=frame_support(a,b,.01,proofs=8)
 assert initial['count']==29
 assert not original_frame_fastpath(a,b,.01,initial)[0]

def test_full_offset_needs_alignment():
 shape=BRepPrimAPI_MakeBox(17,11,9).Shape()
 a=[make(shape,(i*40,i*i*3,0),i) for i in range(20)]
 b=[make(shape,(i*40+500,i*i*3+100,0),i) for i in range(20)]
 assert not original_frame_fastpath(a,b,.01)[0]

def test_unshifted_cli_does_not_call_align(tmp_path,monkeypatch):
 from dsac29 import cli,alignment
 stable=BRepPrimAPI_MakeBox(20,11,9).Shape()
 old=BRepPrimAPI_MakeBox(13,14,15).Shape()
 new=BRepPrimAPI_MakeBox(13,14,16).Shape()
 a=[make(stable if i<20 else old,(i*41,i*i*2,0),i) for i in range(40)]
 b=[make(stable if i<20 else new,(i*41,i*i*2,0),i) for i in range(40)]
 pa=tmp_path/'old.step';pb=tmp_path/'new.step'
 pa.write_text('old');pb.write_text('new')
 monkeypatch.setattr(cli,'load_step',lambda path,**kw:a if path==pa else b)
 def forbidden(*args,**kwargs):raise AssertionError('Registration should not run')
 monkeypatch.setattr(alignment,'align_assembly',forbidden)
 dest=tmp_path/'out';dest.mkdir()
 cli.process(pa,pb,dest,step=False,diff_step=False,full_bom=False,
             revision_style=True,auto_align=True,alignment_approval=forbidden,progress=None)
 summary=json.loads((dest/'PODSUMOWANIE.json').read_text(encoding='utf8'))
 timing=json.loads((dest/'CZASY_ANALIZY.json').read_text(encoding='utf8'))
 assert summary['statuses']['SAME']==20
 assert summary['alignment']['method']=='original_cad_frame_preflight'
 assert 'alignment_preflight_and_optional_registration_s' in timing
