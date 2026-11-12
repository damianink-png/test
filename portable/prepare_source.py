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
for source in (here/'frontend').iterdir():
 if source.suffix in ('.svelte','.css','.ts'):target=out/'desktop/src'/source.name
 elif source.suffix=='.rs':target=out/'desktop/src-tauri/src'/source.name
 else:continue
 target.write_bytes(source.read_bytes())
p=out/'desktop/src-tauri/src/lib.rs';s=p.read_text(encoding='utf8')+'\npub mod startup;\npub mod reports;\n';s=s.replace('"BOM_A.csv","BOM_B.csv"','"BOM_A.csv","BOM_B.csv","BOM_A.html","BOM_B.html"');p.write_text(s,encoding='utf8')
p=out/'desktop/src-tauri/src/lib.rs'
s=p.read_text(encoding='utf8')
old='fs::read_to_string(job.folder.join("_POSTEP_V37.jsonl")).unwrap_or_default()'
assert s.count(old)==1,'Progress reader baseline changed'
s=s.replace(old,'progress_tail::read(&job.folder.join("_POSTEP_V37.jsonl"),100).unwrap_or_default()')
p.write_text(s+'\npub mod progress_tail;\n',encoding='utf8')
for name in ('desktop/package.json','desktop/package-lock.json','desktop/src-tauri/tauri.conf.json'):
 p=out/name;d=json.loads(p.read_text(encoding='utf8'));d['version']='0.6.16'
 if name.endswith('package-lock.json'):d['packages']['']['version']='0.6.16'
 if name.endswith('tauri.conf.json'):
  w=d['app']['windows'][0];w.update(title='DS Compare',width=1280,height=820,minWidth=480,minHeight=360,dragDropEnabled=True)
 p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
p=out/'desktop/src-tauri/Cargo.toml';p.write_text(p.read_text(encoding='utf8').replace('version = "0.5.1"','version = "0.6.16"',1),encoding='utf8')
p=out/'desktop/src-tauri/Cargo.lock';s,n=re.subn(r'(\[\[package\]\]\nname = "dscompare-desktop"\nversion = )"0\.5\.1"',r'\g<1>"0.6.16"',p.read_text(encoding='utf8'));assert n==1;p.write_text(s,encoding="utf8")
(out/'desktop/tests/usability.test.ts').write_bytes((here/'tests/model.test.ts').read_bytes())
checked=0
for name,digest in manifest['sha256'].items():
 if name.startswith('dsac29/') or name in ('DSCompareV3.py','requirements.txt','BUDUJ_WINDOWS.ps1'):
  assert hashlib.sha256((out/name).read_bytes()).hexdigest()==digest,'Changed tested CAD engine: '+name;checked+=1
print('TESTED_ENGINE_SOURCE_MATCH_PASS',checked,'files, pinned run 41291652234')
# The portable build must ship the same bounded, fail-closed Windows native
# completion-mailbox fix as the integrated RC9 Windows build.  Apply it only
# AFTER validating the immutable baseline manifest above: a patched source
# cannot and should not masquerade as a byte-identical original snapshot.
import subprocess
native_session = out/'dsac29/native_session.py'
patch_script = here.parent/'review/fix06/ci/patch_native_completion_read.py'
assert native_session.is_file() and patch_script.is_file(), 'Native completion patch inputs missing'
subprocess.run([sys.executable, str(patch_script), str(native_session)], check=True)
compile(native_session.read_text(encoding='utf8'), str(native_session), 'exec')
print('PORTABLE_NATIVE_COMPLETION_READ_PATCH_PASS', flush=True)

# Extend the existing diagnostic worker to accept a pair of STEP files.
p=out/'desktop/src-tauri/src/lib.rs';s=p.read_text(encoding='utf8')
anchor=' if r.mode=="mass"&&r.files.is_empty()'
assert s.count(anchor)==1
s=s.replace(anchor,' if r.mode=="diagnostic"&&!r.files.is_empty()&&r.files.len()!=2{return Err("Wybierz dwa pliki STEP".into())}\n'+anchor)
anchor=' }else if r.mode=="mass"{let list=out.join("inputs.json");'
assert s.count(anchor)==1
s=s.replace(anchor,' }else if r.mode=="diagnostic"&&r.files.len()==2{a.extend(["--a".into(),r.files[0].clone(),"--b".into(),r.files[1].clone()]);'+anchor)
s=s.replace('"RAPORT_TESTOW.html"]','"RAPORT_TESTOW.html","DIAGNOSTYKA_MODELI.txt"]')
p.write_text(s,encoding='utf8')
