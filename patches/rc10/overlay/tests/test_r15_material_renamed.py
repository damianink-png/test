from pathlib import Path
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCP.gp import gp_Trsf,gp_Vec
from OCP.TopLoc import TopLoc_Location
from dsac29.geometry import describe
from dsac29.compare import compare,Record
from dsac29.revision_rules import classify_revisions
from dsac29.material_deltas import calculate
from dsac29.report import produce
from dsac29.step_io import load_step
import json

def shape(name,length,dx=0,dy=0):
    part=BRepPrimAPI_MakeBox(length,10,10).Shape()
    t=gp_Trsf();t.SetTranslation(gp_Vec(dx,dy,0))
    return describe(part.Located(TopLoc_Location(t)),name,'SUBASSEMBLY/COMPONENT/'+name)

def test_same_name_different_geometry_is_changed():
    a=[shape('PLATE_012',20)];b=[shape('PLATE_012',25)]
    rec=classify_revisions(a,b,compare(a,b))
    assert len(rec)==1 and rec[0].status=='CHANGED',rec
    delta=calculate(a[0],b[0])
    assert abs(delta.common_mm3-2000)<1e-3
    assert abs(delta.added_mm3-500)<1e-3
    assert delta.removed_mm3 <1e-3

def test_renamed_identical_is_separate_report_category(tmp_path):
    a=[shape('OLD_BRACKET',20)];b=[shape('NEW_BRACKET',20)]
    rec=classify_revisions(a,b,compare(a,b))
    assert [r.status for r in rec]==['RENAMED']
    produce(tmp_path,a,b,rec,generate_step=False,diff_step=False,revision_style=True,full_bom=False)
    html=(tmp_path/'RAPORT.html').read_text(encoding='utf8')
    assert 'value="RENAMED"' in html and 'OLD_BRACKET' in html and 'NEW_BRACKET' in html

def test_changed_three_parts_in_step_preview_report(tmp_path):
    a=[shape(f'P{i}',30+i,0,i*40) for i in range(3)]
    b=[shape(f'P{i}',25 if i==0 else (35 if i==1 else 32),0,i*40) for i in range(3)]
    rec=classify_revisions(a,b,compare(a,b))
    assert sorted(r.status for r in rec)==['CHANGED','CHANGED','SAME'],rec
    produce(tmp_path,a,b,rec,generate_step=True,diff_step=False,revision_style=True,preview3d=True,full_bom=False)
    summary=json.loads((tmp_path/'PODSUMOWANIE.json').read_text(encoding='utf8'))
    assert summary['main_step_ready'],summary.get('step_export_error')
    assert summary['statuses']['CHANGED']==2
    assert len(summary['material_regions'])==2,summary.get('material_errors')
    assert summary['material_errors']=={}
    assert (tmp_path/'MATERIAL_ROZNICE.csv').exists()
    html=(tmp_path/'RAPORT.html').read_text(encoding='utf8')
    assert 'Materiał wspólny' in html and 'Materiał dodany' in html
    step=(tmp_path/'POROWNANIE_KOLORY.step').read_text(encoding='latin-1')
    assert 'CHANGED_COMMON' in step and 'CHANGED_ADDED' in step and 'CHANGED_REMOVED' in step
    preview=(tmp_path/'PODGLAD_KOLOROW_3D.html').read_text(encoding='utf8')
    assert 'CHANGED_COMMON' in preview and 'CHANGED_ADDED' in preview and 'CHANGED_REMOVED' in preview
    assert 'PARA_' in step
