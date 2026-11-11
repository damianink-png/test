"""DS Compare STEP scale regression: 4201 exact XCAF instances and STEP round-trips.

Uses actual OCCT B-Rep solids and the assembled production dsac29 package.
The >3500 case is a synthetic stress fixture, NOT a public assembly STEP.
No changes to classification, UI, source CAD, or import tolerances.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from time import perf_counter
from traceback import format_exc
from types import SimpleNamespace

from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCP.gp import gp_Trsf, gp_Vec
from OCP.TopLoc import TopLoc_Location

from dsac29.occurrence_identity import prepare_occurrence_identities
from dsac29.step_io import ColoredDocument, inspect_step_colors, load_step

ROOT = Path("evidence/step_scale_export").resolve()
ROOT.mkdir(parents=True, exist_ok=True)
RESULT = ROOT / "RESULT.json"
DATA = {
    "scope": "DS Compare synthetic OCC STEP scale stress, not authentic 4200-part revision",
    "github_sha": os.environ.get("GITHUB_SHA", "local"),
    "cases": [],
    "verdict": "RUNNING",
}


def save():
    RESULT.write_text(json.dumps(DATA, ensure_ascii=False, indent=2), encoding="utf-8")


def run(name, fn):
    entry = {"case": name, "status": "RUNNING"}
    DATA["cases"].append(entry)
    save()
    start = perf_counter()
    try:
        entry.update(fn())
        entry["status"] = "PASS"
        print("STRESS_CASE_PASS", name, json.dumps(entry, ensure_ascii=False), flush=True)
    except BaseException:
        entry["status"] = "FAIL"
        entry["traceback"] = format_exc()
        print("STRESS_CASE_FAIL", name, entry["traceback"], flush=True)
        raise
    finally:
        entry["seconds"] = round(perf_counter() - start, 3)
        save()


def repeated_4201():
    # Real OCC solids, with two different STEP source identities and one
    # changed definition. These keys model source-scoped XCAF references.
    base = BRepPrimAPI_MakeBox(10., 20., 4.).Shape()
    changed = BRepPrimAPI_MakeBox(10., 20., 4.5).Shape()
    old = [SimpleNamespace(shape=base, volume=800., area=640.,
                           step_definition_key=("old.step", "0:1:1:10", 1))
           for _ in range(2100)]
    new = [SimpleNamespace(shape=base, volume=800., area=640.,
                           step_definition_key=("new.step", "0:1:1:10", 1))
           for _ in range(2100)]
    changed_part = SimpleNamespace(
        shape=changed, volume=900., area=670.,
        step_definition_key=("new.step", "0:1:1:11", 1))
    new.append(changed_part)
    stats = prepare_occurrence_identities(old, new, limit=3500)
    assert stats["selected"] == 4201, stats
    assert stats["proven"] == 4201 and stats["skipped"] == 0, stats
    assert stats["xcaf_reuse"] == 4198, stats
    assert old[0]._dscompare_normalized_digest == new[0]._dscompare_normalized_digest
    assert changed_part._dscompare_normalized_digest != old[0]._dscompare_normalized_digest
    return {"occurrences": 4201, "unique_source_definitions": 3,
            "changed_definition_distinct": True, "statistics": stats}


def independent_3551():
    # When all occurrences have different source-scoped definitions the
    # expensive normalization still fails closed at the 3500 definition cap.
    parts = [SimpleNamespace(volume=800., area=640.,
                             step_definition_key=("distinct.step", str(i), 1))
             for i in range(3551)]
    stats = prepare_occurrence_identities(parts, [], limit=3500)
    assert stats["selected"] == 3551, stats
    assert stats["proven"] == 0 and stats["skipped"] == 3551, stats
    return {"occurrences": 3551, "independent_definitions": 3551,
            "no_unsupported_positive_proof": True, "statistics": stats}


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1048576), b""):
            digest.update(chunk)
    return digest.hexdigest()


def export_file(path, count, reuse, pcurves):
    os.environ["DSCOMPARE_STEP_VERIFY"] = "fast"
    os.environ["DSCOMPARE_STEP_PCURVES"] = pcurves
    model = BRepPrimAPI_MakeBox(10., 20., 4.).Shape()
    doc = ColoredDocument(group_by_status=True, reuse_definitions=reuse)
    for i in range(count):
        pose = gp_Trsf()
        pose.SetTranslation(gp_Vec(i * 25., (i % 7) * 30., 0.))
        occurrence = model.Moved(TopLoc_Location(pose))
        doc.add(occurrence, f"PLATE_{i:04d}", (0.2, 0.6, 0.8),
                group="SAME", source_name="PLATE")
    report = doc.write(str(path))
    assert path.is_file() and path.stat().st_size > 1024
    assert report["rzeczywiste_bryly_step"] == count, report
    assert report["ponownie_uzyte_definicje"] == (count - 1 if reuse else 0), report
    assert report["definicje_unikalne"] == (1 if reuse else count), report
    return {
        "name": path.name, "bytes": path.stat().st_size,
        "sha256": sha256_file(path), "diagnostics": report,
    }


def step_export_roundtrip():
    # 180 occurrences: intentionally >150, hence the real default export
    # uses structural validation; verify the resulting file by OCC reimport.
    count = 180
    normal_path = ROOT / "reuse_180.step"
    baseline_path = ROOT / "no_reuse_180.step"
    compact_path = ROOT / "compact_pcurves_off_180.step"
    try:
        optimized = export_file(normal_path, count, reuse=True, pcurves="on")
        baseline = export_file(baseline_path, count, reuse=False, pcurves="on")
        compact = export_file(compact_path, count, reuse=True, pcurves="off")
        assert optimized["bytes"] < baseline["bytes"], (optimized, baseline)
        assert compact["bytes"] < optimized["bytes"], (compact, optimized)
        # The experiment must preserve the number of solids and mass, not
        # merely write fewer bytes. Import both on and off pcurve variants.
        normal_parts = load_step(str(normal_path))
        compact_parts = load_step(str(compact_path))
        assert len(normal_parts) == len(compact_parts) == count
        normal_volumes = sorted(round(float(p.volume), 5) for p in normal_parts)
        compact_volumes = sorted(round(float(p.volume), 5) for p in compact_parts)
        assert normal_volumes == compact_volumes == [800.] * count
        visual = inspect_step_colors(str(normal_path))
        assert visual["bryly_wynikowe"] == count, visual
        assert visual["bryly_bez_koloru"] == 0, visual
        return {
            "count": count, "with_reuse": optimized,
            "without_reuse": baseline, "experimental_no_pcurves": compact,
            "reuse_size_reduction_pct": round(
                100 * (1 - optimized["bytes"] / baseline["bytes"]), 2),
            "compact_size_reduction_pct": round(
                100 * (1 - compact["bytes"] / optimized["bytes"]), 2),
            "occt_reimport_count": count,
            "occt_roundtrip_geometry_and_colors": "PASS",
            "zw3d_2019_import": "NOT_TESTED",
        }
    finally:
        # Other tests must never inherit the experimental writer mode.
        os.environ["DSCOMPARE_STEP_PCURVES"] = "on"


def main():
    try:
        run("4201_references_three_exact_definitions", repeated_4201)
        run("3551_independent_definitions_budget_guard", independent_3551)
        run("180_occt_step_export_size_and_roundtrip", step_export_roundtrip)
    except BaseException:
        DATA["verdict"] = "FAIL"
        save()
        raise
    DATA["verdict"] = "PASS"
    save()
    print("STEP_SCALE_EXPORT_RESULT", json.dumps(DATA, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
