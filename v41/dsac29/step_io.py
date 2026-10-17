"""STEPCAF load/save to keep STEP names and per-body colors. Lengths expected in mm."""
from __future__ import annotations
from dataclasses import dataclass
import re
from pathlib import Path
from OCP.STEPCAFControl import STEPCAFControl_Reader, STEPCAFControl_Writer
from OCP.TDocStd import TDocStd_Document
from OCP.TCollection import TCollection_ExtendedString
from OCP.TDF import TDF_LabelSequence, TDF_Label
from OCP.TDataStd import TDataStd_Name
from OCP.XCAFDoc import XCAFDoc_DocumentTool, XCAFDoc_ColorType
from OCP.TopoDS import TopoDS_Shape
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_SOLID, TopAbs_FACE
from OCP.TopLoc import TopLoc_Location
from OCP.Quantity import Quantity_Color,Quantity_TOC_RGB
from OCP.IFSelect import IFSelect_RetDone
from .geometry import SolidInfo,describe


def _label_name(label: TDF_Label, default=''): 
    attr=TDataStd_Name()
    if label.FindAttribute(TDataStd_Name.GetID_s(),attr):
        txt=attr.Get().ToExtString().strip()
        if txt: return txt
    return default


from .names import technical

def _real_name(label):return not technical(label)


def _solids(shape: TopoDS_Shape):
    ex=TopExp_Explorer(shape, TopAbs_SOLID)
    while ex.More():
        yield ex.Current()
        ex.Next()


def _faces(shape: TopoDS_Shape):
    ex=TopExp_Explorer(shape,TopAbs_FACE)
    while ex.More():
        yield ex.Current()
        ex.Next()


def inspect_step_colors(path: str) -> dict:
    """Nie ufaj samemu sukcesowi zapisu: sprawdź kolory po ponownym imporcie XCAF."""
    from OCP.Quantity import Quantity_Color
    p=Path(path)
    document=TDocStd_Document(TCollection_ExtendedString('BinXCAF'))
    reader=STEPCAFControl_Reader()
    reader.SetNameMode(True);reader.SetColorMode(True)
    if reader.ReadFile(str(p))!=IFSelect_RetDone or not reader.Transfer(document):
        raise RuntimeError('Nie można ponownie odczytać wynikowego STEP')
    shape_tool=XCAFDoc_DocumentTool.ShapeTool_s(document.Main())
    colors=XCAFDoc_DocumentTool.ColorTool_s(document.Main())
    roots=TDF_LabelSequence();shape_tool.GetFreeShapes(roots)
    seen=[]; colored_labels=0;colored_faces=0;missing_bodies=0;missing_faces=0
    def detect(lab,depth=0):
        nonlocal colored_labels,colored_faces,missing_bodies,missing_faces
        if depth>64:raise RuntimeError('Cykliczna struktura STEP')
        target=TDF_Label()
        if shape_tool.IsReference_s(lab) and shape_tool.GetReferredShape_s(lab,target):
            detect(target,depth+1);return
        comps=TDF_LabelSequence()
        if shape_tool.GetComponents_s(lab,comps) and comps.Length():
            for i in range(1,comps.Length()+1):detect(comps.Value(i),depth+1)
            return
        shape=shape_tool.GetShape_s(lab)
        if shape.IsNull():return
        color=Quantity_Color()
        has=(colors.GetColor_s(lab,XCAFDoc_ColorType.XCAFDoc_ColorSurf,color) or
             colors.GetColor_s(lab,XCAFDoc_ColorType.XCAFDoc_ColorGen,color))
        if has:
            colored_labels+=1
            seen.append(tuple(round(x,4) for x in [color.Red(),color.Green(),color.Blue()]))
        else:missing_bodies+=1
        for face in _faces(shape):
            facecol=Quantity_Color()
            if colors.GetColor(face,XCAFDoc_ColorType.XCAFDoc_ColorSurf,facecol):
                colored_faces+=1
                seen.append(tuple(round(x,4) for x in [facecol.Red(),facecol.Green(),facecol.Blue()]))
            else:missing_faces+=1
    for idx in range(1,roots.Length()+1):detect(roots.Value(idx))
    # Diagnostyka zapisanych rekordów stylu STEP, a nie tylko wyglądu CADbro.
    with p.open('rb') as inp:data=inp.read()
    result={'liczba_etykiet':roots.Length(),'bryly_bez_koloru':missing_bodies,'powierzchnie_bez_koloru':missing_faces,
            'pokolorowane_etykiety':colored_labels,
            'pokolorowane_powierzchnie':colored_faces,
            'brak_kolorow_powierzchni':not bool(colored_faces),
            'kolory_wczytane_rgb':sorted(set(seen)),
            'rekordy_kolorow_step':data.count(b'COLOUR_RGB('),
            'rekordy_stylow_step':data.count(b'STYLED_ITEM(')}
    if not result['rekordy_kolorow_step'] or not result['rekordy_stylow_step']:
        raise RuntimeError('STEP został zapisany bez rekordów koloru — nie uznajemy eksportu za udany')
    if not (colored_labels or colored_faces):
        raise RuntimeError('Po ponownym wczytaniu STEP nie wykryto kolorów przypisanych do brył/powierzchni')
    return result

def load_step(path: str, max_solids: int = 1000, progress=None) -> list[SolidInfo]:
    p=Path(path)
    if not p.is_file(): raise FileNotFoundError(str(path))
    if p.suffix.lower() not in ('.stp','.step'): raise ValueError('Prototyp B-Rep wymaga STEP/STP (eksport z ZW3D).')
    document=TDocStd_Document(TCollection_ExtendedString('BinXCAF'))
    reader=STEPCAFControl_Reader();reader.SetNameMode(True);reader.SetColorMode(True)
    if reader.ReadFile(str(p))!=IFSelect_RetDone: raise ValueError('Nie można odczytać STEP: '+str(p))
    if not reader.Transfer(document): raise ValueError('Błąd transferu STEP: '+str(p))
    tool=XCAFDoc_DocumentTool.ShapeTool_s(document.Main())
    roots=TDF_LabelSequence();tool.GetFreeShapes(roots)
    out=[]
    def add_shape(shape,name,hierarchy,name_origin):
        solids=list(_solids(shape))
        for k,s in enumerate(solids,1):
            if len(out)>=max_solids: raise ValueError(f'Limit bezpieczenstwa: {max_solids} bryl na plik')
            name2=name if len(solids)==1 else f'{name}#{k}'
            info=describe(s,name2,hierarchy+'/'+name2,str(p))
            info.name_origin=name_origin
            out.append(info)
            if progress and len(out)%10==0: progress(f'{p.name}: wczytano {len(out)} brył')
    def walk(lab: TDF_Label, parent_loc: TopLoc_Location, hierarchy:str, depth:int):
        if depth>32: raise ValueError('Zbyt głębokie podzłożenie (>32 poziomów)')
        is_ref=tool.IsReference_s(lab)
        actual=TDF_Label()
        if is_ref and tool.GetReferredShape_s(lab,actual):
            target=actual
            loc=parent_loc.Multiplied(tool.GetLocation_s(lab))
        else:target=lab;loc=parent_loc
        # ZW3D eksportuje czasem referencję jako =>[0:1:1:102].
        # To znacznik OCAF, nie nazwa części; preferuj nazwę docelowego kształtu.
        local_name=_label_name(lab,'')
        target_name=_label_name(target,'')
        name_origin='explicit' if _real_name(local_name) else 'definition_fallback'
        label_name=local_name if _real_name(local_name) else target_name
        if not _real_name(label_name):
            name_origin='generated'
            meaningful=[v for v in reversed(hierarchy.split('/')) if _real_name(v)]
            label_name=meaningful[0] if meaningful else f'Element_{len(out)+1:04d}'
        fullname=f'{hierarchy}/{label_name}' if hierarchy else label_name
        comps=TDF_LabelSequence()
        if tool.GetComponents_s(target,comps) and comps.Length()>0:
            for idx in range(1,comps.Length()+1): walk(comps.Value(idx),loc,fullname,depth+1)
        else:
            sh=tool.GetShape_s(target)
            if sh.IsNull():return
            # Apply parent transform to shape if necessary. A shape may have its own location.
            if not loc.IsIdentity(): sh=sh.Moved(loc)
            add_shape(sh,label_name,fullname,name_origin)
    for i in range(1,roots.Length()+1): walk(roots.Value(i),TopLoc_Location(),'',0)
    if not out: raise ValueError('W pliku STEP nie znaleziono zadnej bryly zamknietej (SOLID).')
    if progress:progress(f'{p.name}: gotowe {len(out)} brył')
    return out


COLORS={'SAME':(0.15,0.68,0.26),'RENAMED':(0.15,0.68,0.26),
        'MOVED':(0.12,0.65,0.85),'CHANGED':(0.40,0.35,0.83),
        'ADDED':(0.20,0.40,0.95),'REMOVED':(0.90,0.56,0.24),
        'UNCERTAIN':(0.65,0.68,0.72)}

class ColoredDocument:
    """Unique part definitions + explicit face styles + assembly occurrence styles.

    A located shape passed straight to AddShape may become a reference label.
    Face labels must be children of the unlocated definition, never that reference.
    """
    def __init__(self):
        from OCP.TopoDS import TopoDS_Compound
        from OCP.BRep import BRep_Builder
        self.doc=TDocStd_Document(TCollection_ExtendedString('BinXCAF'))
        self.tool=XCAFDoc_DocumentTool.ShapeTool_s(self.doc.Main())
        self.colors=XCAFDoc_DocumentTool.ColorTool_s(self.doc.Main())
        compound=TopoDS_Compound();BRep_Builder().MakeCompound(compound)
        self.root=self.tool.AddShape(compound,True)
        TDataStd_Name.Set_s(self.root,TCollection_ExtendedString('DS Compare'))
        self.count=0

    def add(self,shape,name,rgb):
        from OCP.BRepBuilderAPI import BRepBuilderAPI_Copy
        loc=shape.Location()
        local=shape.Located(TopLoc_Location())
        local=BRepBuilderAPI_Copy(local,True,False).Shape()
        label=self.tool.AddShape(local,False)
        col=Quantity_Color(*map(float,rgb),Quantity_TOC_RGB)
        TDataStd_Name.Set_s(label,TCollection_ExtendedString(name))
        for kind in (XCAFDoc_ColorType.XCAFDoc_ColorGen,XCAFDoc_ColorType.XCAFDoc_ColorSurf):
            self.colors.SetColor(label,col,kind)
        for face in _faces(local):
            sub=self.tool.AddSubShape(label,face)
            if sub.IsNull():raise RuntimeError('Nie można przypisać koloru powierzchni')
            self.colors.SetColor(sub,col,XCAFDoc_ColorType.XCAFDoc_ColorSurf)
            self.colors.SetColor(sub,col,XCAFDoc_ColorType.XCAFDoc_ColorGen)
        occurrence=self.tool.AddComponent(self.root,label,loc)
        TDataStd_Name.Set_s(occurrence,TCollection_ExtendedString(name))
        for kind in (XCAFDoc_ColorType.XCAFDoc_ColorGen,XCAFDoc_ColorType.XCAFDoc_ColorSurf):
            self.colors.SetColor(occurrence,col,kind)
        self.count+=1

    def write(self,path):
        import os
        from OCP.Interface import Interface_Static
        from OCP.STEPControl import STEPControl_Controller
        STEPControl_Controller.Init_s()
        schema=os.getenv('DSCOMPARE_STEP_SCHEMA','AP214IS')
        if schema not in ('AP214IS','AP242DIS'):schema='AP214IS'
        if not Interface_Static.SetCVal_s('write.step.schema',schema):
            raise RuntimeError('Nie można ustawić schematu STEP')
        Interface_Static.SetIVal_s('write.step.assembly',1)
        self.tool.UpdateAssemblies()
        writer=STEPCAFControl_Writer();writer.SetNameMode(True);writer.SetColorMode(True)
        if not writer.Transfer(self.doc):raise RuntimeError('Transfer kolorowego STEP nie powiódł się')
        target=Path(path);temporary=target.with_name(target.name+'.tmp')
        try:
            if writer.Write(str(temporary))!=IFSelect_RetDone:raise RuntimeError('Zapis STEP nie powiódł się')
            diag=inspect_step_colors(str(temporary))
            if diag['bryly_bez_koloru'] or diag['powierzchnie_bez_koloru']:
                raise RuntimeError('Niepełny zapis kolorów powierzchni STEP')
            temporary.replace(target)
        finally:
            if temporary.exists():temporary.unlink()


def export_colored_step(path: str, records, a_parts, b_parts, colors=None):
    palette={**COLORS,**(colors or {})}
    document=ColoredDocument()
    for number,r in enumerate(records):
        if r.b_index is not None:part=b_parts[r.b_index];model='B'
        elif r.a_index is not None:part=a_parts[r.a_index];model='A'
        else:continue
        document.add(part.shape,f'[{r.status}] [R{number:06d}] {part.name} [{model}]',palette[r.status])
    document.write(path)


def export_differences_step(path: str, records, a_parts, b_parts,
                            tolerance: float = 0.01, progress=None,
                            max_changed: int = 60, colors: dict | None = None):
    """Second STEP: highlight *only* changed material (A\\B orange, B\\A violet).

    For ADDED/REMOVED include the whole new/old body. For MOVED include
    ghost old + new placement; no ghosts in the main comparison STEP.
    CHANGED requires two real Boolean cuts, executed only for this export.
    """
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut
    from OCP.BRepGProp import BRepGProp
    from OCP.GProp import GProp_GProps
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopAbs import TopAbs_SOLID, TopAbs_FACE

    changed = [r for r in records if r.status == 'CHANGED']
    if len(changed) > max_changed:
        raise ValueError(f'Model ma {len(changed)} zmienionych par. Szczegółowa geometria różnic '
                         f'ograniczona do {max_changed}; rozważ porównanie podzłożenia.')

    document=ColoredDocument()
    palette={**COLORS, **(colors or {})}
    added_rgb=tuple(palette['ADDED']); removed_rgb=tuple(palette['REMOVED'])
    n=0; deltas=[]; errors=[]

    def insert(shape, name, rgb):
        nonlocal n
        exp=TopExp_Explorer(shape,TopAbs_SOLID)
        if not exp.More():return 0.0
        props=GProp_GProps();BRepGProp.VolumeProperties_s(shape,props)
        volume=max(0.0,float(props.Mass()))
        if volume <= max(tolerance**3,1e-5):return 0.0
        document.add(shape,name,rgb)
        n+=1
        return volume

    def cut_shape(a,b):
        op=BRepAlgoAPI_Cut(a,b)
        op.SetFuzzyValue(max(tolerance/100.,1e-6))
        op.Build()
        if not op.IsDone():raise RuntimeError('Boolean CUT not completed')
        return op.Shape()

    for num,r in enumerate(records,1):
        old=a_parts[r.a_index] if r.a_index is not None else None
        new=b_parts[r.b_index] if r.b_index is not None else None
        if r.status in ('SAME','RENAMED','UNCERTAIN'):continue
        key=f'{num:04d}'
        if r.status=='ADDED':
            insert(new.shape,key+' NOWA: '+new.name,added_rgb)
        elif r.status=='REMOVED':
            insert(old.shape,key+' USUNIETA: '+old.name,removed_rgb)
        elif r.status=='MOVED':
            insert(old.shape,key+' POPRZEDNIE POLOZENIE: '+old.name,removed_rgb)
            insert(new.shape,key+' NOWE POLOZENIE: '+new.name,tuple(palette['MOVED']))
        elif r.status=='CHANGED':
            if progress:progress(f'Różnice B-Rep {len(deltas)+1}/{len(changed)}: {new.name}')
            try:
                va=insert(cut_shape(old.shape,new.shape),key+' USUNIETY MATERIAL: '+old.name,removed_rgb)
                vb=insert(cut_shape(new.shape,old.shape),key+' DODANY MATERIAL: '+new.name,tuple(palette['CHANGED']))
                deltas.append((old.name,new.name,round(va,5),round(vb,5)))
            except Exception as exc:
                errors.append(f'{new.path}: {exc}')
    if n:
        document.write(path)
    return {'written':n>0,'solids':n,'changes':deltas,'errors':errors}
