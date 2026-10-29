"""Reuse exact XCAF definition geometry; preserve per-instance world calculations.

Staged optimization only. Does not start CI or change production source archive.
"""
from pathlib import Path
import sys

def apply(root):
    p=Path(root)/'src/openassembly/stepio.py'
    s=p.read_text(encoding='utf-8')
    if 'def _local_measure(' in s:
        raise RuntimeError('Already patched')
    old='def _measure(local_shape, world_shape):'
    assert s.count(old)==1
    s=s.replace(old,'def _measure(local_shape, world_shape, local_data=None):',1)
    start=s.index('    local_volume = GProp_GProps()',s.index('def _measure('))
    stop=s.index('    world_prop = GProp_GProps()',start)
    block=s[start:stop]
    start2=s.index('    mat = local_volume.MatrixOfInertia()',stop)
    stop2=s.index('    tf = world_shape.Location().Transformation()',start2)
    block2=s[start2:stop2]
    imports=s[s.index('    from OCP.BRepGProp import BRepGProp',s.index('def _measure(')):s.index('    if world_shape.IsNull()',s.index('def _measure('))]
    local_func=('def _local_measure(local_shape):\n'+imports+block+block2+
        '    c = local_volume.CentreOfMass() if volume >= 1e-12 else area_prop.CentreOfMass()\n'+
        '    return volume, area, key, (float(c.X()), float(c.Y()), float(c.Z()))\n\n\n')
    s=s[:s.index('def _measure(')]+local_func+s[s.index('def _measure('):]
    start=s.index('    local_volume = GProp_GProps()',s.index('def _measure('))
    stop=s.index('    world_prop = GProp_GProps()',start)
    s=s[:start]+'''    if local_data is None:
        local_data = _local_measure(local_shape)
    volume, area, key, local_center = local_data
'''+s[stop:]
    start=s.index('    world_prop = GProp_GProps()',s.index('def _measure('))
    stop=s.index('    tf = world_shape.Location().Transformation()',start)
    s=s[:start]+'''    # Safe fast path: identical TShape and orientation, differing only by TopLoc.
    # Otherwise keep the exact OCCT world-integral fallback.
    if (world_shape.IsPartner(local_shape)
            and world_shape.Orientation() == local_shape.Orientation()):
        from OCP.gp import gp_Pnt
        relative = (world_shape.Location().Transformation().Multiplied(
            local_shape.Location().Transformation().Inverted()))
        c = gp_Pnt(*local_center).Transformed(relative)
    else:
        world_prop = GProp_GProps()
        BRepGProp.VolumeProperties_s(world_shape, world_prop)
        if volume < 1e-12:
            BRepGProp.SurfaceProperties_s(world_shape, world_prop)
        c = world_prop.CentreOfMass()
    center = (float(c.X()), float(c.Y()), float(c.Z()))
'''+s[stop:]
    anchor='    out = []\n    while exp.More():'
    assert s.count(anchor)==1
    s=s.replace(anchor,'    out = []\n    definition_cache = {}\n    cache_hits = 0\n    while exp.More():',1)
    anchor='            volume, area, center, fp, rotation, extents = _measure(local, world)'
    assert s.count(anchor)==1
    s=s.replace(anchor,'''            # Canonical reference label, never the part name or approximate mass.
            ref = node.RefLabel
            from OCP.TDF import TDF_Tool
            from OCP.TCollection import TCollection_AsciiString
            entry = TCollection_AsciiString()
            if not ref.IsNull():
                TDF_Tool.Entry_s(ref, entry)
            key_label = entry.ToCString() if not ref.IsNull() else None
            if key_label is None:
                local_data = None
            elif key_label in definition_cache:
                local_data = definition_cache[key_label]
                cache_hits += 1
            else:
                local_data = _local_measure(local)
                definition_cache[key_label] = local_data
            volume, area, center, fp, rotation, extents = _measure(local, world, local_data)''',1)
    anchor="    log.info('Read %s: %d solid occurrences', path, len(out))"
    assert s.count(anchor)==1
    s=s.replace(anchor,"    log.info('Read %s: %d solid occurrences; %d unique definitions; %d cache hits', path, len(out), len(definition_cache), cache_hits)",1)
    compile(s,str(p),'exec')
    p.write_text(s,encoding='utf-8')
    print('Applied XCAF local geometry cache')

if __name__=='__main__':
    apply(sys.argv[1])
