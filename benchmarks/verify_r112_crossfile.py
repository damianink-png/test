"""Integration check for R11.2: files differing in bytes but equal in CAD data and changed revisions."""
from pathlib import Path
from tempfile import TemporaryDirectory
import csv, json, sys, os
ROOT = Path(os.environ["DS_COMPARE_SOURCE"]) if os.environ.get("DS_COMPARE_SOURCE") else Path(__file__).resolve().parents[1] / "v46"
sys.path.insert(0, str(ROOT))
from dsac29.cli import process
from dsac29.step_io import load_step
from dsac29.report import geometry_groups, _bill

def read_rows(p):
    with p.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter=";"))

source = (ROOT / "samples" / "MODEL_A.step").read_bytes()
assert b"ISO-10303-21;" in source
altered = source.replace(b"ISO-10303-21;", b"ISO-10303-21;\n/* R112 independently imported but identical geometry */", 1)
assert altered != source

with TemporaryDirectory() as tmp:
    root = Path(tmp)
    (root / "left.step").write_bytes(source)
    (root / "right.step").write_bytes(altered)
    logs = []
    out, records, err = process(str(root/"left.step"), str(root/"right.step"), str(root/"identical"),
                                step=False, diff_step=False, progress=logs.append)
    assert err is None
    assert len(records) == 4 and all(r.status in ("SAME", "RENAMED") for r in records)
    assert any("ponowne użycie zweryfikowanych grup A" in s for s in logs), logs
    assert read_rows(out/"BOM_A.csv") == read_rows(out/"BOM_B.csv")
    items_b = load_step(str(root/"right.step"))
    independent = _bill(items_b, 7850, geometry_groups(items_b))
    expected_qty = sum(int(q["Ilość"]) for q in read_rows(out/"BOM_B.csv"))
    assert expected_qty == len(items_b) == sum(row[1] for row in independent)
    print("R112 CROSS_FILE_SAME_PASS:",len(records),"solids, verified BOM groups reused")
    logs = []
    changed, records, err = process(str(ROOT/"samples"/"MODEL_A.step"), str(ROOT/"samples"/"MODEL_B.step"),
                                    str(root/"changed"), step=False, diff_step=False, progress=logs.append)
    assert err is None
    assert any(r.status in ("CHANGED","ADDED","REMOVED","MOVED") for r in records)
    assert not any("ponowne użycie zweryfikowanych grup A" in s for s in logs)
    assert (changed/"BOM_A.csv").exists() and (changed/"BOM_B.csv").exists()
    print("R112 CHANGED_REVISIONS_FALLBACK_PASS:",{r.status for r in records})
print("R112 INTEGRATION PASS")