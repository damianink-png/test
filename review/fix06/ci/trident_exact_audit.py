"""Strict provenance + completeness audit for the two USER-UPLOADED Trident STEP files.

No model substitution: refuse inputs with different bytes even if names match.
This tool never treats a partial comparison as a successful geometry comparison.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

SOURCES = {
    "Trident_Assembly1.step": {
        "sha256": "e26006c887004d1dcacac36e08ca083268336d80668ea2d868a16e2b20aee370",
        "bytes": 192710725,
        "nauo": 1516,
        "manifold_solid_brep_definitions": 493,
    },
    "trident_assembly.step": {
        "sha256": "416eda4e9212b894ed6f78ad3a6af55757115ebfcc4c18db933743d97dd48ccf",
        "bytes": 185183500,
        "nauo": 1619,
        "manifold_solid_brep_definitions": 575,
    },
}

def digest(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda:f.read(4*1024*1024),b""):
            h.update(block)
    return h.hexdigest()

def preflight(a: Path, b: Path) -> dict:
    out={}
    for name,path in (( "Trident_Assembly1.step",a),("trident_assembly.step",b)):
        expected=SOURCES[name]
        if not path.is_file():
            raise FileNotFoundError("Missing exact user STEP: "+str(path))
        size=path.stat().st_size
        if size!=expected["bytes"]:
            raise ValueError(f"Unexpected size for {name}: {size} != {expected['bytes']}")
        sha=digest(path)
        if sha!=expected["sha256"]:
            raise ValueError(f"Unexpected SHA256 for {name}: {sha}")
        out[name]={"bytes":size,"sha256":sha,"verified":True}
    return out

def strict_summary(path: Path) -> dict:
    data=json.loads(path.read_text(encoding="utf-8-sig"))
    counts=data.get("statuses") or {}
    uncertain=sum(1 for r in data.get("records",[]) if r.get("status")=="UNCERTAIN")
    overlap=data.get("revision_overlap") or {}
    source_a=Path(data.get("source_A") or "").name
    source_b=Path(data.get("source_B") or "").name
    # Some versions do not persist full paths. Those must be verified by
    # the independent preflight and source fingerprints in the calling CI.
    if source_a and source_a!="Trident_Assembly1.step":
        raise ValueError("Summary source_A differs from user input: "+source_a)
    if source_b and source_b!="trident_assembly.step":
        raise ValueError("Summary source_B differs from user input: "+source_b)
    failed=int(overlap.get("failed_pairs_total") or len(overlap.get("failed_pairs") or []))
    ok=(data.get("analysis_complete") is True
        and data.get("material_analysis_complete") is True
        and overlap.get("incomplete") is not True
        and int(counts.get("UNCERTAIN",0))==0
        and uncertain==0
        and failed==0)
    return {"strict_pass":ok,"solids_A":data.get("solids_A"),"solids_B":data.get("solids_B"),
            "statuses":counts,"uncertain_records":uncertain,"failed_pairs_total":failed,
            "failed_pairs":(overlap.get("failed_pairs") or [])[:30],
            "analysis_complete":data.get("analysis_complete"),
            "material_analysis_complete":data.get("material_analysis_complete"),
            "source_A":data.get("source_A"),"source_B":data.get("source_B")}

def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--a",required=True,type=Path)
    ap.add_argument("--b",required=True,type=Path)
    ap.add_argument("--summary",type=Path)
    ap.add_argument("--report",type=Path)
    args=ap.parse_args()
    result={"inputs":preflight(args.a,args.b)}
    if args.summary:
        if not args.summary.is_file():
            raise FileNotFoundError("Comparison did not produce summary: "+str(args.summary))
        result["comparison"]=strict_summary(args.summary)
    if args.report:
        args.report.parent.mkdir(parents=True,exist_ok=True)
        args.report.write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding="utf-8")
    print(json.dumps(result,indent=2,ensure_ascii=False))
    return 0 if not args.summary or result["comparison"]["strict_pass"] else 1

if __name__=="__main__":
    raise SystemExit(main())
