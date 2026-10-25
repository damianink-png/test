"""Large real CAD test: authentic revision in original coordinates; no global shift."""
import gc
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback
import urllib.request
import zipfile

MODEL_FILES = {
    "v2": ("Voron-2", "e64c83bcb84d41c0324e104a1c911879174d08aa", "e47cc70edbdb0c36916885b54a5e1f30f52a717a", "CAD/Voron_2.4r2_Assembly_STEP.zip"),
    "trident": ("Voron-Trident", "1a49bdc2c524cd6f4491a01e8fd566d0bd6acd0a", "9d9223311f2b0fce72484023d6a755e13a733319", "CAD/trident_assembly.step.zip"),
}
exe = Path(sys.argv[1]).resolve()
model = sys.argv[2]
assert model in MODEL_FILES
root = Path("evidence").resolve()
root.mkdir(parents=True,exist_ok=True)
out = root/"comparison"
out.mkdir(exist_ok=True)
report = {"model":model,"scenario":"authentic_revision_without_global_shift","exe_sha256":hashlib.sha256(exe.read_bytes()).hexdigest(),"source":[]}
def save():
    (root/"TEST_RESULT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
def download(repo,revision,label,file_path):
    folder=Path("models")/label
    folder.mkdir(parents=True,exist_ok=True)
    source_url=f"https://raw.githubusercontent.com/VoronDesign/{repo}/{revision}/{file_path}"
    archive=folder/"source.zip"
    urllib.request.urlretrieve(source_url,archive)
    with zipfile.ZipFile(archive) as z:
        z.extractall(folder)
    candidates=[x for x in folder.rglob("*") if x.suffix.lower() in (".stp",".step")]
    if not candidates:
        raise RuntimeError("Brak STEP: "+label)
    f=max(candidates,key=lambda x:x.stat().st_size).resolve()
    report["source"].append({"label":label,"revision":revision,"url":source_url,"file":str(f),"sha256":hashlib.sha256(f.read_bytes()).hexdigest()})
    save()
    return f
try:
    repo,latest,older,path=MODEL_FILES[model]
    old=download(repo,older,"old",path)
    new=download(repo,latest,"new",path)
    from dsac29.step_io import load_step
    for label,p in (("A",old),("B",new)):
        count=len(load_step(str(p),max_solids=20000))
        report["solids_"+label]=count
        save()
        if count<=600:raise AssertionError(f"{label} has <=600 solids")
    gc.collect()
    args=[str(exe),"--worker","compare","--a",str(old),"--b",str(new),"--output",str(out),"--align-auto","--generate-step","--preview3d","--revision-style","--no-bom"]
    report["command"]=args
    save()
    start=time.monotonic()
    proc=subprocess.Popen(args)
    decisions=[]
    while proc.poll() is None:
        question=out/"_WYROWNANIE_PYTANIE.json"
        if question.exists():
            try:
                proposal=json.loads(question.read_text(encoding="utf-8"))
                token=proposal["token"]
                if token not in decisions:
                    decisions.append(token)
                    # Real revisions are evaluated in original coordinates, no alignment accepted.
                    (out/"_WYROWNANIE_ODPOWIEDZ.json").write_text(json.dumps({"token":token,"decision":"original"}),encoding="utf-8")
            except (OSError,ValueError,KeyError):
                pass
        if time.monotonic()-start>2400:
            subprocess.run(["taskkill","/F","/T","/PID",str(proc.pid)],capture_output=True)
            raise TimeoutError("EXE comparison exceeded 2400 seconds")
        time.sleep(.5)
    report["seconds"]=round(time.monotonic()-start,2)
    report["returncode"]=proc.returncode
    report["alignment_prompts"]=len(decisions)
    save()
    if proc.returncode!=0:raise RuntimeError("Frozen EXE failed with "+str(proc.returncode))
    worker=json.loads((out/"_WYNIK_V37.json").read_text(encoding="utf-8"))
    if not worker.get("ok"):raise RuntimeError("Worker failed: "+str(worker))
    summary=json.loads((out/"PODSUMOWANIE.json").read_text(encoding="utf-8"))
    report["summary"]=summary
    timing=out/"CZASY_ANALIZY.json"
    if timing.exists():report["timings"]=json.loads(timing.read_text(encoding="utf-8"))
    save()
    counts=summary.get("statuses",{})
    changes=sum(counts.get(k,0) for k in ("ADDED","REMOVED","CHANGED","MOVED"))
    if changes<=0:raise AssertionError("No revision changes were detected: "+repr(counts))
    if summary.get("alignment",{}).get("applied"):raise AssertionError("Incorrect global alignment in original frame")
    if not summary.get("main_step_ready") or summary.get("main_step_error"):raise AssertionError("Export STEP missing")
    if summary.get("preview_3d",{}).get("pominiete")!=0:raise AssertionError("3D HTML omitted solids")
    html=out/"PODGLAD_KOLOROW_3D.html"
    if not html.is_file() or html.stat().st_size<1000:raise AssertionError("HTML 3D missing")
    report["result"]="PASS"
    save()
    print(json.dumps(report,ensure_ascii=False),flush=True)
except BaseException:
    report["result"]="FAIL"
    report["error"]=traceback.format_exc()
    save()
    raise
