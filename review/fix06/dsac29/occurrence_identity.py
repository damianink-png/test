"""Exact translation-invariant OCC B-Rep identity for repeated STEP occurrences.

Never promote area, volume, bbox, labels, or quantized descriptors to proof.
An identical complete B-Rep after a *pure translation* is a strict geometry
certificate. Arbitrary baked rotations and topology rewrites remain for native
CAD checks. No persistent state, UI options, or changed comparison tolerance.
"""
from collections import Counter
from hashlib import sha256
from math import isfinite, log
from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter
import numpy as np


def _bucket(part):
    volume=float(part.volume)
    area=float(part.area)
    if not all(isfinite(x) and x>0 for x in (volume,area)):
        return None
    return round(log(volume)*12),round(log(area)*12)


def _canonical(part,directory):
    from OCP.Bnd import Bnd_Box
    from OCP.BRepBndLib import BRepBndLib
    from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
    from OCP.BRepTools import BRepTools
    from OCP.TopLoc import TopLoc_Location
    from OCP.gp import gp_Trsf,gp_Vec
    local=part.shape.Located(TopLoc_Location())
    bounds=Bnd_Box()
    BRepBndLib.AddOptimal_s(local,bounds,False,False)
    if bounds.IsVoid() or bounds.IsOpen():
        return None
    origin=np.asarray(bounds.Get()[:3],dtype=float)
    if not np.isfinite(origin).all():
        return None
    transform=gp_Trsf()
    transform.SetTranslation(gp_Vec(*map(float,-origin)))
    normalized=BRepBuilderAPI_Transform(local,transform,True).Shape().Located(TopLoc_Location())
    path=directory/'normalized.brep'
    try:
        if not BRepTools.Write_s(normalized,str(path)):
            return None
        digest=sha256()
        with path.open('rb') as f:
            for chunk in iter(lambda:f.read(1024*1024),b''):
                digest.update(chunk)
        return digest.digest(),tuple(float(x) for x in origin)
    finally:
        path.unlink(missing_ok=True)


def prepare_occurrence_identities(a,b,*,progress=None,limit=3500,face_cap=400):
    """Normalize repeated candidate families; equality uses complete B-Rep.

    Select by loose integrated mass properties only to avoid serializing every
    unrelated giant STEP part. Candidate filters cannot assert a SAME result.
    """
    from OCP.TopAbs import TopAbs_FACE
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopLoc import TopLoc_Location
    parts=list(a)+list(b)
    keys=[_bucket(p) for p in parts]
    candidates=Counter(k for k in keys if k is not None)
    repeated={k for k,n in candidates.items() if n>=3}
    if not repeated:
        return {'selected':0,'proven':0,'skipped':0,'elapsed_s':0.0}
    # The previous all-parts x repeated-buckets scan became quadratic for
    # assemblies containing many different repeated families. Expand the
    # same +/-2 log-bucket neighbourhood once and use constant-time lookups.
    # This is ONLY a candidate filter; equality still needs complete B-Rep.
    candidate_neighbourhood={(v+dv,a+da)
                             for v,a in repeated
                             for dv in range(-2,3)
                             for da in range(-2,3)}
    selected=[i for i,k in enumerate(keys)
              if k is not None and k in candidate_neighbourhood]
    if len(selected)>limit:
        if progress:
            progress('Powtórzenia STEP: pomijam kosztowną normalizację bardzo dużej grupy; stosuję pełne dowody CAD.')
        return {'selected':len(selected),'proven':0,'skipped':len(selected),'elapsed_s':0.0}
    started=perf_counter()
    native_cache={}
    # XCAF references to the SAME source-file definition and subsolid
    # have identical local B-Rep. Serialize the definition exactly once,
    # even when OCC built separate native wrappers for each occurrence.
    # The key is file+XCAF target label+solid index; never reuse cross-file.
    xcaf_cache={}
    completed=0
    native_hits=0
    xcaf_hits=0
    with TemporaryDirectory(prefix='dscompare_occur_') as temp:
        directory=Path(temp)
        for i in selected:
            part=parts[i]
            if getattr(part,'_dscompare_normalized_digest',None) is not None:
                completed+=1
                continue
            source_key=getattr(part,'step_definition_key',None)
            source_key=tuple(source_key) if source_key is not None else None
            result=xcaf_cache.get(source_key) if source_key is not None else None
            if result is not None:
                xcaf_hits+=1
            else:
                key=hash(part.shape.TShape())
                for representative,value in native_cache.get(key,()):
                    if part.shape.IsPartner(representative.shape):
                        result=value
                        native_hits+=1
                        break
                if result is None:
                    ex=TopExp_Explorer(part.shape.Located(TopLoc_Location()),TopAbs_FACE)
                    faces=0
                    while ex.More() and faces<=face_cap:
                        faces+=1
                        ex.Next()
                    if faces>face_cap:
                        continue
                    try:
                        result=_canonical(part,directory)
                    except Exception:
                        continue
                    if result is None:
                        continue
                    native_cache.setdefault(key,[]).append((part,result))
                if source_key is not None:
                    # Same XCAF definition inside one STEP has precisely
                    # the same local coordinates once TopLoc is removed.
                    # Placement is still verified separately per occurrence.
                    xcaf_cache[source_key]=result
            part._dscompare_normalized_digest=result[0]
            part._dscompare_local_origin=result[1]
            completed+=1
    elapsed=perf_counter()-started
    stats={'selected':len(selected),'proven':completed,
           'skipped':len(selected)-completed,'native_reuse':native_hits,
           'xcaf_reuse':xcaf_hits,'elapsed_s':round(elapsed,3)}
    if progress:
        progress(f'Powtórzenia STEP: pełne lokalne B-Rep {completed}/{len(selected)}; '
                 f'trafienia pamięci XCAF {xcaf_hits}, natywne {native_hits}; {elapsed:.1f} s. '
                 'Niezgodne skróty kieruję do natywnego dowodu geometrii.')
    return stats
