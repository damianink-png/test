"""Build the portable UI around the byte-identical Windows-tested CAD engine."""
import hashlib,json,re,sys,zipfile
from pathlib import Path
BASE_SHA='3a21c5e7f917e5b64223e2e11a32991ebc677262a4683e9e92d34af234eaeb3f'
base=Path(sys.argv[1]);out=Path(sys.argv[2]);here=Path(__file__).resolve().parent
assert hashlib.sha256(base.read_bytes()).hexdigest()==BASE_SHA,'Unverified source baseline'
with zipfile.ZipFile(base) as archive:
 manifest=json.loads(archive.read('dscompare_rc9_manual/SOURCE_MANIFEST.json'))
 for name,digest in manifest['sha256'].items():
  data=archive.read('dscompare_rc9_manual/'+name);assert hashlib.sha256(data).hexdigest()==digest,name
  target=out/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
for source,target in [('App.svelte','desktop/src/App.svelte'),('main.rs','desktop/src-tauri/src/main.rs'),('startup.rs','desktop/src-tauri/src/startup.rs')]:
 (out/target).write_bytes((here/'frontend'/source).read_bytes())
p=out/'desktop/src-tauri/src/lib.rs';p.write_text(p.read_text()+'\npub mod startup;\n')
for name in ('desktop/package.json','desktop/package-lock.json','desktop/src-tauri/tauri.conf.json'):
 p=out/name;d=json.loads(p.read_text());d['version']='0.5.2'
 if name.endswith('package-lock.json'):d['packages']['']['version']='0.5.2'
 p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
p=out/'desktop/src-tauri/Cargo.toml';p.write_text(p.read_text().replace('version = "0.5.1"','version = "0.5.2"',1))
p=out/'desktop/src-tauri/Cargo.lock';s,n=re.subn(r'(\[\[package\]\]\nname = "dscompare-desktop"\nversion = )"0\.5\.1"',r'\g<1>"0.5.2"',p.read_text());assert n==1;p.write_text(s)
checked=0
for name,digest in manifest['sha256'].items():
 if name.startswith('dsac29/') or name in ('DSCompareV3.py','requirements.txt','BUDUJ_WINDOWS.ps1'):
  assert hashlib.sha256((out/name).read_bytes()).hexdigest()==digest,'Changed tested CAD engine: '+name;checked+=1
print('TESTED_ENGINE_SOURCE_MATCH_PASS',checked,'files, pinned run 41291652234')
