"""Re-export a verified B->A alignment as STEP, reimport it, then compare anew.

Never treats the export or numerical signatures as a geometry identity proof.
Every imported solid must have a corresponding source occurrence; the normal
B-Rep comparison must still prove SAME/CHANGED after the round-trip.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import replace
from pathlib import Path
from time import perf_counter
import json
import os
import math


def _match_imported(original, imported, tolerance):
    """Bijection for metadata only; NEVER a proof of equivalent geometry."""
    if len(original) != len(imported):
        raise RuntimeError(f'Wyrównany STEP: liczba brył {len(imported)} != {len(original)}')
    for item in list(original) + list(imported):
        if not all(math.isfinite(float(v)) for v in (*item.center, item.volume, item.area)):
            raise RuntimeError('Invalid STEP numeric metadata')
    groups = defaultdict(list)
    for idx, p in enumerate(original):
        groups[p.name].append(idx)
    used = set()
    restored = []
    max_center = min(max(float(tolerance) * .5, 0.0005), .01)
    for part in imported:
        candidates = groups.get(part.name, ())
        best = None
        for idx in candidates:
            if idx in used:
                continue
            old = original[idx]
            dc = float(sum((float(x)-float(y))**2 for x,y in zip(old.center, part.center)))**.5
            if dc > max_center:
                continue
            vol_error = abs(float(old.volume) - float(part.volume))
            area_error = abs(float(old.area) - float(part.area))
            if vol_error > max(1.e-3, abs(float(old.volume)) * 1.e-5):
                continue
            if area_error > max(1.e-3, abs(float(old.area)) * 1.e-5):
                continue
            metric = (dc, vol_error, area_error, idx)
            if best is None or metric < best[0]:
                best = (metric, idx)
        if best is not None:
            # Multiple occurrences with the same name and indistinguishable
            # spatial/scalar metadata cannot be assigned stable source paths.
            # A deterministic index choice would invent occurrence identity.
            ambiguous=[]
            for idx in candidates:
                if idx in used or idx == best[1]:
                    continue
                old=original[idx]
                dc=float(sum((float(x)-float(y))**2 for x,y in zip(old.center,part.center)))**.5
                ve=abs(float(old.volume)-float(part.volume))
                ae=abs(float(old.area)-float(part.area))
                if (abs(dc-best[0][0])<=1.e-7 and
                    abs(ve-best[0][1])<=1.e-6 and
                    abs(ae-best[0][2])<=1.e-6):
                    ambiguous.append(idx)
            if ambiguous:
                raise RuntimeError(
                    'Wyrównany STEP: brak jednoznacznie odpowiadającego elementu '
                    +part.name+'; nierozróżnialne wystąpienia o tej samej nazwie: '
                    +str([best[1]]+ambiguous))
        if best is None:
            # STEPCAF may replace an instance name with its shared definition
            # name. Recover metadata ONLY when an otherwise unmatched original
            # occurrence is uniquely identified by strict spatial and scalar
            # invariants. This is not a geometry identity certificate.
            fallback=[]
            for idx,old in enumerate(original):
                if idx in used:
                    continue
                dc=float(sum((float(x)-float(y))**2 for x,y in zip(old.center,part.center)))**.5
                if dc > max_center:
                    continue
                ve=abs(float(old.volume)-float(part.volume))
                ae=abs(float(old.area)-float(part.area))
                if ve <= max(1.e-3,abs(float(old.volume))*1.e-5) and ae <= max(1.e-3,abs(float(old.area))*1.e-5):
                    fallback.append(((dc,ve,ae,idx),idx))
            if len(fallback)==1:
                best=fallback[0]
            # If more than one source occurrence qualifies, the identity is
            # ambiguous. Refuse to invent an occurrence mapping.
        if best is None:
            # Diagnostic only: do not relax geometry tolerances or infer SAME.
            # Report why an apparently successful STEP round-trip cannot be
            # bijectively associated with the original occurrences.
            def metrics(i):
                old = original[i]
                dc = float(sum((float(x)-float(y))**2 for x,y in zip(old.center, part.center)))**.5
                return {'index': i, 'name': old.name, 'center_delta_mm': round(dc, 7),
                        'volume_delta': round(abs(float(old.volume)-float(part.volume)), 7),
                        'area_delta': round(abs(float(old.area)-float(part.area)), 7),
                        'old_center': [round(float(v),5) for v in old.center],
                        'new_center': [round(float(v),5) for v in part.center]}
            by_name = [i for i in candidates if i not in used]
            all_unused = [i for i in range(len(original)) if i not in used]
            closest_by_name = sorted(by_name, key=lambda i: metrics(i)['center_delta_mm'])[:3]
            closest_any = sorted(all_unused, key=lambda i: metrics(i)['center_delta_mm'])[:3]
            detail = {'imported_name': part.name, 'imported_center': list(map(float,part.center)),
                      'imported_volume': float(part.volume), 'imported_area': float(part.area),
                      'same_name_unused': len(by_name), 'same_name_used': len(candidates)-len(by_name),
                      'compatible_any_name_count': len(fallback),
                      'nearest_same_name': [metrics(i) for i in closest_by_name],
                      'nearest_any_name': [metrics(i) for i in closest_any]}
            raise RuntimeError('Wyrównany STEP: brak jednoznacznie odpowiadającego elementu '
                               +part.name+'; diagnostyka='+json.dumps(detail,ensure_ascii=False))
        old = original[best[1]]
        used.add(best[1])
        restored.append(replace(part, name=old.name, path=old.path,
                                source=old.source, name_origin=old.name_origin))
    if len(used) != len(original):
        raise RuntimeError('Wyrównany STEP: utracone wystąpienia części')
    return restored


def save_aligned_step_and_reload(parts, output, tolerance, max_solids=20000, progress=None):
    """Persist already-relocated B, read it again; fail closed on any mismatch.

    Caller must have approved and B-Rep-verified the assembly transform.
    Returns (reimported_parts, step_path, diagnostics).
    """
    if not parts:
        raise ValueError('Brak części B do eksportu po wyrównaniu')
    from OCP.BRep import BRep_Builder
    from OCP.IFSelect import IFSelect_RetDone
    from OCP.Interface import Interface_Static
    from OCP.STEPCAFControl import STEPCAFControl_Writer
    from OCP.STEPControl import STEPControl_Controller
    from OCP.TCollection import TCollection_ExtendedString
    from OCP.TDataStd import TDataStd_Name
    from OCP.TDocStd import TDocStd_Document
    from OCP.TopoDS import TopoDS_Compound
    from OCP.TopLoc import TopLoc_Location
    from OCP.XCAFDoc import XCAFDoc_DocumentTool
    from .step_io import _single_solid_without_wrapper
    from .import_cache import load_step_persistent

    t0 = perf_counter()
    folder = Path(output).resolve() / '_WYROWNANY_STEP'
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / 'B_WYROWNANY.step'
    temporary = folder / 'B_WYROWNANY.partial.step'
    temporary.unlink(missing_ok=True)
    doc = TDocStd_Document(TCollection_ExtendedString('BinXCAF'))
    tool = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())
    compound = TopoDS_Compound()
    BRep_Builder().MakeCompound(compound)
    root = tool.AddShape(compound, True)
    TDataStd_Name.Set_s(root, TCollection_ExtendedString('DS_COMPARE_B_WYROWNANY'))
    for part in parts:
        loc = part.shape.Location()
        local = _single_solid_without_wrapper(part.shape.Located(TopLoc_Location()))
        label = tool.AddShape(local, False)
        if label.IsNull():
            raise RuntimeError('Wyrównany STEP: nie można dodać bryły '+part.name)
        TDataStd_Name.Set_s(label, TCollection_ExtendedString(part.name))
        instance = tool.AddComponent(root, label, loc)
        if instance.IsNull():
            raise RuntimeError('Wyrównany STEP: nie można dodać wystąpienia '+part.name)
        TDataStd_Name.Set_s(instance, TCollection_ExtendedString(part.name))
    tool.UpdateAssemblies()
    STEPControl_Controller.Init_s()
    if not Interface_Static.SetCVal_s('write.step.schema', 'AP214IS'):
        raise RuntimeError('Wyrównany STEP: brak schematu AP214IS')
    writer = STEPCAFControl_Writer()
    writer.SetNameMode(True)
    writer.SetColorMode(False)
    writer.SetLayerMode(False)
    if not writer.Transfer(doc) or writer.Write(str(temporary)) != IFSelect_RetDone:
        temporary.unlink(missing_ok=True)
        raise RuntimeError('Wyrównany STEP: błąd transferu/zapisu')
    os.replace(temporary, target)
    write_s = perf_counter() - t0
    if progress:
        progress(f'Wyrównanie: zapisano {len(parts)} wystąpień w {target.name}; ponowny import…')
    # Do not use cache: reimport is an intentional independent round-trip.
    imported = load_step_persistent(str(target), max_solids=max_solids, progress=progress)
    restored = _match_imported(parts, imported, tolerance)
    renamed_occurrences = sum(a.name != b.name for a,b in zip(restored, imported))
    diagnostics = {'path': str(target), 'solids_expected': len(parts),
                   'step_names_recovered_from_unique_metadata': renamed_occurrences,
                   'solids_reimported': len(imported), 'write_s': round(write_s,3),
                   'total_s': round(perf_counter()-t0,3),
                   'validation': 'occurrence_count_name_center_volume_area_only_not_geometry_proof'}
    (folder / 'WERYFIKACJA_IMPORTU.json').write_text(
        json.dumps(diagnostics, ensure_ascii=False, indent=2), encoding='utf-8')
    return restored, target, diagnostics
