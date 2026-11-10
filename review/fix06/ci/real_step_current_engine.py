"""Validate the actual, newly assembled DS Compare engine on public STEP files.

Two scopes:
* quick: downloaded real individual CAD STEP models, re-export and shifted
  small assembly assembled from their authentic solids.
* full: two distinct official Voron Trident STEP revisions, untouched.

All reports preserve SHA256 provenance, full outcomes and errors. An
incomplete / UNCERTAIN comparison is a FAIL, not a green smoke test.
"""
import argparse,hashlib,json,os,sys,time,traceback,urllib.request,zipfile
from pathlib import Path
import numpy as np

ROOT=Path('evidence/real_step').resolve()
ROOT.mkdir(parents=True,exist_ok=True)
RESULT=ROOT/'TEST_RESULT.json'
DATA={'run':'real_public_step_sources','inputs':[],'cases':[],'verdict':'IN_PROGRESS',
      'source':'VoronDesign public published CAD assets; not synthetic primitives'}

def save():
    RESULT.write_text(json.dumps(DATA,ensure_ascii=False,indent=2,default=str),encoding='utf-8')

def record(name,callback):
    start=time.perf_counter()
    case={'name':name,'status':'RUNNING'}
    DATA['cases'].append(case);save()
    try:
        detail=callback()
        case.update(detail or {})
        case['status']='PASS'
    except BaseException:
        case['status']='FAIL'
        case['traceback']=traceback.format_exc()
        save()
        raise
    finally:
        case['seconds']=round(time.perf_counter()-start,3)
        save()
    return case

def fetch(url,path):
    path.parent.mkdir(parents=True,exist_ok=True)
    req=urllib.request.Request(url,headers={'User-Agent':'DSCompare-Real-CAD-Benchmark'})
    with urllib.request.urlopen(req,timeout=90) as response,path.open('wb') as out:
        while True:
            chunk=response.read(1024*1024)
            if not chunk:break
            out.write(chunk)
    assert path.stat().st_size>2000, f'Blank or missing public STEP: {url}'
    sha=hashlib.sha256(path.read_bytes()).hexdigest()
    DATA['inputs'].append({'url':url,'path':str(path),'bytes':path.stat().st_size,
                           'sha256':sha})
    save()
    return path

def models():
    rev='main'
    base=f'https://raw.githubusercontent.com/VoronDesign/Voron-Trident/{rev}/'
    paths=[
        'Drawings_DXFs/Build_Plate/MIC6_Bed_250.step',
        'Drawings_DXFs/Build_Plate/MIC6_Bed_300.step',
        'Drawings_DXFs/Build_Plate/MIC6_Bed_350.step',
        'experimental/horiz_chain_umb/umbilical_mount_bottom.step',
        'experimental/horiz_chain_umb/corner_ptfe_plate.step',
    ]
    return [fetch(base+p,ROOT/'source'/Path(p).name) for p in paths]

def write_step(path,parts):
    from OCP.STEPControl import STEPControl_Writer,STEPControl_AsIs
    from OCP.IFSelect import IFSelect_RetDone
    writer=STEPControl_Writer()
    for shape in parts:
        assert writer.Transfer(shape,STEPControl_AsIs)==IFSelect_RetDone
    assert writer.Write(str(path))==IFSelect_RetDone
    assert path.exists() and path.stat().st_size>5000
    return path

def import_steps(paths):
    from dsac29.step_io import load_step
    imported=[]
    for path in paths:
        pieces=load_step(str(path),progress=None)
        assert pieces,f'No solid after importing authentic STEP: {path}'
        imported.append(pieces)
    return imported

def quick():
    paths=models()
    imported=import_steps(paths)
    DATA['real_imported_solid_counts']=[len(p) for p in imported]
    save()
    def reexport():
        from dsac29.compare import compare
        from dsac29.geometry_registry import GeometryRegistry
        source=imported[0][0]
        path=write_step(ROOT/'reexport250.step',[source.shape])
        new=import_steps([path])[0][0]
        rows=compare([source],[new],tolerance=.01,revision_only=True,
                     geometry_context=GeometryRegistry(),exact_serialization=True)
        statuses=[r.status for r in rows]
        assert statuses==['SAME'] or statuses==['RENAMED'],statuses
        return {'statuses':statuses,'original_volume':source.volume,'new_volume':new.volume}
    record('authentic_STEP_reexport_same_geometry',reexport)

    def revised_bed():
        from dsac29.compare import compare,Record
        from dsac29.geometry_registry import GeometryRegistry
        from dsac29.revision_overlap import merge_material_revisions
        a=[imported[0][0]];b=[imported[1][0]]
        rows=compare(a,b,tolerance=.01,revision_only=True,
                     geometry_context=GeometryRegistry(),exact_serialization=True)
        assert not any(r.status in ('SAME','RENAMED') for r in rows)
        potential=[Record(0,None,'REMOVED',''),Record(None,0,'ADDED','')]
        revised,regions,diagnostics=merge_material_revisions(
            a,b,potential,tolerance=.01,review_approval=lambda _: 'review')
        statuses=[r.status for r in revised]
        assert 'SAME' not in statuses and 'RENAMED' not in statuses
        return {'statuses':statuses,'material_checks':diagnostics.get('boolean_checks'),
                'fingerprint_surface_analyses':diagnostics.get('fingerprint_surface_analyses'),
                'uncertain_count':statuses.count('UNCERTAIN'),
                'native_stats':{k:v for k,v in diagnostics.items()
                                if k.startswith('fingerprint_') or k in ('boolean_checks','accepted','incomplete')}}
    record('authentic_different_sized_beds_material_candidate',revised_bed)

    def shifted():
        from OCP.gp import gp_Trsf,gp_Vec
        from OCP.TopLoc import TopLoc_Location
        from dsac29.cli import process
        parts=[s[0].shape for s in imported]
        # Real original CAD bodies, only their assembly placements are changed.
        translations=[(i*235.,(i%5)*160.,(i%3)*60.) for i in range(15)]
        shift=(130.,-280.,-410.)
        originals=[];shifted=[]
        for i,point in enumerate(translations):
            a=gp_Trsf();a.SetTranslation(gp_Vec(*point))
            b=gp_Trsf();b.SetTranslation(gp_Vec(*tuple(point[k]+shift[k] for k in range(3))))
            originals.append(parts[i%len(parts)].Moved(TopLoc_Location(a)))
            shifted.append(parts[i%len(parts)].Moved(TopLoc_Location(b)))
        a=write_step(ROOT/'authentic_parts_original.step',originals)
        b=write_step(ROOT/'authentic_parts_translated.step',shifted)
        outdir=ROOT/'shifted_assembly'
        folder,rows,error=process(str(a),str(b),str(outdir),tolerance=.01,
            step=False,diff_step=False,preview3d=False,revision_style=True,
            auto_align=True,force_unrelated=True,full_bom=False,bom_csv=False,
            alignment_approval=lambda _: 'align',
            material_approval=lambda _: 'review',
            progress=lambda msg:print(str(msg),flush=True))
        statuses={}
        for item in rows:statuses[item.status]=statuses.get(item.status,0)+1
        summary=json.loads((folder/'PODSUMOWANIE.json').read_text(encoding='utf-8'))
        timing=json.loads((folder/'CZASY_ANALIZY.json').read_text(encoding='utf-8'))
        assert not error,error
        assert summary.get('solids_A')==len(originals),summary
        assert summary.get('solids_B')==len(shifted),summary
        assert summary.get('alignment',{}).get('applied') is True,summary.get('alignment')
        assert statuses.get('SAME',0)+statuses.get('RENAMED',0)==len(originals),statuses
        assert statuses.get('MOVED',0)==0 and statuses.get('UNCERTAIN',0)==0,statuses
        return {'statuses':statuses,'alignment':summary.get('alignment'),
                'seconds':timing.get('total_s'),'fingerprint_cache':timing.get('registry')}
    record('shift_15_authentic_industrial_STEP_parts',shifted)

def full():
    from dsac29.cli import process
    a_sha='9d9223311f2b0fce72484023d6a755e13a733319'
    b_sha='1a49bdc2c524cd6f4491a01e8fd566d0bd6acd0a'
    remote='CAD/trident_assembly.step.zip'
    def get(sha,label):
        url=f'https://raw.githubusercontent.com/VoronDesign/Voron-Trident/{sha}/{remote}'
        archive=fetch(url,ROOT/'full_source'/f'{label}.zip')
        folder=ROOT/'full_source'/label
        folder.mkdir(exist_ok=True)
        with zipfile.ZipFile(archive) as z:
            names=[n for n in z.namelist() if n.lower().endswith(('.step','.stp'))]
            assert names
            name=max(names,key=lambda n:z.getinfo(n).file_size)
            target=folder/Path(name).name
            with z.open(name) as inp,target.open('wb') as out:
                while True:
                    block=inp.read(1024*1024)
                    if not block:break
                    out.write(block)
        DATA['inputs'].append({'url':url,'path':str(target),
                               'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),
                               'bytes':target.stat().st_size})
        save()
        return target
    old=get(a_sha,'trident_older')
    new=get(b_sha,'trident_newer')
    def compare_real_revision():
        folder,rows,error=process(str(old),str(new),str(ROOT/'trident_real_revision'),
            tolerance=.01,auto_align=True,force_unrelated=True,
            step=False,diff_step=False,preview3d=False,
            revision_style=True,full_bom=False,bom_csv=False,
            alignment_approval=lambda _: 'original',
            material_approval=lambda _: 'review',
            progress=lambda msg:print(str(msg),flush=True))
        stats={}
        for row in rows:stats[row.status]=stats.get(row.status,0)+1
        summary=json.loads((folder/'PODSUMOWANIE.json').read_text(encoding='utf8'))
        timing=json.loads((folder/'CZASY_ANALIZY.json').read_text(encoding='utf8'))
        details={'statuses':stats,'seconds':timing.get('total_s'),
                 'material_revision_matching_s':timing.get('material_revision_matching_s'),
                 'incomplete':summary.get('analysis_complete') is not True,
                 'material_complete':summary.get('material_analysis_complete'),
                 'alignment':summary.get('alignment')}
        DATA['full_real_summary']=details
        save()
        if error:raise RuntimeError(f'Comparison error {error}')
        if stats.get('UNCERTAIN',0)>0:raise AssertionError(f'Incomplete real STEP geometry: {stats}')
        if summary.get('analysis_complete') is not True:
            raise AssertionError(f'Real STEP comparison not fully complete: {stats}')
        return details
    record('two_authentic_Trident_revision_STEP_files',compare_real_revision)

def main():
    p=argparse.ArgumentParser()
    p.add_argument('mode',choices=('quick','full'))
    args=p.parse_args()
    try:
        if args.mode=='quick':quick()
        else:full()
        DATA['verdict']='PASS'
    except BaseException:
        DATA['verdict']='FAIL'
        DATA['error']=traceback.format_exc()
        raise
    finally:
        save()
        print('REAL_STEP_TEST_SUMMARY',json.dumps({
            'verdict':DATA['verdict'],
            'cases':[{k:v for k,v in case.items() if k in ('name','status','seconds','statuses','uncertain_count')}
                     for case in DATA['cases']]},ensure_ascii=False),flush=True)

if __name__=='__main__':main()
