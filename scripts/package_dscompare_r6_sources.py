"""Archive exact DS Compare 1.0 R6 sources from GH runner before build."""
import os,zipfile,hashlib
from pathlib import Path
root=Path(os.environ['DS_COMPARE_SOURCE'])
dest=Path(os.environ['GITHUB_WORKSPACE'])/'DSCompare_1_0_R6_ZRODLA_Z_GITHUB.zip'
excluded={'__pycache__','.pytest_cache','dist','build','.venv','venv','.git'}
files=[p for p in root.rglob('*') if p.is_file()
       and not any(x in excluded for x in p.relative_to(root).parts)
       and p.suffix.lower() not in ('.pyc','.pyo')
       and p.stat().st_size<60_000_000]
required=['DSCompareV3.py','BUDUJ_WINDOWS.ps1','TESTUJ.py',
          'dsac29/preview3d.py','dsac29/preview_template.html',
          'tests/test_r6_preview.py','dsac29/step_io.py']
for name in required:
    if not (root/name).is_file():raise RuntimeError('Missing R6 source: '+name)
assert (root/'VERSION.txt').read_text('utf8').startswith('DS Compare 1.0 R6')
with zipfile.ZipFile(dest,'w',zipfile.ZIP_DEFLATED,compresslevel=7) as archive:
    for p in sorted(files):
        archive.write(p,'DSCompare_1_0_R6_ZRODLA/'+p.relative_to(root).as_posix())
with zipfile.ZipFile(dest) as archive:
    assert archive.testzip() is None
    assert len(archive.namelist())>=130
print('R6 source archive verified:',dest.name,len(files),dest.stat().st_size,hashlib.sha256(dest.read_bytes()).hexdigest())
