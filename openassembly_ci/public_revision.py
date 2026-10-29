"""Regression on REAL public Voron/Trident STEP assemblies with CONTROLLED edits.
B is synthetic, not a genuine manufacturer revision. Independent OpenAssembly code.
"""
import argparse, csv, hashlib, json, os, subprocess, sys, time, traceback, urllib.request, zipfile
from collections import Counter
from pathlib import Path
from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
from OCP.gp import gp_Pnt, gp_Trsf, gp_Vec
from OCP.IFSelect import IFSelect_RetDone
from OCP.STEPCAFControl import STEPCAFControl_Writer
from OCP.TCollection import TCollection_ExtendedString
from OCP.TDataStd import TDataStd_Name
from OCP.TopLoc import TopLoc_Location
from OCP.XCAFDoc import XCAFDoc_DocumentTool
from openassembly.stepio import empty_doc, load_step

SOURCES = {
    'voron2': ('Voron-2','e64c83bcb84d41c0324e104a1c911879174d08aa','CAD/Voron_2.4r2_Assembly_STEP.zip'),
    'trident': ('Voron-Trident','1a49bdc2c524cd6f4491a01e8fd566d0bd6acd0a','CAD/trident_assembly.step.zip')
}

def choose(parts):
    geom = Counter(p.fingerprint for p in parts)
    names = Counter(p.name.casefold() for p in parts)
    eligible = [p for p in parts if geom[p.fingerprint] == 1 and names[p.name.casefold()] == 1
                and p.name.strip() and p.volume > 25 and p.area > 0
                and p.extents and min(p.extents) > 1]
    eligible.sort(key=lambda p: (len(p.fingerprint[3]),len(p.fingerprint[4]),p.volume,p.uid))
    assert len(eligible) >= 3, 'Not enough unique CAD parts for provable revision'
    return dict(zip(('revised','moved','removed'),eligible[:3]))

def make_b(parts, selected, target):
    import cadquery as cq
    doc = empty_doc()
    tool = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())
    move = gp_Trsf()
    move.SetTranslation(gp_Vec(17,-9,13))
    scale = gp_Trsf()
    scale.SetScale(gp_Pnt(*selected['revised'].centroid),1.025)
    for part in parts:
        if part is selected['removed']:
            continue
        shape = (part.shape.Moved(TopLoc_Location(move)) if part is selected['moved']
                 else BRepBuilderAPI_Transform(part.shape,scale,True).Shape()
                 if part is selected['revised'] else part.shape)
        label = tool.AddShape(shape,False)
        TDataStd_Name.Set_s(label,TCollection_ExtendedString(part.name))
    center = (max(p.centroid[0] for p in parts)+2000,0,0)
    marker = cq.Workplane().box(7.23,11.37,19.19).val().translate(center)
    label = tool.AddShape(marker.wrapped,False)
    TDataStd_Name.Set_s(label,TCollection_ExtendedString('OAC_CI_NEW_MARKER'))
    writer = STEPCAFControl_Writer()
    writer.SetNameMode(True)
    assert writer.Transfer(doc), 'Cannot transfer controlled revision'
    assert writer.Write(str(target)) == IFSelect_RetDone, 'Cannot export controlled revision'

def verify(result, job, n, selected, env, timeout):
    data = json.loads((job/'comparison.json').read_text(encoding='utf-8'))
    expected = {'unchanged':n-3,'moved':1,'removed':1,'new':1,'revised_old':1,'revised_new':1}
    result['expected_summary'] = expected
    result['actual_summary'] = data.get('summary')
    assert data['summary'] == expected, ('Wrong classification',data['summary'],expected)
    assert not data['alignment']['applied'], ('Spurious global shift',data['alignment'])
    assert len(data['revisions']) == 1, data['revisions']
    revision = data['revisions'][0]
    assert revision['overlap'] >= .72 and (
        revision.get('added_mm3',0)>0 or revision.get('removed_mm3',0)>0), revision
    assert not data['skipped_parts'], data['skipped_parts']
    for category, source, status in [('revised','B','revised_new'),('moved','B','moved'),('removed','A','removed')]:
        name = selected[category].name
        items = [x for x in data['items'] if x['name']==name and x['source']==source]
        assert len(items)==1 and items[0]['status']==status, (category,name,items)
    added = [x for x in data['items'] if x['source']=='B' and x['name']=='OAC_CI_NEW_MARKER']
    assert len(added)==1 and added[0]['status']=='new', added
    html = (job/'RAPORT_3D.html').read_text(encoding='utf-8')
    assert len(html)>1000 and '<canvas' in html and 'moved' in html and 'revised_new' in html
    for file in ('BOM_A.csv','BOM_B.csv','BOM_ROZNICE.csv','BOM_ZMIANY.csv','RAPORT_ZMIAN.md'):
        assert (job/file).stat().st_size>50, file
    with (job/'BOM_ROZNICE.csv').open(encoding='utf-8-sig',newline='') as f:
        rows = list(csv.DictReader(f,delimiter=';'))
    assert any(x['Nazwa części']=='OAC_CI_NEW_MARKER' and x['Zmiana ilości']=='1'
               for x in rows), 'Added part absent from BOM'
    # B has n occurrences, plus removed and old revised geometry in colored STEP.
    cmd = [sys.executable,'-m','openassembly.benchmark_readback',
           str(job/'POROWNANIE_KOLORY.step'),str(n+2)]
    p = subprocess.run(cmd,capture_output=True,text=True,timeout=min(timeout,600),env=env)
    result['readback_stdout'] = p.stdout[-2000:]
    result['readback_stderr'] = p.stderr[-2000:]
    assert p.returncode == 0, ('STEP readback failed',p.stderr[-1000:])
    result['result_file_bytes'] = {x.name:x.stat().st_size for x in job.iterdir() if x.is_file()}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--model',choices=SOURCES,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--executable',type=Path,required=True)
    parser.add_argument('--timeout',type=int,default=3000)
    o = parser.parse_args()
    root = o.output.resolve()
    root.mkdir(parents=True,exist_ok=True)
    start = time.monotonic()
    result = {'model':o.model,'scenario':'controlled_revision','status':'FAIL','stages':[]}
    def save():
        (root/'RESULT.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    def mark(stage):
        entry = {'stage':stage,'elapsed_s':round(time.monotonic()-start,2)}
        result['stages'].append(entry)
        print('[PUBLIC REVISION]',json.dumps(entry),flush=True)
        save()
    try:
        repo,commit,file = SOURCES[o.model]
        url = f'https://raw.githubusercontent.com/VoronDesign/{repo}/{commit}/{file}'
        archive = root/'public.zip'
        if not archive.exists():
            urllib.request.urlretrieve(url,str(archive))
        with zipfile.ZipFile(archive) as z:
            entries = [x for x in z.namelist() if Path(x).suffix.lower() in ('.step','.stp')
                       and not x.startswith('__MACOSX/')]
            assert entries, 'No public STEP file'
            a = root/'A.step'
            a.write_bytes(z.read(max(entries,key=lambda x:z.getinfo(x).file_size)))
        result.update(source=url,source_sha256=hashlib.sha256(a.read_bytes()).hexdigest())
        mark('download_original')
        old = load_step(a,'A')
        n = len(old)
        assert n>600, ('Expected a real large assembly',n)
        result['old_count'] = n
        selected = choose(old)
        result['selected'] = {k:{'name':v.name,'id':v.uid,'volume_mm3':v.volume}
                              for k,v in selected.items()}
        mark('import_and_select')
        b = root/'B_controlled_revision.step'
        make_b(old,selected,b)
        mark('create_controlled_revision')
        job = root/'comparison'
        job.mkdir(exist_ok=True)
        env = {**os.environ,'PYTHONFAULTHANDLER':'1','PYTHONUTF8':'1'}
        cmd = [str(o.executable.resolve()),str(a),str(b),'-o',str(job)]
        result['command'] = cmd
        save()
        worker_start = time.monotonic()
        with (root/'worker.log').open('w',encoding='utf-8') as log:
            p = subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,timeout=o.timeout,env=env)
        result['worker_elapsed_s'] = round(time.monotonic()-worker_start,2)
        result['return_code'] = p.returncode
        mark('comparison_worker_exit')
        assert p.returncode == 0, ('CLI failed',p.returncode)
        verify(result,job,n,selected,env,o.timeout)
        result['status'] = 'PASS'
        mark('revision_export_readback_PASS')
    except BaseException:
        result['error'] = traceback.format_exc()
        print(result['error'],flush=True)
        save()
        raise
    finally:
        save()

if __name__=='__main__':
    main()
