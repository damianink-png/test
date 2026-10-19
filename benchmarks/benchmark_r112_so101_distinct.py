"""Benchmark real SO-101 STEP CAD, separate files with equal CAD geometry but unequal hashes."""
from pathlib import Path
from time import perf_counter
from urllib.request import urlopen
from tempfile import TemporaryDirectory
from collections import Counter
import csv,hashlib,json,sys,traceback
ROOT = Path(__file__).resolve().parents[1] / "v46"
sys.path.insert(0,str(ROOT.resolve()))
from dsac29.cli import process
URL = "https://raw.githubusercontent.com/TheRobotStudio/SO-ARM100/a758567c3978dfeefe282ede0500085a48fe8f78/STEP/SO101/SO101%20Assembly.step"
RESULT = Path("real_cad_results") / "r112_so101_distinct_step.json"
RESULT.parent.mkdir(parents=True,exist_ok=True)
data={"case":"SO101 distinct STEP SHA vs identical CAD geometry", "source":URL}
t0=perf_counter()
try:
    source=urlopen(URL,timeout=90).read()
    assert len(source)>10000000 and b"ISO-10303-21;" in source
    modified=source.replace(b"ISO-10303-21;",b"ISO-10303-21;\n/* R112 separate source file, same CAD geometry */",1)
    assert hashlib.sha256(source).digest()!=hashlib.sha256(modified).digest()
    with TemporaryDirectory() as td:
        root=Path(td)
        left=root/"SO101_A.step";right=root/"SO101_B.step"
        left.write_bytes(source);right.write_bytes(modified)
        logs=[]
        step_ready=[]
        def progress(message):
            logs.append(message)
            if "STEP GOTOWY" in message:step_ready.append(perf_counter()-t0)
            if len(logs)%30==1 or "BOM" in message or "STEP GOTOWY" in message: print("PROGRESS",round(perf_counter()-t0,2),message,flush=True)
        output,records,err=process(str(left),str(right),str(root/"output"),progress=progress,
                                   revision_style=True,diff_step=False,step=True,max_solids=1000)
        status=dict(Counter(r.status for r in records))
        data.update(elapsed_s=round(perf_counter()-t0,2),step_ready_s=round(step_ready[0],2) if step_ready else None,
                    statuses=status,reused_verified_groups=any("ponowne użycie zweryfikowanych grup A" in msg for msg in logs),
                    step_bytes=(output/"POROWNANIE_KOLORY.step").stat().st_size if (output/"POROWNANIE_KOLORY.step").exists() else 0,
                    report_files={n:(output/n).exists() for n in ("RAPORT.html","BOM_A.csv","BOM_B.csv","ZMIANY.csv")},error=err)
        with (output/"BOM_A.csv").open(encoding="utf-8-sig",newline="") as f: bom_a=list(csv.reader(f,delimiter=";"))
        with (output/"BOM_B.csv").open(encoding="utf-8-sig",newline="") as f: bom_b=list(csv.reader(f,delimiter=";"))
        data["equal_bom"]=bom_a==bom_b
        assert err is None
        assert len(records)==266 and set(status).issubset({"SAME","RENAMED"}),status
        assert data["reused_verified_groups"],logs[-20:]
        assert data["equal_bom"]
        assert data["step_bytes"]>100000
        assert all(data["report_files"].values())
        data["status"]="PASS"
except Exception as exc:
    data["status"]="FAIL";data["exception"]=repr(exc);data["traceback"]=traceback.format_exc()
finally:
    RESULT.write_text(json.dumps(data,indent=2,ensure_ascii=False),encoding="utf8")
    print("R112_SO101_DISTINCT_RESULT",json.dumps(data,ensure_ascii=False),flush=True)
if data["status"]!="PASS":raise SystemExit(1)
