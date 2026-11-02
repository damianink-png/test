"""Real public Simple Swerve revision pair, using the frozen Windows EXE."""
import hashlib,json,subprocess,time,traceback,urllib.request,zipfile
from pathlib import Path
import sys
exe=Path(sys.argv[1]).resolve()
root=Path('evidence').resolve();root.mkdir(exist_ok=True)
out=root/'comparison';out.mkdir(exist_ok=True)
report={'model':'Simple Swerve','case':'v1_to_v2_gobilda','exe_sha256':hashlib.sha256(exe.read_bytes()).hexdigest(),'sources':[]}
def save():(root/'TEST_RESULT.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
try:
    sources=[]
    for name in ('simple-swerve-v1.zip','simple-swerve-v2-gobilda.zip'):
        url='https://raw.githubusercontent.com/AloeVeraZ/diffy-swerve/main/cad/releases/'+name
        folder=Path('models')/name.replace('.zip','');folder.mkdir(parents=True,exist_ok=True)
        archive=folder/name
        urllib.request.urlretrieve(url,archive)
        with zipfile.ZipFile(archive) as z:z.extractall(folder)
        candidates=[p for p in folder.rglob('*') if p.suffix.lower() in ('.step','.stp')]
        if not candidates:raise RuntimeError('No STEP model in '+name)
        source=max(candidates,key=lambda p:p.stat().st_size).resolve()
        sources.append(source)
        report['sources'].append({'url':url,'name':source.name,'sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'bytes':source.stat().st_size})
    save()
    cmd=[str(exe),'--worker','compare','--a',str(sources[0]),'--b',str(sources[1]),
         '--output',str(out),'--align-auto','--generate-step','--preview3d','--revision-style']
    report['command']=cmd;save()
    start=time.monotonic()
    with (root/'EXE_STDOUT.log').open('wb') as stdout,(root/'EXE_STDERR.log').open('wb') as stderr:
        proc=subprocess.Popen(cmd,stdout=stdout,stderr=stderr)
        handled=set()
        while proc.poll() is None:
            question=out/'_WYROWNANIE_PYTANIE.json'
            if question.is_file():
                try:
                    data=json.loads(question.read_text(encoding='utf-8'));token=data['token']
                    if token not in handled:
                        handled.add(token)
                        decision='review' if data.get('material_unverified') else 'original'
                        (out/'_WYROWNANIE_ODPOWIEDZ.json').write_text(json.dumps({'token':token,'decision':decision}),encoding='utf-8')
                except (OSError,ValueError,KeyError):pass
            if time.monotonic()-start>1800:
                subprocess.run(['taskkill','/F','/T','/PID',str(proc.pid)],capture_output=True)
                raise TimeoutError('Simple Swerve comparison exceeded 1800 seconds')
            time.sleep(.5)
    report['seconds']=round(time.monotonic()-start,2)
    report['returncode']=proc.returncode;save()
    if proc.returncode:raise RuntimeError('Windows EXE failed with '+str(proc.returncode))
    summary=json.loads((out/'PODSUMOWANIE.json').read_text(encoding='utf-8'))
    report['solids_A']=summary.get('solids_A');report['solids_B']=summary.get('solids_B')
    report['statuses']=summary.get('statuses');report['analysis_complete']=summary.get('analysis_complete')
    report['material_analysis_complete']=summary.get('material_analysis_complete')
    if (out/'CZASY_ANALIZY.json').exists():
        report['timings']=json.loads((out/'CZASY_ANALIZY.json').read_text(encoding='utf-8'))
    save()
    if not summary.get('main_step_ready') or summary.get('main_step_error'):raise AssertionError('Main STEP missing')
    if summary.get('preview_3d',{}).get('pominiete',1)!=0:raise AssertionError('3D HTML missing solids')
    if report['statuses'].get('UNCERTAIN',0):raise AssertionError('Unverified Simple Swerve pairs: '+str(report['statuses']))
    report['status']='PASS';save();print(json.dumps(report,ensure_ascii=False))
except BaseException:
    report['status']='FAIL';report['error']=traceback.format_exc();save();raise
