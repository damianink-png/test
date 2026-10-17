"""Visualization from the already loaded B-Rep; no intermediate STEP export."""
import json,re
from pathlib import Path
import numpy as np
from .preview3d import _faces_meshed
from .step_io import COLORS

def metadata(name):
    m=re.match(r'^\[([A-Z]+)\] \[R(\d+)\]',str(name))
    return (m.group(1),int(m.group(2))) if m else ('',None)

def make_result_scene(a,b,records,folder,colors=None,progress=None):
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    (folder/'SCENA_WYNIK.npz').unlink(missing_ok=True)
    (folder/'UWAGI_SCENA.txt').unlink(missing_ok=True)
    palette={**COLORS,**(colors or {})}
    vertices=[];offsets=[0];names=[];rgb=[];roles=[];errors=[]
    for n,record in enumerate(records):
        if record.a_index is not None and record.b_index is not None and record.status in ('CHANGED','UNCERTAIN','MOVED'):
            from OCP.BRepTools import BRepTools
            cache=folder/'Geometria';cache.mkdir(exist_ok=True)
            for role,part in [('A',a[record.a_index]),('B',b[record.b_index])]:
                if not BRepTools.Write_s(part.shape,str(cache/f'R{n:06d}_{role}.brep')):
                    raise RuntimeError('Nie zapisano geometrii do szczegółów')
        entries=[]
        if record.b_index is not None:entries.append((b[record.b_index],'B'))
        if record.a_index is not None and (record.b_index is None or record.status in ('MOVED','CHANGED','UNCERTAIN')):
            entries.append((a[record.a_index],'A'))
        for part,role in entries:
            try:
                linear=max(0.03,min(0.6,max(part.bbox)*0.0015))
                pts=np.asarray([p for tri in _faces_meshed(part.shape,linear) for p in tri],dtype=np.float32).reshape(-1,3)
                if not len(pts):raise ValueError('Brak trójkątów')
                vertices.append(pts);offsets.append(offsets[-1]+len(pts))
                names.append(f'[{record.status}] [R{n:06d}] {part.name} [{role}]')
                rgb.append(palette[record.status]);roles.append(role)
            except Exception as exc:errors.append({'record':n,'role':role,'error':str(exc)})
        if progress and n%25==0:progress(f'Podgląd wyniku: {n+1}/{len(records)} pozycji')
    info={'expected_records':len(records),'rendered_records':len({metadata(n)[1] for n in names}),
          'bodies':len(names),'errors':errors,'complete':not errors}
    (folder/'SCENA_DIAGNOSTYKA.json').write_text(json.dumps(info,ensure_ascii=False,indent=2),encoding='utf-8')
    if errors:
        (folder/'UWAGI_SCENA.txt').write_text(f"Niepełny podgląd: {info['rendered_records']}/{info['expected_records']} pozycji; błędów siatki: {len(errors)}. Zobacz SCENA_DIAGNOSTYKA.json.",encoding='utf-8')
    if vertices:
        temp=folder/'SCENA_WYNIK.npz.tmp'
        with temp.open('wb') as f:
            np.savez_compressed(f,vertices=np.concatenate(vertices),offsets=np.array(offsets,dtype=np.int64),
                names=np.array(names),colors=np.array(rgb,dtype=np.float32),roles=np.array(roles))
        temp.replace(folder/'SCENA_WYNIK.npz')
    return info


def make_detail(folder,index,tolerance=0.01,progress=None):
    from OCP.BRepTools import BRepTools
    from OCP.BRep import BRep_Builder
    from OCP.TopoDS import TopoDS_Shape
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut
    from .geometry import describe
    from .step_io import _solids
    from .compare import Record
    folder=Path(folder);shapes=[]
    for role in ('A','B'):
        shape=TopoDS_Shape()
        if not BRepTools.Read_s(shape,str(folder/'Geometria'/f'R{index:06d}_{role}.brep'),BRep_Builder()):
            raise ValueError('Brak zapisanej pary geometrii. Uruchom porównanie w V4.2.')
        shapes.append(shape)
    added=[];removed=[];records=[]
    for first,second,parts,status in [(shapes[0],shapes[1],removed,'REMOVED'),(shapes[1],shapes[0],added,'ADDED')]:
        op=BRepAlgoAPI_Cut(first,second);op.SetFuzzyValue(max(tolerance/100,1e-6));op.Build()
        if not op.IsDone():raise RuntimeError('Nie udało się obliczyć różnicy B-Rep')
        for shape in _solids(op.Shape()):
            part=describe(shape,'Różnica materiału','Różnica materiału')
            if part.volume<=max(tolerance**3,1e-5):continue
            idx=len(parts);parts.append(part)
            records.append(Record(idx if status=='REMOVED' else None,idx if status=='ADDED' else None,status,'Różnica wybranej pary'))
    out=folder/f'Szczegoly_R{index:06d}';out.mkdir(exist_ok=True)
    make_result_scene(removed,added,records,out,progress=progress)
    return out
