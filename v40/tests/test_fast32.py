"""V3.2 performance, world-rigid memoization, and B-Rep material delta regressions."""
from collections import Counter
from pathlib import Path
import numpy as np
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCP.gp import gp_Vec,gp_Trsf
from OCP.TopLoc import TopLoc_Location
from dsac29.geometry import describe
from dsac29.compare import compare
from dsac29.cli import process
from dsac29.step_io import load_step


def _instance(base, x, name):
    tr=gp_Trsf();tr.SetTranslation(gp_Vec(x,0.,0.))
    return describe(base.Moved(TopLoc_Location(tr)),name,name)


def test_repeated_parts_only_one_boolean(monkeypatch):
    import dsac29.compare as impl
    a_shape=BRepPrimAPI_MakeBox(20.,12.,8.).Shape()
    b_shape=BRepPrimAPI_MakeBox(20.,12.,8.).Shape()
    a=[_instance(a_shape,i*27,'PLYTA_A') for i in range(70)]
    b=[_instance(b_shape,i*27,'PLYTA_B') for i in range(70)]
    original=impl.equivalent_world
    calls=[0]
    def wrapped(*args,**kwargs):calls[0]+=1;return original(*args,**kwargs)
    monkeypatch.setattr(impl,'equivalent_world',wrapped)
    r=compare(a,b)
    assert len(r)==70 and Counter(q.status for q in r)=={'RENAMED':70}
    assert calls[0]<=2, f'Expected cached B-Rep results, got {calls[0]} Boolean checks'


def test_moved_duplicates_are_matched_without_repeated_boolean(monkeypatch):
    import dsac29.compare as impl
    a_shape=BRepPrimAPI_MakeBox(20.,12.,8.).Shape()
    b_shape=BRepPrimAPI_MakeBox(20.,12.,8.).Shape()
    a=[_instance(a_shape,i*50,'A') for i in range(30)]
    b=[_instance(b_shape,1500+i*50,'A') for i in range(30)]
    original=impl.equivalent_rigid
    calls=[0]
    def wrapped(*args,**kwargs):calls[0]+=1;return original(*args,**kwargs)
    monkeypatch.setattr(impl,'equivalent_rigid',wrapped)
    r=compare(a,b)
    assert len(r)==30 and all(q.status=='MOVED' for q in r)
    assert calls[0]<=2


def test_diff_export_reports_equal_volume_hole_shift(tmp_path):
    from OCP.BRepPrimAPI import BRepPrimAPI_MakeCylinder
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut
    from OCP.gp import gp_Pnt, gp_Ax2, gp_Dir
    def plate_with_hole(offset):
        plate=BRepPrimAPI_MakeBox(120.,80.,10.).Shape()
        bore=BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(25.+offset,25.,-2.),gp_Dir(0,0,1)),8.,14.).Shape()
        obj=BRepAlgoAPI_Cut(plate,bore);obj.Build();assert obj.IsDone()
        return obj.Shape()
    # The volume stays constant, but the exact cut fragments must be present.
    a=[describe(plate_with_hole(0),'P','P')]
    b=[describe(plate_with_hole(4),'P','P')]
    from dsac29.report import produce
    out,err=produce(tmp_path,a,b,compare(a,b),generate_step=False,diff_step=True)
    assert err is None
    assert (out/'ROZNICE_BREP.step').exists()
    parts=load_step(str(out/'ROZNICE_BREP.step'))
    assert len(parts)==2
    volumes=sorted(p.volume for p in parts)
    assert abs(volumes[0]-volumes[1])<1e-3
    assert volumes[0]>0
    assert (out/'DETAL_ROZNICE.csv').exists()


def test_fast_worker_subprocess_cli(tmp_path):
    import subprocess,sys
    root=Path(__file__).resolve().parents[1]
    result=subprocess.run([sys.executable,str(root/'DSCompareV3.py'),'--dscompare-worker',
      '--a',str(root/'samples/MODEL_A.step'),'--b',str(root/'samples/MODEL_B.step'),
      '--output',str(tmp_path),'--no-main-step','--no-diff-step'],
      timeout=30,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,encoding='utf-8')
    assert result.returncode==0,result.stdout[-1200:]
    assert 'DSCOMPARE_EVENT:{"type": "done"' in result.stdout
    assert (tmp_path/'ZMIANY.csv').exists()
