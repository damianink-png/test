"""Consistent adaptive CAD integration across import, matching and Booleans.

The no-Eps OCCT overload uses fixed quadrature: even an exact rational NURBS
cylinder can have a materially wrong mass/inertia. Eps is a dimensionless
integration accuracy, NOT a geometric tolerance and never moves a surface.
"""
from OCP.BRepGProp import BRepGProp

RELATIVE_INTEGRATION_ERROR = 1e-12


def volume_properties(shape, properties):
    return BRepGProp.VolumeProperties_s(shape, properties, RELATIVE_INTEGRATION_ERROR)


def surface_properties(shape, properties):
    return BRepGProp.SurfaceProperties_s(shape, properties, RELATIVE_INTEGRATION_ERROR)
