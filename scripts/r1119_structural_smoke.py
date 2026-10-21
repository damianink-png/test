"""Quick structure regression: real status subassemblies, no empty solid leaves."""
import os,re,json
from pathlib import Path
from tempfile import TemporaryDirectory
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCP.gp import gp_Trsf,gp_Vec
from OCP.TopLoc import TopLoc_Location
from dsac29.geometry import describe
from dsac29.compare import compare
from dsac29.step_io import export_revision_step,inspect_step_colors

def make(label,x,y,size=15):
    solid=BRepPrimAPI_MakeBox(size,10,8).Shape()
    tr=gp_Trsf()
    tr.SetTranslation(gp_Vec(float(x),float(y),0))
    return describe(solid.Located(TopLoc_Location(tr)),label,label)

def main():
    os.environ['DSCOMPARE_STEP_VERIFY']='full'
    os.environ.pop('DSCOMPARE_FLAT_FALLBACK',None)
    a=[make('unchanged',0,0,19),make('move',40,0,15),make('removed',80,0,23)]
    b=[make('unchanged',0,0,19),make('move',40,40,15),make('added',160,0,25)]
    revisions=compare(a,b,revision_only=True)
    assert {'SAME','MOVED','REMOVED','ADDED'}.issubset({x.status for x in revisions})
    with TemporaryDirectory() as td:
        p=Path(td)/'POROWNANIE_KOLORY.step'
        diag=export_revision_step(str(p),revisions,a,b)
        read=inspect_step_colors(str(p))
        assert diag['grupowanie_zlozenia'] is True,diag
        assert diag['samodzielne_puste_produkty']==0,diag
        assert diag['podzlozenia_step']>=4,diag
        assert diag['rzeczywiste_bryly_step']==read['bryly_wynikowe'],(diag,read)
        assert read['elementy_bez_bryly']==0,read
        assert read['bryly_bez_koloru']==0,read
        assert read['powierzchnie_bez_koloru']==0,read
        data=p.read_text(errors='replace')
        assert 'NEXT_ASSEMBLY_USAGE_OCCURRENCE' in data
        for group in ('01_BEZ_ZMIAN','03_PRZESUNIETE','04_NOWE','05_USUNIETE'):
            assert group in data,group
        names=re.findall(r"(?m)^#\d+\s*=\s*PRODUCT\('([^']*)'",data)
        assert not any(x.upper().startswith('ABSR') for x in names),names
        assert len(names)==diag['produkty_step']
        manifest=json.loads((p.parent/'GRUPY_ZW3D.json').read_text('utf8'))
        assert manifest['status']=='natywne_podzlozenia_step'
        print('PASS: STEP nested statuses, all solids, no empty leaf products, native colors')
if __name__=='__main__':main()
