"""Reuse byte-identical STEP imports across revisions A and B; preserve RC9 exports."""
from pathlib import Path
import ast
import sys

def apply(root):
    bridge=Path(root)/'dsac29'/'oac_bridge.py'
    src=bridge.read_text(encoding='utf-8')
    before='''def report_parts(parts):
    """Describe each native definition once; keep occurrence names/placements."""
    from OCP.TopLoc import TopLoc_Location
    cache = {}
'''
    after='''def report_parts(parts, cache=None):
    """Describe each native definition once across both A/B; keep placements."""
    from OCP.TopLoc import TopLoc_Location
    if cache is None:
        cache = {}
'''
    assert src.count(before)==1,'Unexpected report_parts implementation'
    src=src.replace(before,after,1)
    before='''    imported=[]
    for label,path in [('A',a_path),('B',b_path)]:
        status('OpenAssembly: wczytywanie '+label+'…')
        before=time.perf_counter()
        with open(path,'rb') as stream: fingerprints[label]=hashlib.file_digest(stream,'sha256').hexdigest()
        parts=load_step(path,label)
        if not parts: raise ValueError('Brak brył w modelu '+label)
        if len(parts)>max_solids: raise ValueError('Przekroczono limit brył: '+label)
        imported.append(parts);timing['import_'+label+'_s']=time.perf_counter()-before
'''
    after='''    imported=[]
    # Import identical bytes once; clone metadata for independent A/B classification.
    by_digest={}
    by_path={}
    for label,path in [('A',a_path),('B',b_path)]:
        status('OpenAssembly: wczytywanie '+label+'…')
        before=time.perf_counter()
        identity=str(Path(path).resolve())
        digest=by_path.get(identity)
        if digest is None:
            with open(path,'rb') as stream:
                digest=hashlib.file_digest(stream,'sha256').hexdigest()
            by_path[identity]=digest
        fingerprints[label]=digest
        if digest in by_digest:
            parts=[replace(p,uid=f'{label}{i:06}',source=label,status='',
                           match='',match_quality='',virtual_transform=())
                   for i,p in enumerate(by_digest[digest])]
            status(f'OpenAssembly: {label} — identyczna geometria, użyto cache importu ({len(parts)} brył)')
            timing['reused_import_'+label]=True
        else:
            parts=load_step(path,label)
            by_digest[digest]=parts
            timing['reused_import_'+label]=False
        if not parts: raise ValueError('Brak brył w modelu '+label)
        if len(parts)>max_solids: raise ValueError('Przekroczono limit brył: '+label)
        imported.append(parts)
        timing['import_'+label+'_s']=time.perf_counter()-before
'''
    assert src.count(before)==1,'Unexpected import implementation'
    src=src.replace(before,after,1)
    before='    a,b=(report_parts(parts) for parts in imported)\n'
    after='    report_cache={}\n    a,b=(report_parts(parts,report_cache) for parts in imported)\n'
    assert src.count(before)==1,'Unexpected description path'
    src=src.replace(before,after,1)
    ast.parse(src,filename=str(bridge))
    bridge.write_text(src,encoding='utf-8')
    tests=Path(root)/'integration'/'test_bridge.py'
    code=tests.read_text(encoding='utf-8')
    assert 'test_identical_file_reuses_import_once' not in code
    code+='''

def test_identical_file_reuses_import_once(tmp_path, monkeypatch):
    """One STEP import; two separate matchable occurrence lists."""
    import dsac29.oac_bridge as bridge
    a=tmp_path/'same.step'
    assembly(a,qty=3)
    original=bridge.load_step
    calls=[]
    def counting(path, source):
        calls.append(source)
        return original(path, source)
    monkeypatch.setattr(bridge, 'load_step', counting)
    out, records, error=bridge.process(a,a,tmp_path/'output',auto_align=True,
            revision_style=True,preview3d=False,diff_step=False,bom_fast=True,progress=None)
    assert error is None, error
    assert calls == ['A']
    assert Counter(r.status for r in records)=={'SAME':3}
    diagnostics=json.loads((out/'CZASY_ANALIZY.json').read_text(encoding='utf-8'))
    assert diagnostics['reused_import_A'] is False
    assert diagnostics['reused_import_B'] is True
    assert len(load_step(str(out/'POROWNANIE_KOLORY.step')))==3

def test_byte_identical_separate_paths_share_import(tmp_path, monkeypatch):
    import shutil
    import dsac29.oac_bridge as bridge
    a,b=tmp_path/'revision_a.step',tmp_path/'revision_b.step'
    assembly(a,qty=3)
    shutil.copyfile(a,b)
    original=bridge.load_step
    calls=[]
    def counting(path, source):
        calls.append(source)
        return original(path,source)
    monkeypatch.setattr(bridge,'load_step',counting)
    out,records,error=bridge.process(a,b,tmp_path/'output',auto_align=True,
            revision_style=True,preview3d=False,diff_step=False,bom_fast=True,progress=None)
    assert error is None,error
    assert calls==['A']
    assert Counter(r.status for r in records)=={'SAME':3}
'''
    ast.parse(code,filename=str(tests))
    tests.write_text(code,encoding='utf-8')
    print('Applied import reuse + two regression tests')

if __name__=='__main__':
    apply(sys.argv[1])
