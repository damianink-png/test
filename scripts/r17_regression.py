from pathlib import Path
from tempfile import TemporaryDirectory
import json
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCP.gp import gp_Trsf,gp_Vec
from OCP.TopLoc import TopLoc_Location
from dsac29.geometry import describe
from dsac29.compare import compare
from dsac29.revision_rules import classify_revisions
from dsac29.revision_overlap import merge_material_revisions
from dsac29.report import produce

def box(name,length=20,x=0,y=0):
    part=BRepPrimAPI_MakeBox(length,10,10).Shape()
    tr=gp_Trsf();tr.SetTranslation(gp_Vec(x,y,0))
    return describe(part.Located(TopLoc_Location(tr)),name,'ASSEMBLY/'+name)

def pair(a,b):
    rec=classify_revisions(a,b,compare(a,b,revision_only=True),geometry_first=True)
    return merge_material_revisions(a,b,rec)

def check():
    a=[box('BRACKET_001',30)];b=[box('VENDOR_Z999',34)]
    rec,regions,diag=pair(a,b)
    assert len(rec)==1 and rec[0].status=='CHANGED' and rec[0].name_changed,rec
    assert abs(regions[0].common_mm3-3000)<.01
    assert abs(regions[0].added_mm3-400)<.01
    assert diag['accepted']==1
    with TemporaryDirectory() as d:
        output=Path(d)
        produce(d,a,b,rec,generate_step=True,diff_step=False,revision_style=True,full_bom=False,
                preview3d=True,precomputed_material_regions=regions,
                report_context={'revision_overlap':diag})
        info=json.loads((output/'PODSUMOWANIE.json').read_text('utf8'))
        assert info['statuses']['CHANGED']==1 and info['geometry_and_name_changed_count']==1
        assert len(info['material_regions'])==1 and not info['material_errors']
        assert (output/'NAZWY_ZMIENIONA_GEOMETRIA.csv').is_file()
        assert 'CHANGED_COMMON' in (output/'POROWNANIE_KOLORY.step').read_text('latin1')
        assert 'CHANGED_COMMON' in (output/'PODGLAD_KOLOROW_3D.html').read_text('utf8')
        assert 'Zmiana' in (output/'RAPORT.html').read_text('utf8')
    print('PASS: renamed geometry and actual material volumes with STEP, HTML, CSV')
    a=[box('OLD',20)];b=[box('UNRELATED',20,13)]
    rec,regions,_=pair(a,b)
    assert sorted(r.status for r in rec)==['ADDED','REMOVED'] and not regions
    print('PASS: insufficient shared volume cannot become CHANGED')
    a=[box(f'old{i}',20,y=i*40) for i in range(3)]
    b=[box(f'new{i}',25 if i==0 else (16 if i==1 else 20),y=i*40) for i in range(3)]
    rec,regions,_=pair(a,b)
    assert sorted(x.status for x in rec)==['CHANGED','CHANGED','SAME'],[x.status for x in rec]
    assert len(regions)==2 and all(r.name_changed for r in rec)
    assert sum(r.added_mm3 for r in regions.values())>0
    assert sum(r.removed_mm3 for r in regions.values())>0
    print('PASS: three-part assembly')
    a=[box('OLD',20)];b=[box('B1',22),box('B2',22)]
    rec,regions,diag=pair(a,b)
    assert not any(r.status=='CHANGED' for r in rec) and not regions and diag['ambiguous']>0
    print('PASS: ambiguous repeated solids are not guessed')
if __name__=='__main__':check()
