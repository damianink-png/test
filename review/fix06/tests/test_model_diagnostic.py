import json
from dataclasses import replace
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox, BRepPrimAPI_MakeCylinder
from OCP.TopLoc import TopLoc_Location
from OCP.gp import gp_Trsf, gp_Vec
from dsac29 import model_diagnostic as diagnostic
from dsac29.geometry import describe


def test_topology_and_analytic_surface_details():
    box=diagnostic._shape_details(BRepPrimAPI_MakeBox(10.,20.,30.).Shape())
    assert box['counts']==dict(faces=6,edges=12,vertices=8,solids=1,shells=1)
    assert box['topology_valid_without_geometric_checks']
    assert len(box['surface_types'])==1
    assert all('normal' in f['analytic'] for f in box['faces'])
    assert all(0<=e['edge_index']<12 for f in box['faces'] for e in f['boundary_edges'])
    assert not box['errors']
    cylinder=diagnostic._shape_details(BRepPrimAPI_MakeCylinder(5.,10.).Shape())
    assert any(f.get('analytic',{}).get('radius_mm')==5. for f in cylinder['faces'])
    assert not cylinder['errors']


def test_one_inspection_per_definition_with_every_placement(tmp_path, monkeypatch):
    from dsac29 import step_io
    base=describe(BRepPrimAPI_MakeBox(1.,2.,3.).Shape(),'part','assembly/part')
    tr=gp_Trsf();tr.SetTranslation(gp_Vec(130.,280.,410.))
    moved=replace(base,shape=base.shape.Moved(TopLoc_Location(tr)),center=base.center+[130.,280.,410.])
    source=tmp_path/'source.step';source.write_text('ISO-10303-21;\nHEADER;\nENDSEC;')
    monkeypatch.setattr(step_io,'load_step',lambda *args,**kw:[base,moved])
    calls=[]; original=diagnostic._shape_details
    def inspect(shape):calls.append(1);return original(shape)
    monkeypatch.setattr(diagnostic,'_shape_details',inspect)
    report=diagnostic.run([source],tmp_path/'out',100,None)
    data=json.loads(report.read_text())
    assert data['report_schema']==2 and data['complete']
    assert len(calls)==1
    model=data['models'][0]; d=model['definitions'][0]
    assert len(model['source_sha256'])==64
    assert d['occurrence_indices']==[0,1]
    assert [r[3] for r in d['placements'][1]['location_3x4']]==[130.,280.,410.]
    assert not data['has_inspection_errors']


def test_diagnostic_keeps_failure_and_writes_valid_json(tmp_path,monkeypatch):
    from dsac29 import step_io
    base=describe(BRepPrimAPI_MakeBox(1.,2.,3.).Shape(),'bad','bad')
    source=tmp_path/'source.step';source.write_text('test')
    monkeypatch.setattr(step_io,'load_step',lambda *args,**kw:[base])
    def fail(shape):raise RuntimeError('synthetic inspection failure')
    monkeypatch.setattr(diagnostic,'_shape_details',fail)
    data=json.loads(diagnostic.run([source],tmp_path/'out',10,None).read_text())
    assert data['complete'] and data['has_inspection_errors']
    assert 'synthetic inspection failure' in data['models'][0]['definitions'][0]['geometry']['errors'][0]['error']
    assert diagnostic._finite_json({'bad':[float('nan'),float('inf')]})=={'bad':[None,None]}


def test_nurbs_report_contains_degrees_and_periodicity_without_control_points():
    from OCP.BRepBuilderAPI import BRepBuilderAPI_NurbsConvert
    shape=BRepBuilderAPI_NurbsConvert(BRepPrimAPI_MakeCylinder(5.,10.).Shape(),True).Shape()
    result=diagnostic._shape_details(shape)
    assert not result['errors']
    assert all('BSplineSurface' in f['type'] for f in result['faces'])
    assert all('u_degree' in f['spline'] and 'u_knots' in f['spline'] for f in result['faces'])
    assert any(f['spline']['u_periodic'] for f in result['faces'])
    assert all(isinstance(f['spline']['u_poles'],int) for f in result['faces'])
