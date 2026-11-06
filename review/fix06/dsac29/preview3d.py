"""Self-contained WebGL preview: visual colors, independent of STEP reader settings.

The preview is an approximation produced from B-Rep triangulation, not CAD-quality
geometry, and never substitutes for the original STEP geometry or the BOM.
"""
from __future__ import annotations
import base64
import json
import shutil
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


class _MeshCache:
    """Exact native definition cache, limited to 32 MiB per export."""
    def __init__(self):
        self.entries={};self.bytes=0;self.hits=0
    def world_points(self,shape,deflection):
        local=shape.Located(TopLoc_Location())
        key=(hash(local),int(local.Orientation()),float(deflection))
        pts=None
        for saved,points in self.entries.get(key,()):
            if local.IsSame(saved):pts=points;self.hits+=1;break
        if pts is None:
            pts=np.asarray(list(_faces_meshed(local,deflection)),dtype=float).reshape(-1,3)
            if self.bytes+pts.nbytes<=32*1024*1024:
                self.entries.setdefault(key,[]).append((local,pts));self.bytes+=pts.nbytes
        tr=shape.Location().Transformation()
        rotation=np.array([[tr.Value(i,j) for j in range(1,4)] for i in range(1,4)])
        offset=np.array([tr.Value(i,4) for i in range(1,4)])
        return pts@rotation.T+offset


def create_preview(path, records, a_parts, b_parts, colors=None, max_triangles=300000, progress=None, old_alpha=0.4, material_regions=None, alignment=None, dual_revisions=False):
    """Offline comparison scene, both revisions, after global registration.

    Whole occurrences only: the triangle target never drops a solid.
    Coordinates are centered in double precision before packing float32.
    """
    from .step_io import REVISION_COLORS
    from .material_deltas import COLORS as MATERIAL_COLORS,solids as delta_solids
    from .geometry import describe
    palette={**REVISION_COLORS,**MATERIAL_COLORS,**(colors or {})}
    material_regions=material_regions or {}
    entries=[]
    for record_index,record in enumerate(records):
        status=record.status
        if status=='CHANGED' and record_index in material_regions:
            regions=material_regions[record_index]
            parent=b_parts[record.b_index]
            for kind,shape,role in (
                ('CHANGED_COMMON',regions.common,'B'),
                ('CHANGED_ADDED',regions.added,'B'),
                ('CHANGED_REMOVED',regions.removed,'A')):
                for n,piece in enumerate(delta_solids(shape),1):
                    label=f'{parent.name} / {kind} ({n})'
                    part=describe(piece,label,parent.path,source=parent.source)
                    entries.append((part,kind,role,old_alpha if role=='A' else 1.,record_index,
                                    record.a_index if role=='A' else record.b_index))
                    if dual_revisions and kind=='CHANGED_COMMON':
                        old=a_parts[record.a_index]
                        from dataclasses import replace
                        old_common=replace(part,name=f'{old.name} / {kind} ({n})',path=old.path,source=old.source)
                        entries.append((old_common,kind,'A',old_alpha,record_index,record.a_index))
            continue
        if status in ('SAME','RENAMED'):
            if dual_revisions and record.a_index is not None:entries.append((a_parts[record.a_index],'SAME','A',old_alpha,record_index,record.a_index))
            if record.b_index is not None:entries.append((b_parts[record.b_index],'SAME','B',1.0,record_index,record.b_index))
            continue
        for role,index,parts in (('A',record.a_index,a_parts),('B',record.b_index,b_parts)):
            if index is None:continue
            key=(('MOVED_OLD' if role=='A' else 'MOVED') if status=='MOVED' else
                 (status+('_OLD' if role=='A' else '_NEW')) if status in ('CHANGED','UNCERTAIN') else
                 ('REMOVED' if role=='A' else 'ADDED'))
            entries.append((parts[index],key,role,old_alpha if role=='A' else 1.0,record_index,index))
    if not entries:raise ValueError('Podgląd 3D: brak brył do wyświetlenia.')
    entries.sort(key=lambda item: (item[1]=='SAME', item[2]!='A'))
    origin=np.mean([p.center for p,_,_,_,_,_ in entries],axis=0)
    # Stream the potentially very large mesh scene to disk rather than
    # retaining the base64 data for every occurrence in the Python heap.
    path=Path(path)
    scene_draft=path.with_suffix('.scene.json.tmp')
    draft=path.with_suffix('.html.tmp')
    packed_count=0;total=0;omitted=0
    from .shared_mesh import SharedMesh
    mesh_cache=SharedMesh()
    try:
        with scene_draft.open('w',encoding='utf-8') as scene:
            scene.write('[')
            for i,(part,key,role,alpha,record_index,part_index) in enumerate(entries):
                extent=max(float(v) for v in part.bbox)
                payload,count=mesh_cache.pack(part.shape,max(0.15,min(3.0,extent*0.003)),origin,_faces_meshed)
                total+=count//3
                record=records[record_index]
                source_a=a_parts[record.a_index] if record.a_index is not None else None
                source_b=b_parts[record.b_index] if record.b_index is not None else None
                packed_item={'status':key,'role':role,'rgb':list(palette[key]),'alpha':float(alpha),
                             'name':str(part.name),'record_index':record_index,'part_index':part_index,
                             'pair_id':f'PAIR_{record_index:06d}',
                             'path_A':str(source_a.path) if source_a else '',
                             'path_B':str(source_b.path) if source_b else '',
                             'name_A':str(source_a.name) if source_a else '',
                             'name_B':str(source_b.name) if source_b else '',
                             **payload}
                if packed_count:scene.write(',')
                scene.write(json.dumps(packed_item,separators=(',',':'),ensure_ascii=False).replace('<',r'\u003c'))
                packed_count+=1
                if progress and i%100==0:progress(f'Podgląd HTML: {i+1}/{len(entries)} wystąpień')
            scene.write(']')
        if not packed_count:raise ValueError('Podgląd 3D: brak pełnych brył w limicie siatki.')
        info={'elementy':packed_count,'wszystkie':len(entries),'trojkaty':total,'pominiete':omitted,
              'dual_revisions':bool(dual_revisions),'alignment':alignment or {},'world_origin':origin.tolist(),
              'mesh_cache_hits':mesh_cache.hits,'unique_meshes':mesh_cache.definitions,'ograniczony':False,'limit_trojkatow':max_triangles,'przekroczony_cel_siatki':total>max_triangles}
        template=Path(__file__).with_name('preview_template.html').read_text(encoding='utf-8')
        before,after=template.split('/*__SCENE__*/',1)
        statistics=json.dumps(info,ensure_ascii=False).replace('<',r'\u003c')
        before=before.replace('/*__STATS__*/',statistics)
        after=after.replace('/*__STATS__*/',statistics)
        with draft.open('w',encoding='utf-8') as stream:
            stream.write(before)
            with scene_draft.open('r',encoding='utf-8') as scene:
                shutil.copyfileobj(scene,stream,length=1024*1024)
            stream.write(after)
        draft.replace(path)
    finally:
        scene_draft.unlink(missing_ok=True)
        draft.unlink(missing_ok=True)
    if progress:progress(f'Podgląd 3D: {packed_count} wystąpień, {total} trójkątów; pominięto {omitted}')
    return info
