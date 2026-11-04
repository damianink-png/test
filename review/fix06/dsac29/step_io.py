"""STEPCAF load/save to keep STEP names and per-body colors. Lengths expected in mm."""
from __future__ import annotations
import json
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
from OCP.Quantity import Quantity_Color,Quantity_ColorRGBA,Quantity_TOC_RGB
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
    alphas=[]
    seen=[]; colored_labels=0;colored_faces=0;missing_bodies=0;missing_faces=0
    solid_instances=0;non_solid_leaves=0
    def detect(lab,depth=0):
        nonlocal colored_labels,colored_faces,missing_bodies,missing_faces,solid_instances,non_solid_leaves
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
        native_solids=sum(1 for _ in _solids(shape))
        solid_instances+=native_solids
        if native_solids==0:non_solid_leaves+=1
        color=Quantity_Color()
        has=(colors.GetColor_s(lab,XCAFDoc_ColorType.XCAFDoc_ColorSurf,color) or
             colors.GetColor_s(lab,XCAFDoc_ColorType.XCAFDoc_ColorGen,color))
        if has:
            colored_labels+=1
            seen.append(tuple(round(x,4) for x in [color.Red(),color.Green(),color.Blue()]))
        else:missing_bodies+=1
        for face in _faces(shape):
            facecol=Quantity_ColorRGBA()
            if colors.GetColor(face,XCAFDoc_ColorType.XCAFDoc_ColorSurf,facecol):
                colored_faces+=1
                alphas.append(round(facecol.Alpha(),4))
                facecol=facecol.GetRGB()
                seen.append(tuple(round(x,4) for x in [facecol.Red(),facecol.Green(),facecol.Blue()]))
            else:missing_faces+=1
    for idx in range(1,roots.Length()+1):detect(roots.Value(idx))
    # Diagnostyka zapisanych rekordów stylu STEP, a nie tylko wyglądu CADbro.
    from .step_structure import structure_counts
    structure=structure_counts(p)
    result={'liczba_etykiet':roots.Length(),'bryly_wynikowe':solid_instances,
            'elementy_bez_bryly':non_solid_leaves,'bryly_bez_koloru':missing_bodies,'powierzchnie_bez_koloru':missing_faces,
            'pokolorowane_etykiety':colored_labels,
            'pokolorowane_powierzchnie':colored_faces,
            'brak_kolorow_powierzchni':not bool(colored_faces),
            'kolory_wczytane_rgb':sorted(set(seen)),
            'alfy_powierzchni':sorted(set(alphas)),
            'powierzchnie_przezroczyste':sum(x<0.9999 for x in alphas),
            'rekordy_przezroczystosci_step':structure['alpha'],
            'rekordy_kolorow_step':structure['colors'],
            'rekordy_stylow_step':structure['styles']}
    if not result['rekordy_kolorow_step'] or not result['rekordy_stylow_step']:
        raise RuntimeError('STEP został zapisany bez rekordów koloru — nie uznajemy eksportu za udany')
    if not (colored_labels or colored_faces):
        raise RuntimeError('Po ponownym wczytaniu STEP nie wykryto kolorów przypisanych do brył/powierzchni')
    return result

def load_step(path: str, max_solids: int = 20000, progress=None, diagnostics=None) -> list[SolidInfo]:
    if not 1<=max_solids<=50000:raise ValueError('Limit brył musi wynosić od 1 do 50000')
    p=Path(path)
    if not p.is_file(): raise FileNotFoundError(str(path))
    if p.suffix.lower() not in ('.stp','.step'): raise ValueError('Prototyp B-Rep wymaga STEP/STP (eksport z ZW3D).')
    if progress: progress(f'{p.name}: odczyt i dekodowanie STEP…')
    document=TDocStd_Document(TCollection_ExtendedString('BinXCAF'))
    reader=STEPCAFControl_Reader();reader.SetNameMode(True);reader.SetColorMode(False)
    for setter_name in ('SetLayerMode','SetMatMode','SetPropsMode','SetGDTMode'):
        setter=getattr(reader,setter_name,None)
        if setter is not None:setter(False)
    from time import perf_counter
    t_read=perf_counter()
    if reader.ReadFile(str(p))!=IFSelect_RetDone: raise ValueError('Nie można odczytać STEP: '+str(p))
    read_s=perf_counter()-t_read
    if progress: progress(f'{p.name}: ReadFile OK ({read_s:.1f} s); rozpoczynam transfer XCAF…')
    t_transfer=perf_counter()
    if not reader.Transfer(document): raise ValueError('Błąd transferu STEP: '+str(p))
    transfer_s=perf_counter()-t_transfer
    if diagnostics is not None:
        diagnostics['step_readfile_s']=round(read_s,3)
        diagnostics['step_xcaf_transfer_s']=round(transfer_s,3)
    if progress: progress(f'{p.name}: Transfer XCAF OK ({transfer_s:.1f} s); budowanie charakterystyk brył…')
    tool=XCAFDoc_DocumentTool.ShapeTool_s(document.Main())
    roots=TDF_LabelSequence();tool.GetFreeShapes(roots)
    from .geometry import DescriptionCache
    description_cache=DescriptionCache()
    out=[]
    stats={"solids":0,"faces_outside_solids":0,"solid_limit":max_solids,"reversed_solid_orientations":0}
    def add_shape(shape,name,hierarchy,name_origin):
        outside=TopExp_Explorer(shape,TopAbs_FACE,TopAbs_SOLID)
        while outside.More():stats['faces_outside_solids']+=1;outside.Next()
        solids=list(_solids(shape))
        for k,s in enumerate(solids,1):
            if len(out)>=max_solids: raise ValueError(f'Limit bezpieczenstwa: {max_solids} bryl na plik')
            name2=name if len(solids)==1 else f'{name}#{k}'
            try:
                info=description_cache.describe(s,name2,hierarchy+'/'+name2,str(p))
            except ValueError as exc:
                if 'zerowa/ujemna objetosc' not in str(exc):raise
                from .import_validation import orient_positive_solid
                corrected=orient_positive_solid(s,hierarchy+'/'+name2)
                info=description_cache.describe(corrected,name2,hierarchy+'/'+name2,str(p))
                stats['reversed_solid_orientations']+=1
                if progress:progress('Skorygowano orientację zamkniętej bryły: '+hierarchy+'/'+name2)
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
    stats['solids']=len(out)
    if diagnostics is not None:diagnostics.update(stats)
    if progress:
        progress(f'{p.name}: gotowe {len(out)} brył; powierzchni poza bryłami: {stats["faces_outside_solids"]}')
        if stats['faces_outside_solids']:progress('UWAGA: powierzchnie poza bryłami SOLID nie są porównywane ani uwzględniane w masie.')
    return out


from .palette import COLORS

# Distinct subassemblies can be hidden as a whole in CAD applications that
# preserve the XCAF/STEP product assembly structure (including ZW3D on import).
REVISION_GROUPS = {
    'SAME': '01_BEZ_ZMIAN',
    'RENAMED': '01_BEZ_ZMIAN',
    'CHANGED': '02_ZMIENIONE',
    'MOVED': '03_PRZESUNIETE',
    'ADDED': '04_NOWE',
    'REMOVED': '05_USUNIETE',
    'UNCERTAIN': '06_DO_SPRAWDZENIA', # explicitly unverified material/geometry review
}

def _single_solid_without_wrapper(shape):
    """Remove a COMPOUND wrapping exactly one SOLID, retaining its position."""
    import os
    from OCP.TopAbs import TopAbs_COMPOUND
    from OCP.TopExp import TopExp_Explorer
    if shape.ShapeType()!=TopAbs_COMPOUND:
        return shape
    solids=list(_solids(shape))
    if os.getenv('DSCOMPARE_STRICT_SOLIDS','0')=='1' and len(solids)!=1:
        raise ValueError(f'DSCOMPARE_STRICT_SOLIDS: oczekiwano jednej bryły, wykryto {len(solids)}')
    if len(solids)!=1:
        return shape
    outside=TopExp_Explorer(shape,TopAbs_FACE,TopAbs_SOLID)
    if outside.More():
        return shape
    return solids[0]


class ColoredDocument:
    """XCAF assembly writer with shared part definitions and per-face RGBA.

    Each unique native geometry + color + opacity is only copied and styled
    once. Repeated occurrences remain separately located assembly components.
    When enabled, categorized subassemblies can be suppressed from the CAD
    assembly tree without deleting geometry.
    """
    def __init__(self, group_by_status=False, reuse_definitions=True, flat_zw3d=False, rootless_group=False):
        from OCP.TopoDS import TopoDS_Compound
        from OCP.BRep import BRep_Builder
        self.doc=TDocStd_Document(TCollection_ExtendedString('BinXCAF'))
        self.tool=XCAFDoc_DocumentTool.ShapeTool_s(self.doc.Main())
        self.colors=XCAFDoc_DocumentTool.ColorTool_s(self.doc.Main())
        # STEP layers provide switchable status groups without empty assembly products.
        self.layers=XCAFDoc_DocumentTool.LayerTool_s(self.doc.Main())
        self.layered_count=0
        # STEP hierarchy can use legitimate SHAPE_REPRESENTATION
        # products. Color on occurrences is the cause of excess anonymous ABSR.
        # The flat mode has no containers / usages: one STEP PRODUCT per real SOLID.
        self.flat_zw3d=bool(flat_zw3d)
        self.rootless_group=bool(rootless_group and not self.flat_zw3d and group_by_status)
        # Distinct test: each status group becomes a genuine free XCAF
        # assembly root, not a child of a dummy DS Compare wrapper.
        self.root=None if self.flat_zw3d or self.rootless_group else self._assembly('DS COMPARE - POROWNANIE REWIZJI')
        self.count=0
        self.transparent_faces=0
        self.group_by_status=bool(group_by_status and not self.flat_zw3d)
        self._groups={}
        self._definitions={}
        self.reuse_definitions=bool(reuse_definitions and not self.flat_zw3d)
        import os
        self.body_colors=os.environ.get('DSCOMPARE_BODY_COLORS','0')=='1' and group_by_status
        self.face_styles_created=0
        self.definitions_created=0
        self.definitions_reused=0
        self._named_definitions={}
        # Only previously serialized exact BRep signatures are indexed;
        # hash lookup by itself never bypasses the original byte fingerprint.
        self._named_fingerprint_index={}
        self._exact_index_hits=0
        self._exact_reuse_attempts=0
        self._exact_reuse_seconds=0.0

    @staticmethod
    def _serialized_brep_signature(shape):
        """Exact serialized BRep fingerprint, never an approximate geometry test."""
        import hashlib
        import os
        import tempfile
        from OCP.BRepTools import BRepTools
        fd,filename=tempfile.mkstemp(prefix='dscompare_exact_',suffix='.brep')
        os.close(fd)
        try:
            if not BRepTools.Write_s(shape,filename):return None
            size=os.path.getsize(filename)
            # Four MiB discarded exact grouping for larger repeated parts.
            # Hash incrementally and support up to 32 MiB per definition.
            # The fingerprint is evidence of equality, never an approximation.
            if not 0<size<=32*1024*1024:return None
            digest=hashlib.sha256()
            with open(filename,'rb') as handle:
                for chunk in iter(lambda:handle.read(1024*1024),b''):
                    digest.update(chunk)
            return size,digest.digest()
        except (OSError,RuntimeError,TypeError):
            return None
        finally:
            try:os.unlink(filename)
            except OSError:pass

    def _assembly(self,name,parent=None):
        from OCP.TopoDS import TopoDS_Compound
        from OCP.BRep import BRep_Builder
        shape=TopoDS_Compound();BRep_Builder().MakeCompound(shape)
        label=self.tool.AddShape(shape,True)
        TDataStd_Name.Set_s(label,TCollection_ExtendedString(name))
        if parent is not None:
            comp=self.tool.AddComponent(parent,label,TopLoc_Location())
            TDataStd_Name.Set_s(comp,TCollection_ExtendedString(name))
        return label

    def _parent(self,group,revision,pair_id=None,region=None):
        if not self.group_by_status or group is None:return self.root
        name=REVISION_GROUPS.get(group,group)
        if name not in self._groups:self._groups[name]=self._assembly(name,self.root)
        parent=self._groups[name]
        if group=='CHANGED' and pair_id is not None:
            pair_key=(name,'PAIR',str(pair_id))
            if pair_key not in self._groups:
                self._groups[pair_key]=self._assembly(str(pair_id),parent)
            parent=self._groups[pair_key]
            if region is not None:
                region_key=pair_key+(str(region),)
                if region_key not in self._groups:
                    self._groups[region_key]=self._assembly(str(region),parent)
                return self._groups[region_key]
        if group in ('CHANGED','MOVED','UNCERTAIN') and revision in ('A','B'):
            name2=('A_STARA' if revision=='A' else 'B_NOWA')
            path=(name,name2)
            if path not in self._groups:self._groups[path]=self._assembly(name2,parent)
            parent=self._groups[path]
        return parent

    def add(self,shape,name,rgb,alpha=1.0,group=None,revision=None,pair_id=None,region=None,source_name=None):
        import math
        name=str(name or '').strip() or f'Element_{self.count+1:04d}'
        if not math.isfinite(float(alpha)) or not 0.0 <= float(alpha) <= 1.0:
            raise ValueError('Nieprawidłowa przezroczystość')
        import os
        loc=shape.Location()
        local=_single_solid_without_wrapper(shape.Located(TopLoc_Location()))
        if os.getenv('DSCOMPARE_STRICT_SOLIDS','0')=='1':
            count=sum(1 for _ in _solids(local))
            if count!=1:
                raise ValueError(f'DSCOMPARE_STRICT_SOLIDS: {name}: {count} brył zamiast jednej')
        # In flat ZW3D mode locations must be baked into the top-level
        # occurrences rather than being represented by assembly links.
        if self.flat_zw3d:
            from OCP.BRepBuilderAPI import BRepBuilderAPI_Copy, BRepBuilderAPI_Transform
            # AddSubShape() cannot color faces of located top-level shapes in OCAF.
            # Move the geometry itself into world coordinates and clear Location.
            world=(BRepBuilderAPI_Transform(local,loc.Transformation(),True).Shape()
                   if not loc.IsIdentity() else BRepBuilderAPI_Copy(local,True,False).Shape())
            if world.IsNull():raise ValueError('Pusta geometria komponentu: '+str(name))
            if sum(1 for _ in _solids(world))!=1:
                raise ValueError('Eksport bez pustych ABSR wymaga pojedynczej bryly SOLID: '+str(name))
            from OCP.BRepGProp import BRepGProp
            from OCP.GProp import GProp_GProps
            volume=GProp_GProps();BRepGProp.VolumeProperties_s(world,volume)
            if volume.Mass()<=1e-9:
                raise ValueError('Zerowa objetosc komponentu: '+str(name))
            label=self.tool.AddShape(world,False)
            if label.IsNull():raise RuntimeError('Nie mozna dodac bryly jako produktu STEP: '+str(name))
            TDataStd_Name.Set_s(label,TCollection_ExtendedString(name))
            if group is not None:
                layer=REVISION_GROUPS.get(group,str(group))
                if pair_id is not None:layer+='__'+str(pair_id)+'__'+str(region or '')
                if group in ('MOVED','CHANGED','UNCERTAIN') and revision in ('A','B'):
                    layer+='__'+('A_STARA' if revision=='A' else 'B_NOWA')
                self.layers.SetLayer(label,TCollection_ExtendedString(layer))
                self.layered_count+=1
            color=Quantity_ColorRGBA(Quantity_Color(*map(float,rgb),Quantity_TOC_RGB),float(alpha))
            for kind in (XCAFDoc_ColorType.XCAFDoc_ColorGen,XCAFDoc_ColorType.XCAFDoc_ColorSurf):
                self.colors.SetColor(label,color,kind)
            num_faces=0
            for face in (() if self.body_colors and alpha>=0.9999 else _faces(world)):
                num_faces+=1
                self.face_styles_created+=1
                sub=self.tool.AddSubShape(label,face)
                if sub.IsNull():raise RuntimeError('Nie mozna przypisac koloru powierzchni: '+str(name))
                self.colors.SetColor(sub,color,XCAFDoc_ColorType.XCAFDoc_ColorSurf)
                self.colors.SetColor(sub,color,XCAFDoc_ColorType.XCAFDoc_ColorGen)
            self.definitions_created+=1
            if alpha<0.9999:self.transparent_faces+=num_faces
            self.count+=1
            return
        rgba=tuple(round(float(c),7) for c in rgb)+(round(float(alpha),7),)
        key=(hash(local),int(local.Orientation()),rgba)
        # The original name restricts candidates, but cannot prove equivalence.
        source_key=(str(source_name).strip().casefold(),int(local.Orientation()),rgba) if source_name else None
        label=None
        for candidate,known,known_faces in (self._definitions.get(key,()) if self.reuse_definitions else ()):
            if local.IsSame(candidate) and local.Orientation()==candidate.Orientation():
                label=known;num_faces=known_faces;break
        if label is None and self.reuse_definitions and source_key:
            candidates=self._named_definitions.get(source_key,())
            if candidates:
                import time
                started=time.perf_counter()
                self._exact_reuse_attempts+=1
                fingerprint=self._serialized_brep_signature(local)
                if fingerprint is not None:
                    index=self._named_fingerprint_index.setdefault(source_key,{})
                    candidate=index.get(fingerprint)
                    if candidate is not None:
                        self._exact_index_hits+=1
                        label=candidate['label'];num_faces=candidate['faces']
                    else:
                        for candidate in candidates:
                            if not candidate['checked']:
                                candidate['fingerprint']=self._serialized_brep_signature(candidate['shape'])
                                candidate['checked']=True
                                if candidate['fingerprint'] is not None:
                                    index.setdefault(candidate['fingerprint'],candidate)
                            if candidate['fingerprint'] is not None and fingerprint==candidate['fingerprint']:
                                label=candidate['label'];num_faces=candidate['faces']
                                break
                self._exact_reuse_seconds+=time.perf_counter()-started
        if label is None:
            # Do not modify the source shape. Copy only once per native definition.
            from OCP.BRepBuilderAPI import BRepBuilderAPI_Copy
            unlocated=BRepBuilderAPI_Copy(local,True,False).Shape()
            label=self.tool.AddShape(unlocated,False)
            col=Quantity_ColorRGBA(Quantity_Color(*map(float,rgb),Quantity_TOC_RGB),float(alpha))
            TDataStd_Name.Set_s(label,TCollection_ExtendedString(name))
            for kind in (XCAFDoc_ColorType.XCAFDoc_ColorGen,XCAFDoc_ColorType.XCAFDoc_ColorSurf):
                self.colors.SetColor(label,col,kind)
            # Face level opacity is important: occurrence-only alpha is often
            # discarded during STEP -> CAD transfer.
            num_faces=0
            for face in (() if self.body_colors else _faces(unlocated)):
                num_faces+=1
                self.face_styles_created+=1
                sub=self.tool.AddSubShape(label,face)
                if sub.IsNull():raise RuntimeError('Nie można przypisać koloru powierzchni')
                self.colors.SetColor(sub,col,XCAFDoc_ColorType.XCAFDoc_ColorSurf)
                self.colors.SetColor(sub,col,XCAFDoc_ColorType.XCAFDoc_ColorGen)
            if self.reuse_definitions:
                self._definitions.setdefault(key,[]).append((local,label,num_faces))
                if source_key:
                    self._named_definitions.setdefault(source_key,[]).append(
                        {'shape':local,'label':label,'faces':num_faces,'checked':False,'fingerprint':None})
            self.definitions_created+=1
        else:
            self.definitions_reused+=1
        parent=self._parent(group,revision,pair_id,region)
        occurrence=self.tool.AddComponent(parent,label,loc)
        TDataStd_Name.Set_s(occurrence,TCollection_ExtendedString(name))
        # IMPORTANT: Color labels on referenced occurrences generate two
        # extra anonymous SHAPE_REPRESENTATION entities per occurrence.
        # The product definition and individual faces are colored already.
        if alpha<0.9999:
            self.transparent_faces+=num_faces
        self.count+=1

    def write(self,path):
        import os
        from OCP.Interface import Interface_Static
        from OCP.STEPControl import STEPControl_Controller
        STEPControl_Controller.Init_s()
        # Experimental, off only when explicitly requested. Many CAD
        # importers rebuild these 2D parametric curves from the 3D edges.
        # ZW3D 2019 compatibility must be checked before changing defaults.
        pcurve_mode=os.getenv('DSCOMPARE_STEP_PCURVES','on').strip().lower()
        if pcurve_mode not in ('on','off'):
            raise ValueError('DSCOMPARE_STEP_PCURVES: dozwolone on/off')
        if not Interface_Static.SetIVal_s('write.surfacecurve.mode',int(pcurve_mode=='on')):
            raise RuntimeError('Nie mozna ustawic zapisu krzywych 2D STEP')
        schema=os.getenv('DSCOMPARE_STEP_SCHEMA','AP214IS')
        if schema not in ('AP214IS','AP242DIS'):schema='AP214IS'
        if not Interface_Static.SetCVal_s('write.step.schema',schema):
            raise RuntimeError('Nie można ustawić schematu STEP')
        Interface_Static.SetIVal_s('write.step.assembly',1)
        Interface_Static.SetIVal_s('write.step.nonmanifold',0)
        if not self.flat_zw3d:
            self.tool.UpdateAssemblies()
            # Every status subassembly must contain genuine SOLID descendants.
            from OCP.XCAFDoc import XCAFDoc_ShapeTool
            from OCP.TDF import TDF_LabelSequence
            if self.rootless_group:
                roots=[v for key,v in self._groups.items() if isinstance(key,str)]
                if not roots:raise RuntimeError('Brak grup w teście STEP bez głównego kontenera')
            else:
                roots=[self.root]
            n_solids=0
            for assembly_root in roots:
                assembled=XCAFDoc_ShapeTool.GetShape_s(assembly_root)
                if assembled.IsNull():raise RuntimeError('Puste złożenie w eksporcie STEP')
                n_solids+=sum(1 for _ in _solids(assembled))
            if n_solids!=self.count:
                raise RuntimeError(f'Niekompletne zlozenie: bryl {n_solids}, oczekiwano {self.count}')
            groups=list(self._groups.values())
            if self.root is not None:groups.insert(0,self.root)
            for label in groups:
                components=TDF_LabelSequence()
                if not XCAFDoc_ShapeTool.GetComponents_s(label,components) or components.Length()==0:
                    raise RuntimeError('W strukturze STEP pozostalo puste podzlozenie')
        writer=STEPCAFControl_Writer();writer.SetNameMode(True);writer.SetColorMode(True);writer.SetLayerMode(True)
        if not writer.Transfer(self.doc):raise RuntimeError('Transfer kolorowego STEP nie powiódł się')
        target=Path(path);temporary=target.with_name(target.name+'.tmp')
        try:
            if writer.Write(str(temporary))!=IFSelect_RetDone:raise RuntimeError('Zapis STEP nie powiódł się')
            # Full read-back preserves the rigorous v4.6 diagnostics on smaller
            # models. Very large models can opt into lightweight structural
            # checks to avoid an entire second OpenCascade STEP import.
            verify=os.getenv('DSCOMPARE_STEP_VERIFY','auto').lower()
            if verify not in ('auto','full','fast'):verify='auto'
            do_full=(verify=='full' or verify=='auto' and self.count<=150)
            # Read-only mapped scans retain every structural assertion without
            # allocating an entire large STEP as a Python bytes buffer.
            structure=None
            if do_full:
                diag=inspect_step_colors(str(temporary))
                if diag['bryly_bez_koloru'] or (not self.body_colors and diag['powierzchnie_bez_koloru']):
                    raise RuntimeError('Niepełny zapis kolorów powierzchni STEP')
                if diag['pokolorowane_etykiety']!=self.count:
                    raise RuntimeError('Niepełny zapis elementów STEP')
                if diag['bryly_wynikowe']!=self.count or diag['elementy_bez_bryly']:
                    raise RuntimeError('Błąd geometrii eksportu: wynik zawiera nadmiarowe/puste komponenty albo niekompletne bryły')
                if diag['powierzchnie_przezroczyste']!=self.transparent_faces:
                    raise RuntimeError('Niepełny zapis przezroczystości STEP')
                diag['weryfikacja']='pelna_ponowny_import'
            else:
                from .step_structure import structure_counts
                structure=structure_counts(temporary)
                ncol=structure['colors']
                nstyle=structure['styles']
                nalpha=structure['alpha']
                if not ncol or not nstyle or (self.transparent_faces and not nalpha):
                    raise RuntimeError('Wynikowy STEP nie ma oczekiwanych styli koloru/przezroczystości')
                diag={'pokolorowane_etykiety':self.count,
                    'pokolorowane_powierzchnie':None,
                    'powierzchnie_przezroczyste':self.transparent_faces,
                    'rekordy_przezroczystosci_step':nalpha,
                    'rekordy_kolorow_step':ncol,
                    'rekordy_stylow_step':nstyle,
                    'weryfikacja':'szybka_strukturalna_bez_ponownego_importu'}
            if not self.flat_zw3d:
                import re
                if structure is None:
                    from .step_structure import structure_counts
                    structure=structure_counts(temporary)
                # Containers MUST remain to support subassemblies; reject
                # surplus zero-volume PRODUCT leaves rather than flattening.
                products=structure['products']
                usages=structure['usages']
                assemblies=len(self._groups)+(0 if self.rootless_group else 1)
                free_roots=sum(isinstance(k,str) for k in self._groups) if self.rootless_group else 1
                wanted_usages=self.count+assemblies-free_roots
                if products!=self.definitions_created+assemblies or usages!=wanted_usages:
                    raise RuntimeError(f'STEP ma nieoczekiwane produkty: {products} produktow, {usages} powiazan, {self.count} bryl')
                # Only legitimate status/subassembly containers may generate
                # anonymous SHAPE_REPRESENTATION in hierarchical export.
                reps=structure['representations']
                if reps>assemblies:
                    raise RuntimeError(f'Nadmiarowe SHAPE_REPRESENTATION powiązane z wystąpieniami: {reps}; dozwolona liczba kontenerów {assemblies}')
                diag.update(puste_reprezentacje_step=max(0,reps-assemblies),
                            anonimowe_reprezentacje_step=reps,
                            kontrola_wstawien_bez_styli=True)
                diag.update(produkty_step=products,powiazania_zlozenia=usages,
                            rzeczywiste_bryly_step=self.count,podzlozenia_step=assemblies,
                            samodzielne_puste_produkty=0,grupowanie_zlozenia=True,
                            test_bez_korzenia=bool(self.rootless_group),
                            uwaga_absr='Brak kolorów wstawek i nadmiarowych reprezentacji; import ZW3D wymaga potwierdzenia')
            if self.flat_zw3d:
                # Structural regression: no empty compound assembly shells or
                # intermediary product definitions that ZW3D calls ABSR1, ABSR2.
                # These are distinct from empty / non-solid leaves seen on import.
                if structure is None:
                    from .step_structure import structure_counts
                    structure=structure_counts(temporary)
                import re
                products=structure['products']
                usages=structure['usages']
                reps=structure['representations']
                if products!=self.count or usages or reps:
                    raise RuntimeError(f'Wynik STEP ma ukryte produkty zlozenia: produktow={products}, bryl={self.count}, wiazania={usages}, puste reprezentacje={reps}')
                diag.update(produkty_step=products, powiazania_zlozenia=usages,
                            puste_reprezentacje_step=reps, eksport_plaski_bez_absr=True)
            # A compact output is never accepted if the parameter was
            # silently ignored by the OCCT writer.
            if pcurve_mode=='off':
                from .step_structure import mapped_step
                with mapped_step(temporary) as mapped:
                    if b'PCURVE(' in mapped:
                        raise RuntimeError('Kompaktowy STEP nadal zawiera PCURVE')
            diag.update(krzywe_2d_step=('pominiete' if pcurve_mode=='off' else 'zapisane'),
                eksperymentalny_step_bez_pcurves=(pcurve_mode=='off'),
                definicje_unikalne=self.definitions_created,
                ponownie_uzyte_definicje=self.definitions_reused,
                grupowanie_zlozenia=bool(self.group_by_status),
                grupy_warstw_step=self.layered_count,
                zapis_alfy_step=self.transparent_faces>0,
                przezroczystosc_w_zw3d='zalezy_od_importera',
                kolory_na_poziomie_bryl=bool(self.body_colors),
                tryb_bez_pustych_kontenerow=bool(self.flat_zw3d),
                rozmiar_step_mb=round(temporary.stat().st_size/1048576,2),
                style_powierzchni_utworzone=self.face_styles_created,
                sredni_rozmiar_na_definicje_kb=round(temporary.stat().st_size/max(1,self.definitions_created)/1024,1),
                dokladne_porownania_brep=self._exact_reuse_attempts,
                czas_porownan_brep_s=round(self._exact_reuse_seconds,3))
            temporary.replace(target)
            return diag
        finally:
            if temporary.exists():temporary.unlink()

def export_colored_step(path: str, records, a_parts, b_parts, colors=None):
    palette={**COLORS,**(colors or {})}
    document=ColoredDocument(flat_zw3d=True)
    for number,r in enumerate(records):
        if r.b_index is not None:part=b_parts[r.b_index];model='B'
        elif r.a_index is not None:part=a_parts[r.a_index];model='A'
        else:continue
        document.add(part.shape,f'[{r.status}] [R{number:06d}] {part.name} [{model}]',palette[r.status])
    return document.write(path)


def export_differences_step(path: str, records, a_parts, b_parts,
                            tolerance: float = 0.01, progress=None,
                            max_changed: int = 60, colors: dict | None = None,material_regions=None):
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
    if len(changed) > max_changed and material_regions is None:
        raise ValueError(f'Model ma {len(changed)} zmienionych par. Szczegółowa geometria różnic '
                         f'ograniczona do {max_changed}; rozważ porównanie podzłożenia.')

    document=ColoredDocument(flat_zw3d=True)
    from .material_deltas import COLORS as MATERIAL_DEFAULTS
    palette={**COLORS,**MATERIAL_DEFAULTS, **(colors or {})}
    added_rgb=tuple(palette['ADDED']); removed_rgb=tuple(palette['REMOVED'])
    n=0; deltas=[]; errors=[]
    from .material_deltas import COLORS as MATERIAL_COLORS,solids as delta_solids
    material_regions=material_regions or {}

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
        from .boolean_ops import configured
        op=configured(BRepAlgoAPI_Cut,a,b,tolerance)
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
                region=material_regions.get(num-1)
                if region is not None:
                    for kind,shape in [('CHANGED_ADDED',region.added),('CHANGED_REMOVED',region.removed)]:
                        for n_comp,piece in enumerate(delta_solids(shape),1):
                            insert(piece,key+' '+kind+' '+str(n_comp)+': '+new.name,palette[kind])
                    va,vb=region.removed_mm3,region.added_mm3
                else:
                    va=insert(cut_shape(old.shape,new.shape),key+' USUNIETY MATERIAL: '+old.name,removed_rgb)
                    vb=insert(cut_shape(new.shape,old.shape),key+' DODANY MATERIAL: '+new.name,tuple(palette['CHANGED']))
                deltas.append((old.name,new.name,round(va,5),round(vb,5)))
            except Exception as exc:
                errors.append(f'{new.path}: {exc}')
    if n:
        document.write(path)
    return {'written':n>0,'solids':n,'changes':deltas,'errors':errors}


from .palette import REVISION_COLORS

def cad_product_name(name, number, status, role):
    """Conservative portable STEP PRODUCT name for third-party CAD importers.

    Keep the real engineering name visible; avoid brackets and characters which
    some STEP->ZW3D importers interpret as occurrence metadata or path syntax.
    This does NOT remove or merge any SOLID; the report keeps original names.
    """
    import unicodedata
    clean=unicodedata.normalize('NFKD',str(name or '')).encode('ascii','ignore').decode('ascii')
    clean=re.sub(r'[^A-Za-z0-9_.-]+','_',clean).strip('._-')
    if not clean:clean='DETAL'
    clean=clean[:90]
    return f'{clean}__{status}__{role}__P{number:06d}'


def _export_revision_step(path, records, a_parts, b_parts, colors=None, old_alpha=0.4, progress=None, reuse_definitions=True, flat_zw3d=False, rootless_group=False, material_regions=None):
    """Unchanged B once; changed/moved pairs as old A + new B, in world coordinates."""
    from .material_deltas import COLORS as MATERIAL_DEFAULTS
    palette={**REVISION_COLORS,**MATERIAL_DEFAULTS,**(colors or {})}
    document=ColoredDocument(group_by_status=True,reuse_definitions=reuse_definitions,flat_zw3d=flat_zw3d,rootless_group=rootless_group)
    roles={'SAME':0,'OLD':0,'NEW':0}
    product_groups=[]
    total=len(records)
    from .material_deltas import COLORS as MATERIAL_COLORS,solids as delta_solids
    material_regions=material_regions or {}
    changed_parts=0
    for number,r in enumerate(records):
        if progress and number and number%50==0: progress(f'Kolorowy STEP: przygotowano {number}/{total} pozycji...')
        if r.status=='CHANGED' and number in material_regions:
            regions=material_regions[number]
            name=b_parts[r.b_index].name
            for kind,shape,role in (
                ('CHANGED_COMMON',regions.common,'B'),
                ('CHANGED_ADDED',regions.added,'B'),
                ('CHANGED_REMOVED',regions.removed,'A')):
                for component,piece in enumerate(delta_solids(shape),1):
                    changed_parts+=1
                    key_name=cad_product_name(name,number,kind,role)+f'__S{component:03d}'
                    opacity=old_alpha if kind=='CHANGED_REMOVED' else 1.0
                    document.add(piece,key_name,palette[kind],opacity,
                                 group='CHANGED',revision=role,pair_id=f'PARA_{number:06d}_{name[:40]}',region=kind)
                    product_groups.append({'produkt_step':key_name,'status':'CHANGED',
                        'rewizja':role,'rodzaj_materialu':kind,
                        'podzlozenie':['02_ZMIENIONE',f'PARA_{number:06d}',kind],
                        'nazwa_czesci':name,'pozycja':number})
                    roles['OLD' if role=='A' else 'NEW']+=1
            continue
        if r.status in ('SAME','RENAMED'):
            if r.b_index is None:raise ValueError('Brak nowej części dla pozycji bez zmian')
            entries=[(b_parts[r.b_index],'SAME','B',1.0)]
        else:
            entries=[]
            if r.a_index is not None:entries.append((a_parts[r.a_index],'OLD','A',old_alpha))
            if r.b_index is not None:entries.append((b_parts[r.b_index],'NEW','B',1.0))
        for part,role,revision,alpha in entries:
            # Purple is reserved for identical geometry relocated in an unchanged-size group.
            # Its old occurrence is translucent, its new occurrence is opaque.
            key=(
                ('MOVED_OLD' if revision=='A' else 'MOVED') if r.status=='MOVED'
                else ('CHANGED_OLD' if revision=='A' else 'CHANGED_NEW') if r.status=='CHANGED'
                else ('UNCERTAIN_OLD' if revision=='A' else 'UNCERTAIN_NEW') if r.status=='UNCERTAIN'
                else {'SAME':'SAME','OLD':'REMOVED','NEW':'ADDED'}[role]
            )
            legacy_warning=' [DO_SPRAWDZENIA]' if r.status=='UNCERTAIN' else ''
            status_pl={'SAME':'BEZ_ZMIAN','RENAMED':'ZMIANA_NAZWY','MOVED':'PRZESUNIETE','REMOVED':'USUNIETE','ADDED':'NOWE','CHANGED':'ZMIENIONE','UNCERTAIN':'DO_SPRAWDZENIA'}[r.status]
            role_pl={'SAME':'BEZ_ZMIAN','OLD':'STARA','NEW':'NOWA'}[role]
            # Names are actual PRODUCT definitions in STEP (not only the HTML report).
            name=cad_product_name(part.name,number,status_pl,role_pl)
            document.add(part.shape,name,palette[key],alpha,group=r.status,revision=revision,
                         source_name=part.name if r.status in ('SAME','RENAMED') else None)
            group_name=REVISION_GROUPS.get(r.status,'99_INNE')
            group_path=[group_name]
            if r.status in ('CHANGED','MOVED','UNCERTAIN'):
                group_path.append('A_STARA' if revision=='A' else 'B_NOWA')
            product_groups.append({'produkt_step':name,'status':r.status,'rewizja':revision,
                'podzlozenie':group_path,'nazwa_czesci':part.name,'pozycja':number})
            roles[role]+=1
    if progress:progress(f'Kolorowy STEP: {document.count} wystąpień, {document.definitions_created} definicji; zapis pliku...')
    diag=document.write(path)
    # STEP already contains actual native parent/child references.
    manifest=Path(path).with_name('GRUPY_ZW3D.json')
    manifest.write_text(json.dumps({'format':'dscompare-subassembly-groups-v2',
        'status':'natywne_podzlozenia_step' if not flat_zw3d else 'plaskie_warstwy_step',
        'STEP':Path(path).name,'liczba_bryl':document.count,
        'uwaga':'Nie ma pustych lisci; ZW3D 2019 moze inaczej przedstawic kontenery',
        'grupy':product_groups},ensure_ascii=False,indent=2),encoding='utf8')

    if progress:progress('Kolorowy STEP: zapis oraz kontrola styli zakończone.')
    diag.update(export_style='revision_A_B',roles=roles,old_alpha=old_alpha,material_region_solids=changed_parts)
    return diag


def export_revision_step(path, records, a_parts, b_parts, colors=None, old_alpha=0.4, progress=None, material_regions=None):
    """Restore real status subassemblies with independent solid STEP products.

    XCAF parent assembly nodes are necessary and cannot be removed as "empty
    parts"; every *leaf* must be a verified positive-volume SOLID.
    """
    import os
    flat=os.environ.get('DSCOMPARE_FLAT_FALLBACK','0')=='1'
    import time
    from .step_diagnostics import save as save_step_diagnostics
    started=time.perf_counter()
    rows=list(records)
    result=_export_revision_step(path,rows,a_parts,b_parts,colors,old_alpha,progress,
                                 reuse_definitions=not flat,flat_zw3d=flat,material_regions=material_regions)
    result['tryb_zapisu']='plaski_awaryjny' if flat else 'podzlozenia_bez_pustych_lisci'
    result['czas_zapisu_i_weryfikacji_s']=round(time.perf_counter()-started,3)
    try:
        diagnostic=save_step_diagnostics(path,result)
        result['raport_diagnostyki_step']=str(Path(diagnostic).name)
    except Exception as err:
        # A valid verified STEP must remain available even if extra JSON fails.
        result['blad_dodatkowej_diagnostyki_step']=str(err)
        if progress:progress('OSTRZEŻENIE: dodatkowy raport STEP: '+str(err))
    if os.environ.get('DSCOMPARE_ABSR_TEST_OUTPUT')=='1' and not flat:
        folder=Path(path).parent/'TEST_ABSR'
        try:
            folder.mkdir(exist_ok=True)
            candidate=folder/'STEP_BEZ_ABSR.step'
            if progress:progress('Test ABSR: zapis dodatkowego płaskiego STEP (bez podzłożeń)...')
            second=_export_revision_step(str(candidate),rows,a_parts,b_parts,colors,old_alpha,progress,
                                         reuse_definitions=False,flat_zw3d=True,material_regions=material_regions)
            report=save_step_diagnostics(candidate,second)
            result['test_absr_step']=str(candidate.relative_to(Path(path).parent))
            result['test_absr_raport']=str(Path(report).relative_to(Path(path).parent))
            if progress:progress('Test ABSR: płaski STEP zapisany; teraz test podzłożeń bez zbędnego głównego kontenera...')
            test_group=folder/'GRUPY_BEZ_KORZENIA'
            test_group.mkdir(exist_ok=True)
            group_path=test_group/'STEP_GRUPY_BEZ_KORZENIA.step'
            groups=_export_revision_step(str(group_path),rows,a_parts,b_parts,colors,old_alpha,progress,
                                          reuse_definitions=False,flat_zw3d=False,rootless_group=True,material_regions=material_regions)
            groups_report=save_step_diagnostics(group_path,groups)
            result['test_podzlozen_bez_korzenia']=str(group_path.relative_to(Path(path).parent))
            result['test_podzlozen_diagnostyka']=str(Path(groups_report).relative_to(Path(path).parent))
            if progress:progress('Test ABSR: dwa pliki testowe gotowe; sprawdź oba w ZW3D 2019.')
        except Exception as err:
            # The primary native assembly STEP is already committed.
            result['test_absr_blad']=str(err)
            (folder/'BLAD_TESTU_ABSR.txt').write_text(str(err),encoding='utf8')
            if progress:progress('OSTRZEŻENIE: testowy STEP bez ABSR nie powiódł się: '+str(err))
    return result
