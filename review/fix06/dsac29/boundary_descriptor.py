"""Minimal advisory descriptors for boundary proof; never equality evidence."""
from math import isfinite
from types import SimpleNamespace


def describe_boundary(shape, properties=None):
    # World boundary matching needs only shape, volume and area. The parent
    # already integrated these at import. Rigid placement preserves them.
    # They admit candidates ONLY; actual surfaces and trims establish equality.
    if properties is not None:
        try:
            volume,area=(float(properties[k]) for k in ('volume','area')) if isinstance(properties,dict) else (float(properties.volume),float(properties.area))
            if all(isfinite(v) and v>0 for v in (volume,area)):
                return SimpleNamespace(shape=shape,volume=volume,area=area)
        except (TypeError,ValueError,KeyError,AttributeError):
            pass
    from OCP.BRepGProp import BRepGProp
    from OCP.GProp import GProp_GProps
    volume,area=GProp_GProps(),GProp_GProps()
    BRepGProp.VolumeProperties_s(shape,volume)
    BRepGProp.SurfaceProperties_s(shape,area)
    v,a=float(volume.Mass()),float(area.Mass())
    if not all(isfinite(x) and x>0 for x in (v,a)):
        raise ValueError('Non-positive or non-finite boundary properties')
    return SimpleNamespace(shape=shape,volume=v,area=a)
