"""Recover a single already-closed shell without sewing, filling or fitting."""
from OCP.TopAbs import TopAbs_SHELL,TopAbs_SOLID,TopAbs_FACE
from OCP.TopExp import TopExp_Explorer
from OCP.TopoDS import TopoDS


def recover(shape):
    from OCP.BRep import BRep_Tool
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeSolid,BRepBuilderAPI_Copy
    from OCP.BRepLib import BRepLib
    from OCP.BRepGProp import BRepGProp
    from OCP.GProp import GProp_GProps
    from .brep_safety import is_valid
    import math
    if TopExp_Explorer(shape,TopAbs_SOLID).More():return None
    shells=[];it=TopExp_Explorer(shape,TopAbs_SHELL)
    while it.More():shells.append(TopoDS.Shell_s(it.Current()));it.Next()
    # Multiple shells can describe cavities or independent parts. Never
    # guess ownership, and never silently discard loose faces.
    if len(shells)!=1 or TopExp_Explorer(shape,TopAbs_FACE,TopAbs_SHELL).More():return None
    shell=shells[0]
    if not BRep_Tool.IsClosed_s(shell) or not is_valid(shell):return None
    copied=TopoDS.Shell_s(BRepBuilderAPI_Copy(shell,True,False).Shape())
    maker=BRepBuilderAPI_MakeSolid(copied)
    if not maker.IsDone():return None
    solid=maker.Solid()
    if not BRepLib.OrientClosedSolid_s(solid) or not is_valid(solid):return None
    props=GProp_GProps();BRepGProp.VolumeProperties_s(solid,props)
    if not math.isfinite(props.Mass()) or props.Mass()<=0:return None
    return solid
