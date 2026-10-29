"""Generate a failure-focused diagnostic summary from persisted CI evidence.

Run even when the frozen EXE exits 1. Never infer a Python exception from
a missing traceback; record the last known checkpoint and missing evidence.
"""
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("evidence")
model = sys.argv[2] if len(sys.argv) > 2 else "unknown"
scenario = sys.argv[3] if len(sys.argv) > 3 else "unknown"
root.mkdir(parents=True, exist_ok=True)
candidates = [
    Path("dscompare_rc9_manual/ci/EXE_STDOUT.log"),
    Path("dscompare_rc9_manual/ci/EXE_STDERR.log"),
]
candidates += sorted(root.rglob("*.log"))
candidates += sorted(root.rglob("*.json"))
findings = []
for p in candidates:
    try:
        if not p.is_file() or p.stat().st_size > 25_000_000:
            continue
        data = p.read_text(encoding="utf-8", errors="replace")
        lines = data.splitlines()
        matching = [(i + 1, line.strip()[:800]) for i, line in enumerate(lines)
                    if re.search(r"traceback|exception|fatal|timeout|failed|error|b-rep|brep|common|last.step|checkpoint|exit.?code|pair|shape|native", line, re.I)]
        if matching:
            findings.append({"file": str(p), "last_matching_lines": matching[-35:],
                             "last_log_lines": lines[-12:]})
    except (OSError, UnicodeError):
        continue
result = {
    "model": model, "scenario": scenario,
    "generated_utc": datetime.now(timezone.utc).isoformat(),
    "status": "diagnostic_only_not_a_cad_verdict",
    "note": "Exit 1 alone does not identify the failed operation. Review last persisted checkpoint, traceback and WER dumps.",
    "crash_dump_files": [str(p) for p in root.rglob("*.dmp")],
    "evidence": findings,
}
out = root / "failure-summary.json"
out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"DIAGNOSTIC_SUMMARY={out}; evidence_sources={len(findings)}; crash_dumps={len(result['crash_dump_files'])}")
for item in findings[-8:]:
    print("SOURCE", item["file"])
    for line_no, value in item["last_matching_lines"][-5:]:
        print(f"  L{line_no}: {value[:350]}")
