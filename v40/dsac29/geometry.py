"""Real Open CASCADE B-Rep comparison; NO calls to the ZW3D process/API."""
from __future__ import annotations
from dataclasses import dataclass
from itertools import permutations, product
import math
import numpy as np
from OCP.TopoDS import TopoDS_Shape
from OCP.GProp import GProp_GProps
from OCP.BRepGProp import BRepGProp
from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut, BRepAlgoAPI_Common
from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
from OCP.BRepBndLib import BRepBndLib
from OCP.Bnd import Bnd_Box
from OCP.gp import gp_Trsf


@dataclass
class SolidInfo:
    shape: TopoDS_Shape
    name: str
    path: str
    volume: float
    area: float
    center: np.ndarray
    inertia: np.ndarray
    eigenvalues: np.ndarray
    axes: np.ndarray
    bbox: tuple[float, float, float]
    source: str = ''


def describe(shape: TopoDS_Shape, name: str, path: str, source: str = '') -> SolidInfo:
    if shape.IsNull():
        raise ValueError('Null B-Rep')
    v = GProp_GProps(); BRepGProp.VolumeProperties_s(shape, v)
    a = GProp_GProps(); BRepGProp.SurfaceProperties_s(shape, a)
    c = v.CentreOfMass(); center = np.array([c.X(), c.Y(), c.Z()], dtype=float)
    m = v.MatrixOfInertia()
    mat = np.array([[m.Value(i, j) for j in range(1, 4)] for i in range(1, 4)], dtype=float)
    eig, axes = np.linalg.eigh(mat)
    ix = np.argsort(eig)
    eig, axes = eig[ix], axes[:, ix]
    bb = Bnd_Box(); BRepBndLib.Add_s(shape, bb)
    x0, y0, z0, x1, y1, z1 = bb.Get()
    bbox = (x1-x0, y1-y0, z1-z0)
    if v.Mass() <= 0:
        raise ValueError(f'Bryla {path} ma zerowa/ujemna objetosc')
    return SolidInfo(shape, name, path, float(v.Mass()), float(a.Mass()), center,
                     mat, eig, axes, bbox, source)


def close(a: float, b: float, abs_tol: float, relative: float = 1e-7) -> bool:
    return abs(a-b) <= max(abs_tol, relative * max(abs(a), abs(b)))


def candidate(a: SolidInfo, b: SolidInfo, tolerance: float = 0.01) -> bool:
    # Pre-filter independent of placement and orientation.
    return (close(a.volume, b.volume, max(tolerance**3, 1e-5))
            and close(a.area, b.area, max(tolerance*tolerance, 1e-4))
            and np.allclose(a.eigenvalues, b.eigenvalues, rtol=1e-6,
                            atol=max(1e-3, tolerance**5)))


def _gp_transformation(rotation: np.ndarray, offset: np.ndarray) -> gp_Trsf:
    R = rotation; t = offset
    tr = gp_Trsf()
    tr.SetValues(float(R[0,0]),float(R[0,1]),float(R[0,2]),float(t[0]),
                 float(R[1,0]),float(R[1,1]),float(R[1,2]),float(t[1]),
                 float(R[2,0]),float(R[2,1]),float(R[2,2]),float(t[2]))
    return tr


def transform(shape: TopoDS_Shape, rotation: np.ndarray, offset: np.ndarray) -> TopoDS_Shape:
    return BRepBuilderAPI_Transform(shape, _gp_transformation(rotation, offset), True).Shape()


def _cut_volume(a: TopoDS_Shape, b: TopoDS_Shape, tolerance: float) -> float:
    cutter = BRepAlgoAPI_Cut(a, b)
    cutter.SetFuzzyValue(max(tolerance/100, 1e-6))
    cutter.Build()
    if not cutter.IsDone():
        raise RuntimeError('Open CASCADE: operacja BRepAlgoAPI_Cut nie powiodla sie')
    g = GProp_GProps()
    BRepGProp.VolumeProperties_s(cutter.Shape(), g)
    return max(0.0, float(g.Mass()))


def difference(a: TopoDS_Shape, b: TopoDS_Shape, tolerance: float = 0.01) -> tuple[float, float]:
    """Volumes A minus B, B minus A in mm^3. Caller handles tolerance/geometry caveats."""
    return _cut_volume(a, b, tolerance), _cut_volume(b, a, tolerance)


def _common_volume(a: TopoDS_Shape, b: TopoDS_Shape, tolerance: float) -> float:
    """One Boolean intersection replaces two expensive cuts in equality checks.

    For two valid solid volumes, |A ∩ B| ~= |A| ~= |B| implies volume equivalence.
    True topology/feature identity is NOT inferred from volume alone.
    """
    common = BRepAlgoAPI_Common(a, b)
    common.SetFuzzyValue(max(tolerance / 100, 1e-6))
    common.Build()
    if not common.IsDone():
        raise RuntimeError('Open CASCADE: Common failed')
    props = GProp_GProps()
    BRepGProp.VolumeProperties_s(common.Shape(), props)
    return max(0., float(props.Mass()))


def _is_common_equal(a: TopoDS_Shape, b: TopoDS_Shape, volume_a: float,
                     volume_b: float, tolerance: float) -> bool:
    if a.IsSame(b):
        return True
    c = _common_volume(a, b, tolerance)
    vtol = max(tolerance**3, 1e-4, min(volume_a, volume_b) * 1e-7)
    return max(abs(volume_a - c), abs(volume_b - c)) <= vtol


def equivalent_world(a: SolidInfo, b: SolidInfo, tolerance: float = 0.01) -> bool:
    if not candidate(a,b,tolerance): return False
    if np.linalg.norm(a.center-b.center)>tolerance: return False
    return _is_common_equal(a.shape, b.shape, a.volume, b.volume, tolerance)


def _basis_rotations(a: SolidInfo, b: SolidInfo):
    # Proper sign/permutation matrices cover the 24 eigenframe orientation choices.
    # Permutations of distinct eigenvalues must not be used (they would swap unequal moments).
    for perm in permutations(range(3)):
        if any(not close(a.eigenvalues[i], b.eigenvalues[perm[i]], 1e-3, 1e-6)
               for i in range(3)):
            continue
        for signs in product((-1.0,1.0), repeat=3):
            p = np.zeros((3,3))
            for i,j in enumerate(perm): p[i,j]=signs[i]
            R = a.axes @ p @ b.axes.T
            if np.linalg.det(R)<0.99: continue
            yield R


def equivalent_rigid(a: SolidInfo, b: SolidInfo, tolerance: float = 0.01,
                     max_trials: int = 24) -> tuple[bool, np.ndarray | None, np.ndarray | None]:
    """Test shape equality up to proper rigid transform (no mirrors)."""
    if not candidate(a,b,tolerance): return False,None,None
    rotations=[np.eye(3),*_basis_rotations(a,b)]
    for R in rotations:
        t=a.center-R @ b.center
        moved=transform(b.shape,R,t)
        if _is_common_equal(a.shape,moved,a.volume,b.volume,tolerance):return True,R,t
    # Equal inertia eigenvalues do not define unique axes. Use geometric vertex
    # frames for e.g. cubes rotated by arbitrary angles, then prove with B-Rep.
    for trial,R in enumerate(_vertex_rotations(a,b,tolerance)):
        t=a.center-R @ b.center
        moved=transform(b.shape,R,t)
        if _is_common_equal(a.shape,moved,a.volume,b.volume,tolerance):return True,R,t
        if trial>=max_trials*4:break
    return False,None,None


def _vertex_rotations(a,b,tolerance):
    from OCP.TopAbs import TopAbs_VERTEX
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopoDS import TopoDS
    from OCP.BRep import BRep_Tool
    def points(part):
        vals=[];seen=set();ex=TopExp_Explorer(part.shape,TopAbs_VERTEX)
        while ex.More():
            p=BRep_Tool.Pnt_s(TopoDS.Vertex_s(ex.Current()))
            v=np.array([p.X(),p.Y(),p.Z()])-part.center
            key=tuple(np.round(v,7))
            if key not in seen:seen.add(key);vals.append(v)
            ex.Next()
        return sorted(vals,key=lambda x:-np.linalg.norm(x))[:128]
    aa,bb=points(a),points(b)
    if len(aa)<2 or len(bb)<2:return
    u=aa[0];nu=np.linalg.norm(u)
    if nu<1e-9:return
    v=max(aa,key=lambda x:np.linalg.norm(np.cross(u,x)))
    nv=np.linalg.norm(v)
    if np.linalg.norm(np.cross(u,v))<1e-8:return
    def frame(x,y):
        e=x/np.linalg.norm(x);f=y-e*np.dot(e,y);f/=np.linalg.norm(f)
        return np.column_stack((e,f,np.cross(e,f)))
    basis=frame(u,v)
    for x in bb:
        if abs(np.linalg.norm(x)-nu)>max(1e-5,tolerance):continue
        for y in bb:
            if abs(np.linalg.norm(y)-nv)>max(1e-5,tolerance):continue
            if abs(np.dot(x,y)-np.dot(u,v))>max(1e-4,tolerance*(nu+nv)):continue
            if np.linalg.norm(np.cross(x,y))<1e-8:continue
            yield basis@frame(x,y).T


def signature(s: SolidInfo) -> tuple:
    # Only a candidate index; this is NOT proof of equal geometry.
    return (round(s.volume,3),round(s.area,3),
            *[round(float(v),2) for v in s.eigenvalues])


def dist(a: SolidInfo,b: SolidInfo) -> float:
    return float(np.linalg.norm(a.center-b.center))
