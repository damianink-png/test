"""Create self-contained small STEP models for offline acceptance tests."""
from pathlib import Path
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox, BRepPrimAPI_MakeCylinder
from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut
from OCP.gp import gp_Pnt,gp_Ax2,gp_Dir
from OCP.TDocStd import TDocStd_Document
from OCP.TCollection import TCollection_ExtendedString
from OCP.XCAFDoc import XCAFDoc_DocumentTool
from OCP.TDataStd import TDataStd_Name
from OCP.STEPCAFControl import STEPCAFControl_Writer
from OCP.IFSelect import IFSelect_RetDone


def box(x,y,z,w,d,h):return BRepPrimAPI_MakeBox(gp_Pnt(x,y,z),w,d,h).Shape()

def plate(hole_shift):
    base=box(0,0,0,120,80,10)
    cyl=BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(25+hole_shift,25,-2),gp_Dir(0,0,1)),8,14).Shape()
    tool=BRepAlgoAPI_Cut(base,cyl);tool.Build()
    if not tool.IsDone():raise RuntimeError('Sample: failed cylinder cut')
    return tool.Shape()

def save(path,parts):
    doc=TDocStd_Document(TCollection_ExtendedString('BinXCAF'))
    shape_tool=XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())
    for name,sh in parts:
        label=shape_tool.AddShape(sh,False)
        TDataStd_Name.Set_s(label,TCollection_ExtendedString(name))
    w=STEPCAFControl_Writer();w.SetNameMode(True)
    if not w.Transfer(doc) or w.Write(str(path))!=IFSelect_RetDone:raise RuntimeError('Cannot write '+str(path))

def main():
    folder=Path(__file__).parent/'samples';folder.mkdir(exist_ok=True)
    a=[('PLYTA_OTWOR',plate(0)),('BLACHA_001',box(200,0,0,60,40,8)),
       ('PROFIL_STARA_POZYCJA',box(330,0,0,40,20,150)),
       ('ELEMENT_USUNIETY',box(500,0,0,22,18,7))]
    b=[('PLYTA_OTWOR',plate(4)),('WSPORNIK_001',box(200,0,0,60,40,8)),
       ('PROFIL_STARA_POZYCJA',box(330,50,0,40,20,150)),
       ('NOWY_ELEMENT',box(600,0,0,26,19,6))]
    save(folder/'MODEL_A.step',a)
    save(folder/'MODEL_B.step',b)
    print('Wygenerowano:',folder/'MODEL_A.step',folder/'MODEL_B.step')
if __name__=='__main__': main()
