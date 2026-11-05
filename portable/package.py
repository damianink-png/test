"""Create the exact app manifest/payload and append it to the native PE stub."""
import argparse,hashlib,json,shutil,struct,zipfile
from pathlib import Path
p=argparse.ArgumentParser();sub=p.add_subparsers(dest='command',required=True)
a=sub.add_parser('payload');a.add_argument('app',type=Path);a.add_argument('output',type=Path)
a=sub.add_parser('onefile');a.add_argument('stub',type=Path);a.add_argument('payload',type=Path);a.add_argument('output',type=Path)
args=p.parse_args()
def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for block in iter(lambda:f.read(4*1024*1024),b''):h.update(block)
 return h.hexdigest()
if args.command=='payload':
 args.output.mkdir(parents=True,exist_ok=True);files=[]
 for path in sorted(args.app.rglob('*')):
  if path.is_file():files.append({'path':path.relative_to(args.app).as_posix(),'size':path.stat().st_size,'sha256':sha(path)})
 assert any(f['path']=='DSCompareDesktop.exe' for f in files)
 assert any(f['path']=='WebView2/msedgewebview2.exe' for f in files)
 assert any(f['path']=='engine/DSCompare/DSCompare.exe' for f in files)
 (args.output/'manifest.json').write_text(json.dumps({'version':'0.6.5','files':files},ensure_ascii=False,separators=(',',':')),encoding='utf8')
 with zipfile.ZipFile(args.output/'payload.zip','w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  for entry in files:z.write(args.app/entry['path'],entry['path'])
 print('PORTABLE_PAYLOAD_PASS',len(files),'files',sum(f['size'] for f in files),'uncompressed bytes',flush=True)
else:
 args.output.parent.mkdir(parents=True,exist_ok=True)
 with args.output.open('wb') as out,args.stub.open('rb') as stub,args.payload.open('rb') as payload:
  shutil.copyfileobj(stub,out,4*1024*1024);offset=out.tell();shutil.copyfileobj(payload,out,4*1024*1024);length=out.tell()-offset
  out.write(b'DSCPORTABLE01ZIP'+struct.pack('<QQ',offset,length))
 with args.output.open('rb') as f:
  f.seek(-32,2);marker=f.read(16);start,size=struct.unpack('<QQ',f.read(16));assert marker==b'DSCPORTABLE01ZIP' and start+size+32==args.output.stat().st_size
 print('ONEFILE_OVERLAY_PASS',args.output.stat().st_size,'bytes','sha256',sha(args.output),flush=True)
