import vtk,numpy as np
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.TopAbs import TopAbs_FACE
from OCP.TopExp import TopExp_Explorer
from OCP.TopoDS import TopoDS
from OCP.BRep import BRep_Tool
from OCP.TopLoc import TopLoc_Location
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
from OCP.gp import gp_Trsf,gp_Vec

def make_surface(shape,deflection=0.001):
    # all topology/geometry comes from the native BRep surfaces
    m=BRepMesh_IncrementalMesh(shape,deflection,False,.12,False);m.Perform()
    if not m.IsDone():raise RuntimeError('mesh failed')
    ps=vtk.vtkPoints();cells=vtk.vtkCellArray();samples=[];f=TopExp_Explorer(shape,TopAbs_FACE)
    while f.More():
        face=TopoDS.Face_s(f.Current());loc=TopLoc_Location()
        mesh=BRep_Tool.Triangulation_s(face,loc)
        if mesh is None: raise RuntimeError('face missing mesh')
        offset=ps.GetNumberOfPoints(); tf=loc.Transformation()
        nd=[mesh.Node(i).Transformed(tf) for i in range(1,mesh.NbNodes()+1)]
        for p in nd: ps.InsertNextPoint(p.X(),p.Y(),p.Z());samples.append((p.X(),p.Y(),p.Z()))
        for k in range(1,mesh.NbTriangles()+1):
            tri=mesh.Triangle(k).Get(); ids=[offset+j-1 for j in tri]
            cell=vtk.vtkTriangle()
            for i,v in enumerate(ids):cell.GetPointIds().SetId(i,int(v))
            cells.InsertNextCell(cell)
            # centroid and edge midpoints: guard against planar cases where
            # only vertices lie on the target but triangle interiors do not.
            a,b,c=(np.array((ps.GetPoint(v))) for v in ids)
            samples.append(tuple((a+b+c)/3))
            for x,y in ((a,b),(b,c),(c,a)):samples.append(tuple((x+y)/2))
        f.Next()
    pd=vtk.vtkPolyData();pd.SetPoints(ps);pd.SetPolys(cells)
    return pd,samples

def check(a,b,tol=.01):
    ap,asamples=make_surface(a);bp,bsamples=make_surface(b)
    def errors(s,t):
        locator=vtk.vtkStaticCellLocator();locator.SetDataSet(t);locator.BuildLocator()
        closest=[0.,0.,0.];cid=vtk.mutable(0);sid=vtk.mutable(0);ds=vtk.mutable(0.)
        mxd=0
        for pt in s:
            locator.FindClosestPoint(pt,closest,cid,sid,ds)
            if ds > tol**2:
                return False,float(ds)**.5
            mxd=max(mxd,float(ds))
        return True,mxd**.5
    return len(asamples),len(bsamples),errors(asamples,bp),errors(bsamples,ap)

if __name__=='__main__':
 import time
 a=BRepPrimAPI_MakeBox(12.,8.,5.).Shape()
 b=BRepPrimAPI_MakeBox(12.,8.,5.).Shape()
 c=BRepPrimAPI_MakeBox(12.02,8.,5.).Shape()
 print('same',check(a,b));print('diff',check(a,c))