"""Regression: Common never converts invalid geometry into a revision verdict."""
import json
from types import SimpleNamespace
import pytest
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCP.gp import gp_Pnt
from OCP.BRepTools import BRepTools
from dsac29 import native_guard, material_deltas


def test_common_worker_produces_checked_positive_intersection_and_phase(tmp_path):
    a=BRepPrimAPI_MakeBox(gp_Pnt(0,0,0),10,10,10).Shape()
    b=BRepPrimAPI_MakeBox(gp_Pnt(5,0,0),10,10,10).Shape()
    for name,shape in [('A',a),('B',b)]:
        with (tmp_path/(name+'.brep')).open('wb') as stream:
            BRepTools.Write_s(shape,stream)
    request=tmp_path/'request.json'
    reply=tmp_path/'reply.json'
    request.write_text(json.dumps({'operation':'common','a':str(tmp_path/'A.brep'),
        'b':str(tmp_path/'B.brep'),'common_shape':str(tmp_path/'common.brep'),
        'tolerance':0.01}),encoding='utf-8')
    assert native_guard.worker(str(request),str(reply))==0
    data=json.loads(reply.read_text(encoding='utf-8'))
    assert data['ok'] is True
    assert abs(data['common_volume']-500.)<1e-4
    assert reply.with_suffix('.phase').read_text(encoding='utf-8')=='common_done'
    assert (tmp_path/'common.brep').stat().st_size>0


def test_impossible_negative_common_is_rejected_before_topology_validation(monkeypatch):
    import OCP.BRepGProp as gprop
    import OCP.GProp as props
    a=BRepPrimAPI_MakeBox(10,10,10).Shape()
    b=BRepPrimAPI_MakeBox(gp_Pnt(5,0,0),10,10,10).Shape()
    class NegativeProperties:
        def Mass(self):return -123.0
    monkeypatch.setattr(props,'GProp_GProps',NegativeProperties)
    monkeypatch.setattr(gprop,'BRepGProp',SimpleNamespace(VolumeProperties_s=lambda shape,output:None))
    def no_topology_check(*args):
        raise AssertionError('Must reject negative signed volume before topology check')
    monkeypatch.setattr(material_deltas,'_check_result',no_topology_check)
    with pytest.raises(RuntimeError,match='impossible signed volume'):
        material_deltas.operate(material_deltas.BRepAlgoAPI_Common,a,b,.01)


def test_negative_common_isolated_child_writes_error_before_native_teardown(monkeypatch,tmp_path):
    import os
    import OCP.BRepGProp as gprop
    import OCP.GProp as props
    from pathlib import Path
    a=BRepPrimAPI_MakeBox(10,10,10).Shape()
    b=BRepPrimAPI_MakeBox(gp_Pnt(5,0,0),10,10,10).Shape()
    reply=tmp_path/'reply.json'
    class NegativeProperties:
        def Mass(self):return -122.58159431091562
    class EarlyExit(BaseException):
        def __init__(self,code):self.code=code
    def exit_without_teardown(code):raise EarlyExit(code)
    monkeypatch.setenv('DSCOMPARE_COMMON_FAILFAST_REPLY',str(reply))
    monkeypatch.setattr(os,'_exit',exit_without_teardown)
    monkeypatch.setattr(props,'GProp_GProps',NegativeProperties)
    monkeypatch.setattr(gprop,'BRepGProp',SimpleNamespace(VolumeProperties_s=lambda shape,output:None))
    with pytest.raises(EarlyExit) as caught:
        material_deltas.operate(material_deltas.BRepAlgoAPI_Common,a,b,.01)
    assert caught.value.code==70
    data=json.loads(reply.read_text(encoding='utf-8'))
    assert data['ok'] is False
    assert 'impossible signed volume' in data['error']
    assert reply.with_suffix('.phase').read_text(encoding='utf-8')=='common_rejected'
