"""Run unchanged regression selection in isolated batches with durable logs.
A separate process per file prevents test-global diagnostic/session state leakage.
The 240s watchdog applies to each batch; native Boolean deadlines stay 35s.
"""
import ast,subprocess,sys,time,json
from pathlib import Path
root=Path(sys.argv[1]).resolve();out=root/'regression_evidence';out.mkdir(exist_ok=True)
module=ast.parse((root/'TESTUJ.py').read_text(encoding='utf8'))
tests=next(ast.literal_eval(n.value) for n in module.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='tests' for t in n.targets))
results=[]
for name in tests:
    start=time.monotonic();log=out/(name+'.log')
    with log.open('w',encoding='utf8') as handle:
        try:
            r=subprocess.run([sys.executable,'-m','pytest','-vv','-x','--tb=short',str(root/'tests'/name),'--junitxml='+str(out/(name+'.xml'))],cwd=root,stdout=handle,stderr=subprocess.STDOUT,timeout=240)
            code=r.returncode
        except subprocess.TimeoutExpired:code=124
    entry={'test':name,'code':code,'seconds':round(time.monotonic()-start,2)};results.append(entry)
    (out/'summary.json').write_text(json.dumps(results,indent=2),encoding='utf8')
    print(json.dumps(entry),flush=True)
    if code:
        print(log.read_text(encoding='utf8'),flush=True);raise SystemExit(code)
