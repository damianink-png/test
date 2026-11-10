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


def authentic_bent(mode):
    """Use unchanged public aerospace sheet-metal STEP geometry as operands."""
    from io import BytesIO
    from collections import Counter
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopAbs import TopAbs_FACE
    from OCP.TopoDS import TopoDS
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    from OCP.BRepTools import BRepTools
    from OCP.gp import gp_Trsf,gp_Vec,gp_Pnt
    from OCP.TopLoc import TopLoc_Location
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut
    from OCP.BRepPrimAPI import BRepPrimAPI_MakeSphere
    from OCP.Bnd import Bnd_Box
    from OCP.BRepBndLib import BRepBndLib
    from OCP.GProp import GProp_GProps
    from OCP.BRepGProp import BRepGProp
    from dsac29.cli import process
    from dsac29.step_io import load_step

    url=('https://zenodo.org/records/7799961/files/'
         'AFR%20source%20code%2C%20STEP%20files%20and%20solved%20examples.zip?download=1')
    archive=fetch(url,ROOT/'aerospace_bent_source.zip')
    assert hashlib.md5(archive.read_bytes()).hexdigest()==(
        'd6ef1bd2bc197c36d74bb706915ae11f'),'External data changed'
    inputs=[]
    with zipfile.ZipFile(archive) as outer:
        for entry in outer.infolist():
            if entry.file_size>60_000_000:continue
            items=[]
            if entry.filename.lower().endswith(('.step','.stp')):
                items=[(entry.filename,outer.read(entry))]
            elif entry.filename.lower().endswith('.zip'):
                try:
                    with zipfile.ZipFile(BytesIO(outer.read(entry))) as inner:
                        items=[(s.filename,inner.read(s)) for s in inner.infolist()
                               if s.filename.lower().endswith(('.step','.stp'))
                               and 200<s.file_size<60_000_000]
                except (zipfile.BadZipFile,RuntimeError):
                    continue
            for original,content in items:
                if len(content)<200:continue
                name=Path(original.replace('\\','/')).name
                dest=ROOT/'aerospace_input'/f'{len(inputs):02d}_{name}'
                dest.parent.mkdir(parents=True,exist_ok=True)
                dest.write_bytes(content)
                inputs.append(dest)
                DATA['inputs'].append({'url':url,'source_name':original,
                                       'sha256':hashlib.sha256(content).hexdigest(),
                                       'bytes':len(content)})
    assert inputs,'Research dataset contains no extractable STEP files'
    items=[]
    for path in inputs:
        try:
            for part in load_step(str(path),progress=None):
                types=Counter()
                ex=TopExp_Explorer(part.shape,TopAbs_FACE)
                while ex.More():
                    adapt=BRepAdaptor_Surface(TopoDS.Face_s(ex.Current()))
                    types[str(adapt.GetType()).split('.')[-1].replace('GeomAbs_','')]+=1
                    ex.Next()
                    if sum(types.values())>350:break
                curved=sum(types[t] for t in ('Cylinder','Cone','Torus','Sphere'))
                if curved:
                    items.append((curved,part,path.name,dict(types)))
        except (ValueError,RuntimeError) as exc:
            DATA.setdefault('unreadable_step_inputs',[]).append((path.name,str(exc)))
    assert items,'No imported analytic curved sheet-metal solid in research STEP data'
    items.sort(key=lambda e:(-e[0],-e[1].volume))
    distinct=[];seen=set()
    for curved,part,path,types in items:
        if path in seen:continue
        seen.add(path);distinct.append(part.shape)
        DATA.setdefault('curved_source_models',[]).append(
            {'file':path,'face_types':types,'volume_mm3':part.volume})
        if len(distinct)>=6:break
    save()
    def bounds(shape):
        b=Bnd_Box()
        BRepBndLib.AddOptimal_s(shape,b,False,False)
        return np.asarray(b.Get(),float)
    def volume(shape):
        g=GProp_GProps()
        BRepGProp.VolumeProperties_s(shape,g)
        return float(g.Mass())
    def shifted(shape,xyz):
        t=gp_Trsf();t.SetTranslation(gp_Vec(*map(float,xyz)))
        return shape.Moved(TopLoc_Location(t))
    def notch(shape):
        before=volume(shape)
        extent=np.linalg.norm(bounds(shape)[3:]-bounds(shape)[:3])
        r=max(2.,min(10.,.03*extent))
        ex=TopExp_Explorer(shape,TopAbs_FACE)
        for _ in range(30):
            if not ex.More():break
            face=TopoDS.Face_s(ex.Current());ex.Next()
            try:
                u0,u1,v0,v1=BRepTools.UVBounds_s(face)
                if not np.isfinite((u0,u1,v0,v1)).all():continue
                p=BRepAdaptor_Surface(face).Value((u0+u1)/2,(v0+v1)/2)
                cutter=BRepPrimAPI_MakeSphere(gp_Pnt(p.X(),p.Y(),p.Z()),r).Shape()
                op=BRepAlgoAPI_Cut(shape,cutter)
                op.Build()
                if not op.IsDone():continue
                changed=op.Shape()
                fraction=(before-volume(changed))/before
                if 1.e-5<fraction<.20:
                    DATA['notch_removed_fraction']=fraction
                    return changed
            except (ValueError,RuntimeError,TypeError):
                continue
        raise AssertionError('Could not remove measurable material from real bent CAD solid')
    variant=notch(distinct[0])
    count=40
    pitch=max(320.,2.*max(max(bounds(s)[3:]-bounds(s)[:3]) for s in distinct))
    old=[];new=[]
    removed_ids={9,37}
    changed_ids=[i for i in range(count)
                 if i%len(distinct)==0 and i not in removed_ids][:2]
    assert len(changed_ids)==2
    DATA['expected_modified_indices']=changed_ids
    for i in range(count):
        point=(float((i%8)*pitch),float((i//8)*pitch),float((i%3)*21))
        source=distinct[i%len(distinct)]
        old.append(shifted(source,point))
        if mode=='bent_repeat' and i in removed_ids:
            continue
        changed=variant if i in (changed_ids[:1] if mode=='bent_single' else changed_ids) else source
        if mode=='bent_single':
            # Exactly one local revision in 40 repeated curved bodies.
            pass
        elif mode=='bent_repeat' and i in (13,27):
            point=(point[0]+pitch*.15,point[1],point[2])
        if mode=='bent_shift':
            point=(point[0]+130.,point[1]-280.,point[2]-410.)
        new.append(shifted(changed,point))
    if mode=='bent_repeat':
        for i in (50,51):
            pos=(float(i%8*pitch+pitch*.31),float(i//8*pitch),21.)
            new.append(shifted(distinct[(i+1)%len(distinct)],pos))
    old_path=write_step(ROOT/f'{mode}_old.step',old)
    new_path=write_step(ROOT/f'{mode}_new.step',new)
    def check():
        folder,rows,error=process(str(old_path),str(new_path),
           str(ROOT/mode),tolerance=.01,auto_align=mode=='bent_shift',
           force_unrelated=True,step=False,diff_step=False,preview3d=False,
           revision_style=True,full_bom=False,bom_csv=False,
           material_approval=lambda _:'review',
           alignment_approval=lambda _:'align',
           progress=lambda msg:print('BENT_STEP',str(msg),flush=True))
        statuses=dict(Counter(r.status for r in rows))
        summ=json.loads((folder/'PODSUMOWANIE.json').read_text(encoding='utf8'))
        times=json.loads((folder/'CZASY_ANALIZY.json').read_text(encoding='utf8'))
        detail={'statuses':statuses,'solids_A':summ.get('solids_A'),
                'solids_B':summ.get('solids_B'),
                'alignment':summ.get('alignment'),'timings':times,
                'error':str(error) if error else None}
        DATA['bent_full_comparison']=detail
        save()
        assert not error,detail
        assert detail['solids_A']==count and detail['solids_B']==count,detail
        assert not statuses.get('UNCERTAIN',0),detail
        assert statuses.get('SAME',0)+statuses.get('RENAMED',0)>=29,detail
        # A green benchmark MUST actually recognize every deliberately
        # modified original sheet-metal solid as CHANGED, not silently
        # accept ADDED+REMOVED as a successful material revision.
        assert statuses.get('CHANGED',0)==(
            1 if mode=='bent_single' else 2),(
            'A genuine changed STEP body was not matched by Common/Cut',detail)
        if mode=='bent_shift':
            assert summ.get('alignment',{}).get('applied') is True,detail
        return {'statuses':statuses,'geometry_changed_occurrences':
                1 if mode=='bent_single' else 2,
                'elapsed_s':times.get('total_s'),
                'curved_source_count':len(distinct)}
    record(f'authentic_sheet_bent_{mode}_40_repeated_bodies',check)


def main():
    p=argparse.ArgumentParser()
    p.add_argument('mode',choices=('quick','full','bent_single','bent_repeat','bent_shift'))
    args=p.parse_args()
    try:
        if args.mode=='quick':quick()
        elif args.mode=='full':full()
        else:authentic_bent(args.mode)
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
