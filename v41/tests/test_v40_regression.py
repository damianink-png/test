import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import json,math
import numpy as np
from pathlib import Path
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCP.gp import gp_Trsf,gp_Vec,gp_Ax1,gp_Pnt,gp_Dir
from OCP.TopLoc import TopLoc_Location
from dsac29.geometry import describe,equivalent_rigid,transform
from dsac29.compare import compare,Record
from dsac29.step_io import export_colored_step,inspect_step_colors,load_step,COLORS
from dsac29.mesh_v37 import make_mesh


def test_located_instances_each_have_surface_color_and_position(tmp_path):
    base=BRepPrimAPI_MakeBox(12,20,8).Shape()
    parts=[]
    for i in range(3):
        tr=gp_Trsf();tr.SetTranslation(gp_Vec(i*100,25,30))
        parts.append(describe(base.Moved(TopLoc_Location(tr)),f'P{i}',f'P{i}'))
    rec=[Record(None,i,s,'test') for i,s in enumerate(('ADDED','CHANGED','MOVED'))]
    path=tmp_path/'colored.step';export_colored_step(str(path),rec,[],parts)
    diag=inspect_step_colors(path)
    assert diag['powierzchnie_bez_koloru']==0
    assert diag['pokolorowane_powierzchnie']==18
    assert diag['pokolorowane_etykiety']==3
    assert len(diag['kolory_wczytane_rgb'])==3
    loaded=load_step(str(path));assert len(loaded)==3
    assert np.allclose(sorted(x.center[0] for x in loaded),[6,106,206],atol=1e-5)
    make_mesh(path,tmp_path/'mesh.npz')
    with np.load(tmp_path/'mesh.npz') as m:
        assert len(m['colors'])==3
        assert len(set(tuple(np.round(c,3)) for c in m['colors']))==3
        assert m['vertices'][:,0].max()>211


def test_cube_arbitrary_rotation_proved_and_reported():
    shape=BRepPrimAPI_MakeBox(20,20,20).Shape()
    a=describe(shape,'cube','cube')
    tr=gp_Trsf();tr.SetRotation(gp_Ax1(gp_Pnt(10,10,10),gp_Dir(1,2,3)),math.radians(23))
    b=describe(shape.Moved(TopLoc_Location(tr)),'cube','cube')
    ok,R,t=equivalent_rigid(a,b)
    assert ok
    r=compare([a],[b])[0]
    assert r.status=='MOVED'
    assert abs(r.rotation_deg-23)<1e-5


def test_ambiguous_changed_names_require_review():
    a=[describe(BRepPrimAPI_MakeBox(10,20,30).Shape(),'P','P') for _ in range(2)]
    b=[describe(BRepPrimAPI_MakeBox(11,20,30).Shape(),'P','P') for _ in range(2)]
    assert all(x.status=='UNCERTAIN' for x in compare(a,b))


def test_failed_boolean_never_classified_as_confirmed_change(monkeypatch):
    import dsac29.compare as c
    def fail(*a,**k):raise RuntimeError('bad geometry')
    monkeypatch.setattr(c,'equivalent_world',fail);monkeypatch.setattr(c,'equivalent_rigid',fail)
    a=[describe(BRepPrimAPI_MakeBox(10,20,30).Shape(),'P','P')]
    b=[describe(BRepPrimAPI_MakeBox(10,20,30).Shape(),'P','P')]
    assert compare(a,b)[0].status=='UNCERTAIN'


def test_rigid_assembly_alignment():
    from dsac29.alignment import align_assembly
    a=[describe(transform(BRepPrimAPI_MakeBox(11+i,23,37).Shape(),np.eye(3),np.array([i*80.,i*i*40.,0.])),f'P{i}',f'P{i}') for i in range(3)]
    R=np.array([[0.,-1.,0.],[1.,0.,0.],[0.,0.,1.]])
    b=[describe(transform(p.shape,R,np.array([300,120,50])),p.name,p.path) for p in a]
    aligned,info=align_assembly(a,b)
    assert info['votes']==3
    assert all(x.status=='SAME' for x in compare(a,aligned))


def test_ui_icons_details_and_cancel(tmp_path,monkeypatch):
    from PySide6.QtWidgets import QApplication,QAbstractItemView
    import dsac29.gui_qt37 as ui
    monkeypatch.setattr(ui,'_settings_path',lambda:tmp_path/'settings.json')
    app=QApplication.instance() or QApplication([])
    w=ui.Window();w.show();app.processEvents()
    assert all(b.iconSize().width()==26 and b.height()==52 for b in w.nav.values())
    assert all(not b.icon().isNull() for b in w.nav.values())
    assert len(w.results_numbers)==7
    assert len(w.legend_filters)==6
    assert w.table.editTriggers()==QAbstractItemView.NoEditTriggers
    assert not w.align_models.isChecked()
    assert w.make_diff.isChecked()
    for page in w.pages:
        w.navigate(page);app.processEvents()
    w.close()
