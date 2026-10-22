"""R11.29 update old ABSR tests for the current flat switch and valid layer names."""
from pathlib import Path
import os,json
root=Path(os.environ['DS_COMPARE_SOURCE'])
p=root/'tests/test_r1111_no_absr.py'
s=p.read_text('utf8')
a="monkeypatch.setenv('DSCOMPARE_SAFE_EXPORT','1')"
b="monkeypatch.setenv('DSCOMPARE_SAFE_EXPORT','0')"
assert s.count(a)==2,(a,s.count(a))
assert s.count(b)==1,(b,s.count(b))
s=s.replace(a,"monkeypatch.setenv('DSCOMPARE_FLAT_FALLBACK','1')")
s=s.replace(b,"monkeypatch.setenv('DSCOMPARE_FLAT_FALLBACK','0')")
old="    assert b'01_BEZ_ZMIAN' not in raw and b'02_ZMIENIONE' not in raw"
new="""    # Statuses are allowed as STEP LAYER names; flat mode has no
    # assembly PRODUCT nodes regardless of layer names.
    assert not re.search(rb"(?m)^#\\d+\\s*=\\s*PRODUCT\\('(?:01_|02_)",raw)"""
assert s.count(old)==1,s.count(old)
p.write_text(s.replace(old,new),encoding='utf8')
(root/'VERSION.txt').write_text('R11.29\n',encoding='utf8')
meta=root/'build_info.json'
if meta.is_file():
    data=json.loads(meta.read_text('utf8'))
    data['version']='R11.29 · GitHub '+os.environ.get('GITHUB_SHA','')[:8]
    data['geometry']='Occurrence color ABSR removed; B-Rep verified repeated-part alignment'
    meta.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8')
print('R11.29 old tests and VERSION updated')
