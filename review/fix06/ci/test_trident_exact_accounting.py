"""Strict checks on exact-pair DS Compare reports; does not replace geometry validation."""
import collections
import json
import sys
from pathlib import Path

EXPECTED = {
    "A": "e26006c887004d1dcacac36e08ca083268336d80668ea2d868a16e2b20aee370",
    "B": "416eda4e9212b894ed6f78ad3a6af55757115ebfcc4c18db933743d97dd48ccf",
}

def check(report):
    assert report["source_fingerprints"] == EXPECTED, "Unexpected source models"
    records = report["records"]
    a = [r["a_index"] for r in records if r.get("a_index") is not None]
    b = [r["b_index"] for r in records if r.get("b_index") is not None]
    assert collections.Counter(a) == collections.Counter(range(report["solids_A"])), "Missing/duplicate A occurrence"
    assert collections.Counter(b) == collections.Counter(range(report["solids_B"])), "Missing/duplicate B occurrence"
    assert dict(collections.Counter(r["status"] for r in records)) == report["statuses"], "Status count mismatch"
    uncertain = [r for r in records if r["status"] == "UNCERTAIN"]
    assert all(r.get("verification") != "confirmed" for r in uncertain), "UNCERTAIN marked confirmed"
    if uncertain or not report.get("analysis_complete") or not report.get("material_analysis_complete"):
        return "INCOMPLETE"
    assert all(r.get("verification") == "confirmed" for r in records), "Unverified result in complete report"
    return "CANDIDATE_FOR_STRICT_AUDIT"

def main():
    report = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    print(check(report))

if __name__ == "__main__":
    main()
