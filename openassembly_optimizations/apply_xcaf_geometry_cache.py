"""Cache local XCAF definition measurements; world placement stays per occurrence.

Staged patch: deliberately outside the workflow paths. No CI is started.
The cache key is the XCAF reference label *within a single document*, never
the part name or approximate volume. Unknown/null references are not cached.
"""
from pathlib import Path
import sys

def apply(root):
    path = Path(root) / "src/openassembly/stepio.py"
    src = path.read_text(encoding="utf-8")
    start = src.index("def _measure(local_shape, world_shape):")
    end = src.index("\n\ndef load_step(", start)
    replacement = '''def _local_geometry(local_shape):
    """Expensive, placement-independent measurements, once per definition."""
    from OCP.BRepGProp import BRepGProp
    from OCP.GProp import GProp_GProps
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopAbs import TopAbs_FACE, TopAbs_EDGE
    from OCP.BRepAdaptor import BRepAdaptor_Surface, BRepAdaptor_Curve
    from OCP.TopoDS import TopoDS
    local_volume = GProp_GProps()
    BRepGProp.VolumeProperties_s(local_shape, local_volume)
    volume = max(0., float(local_volume.Mass()))
    area_prop = GProp_GProps()
    BRepGProp.SurfaceProperties_s(local_shape, area_prop)
    area = max(0., float(area_prop.Mass()))
    mat = local_volume.MatrixOfInertia()
    eig = sorted(float(x) for x in np.linalg.eigvalsh(np.array([
        [mat.Value(i, j) for j in range(1, 4)] for i in range(1, 4)])))
    faces, edges = [], []
    ex = TopExp_Explorer(local_shape, TopAbs_FACE)
    while ex.More():
        face = ex.Current()
        p = GProp_GProps()
        BRepGProp.SurfaceProperties_s(face, p)
        faces.append((int(BRepAdaptor_Surface(TopoDS.Face_s(face)).GetType().value),
                      round(float(p.Mass()), 5)))
        ex.Next()
    ex = TopExp_Explorer(local_shape, TopAbs_EDGE)
    while ex.More():
        edge = ex.Current()
        p = GProp_GProps()
        BRepGProp.LinearProperties_s(edge, p)
        edges.append((int(BRepAdaptor_Curve(TopoDS.Edge_s(edge)).GetType().value),
                      round(float(p.Mass()), 5)))
        ex.Next()
    key = (round(volume, 5), round(area, 5), tuple(round(v, 4) for v in eig),
           tuple(sorted(faces)), tuple(sorted(edges)))
    c = local_volume.CentreOfMass() if volume >= 1e-12 else area_prop.CentreOfMass()
    center_local = (float(c.X()), float(c.Y()), float(c.Z()))
    return volume, area, key, center_local


def _measure(local_shape, world_shape, local_data=None):
    """Keep per-occurrence world placement and bounding box, reuse local shape data."""
    from OCP.BRepBndLib import BRepBndLib
    from OCP.Bnd import Bnd_Box
    if world_shape.IsNull():
        raise ValueError('Null world shape')
    if local_data is None:
        local_data = _local_geometry(local_shape)
    volume, area, key, center_local = local_data
    # Preserve the original world centroid semantics for every occurrence.
    # A local centroid is transformed only if the world shape is a rigid
    # placement of the same local topology; otherwise use the OCCT world integral.
    from OCP.BRepGProp import BRepGProp
    from OCP.GProp import GProp_GProps
    world_prop = GProp_GProps()
    BRepGProp.VolumeProperties_s(world_shape, world_prop)
    if volume < 1e-12:
        BRepGProp.SurfaceProperties_s(world_shape, world_prop)
    c = world_prop.CentreOfMass()
    center = (float(c.X()), float(c.Y()), float(c.Z()))
    tf = world_shape.Location().Transformation()
    rotation = tuple(round(tf.Value(i,j), 7) for i in range(1,4) for j in range(1,4))
    bounds = Bnd_Box()
    BRepBndLib.Add_s(world_shape, bounds)
    x0,y0,z0,x1,y1,z1 = bounds.Get()
    extents = (x1-x0,y1-y0,z1-z0)
    return volume, area, center, key, rotation, extents
'''
    src = src[:start] + replacement + src[end:]
    anchor = "    out = []\n    while exp.More():"
    if src.count(anchor) != 1:
        raise RuntimeError("XCAF occurrence loop anchor changed")
    src = src.replace(anchor, "    out = []\n    local_cache = {}\n    cache_hits = 0\n    while exp.More():", 1)
    anchor = "            volume, area, center, fp, rotation, extents = _measure(local, world)"
    if src.count(anchor) != 1:
        raise RuntimeError("XCAF measurement anchor changed")
    src = src.replace(anchor, """            # RefLabel identifies a definition in this document, not a name.
            ref = node.RefLabel
            cache_key = str(ref.EntryDumpToString()) if not ref.IsNull() else None
            if cache_key is None:
                local_data = None
            elif cache_key in local_cache:
                cache_hits += 1
                local_data = local_cache[cache_key]
            else:
                local_data = _local_geometry(local)
                local_cache[cache_key] = local_data
            volume, area, center, fp, rotation, extents = _measure(local, world, local_data)""", 1)
    anchor = "    log.info('Read %s: %d solid occurrences', path, len(out))"
    if src.count(anchor) != 1:
        raise RuntimeError("Import logging anchor changed")
    src = src.replace(anchor, "    log.info('Read %s: %d solid occurrences; %d unique XCAF definitions, %d cache hits', path, len(out), len(local_cache), cache_hits)", 1)
    path.write_text(src, encoding="utf-8")
    print("XCAF geometry cache staged (not activated in CI)")

if __name__ == "__main__":
    apply(sys.argv[1])
