"""Write BOTH comparison inputs with one STEP writer, then import fresh geometry."""
from pathlib import Path
from time import perf_counter
from uuid import uuid4
import re


def _write(parts, path):
    from OCP.TDocStd import TDocStd_Document
    from OCP.TCollection import TCollection_ExtendedString as String
    from OCP.XCAFDoc import XCAFDoc_DocumentTool
    from OCP.TDataStd import TDataStd_Name
    from OCP.TopoDS import TopoDS_Compound
    from OCP.BRep import BRep_Builder
    from OCP.TopLoc import TopLoc_Location
    from OCP.STEPCAFControl import STEPCAFControl_Writer
    from OCP.IFSelect import IFSelect_RetDone
    doc = TDocStd_Document(String('BinXCAF'))
    tool = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())
    root_shape = TopoDS_Compound(); BRep_Builder().MakeCompound(root_shape)
    root = tool.AddShape(root_shape, True)
    TDataStd_Name.Set_s(root, String('DSCompare'))
    definitions = {}
    for i, part in enumerate(parts):
        local = part.shape.Located(TopLoc_Location())
        # Only native identity is reusable; matching dimensions are not identity.
        key = (hash(local), int(local.Orientation()))
        candidates = definitions.setdefault(key, [])
        label = next((label for shape, label in candidates if shape.IsSame(local)), None)
        if label is None:
            label = tool.AddShape(local, False)
            TDataStd_Name.Set_s(label, String('Solid'))
            candidates.append((local, label))
        occurrence = tool.AddComponent(root, label, part.shape.Location())
        TDataStd_Name.Set_s(occurrence, String(f'DSC_RT_{i:08d}'))
    tool.UpdateAssemblies()
    writer = STEPCAFControl_Writer(); writer.SetNameMode(True)
    if not writer.Transfer(doc):
        raise RuntimeError('Nie udało się przygotować kopii STEP')
    temporary = path.with_suffix('.tmp.step')
    if writer.Write(str(temporary)) != IFSelect_RetDone:
        raise RuntimeError('Nie udało się zapisać kopii STEP')
    temporary.replace(path)


def normalize_pair(a, b, output, max_solids=20000, progress=None, cancelled=None):
    from OCP.Interface import Interface_Static
    from OCP.STEPControl import STEPControl_Controller
    from .step_io import load_step
    started = perf_counter()
    folder = Path(output)/('STEP_DO_POROWNANIA_' + uuid4().hex)
    folder.mkdir(parents=True, exist_ok=False)
    STEPControl_Controller.Init_s()
    settings = [('write.step.schema', 'C', 'AP214IS'),
                ('write.step.unit', 'C', 'MM'),
                ('write.surfacecurve.mode', 'I', 1),
                ('write.step.assembly', 'I', 1),
                ('write.step.nonmanifold', 'I', 0)]
    saved = [(key, kind, getattr(Interface_Static, kind+'Val_s')(key)) for key, kind, _ in settings]
    paths = [folder/'A.step', folder/'B.step']
    try:
        for key, kind, value in settings:
            if not getattr(Interface_Static, 'Set'+kind+'Val_s')(key, value):
                raise RuntimeError('Nie można ustawić eksportera STEP: '+key)
        for role, parts, path in zip(('A','B'), (a,b), paths):
            if cancelled and cancelled(): raise InterruptedError('Anulowano zapis STEP')
            if progress: progress(f'Ujednolicenie STEP: zapis {role}, {len(parts)} brył…')
            _write(parts, path)
    finally:
        for key, kind, value in saved:
            getattr(Interface_Static, 'Set'+kind+'Val_s')(key, value)
    result = []
    for parts, path in zip((a,b), paths):
        if cancelled and cancelled(): raise InterruptedError('Anulowano odczyt STEP')
        imported = load_step(str(path), max_solids=max_solids, progress=progress)
        indexed = {}
        for part in imported:
            match = re.fullmatch(r'DSC_RT_(\d{8})', part.name)
            if not match: raise RuntimeError('Ponowny import STEP utracił identyfikator części')
            index = int(match.group(1))
            if index >= len(parts) or index in indexed:
                raise RuntimeError('Ponowny import STEP zmienił strukturę części')
            original = parts[index]
            part.name, part.path = original.name, original.path
            if hasattr(original, 'name_origin'): part.name_origin = original.name_origin
            indexed[index] = part
        if len(indexed) != len(parts): raise RuntimeError('Ponowny import STEP zmienił liczbę brył')
        result.append([indexed[i] for i in range(len(parts))])
    return *result, {'a': str(paths[0]), 'b': str(paths[1]), 'seconds': perf_counter()-started,
                     'solids_a':len(a), 'solids_b':len(b), 'schema':'AP214IS'}
