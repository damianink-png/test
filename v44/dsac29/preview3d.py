"""Self-contained WebGL preview: visual colors, independent of STEP reader settings.

The preview is an approximation produced from B-Rep triangulation, not CAD-quality
geometry, and never substitutes for the original STEP geometry or the BOM.
"""
from __future__ import annotations
import base64
import json
from pathlib import Path
import numpy as np
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.BRep import BRep_Tool
from OCP.TopExp import TopExp_Explorer
from OCP.TopoDS import TopoDS
from OCP.TopAbs import TopAbs_FACE
from OCP.TopLoc import TopLoc_Location
from .step_io import COLORS


def _faces_meshed(shape, linear_deflection):
    tess = BRepMesh_IncrementalMesh(shape, linear_deflection, False, 0.5, True)
    tess.Perform()
    ex = TopExp_Explorer(shape, TopAbs_FACE)
    while ex.More():
        face = TopoDS.Face_s(ex.Current())
        loc = TopLoc_Location()
        triangulation = BRep_Tool.Triangulation_s(face, loc)
        if triangulation and triangulation.NbTriangles():
            transform = loc.Transformation()
            nodes = [None]
            for node in range(1, triangulation.NbNodes()+1):
                point = triangulation.Node(node).Transformed(transform)
                nodes.append((point.X(),point.Y(),point.Z()))
            reversed_face = int(face.Orientation()) == 1  # TopAbs_REVERSED
            for number in range(1,triangulation.NbTriangles()+1):
                indexes=triangulation.Triangle(number).Get()
                if reversed_face:indexes=indexes[::-1]
                yield (nodes[indexes[0]], nodes[indexes[1]], nodes[indexes[2]])
        ex.Next()


def create_preview(path, records, a_parts, b_parts, colors=None, max_triangles=140000, progress=None):
    """Export an offline HTML viewer with embedded colored triangles; return stats."""
    palette={**COLORS,**(colors or {})}
    geometries=[];status_count={}; total=0; truncated=False
    for record in records:
        if record.b_index is not None:
            part=b_parts[record.b_index]
        elif record.a_index is not None and record.status=='REMOVED':
            part=a_parts[record.a_index]
        else:continue
        status=record.status
        status_count[status]=status_count.get(status,0)+1
        rgb=palette.get(status,COLORS['UNCERTAIN'])
        extent=max(float(v) for v in part.bbox)
        verts=[]
        for triangle in _faces_meshed(part.shape,max(0.15,min(3.0,extent*0.003))):
            if total>=max_triangles:
                truncated=True;break
            verts.extend((*triangle[0],*triangle[1],*triangle[2]))
            total+=1
        if verts:
            geometries.append((status,tuple(rgb),np.asarray(verts,dtype='<f4')))
        if truncated:break
    if not geometries:
        raise ValueError('Podgląd 3D: brak trójkątów do wyświetlenia.')
    packed=[]
    for status,rgb,vertices in geometries:
        packed.append({'status':status,'rgb':list(rgb),'data':base64.b64encode(vertices.tobytes()).decode('ascii')})
    template=Path(__file__).with_name('preview_template.html').read_text(encoding='utf-8')
    title={'SAME':'Bez zmian','RENAMED':'Zmieniona nazwa','MOVED':'Przesunięte',
           'CHANGED':'Zmienione','ADDED':'Nowe','REMOVED':'Usunięte','UNCERTAIN':'Niepewne'}
    counts=', '.join(f'{title.get(k,k)}: {v}' for k,v in status_count.items())
    if truncated:counts+=' · Uwaga: podgląd ograniczony do 140 000 trójkątów'
    html=template.replace('/*__SCENE__*/',json.dumps(packed,separators=(',',':')))
    html=html.replace('/*__STATS__*/',json.dumps(counts,ensure_ascii=False))
    Path(path).write_text(html,encoding='utf-8')
    if progress:progress(f'Podgląd 3D: {len(geometries)} elementów, {total} trójkątów'+(' [uproszczony]' if truncated else ''))
    return {'elementy':len(geometries),'trojkaty':total,'ograniczony':truncated}
