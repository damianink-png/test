"""Independent STEP->VTK mesh cache. Every solid is represented (no global triangle truncation).

Mesh quality changes tessellation error only. Results are visualization; B-Rep is
kept in STEP and is used separately for the precise geometric comparison.
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
from OCP.STEPCAFControl import STEPCAFControl_Reader
from OCP.TDocStd import TDocStd_Document
from OCP.TCollection import TCollection_ExtendedString
from OCP.TDF import TDF_LabelSequence,TDF_Label
from OCP.TopLoc import TopLoc_Location
from OCP.XCAFDoc import XCAFDoc_DocumentTool, XCAFDoc_ColorType
from OCP.Quantity import Quantity_Color
from OCP.IFSelect import IFSelect_RetDone
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_SOLID
from .preview3d import _faces_meshed
from .step_io import _label_name, COLORS


def _rgb(col):
    return [float(col.Red()),float(col.Green()),float(col.Blue())]


def make_mesh(step_path, out_path, quality='normalna', notify=None):
    step=Path(step_path)
    if not step.is_file(): raise FileNotFoundError(str(step))
    levels={'szybka':0.027, 'normalna':0.011, 'dokladna':0.0035}
    if quality not in levels:raise ValueError('Niewłaściwa szczegółowość siatki')
    doc=TDocStd_Document(TCollection_ExtendedString('BinXCAF'))
    reader=STEPCAFControl_Reader()
    reader.SetColorMode(True);reader.SetNameMode(True)
    if reader.ReadFile(str(step))!=IFSelect_RetDone or not reader.Transfer(doc):
        raise RuntimeError('Nie można wczytać geometrii STEP')
    tool=XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())
    color_tool=XCAFDoc_DocumentTool.ColorTool_s(doc.Main())
    roots=TDF_LabelSequence();tool.GetFreeShapes(roots)
    mesh_points=[];mesh_offsets=[0];mesh_rgb=[];mesh_names=[];solid_count=0;attempted=0;missing=[]
    # Each resulting colored STEP entity is a separate top-level body. For
    # external assemblies the STEPCAF reader can expose nested components.
    def visit(label, depth=0, parent_loc=None, inherited_rgb=None):
        nonlocal solid_count,attempted
        if depth>35:raise RuntimeError('Zbyt głęboka struktura modelu STEP')
        if parent_loc is None:parent_loc=TopLoc_Location()
        target=TDF_Label();loc=parent_loc
        if tool.IsReference_s(label) and tool.GetReferredShape_s(label,target):
            loc=parent_loc.Multiplied(tool.GetLocation_s(label))
        else:target=label
        col=Quantity_Color();has=False
        for source in (label,target):
            has=(color_tool.GetColor_s(source,XCAFDoc_ColorType.XCAFDoc_ColorSurf,col) or
                 color_tool.GetColor_s(source,XCAFDoc_ColorType.XCAFDoc_ColorGen,col))
            if has:break
        rgb=_rgb(col) if has else (inherited_rgb or [0.61,0.70,0.80])
        comps=TDF_LabelSequence()
        if tool.GetComponents_s(target,comps) and comps.Length():
            for i in range(1,comps.Length()+1):visit(comps.Value(i),depth+1,loc,rgb)
            return
        sh=tool.GetShape_s(target)
        if sh.IsNull():return
        if not loc.IsIdentity():sh=sh.Moved(loc)
        explorer=TopExp_Explorer(sh,TopAbs_SOLID)
        # Mesh only the concrete shape once, at a deflection adapted to size.
        name=_label_name(label,_label_name(target,'Bryła'))
        while explorer.More():
            sol=explorer.Current();attempted+=1
            from OCP.Bnd import Bnd_Box
            from OCP.BRepBndLib import BRepBndLib
            box=Bnd_Box();BRepBndLib.Add_s(sol,box)
            b=box.Get();extent=max(b[3]-b[0],b[4]-b[1],b[5]-b[2],1.)
            linear=max(0.4,min(12.,extent*levels[quality]))
            pts=[]
            for tri in _faces_meshed(sol,linear):
                pts.extend(tri)
            if pts:
                a=np.asarray(pts,dtype=np.float32).reshape(-1,3)
                mesh_points.append(a)
                mesh_offsets.append(mesh_offsets[-1]+len(a))
                mesh_rgb.append(rgb)
                mesh_names.append(name)
                solid_count+=1
                if notify and solid_count%100==0:notify(f'Siatka 3D: {solid_count} brył...')
            else:missing.append(name)
            explorer.Next()
    for i in range(1,roots.Length()+1):visit(roots.Value(i))
    if not mesh_points:raise ValueError('W STEP nie znaleziono brył możliwych do wyświetlenia')
    pts=np.concatenate(mesh_points)
    target=Path(out_path);target.parent.mkdir(parents=True,exist_ok=True)
    np.savez_compressed(target,vertices=pts,offsets=np.asarray(mesh_offsets,dtype=np.int64),
         colors=np.asarray(mesh_rgb,dtype=np.float32),names=np.asarray(mesh_names,dtype=str))
    return {'bryly':solid_count,'trojkaty':len(pts)//3,'kompletne':not missing,'oczekiwane_bryly':attempted,'pominiete':missing,
            'jakosc':quality,'zrodlo':str(step),'plik':str(target)}
