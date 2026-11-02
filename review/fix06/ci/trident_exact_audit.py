"""Strict provenance + completeness audit for the two USER-UPLOADED Trident STEP files.

No model substitution: refuse inputs with different bytes even if names match.
This tool never treats a partial comparison as a successful geometry comparison.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from collections import Counter
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
    """Conservative, independently checkable full-result verdict.

    No PASS for a partial or inconsistent result, even when the GUI/HTML
    describes the material analysis as complete.
    """
    data=json.loads(path.read_text(encoding="utf-8-sig"))
    counts=data.get("statuses") or {}
    records=data.get("records")
    overlap=data.get("revision_overlap") or {}
    errors=[]
    source_a=Path(data.get("source_A") or "").name
    source_b=Path(data.get("source_B") or "").name
    if source_a!="Trident_Assembly1.step" or source_b!="trident_assembly.step":
        errors.append("source_names_not_exact")
    fingerprints=data.get("source_fingerprints") or {}
    if fingerprints.get("A")!=SOURCES["Trident_Assembly1.step"]["sha256"] or fingerprints.get("B")!=SOURCES["trident_assembly.step"]["sha256"]:
        errors.append("source_fingerprints_missing_or_mismatched")
    statuses={"SAME","RENAMED","CHANGED","MOVED","ADDED","REMOVED","UNCERTAIN"}
    if not isinstance(records,list):
        errors.append("missing_record_list")
        records=[]
    actual=Counter(str(r.get("status")) for r in records if isinstance(r,dict))
    if any(not isinstance(r,dict) for r in records):
        errors.append("non_object_record")
    if set(actual)-statuses or set(counts)-statuses:
        errors.append("unknown_status")
    try:
        declared={k:int(v) for k,v in counts.items()}
    except (TypeError,ValueError):
        declared={}
        errors.append("invalid_status_counts")
    if declared!={k:v for k,v in actual.items() if v}:
        errors.append("status_counts_do_not_match_records")
    seen={"A":[],"B":[]}
    for row in records:
        if not isinstance(row,dict):
            continue
        status=row.get("status")
        a,b=row.get("a_index"),row.get("b_index")
        if a is None and b is None:
            errors.append("record_with_no_operands")
        if status=="ADDED" and (a is not None or b is None):
            errors.append("invalid_added_record")
        if status=="REMOVED" and (a is None or b is not None):
            errors.append("invalid_removed_record")
        if status in ("SAME","RENAMED","CHANGED","MOVED") and (a is None or b is None):
            errors.append("incomplete_matched_record")
        for role,idx in (("A",a),("B",b)):
            if idx is not None:
                if type(idx) is not int or idx<0:
                    errors.append("invalid_"+role+"_index")
                else:
                    seen[role].append(idx)
        if row.get("verification")=="unverified":
            errors.append("unverified_record")
    for role in ("A","B"):
        n=data.get("solids_"+role)
        if type(n) is not int or n<1:
            errors.append("invalid_solids_"+role)
        elif len(seen[role])!=n or len(set(seen[role]))!=n or min(seen[role],default=0)<0 or max(seen[role],default=-1)>=n:
            errors.append("incomplete_or_duplicate_"+role+"_coverage")
    failed=int(overlap.get("failed_pairs_total") or len(overlap.get("failed_pairs") or []))
    if failed: errors.append("failed_material_pairs")
    if overlap.get("incomplete") is True: errors.append("partial_material_overlap")
    if data.get("analysis_complete") is not True or data.get("material_analysis_complete") is not True:
        errors.append("analysis_marked_incomplete")
    if declared.get("UNCERTAIN",0) or actual.get("UNCERTAIN",0):
        errors.append("uncertain_records")
    if data.get("material_errors"):
        errors.append("material_errors")
    if data.get("step_export_error") or data.get("main_step_error"):
        errors.append("step_export_error")
    errors=sorted(set(errors))
    return {
        "strict_pass":not errors,
        "audit_errors":errors,
        "solids_A":data.get("solids_A"),"solids_B":data.get("solids_B"),
        "statuses":counts,"record_count":len(records),
        "covered_A":len(seen["A"]),"covered_B":len(seen["B"]),
        "uncertain_records":actual.get("UNCERTAIN",0),
        "failed_pairs_total":failed,
        "failed_pairs":(overlap.get("failed_pairs") or [])[:30],
        "analysis_complete":data.get("analysis_complete"),
        "material_analysis_complete":data.get("material_analysis_complete"),
        "source_A":data.get("source_A"),"source_B":data.get("source_B"),
        "source_fingerprints":fingerprints,
    }

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
