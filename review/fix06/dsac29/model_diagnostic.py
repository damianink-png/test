"""Read-only STEP property report; properties are hints, not equality proofs."""
import json
from pathlib import Path
from time import perf_counter


def run(paths, folder, max_solids, progress):
    from .step_io import load_step
    from .step_diagnostics import schema_header
    from .geometry_registry import GeometryRegistry
    reports=[]
    for label,path in zip(('A','B'),paths):
        stats={};started=perf_counter()
        parts=load_step(path,max_solids=max_solids,progress=progress,diagnostics=stats)
        registry=GeometryRegistry();groups={}
        for i,p in enumerate(parts):
            key=registry.definition(p)
            groups.setdefault(key,[]).append(i)
        solids=[]
        for ids in groups.values():
            p=parts[ids[0]]
            solids.append({'occurrences':len(ids),'name':p.name,'path':p.path,
                'volume_mm3':float(p.volume),'area_mm2':float(p.area),
                'central_principal_moments':list(map(float,p.eigenvalues)),
                'bbox_mm':list(map(float,p.bbox)),
                'centers_mm':[list(map(float,parts[i].center)) for i in ids]})
        reports.append({'model':label,'file_name':Path(path).name,
            'schema':schema_header(Path(path)),'import_seconds':perf_counter()-started,
            'import_diagnostics':stats,'solid_count':len(parts),'native_definition_count':len(solids),
            'definitions':solids})
    data={'description':'Dane CAD; identyczne wartości nie są dowodem zgodności geometrii. Nazwy i położenia mogą być poufne.',
          'models':reports}
    output=Path(folder)/'DIAGNOSTYKA_MODELI.txt'
    output.write_text(json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
    return output
