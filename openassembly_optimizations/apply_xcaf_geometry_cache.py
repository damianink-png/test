"""Optional source optimization, deliberately not wired to CI until approved.
Cache expensive local geometry properties by XCAF reference label. Each occurrence
still gets independent world centroid, orientation and bounding box.
"""
from pathlib import Path
import sys

def apply(root):
    p=Path(root)/"src/openassembly/stepio.py"
    s=p.read_text(encoding="utf-8")
    changes=[
      ("def _measure(local_shape, world_shape):","def _measure(local_shape, world_shape, geometry_cache=None, geometry_key=None):"),
      ("    local_volume = GProp_GProps()\n    BRepGProp.VolumeProperties_s(local_shape, local_volume)",
       "    cached = geometry_cache.get(geometry_key) if geometry_cache is not None else None\n    if cached is None:\n        local_volume = GProp_GProps()\n        BRepGProp.VolumeProperties_s(local_shape, local_volume)"),
      ("    volume = max(0., float(local_volume.Mass()))\n    area_prop = GProp_GProps()\n    BRepGProp.SurfaceProperties_s(local_shape, area_prop)\n    area = max(0., float(area_prop.Mass()))",
       "        volume = max(0., float(local_volume.Mass()))\n        area_prop = GProp_GProps()\n        BRepGProp.SurfaceProperties_s(local_shape, area_prop)\n        area = max(0., float(area_prop.Mass()))\n    else:\n        volume, area, key = cached"),
      ("    mat = local_volume.MatrixOfInertia()","    if cached is None:\n        mat = local_volume.MatrixOfInertia()"),
      ("    eig = sorted(float(x) for x in np.linalg.eigvalsh(np.array([",
       "        eig = sorted(float(x) for x in np.linalg.eigvalsh(np.array(["),
      ("        [mat.Value(i, j) for j in range(1, 4)] for i in range(1, 4)])))",
       "            [mat.Value(i, j) for j in range(1, 4)])))"),
      ("    faces, edges = [], []\n    ex = TopExp_Explorer(local_shape, TopAbs_FACE)",
       "        faces, edges = [], []\n        ex = TopExp_Explorer(local_shape, TopAbs_FACE)"),
      ("    while ex.More():\n        face = ex.Current()","        while ex.More():\n            face = ex.Current()"),
      ("        p = GProp_GProps()\n        BRepGProp.SurfaceProperties_s(face, p)\n        faces.append((int(BRepAdaptor_Surface(TopoDS.Face_s(face)).GetType().value), round(float(p.Mass()), 5)))\n        ex.Next()",
       "            p = GProp_GProps()\n            BRepGProp.SurfaceProperties_s(face, p)\n            faces.append((int(BRepAdaptor_Surface(TopoDS.Face_s(face)).GetType().value), round(float(p.Mass()), 5)))\n            ex.Next()"),
      ("    ex = TopExp_Explorer(local_shape, TopAbs_EDGE)","        ex = TopExp_Explorer(local_shape, TopAbs_EDGE)"),
      ("    while ex.More():\n        edge = ex.Current()","        while ex.More():\n            edge = ex.Current()"),
      ("        p = GProp_GProps()\n        BRepGProp.LinearProperties_s(edge, p)\n        edges.append((int(BRepAdaptor_Curve(TopoDS.Edge_s(edge)).GetType().value), round(float(p.Mass()), 5)))\n        ex.Next()",
       "            p = GProp_GProps()\n            BRepGProp.LinearProperties_s(edge, p)\n            edges.append((int(BRepAdaptor_Curve(TopoDS.Edge_s(edge)).GetType().value), round(float(p.Mass()), 5)))\n            ex.Next()"),
      ("    key = (round(volume, 5), round(area, 5), tuple(round(v, 4) for v in eig),\n           tuple(sorted(faces)), tuple(sorted(edges)))",
       "        key = (round(volume, 5), round(area, 5), tuple(round(v, 4) for v in eig),\n               tuple(sorted(faces)), tuple(sorted(edges)))\n        if geometry_cache is not None:\n            geometry_cache[geometry_key] = (volume, area, key)"),
      ("    out = []\n    while exp.More():","    out = []\n    geometry_cache = {}\n    cache_hits = 0\n    while exp.More():"),
      ("            volume, area, center, fp, rotation, extents = _measure(local, world)",
       "            # RefLabel identifies the underlying XCAF definition, not its name.\n            # Null reference labels are never cached.\n            ref = node.RefLabel\n            cache_key = str(ref.EntryDumpToString()) if not ref.IsNull() else None\n            if cache_key is None:\n                volume, area, center, fp, rotation, extents = _measure(local, world)\n            else:\n                cache_hits += int(cache_key in geometry_cache)\n                volume, area, center, fp, rotation, extents = _measure(local, world, geometry_cache, cache_key)"),
      ("    log.info('Read %s: %d solid occurrences', path, len(out))",
       "    log.info('Read %s: %d solid occurrences; geometry cache %d definitions, %d hits', path, len(out), len(geometry_cache), cache_hits)")
    ]
    for old,new in changes:
        if s.count(old)!=1: raise RuntimeError("Unexpected source layout at: "+old[:65])
        s=s.replace(old,new,1)
    p.write_text(s,encoding="utf-8")
    print("XCAF local geometry cache overlay applied")

if __name__=="__main__":
    apply(sys.argv[1])
