"""Bounded native B-Rep repros; diagnostic ONLY, never a comparison PASS.

Reproduce the exact failing indexed pairs from compiled RC7 session run
40245403179, with a 120 s isolated OCC operation to distinguish a too-short
35 s deadline from a persistent native crash/hang. Do not change CAD verdicts.
"""
import argparse
import gc
import hashlib
import json
import os
from pathlib import Path
import time
import traceback
import urllib.request
import zipfile

MODELS = {
    "v2": ("Voron-2", "e64c83bcb84d41c0324e104a1c911879174d08aa",
           "CAD/Voron_2.4r2_Assembly_STEP.zip"),
    "trident": ("Voron-Trident", "1a49bdc2c524cd6f4491a01e8fd566d0bd6acd0a",
                "CAD/trident_assembly.step.zip"),
    "trident_old": ("Voron-Trident", "9d9223311f2b0fce72484023d6a755e13a733319",
                    "CAD/trident_assembly.step.zip"),
}
p = argparse.ArgumentParser()
p.add_argument("exe")
p.add_argument("case", choices=["trident_revision_common_679",
                                "trident_shift_common_136", "v2_shift_rigid_1454"])
p.add_argument("--timeout", type=int, default=120)
args = p.parse_args()
assert 35 < args.timeout <= 180
exe = Path(args.exe).resolve()
assert exe.is_file()
root = Path("evidence") / args.case
root.mkdir(parents=True, exist_ok=True)
report = {"case": args.case, "timeout_s": args.timeout, "exe_sha256":
          hashlib.sha256(exe.read_bytes()).hexdigest(),
          "diagnostic_only": True, "source": []}
def save():
    (root / "PROBE.json").write_text(json.dumps(report, indent=2, ensure_ascii=False),
                                      encoding="utf-8")
def download(key):
    repo, ref, name = MODELS[key]
    url = f"https://raw.githubusercontent.com/VoronDesign/{repo}/{ref}/{name}"
    folder = Path("models") / key
    folder.mkdir(parents=True, exist_ok=True)
    archive = folder / "source.zip"
    urllib.request.urlretrieve(url, archive)
    with zipfile.ZipFile(archive) as z:
        z.extractall(folder)
    files = [x for x in folder.rglob("*") if x.suffix.lower() in (".step", ".stp")]
    if not files:
        raise RuntimeError("Missing STEP: " + key)
    source = max(files, key=lambda x: x.stat().st_size).resolve()
    report["source"].append({"key": key, "revision": ref, "url": url,
                             "file": source.name,
                             "sha256": hashlib.sha256(source.read_bytes()).hexdigest()})
    save()
    return source

try:
    from dsac29.step_io import load_step, ColoredDocument
    from dsac29.native_guard import guarded_common, guarded_rigid, NativeGeometryFailure
    from dsac29.material_deltas import volume
    from OCP.BRepTools import BRepTools
    from OCP.gp import gp_Trsf, gp_Vec
    from OCP.TopLoc import TopLoc_Location

    case = args.case
    if case == "trident_revision_common_679":
        src_a, src_b = download("trident_old"), download("trident")
        idx_a = idx_b = 679
        operation = "common"
    else:
        model = "v2" if case.startswith("v2") else "trident"
        src_a = download(model)
        src_b = None
        idx_a = idx_b = 1454 if model == "v2" else 136
        operation = "rigid" if model == "v2" else "common"

    started = time.monotonic()
    parts_a = load_step(str(src_a), max_solids=20000)
    report["count_a"] = len(parts_a)
    assert len(parts_a) > idx_a and len(parts_a) > 600
    if src_b is None:
        tr = gp_Trsf()
        tr.SetTranslation(gp_Vec(1275., -395., 210.))
        writer = ColoredDocument(group_by_status=False, reuse_definitions=True)
        for part in parts_a:
            writer.add(part.shape.Moved(TopLoc_Location(tr)), part.name,
                       (.33, .57, .86), 1.)
        shifted = Path("models") / "moved.step"
        writer.write(str(shifted))
        del writer
        parts_b = load_step(str(shifted), max_solids=20000)
        report["reexported_shift"] = [1275, -395, 210]
        inv = gp_Trsf()
        inv.SetTranslation(gp_Vec(-1275., 395., -210.))
        b_shape = parts_b[idx_b].shape.Moved(TopLoc_Location(inv))
    else:
        parts_b = load_step(str(src_b), max_solids=20000)
        b_shape = parts_b[idx_b].shape
    report["count_b"] = len(parts_b)
    assert len(parts_b) > idx_b and len(parts_b) > 600
    a_shape = parts_a[idx_a].shape
    report["index_a"] = idx_a
    report["index_b"] = idx_b
    report["preparation_seconds"] = round(time.monotonic() - started, 3)
    report["volume_a"] = float(volume(a_shape))
    report["volume_b"] = float(volume(b_shape))
    save()
    # Save exact problematic input B-Reps, so the diagnosis is independently
    # reproducible without downloading 200 MB of original STEP files.
    for name, shape in (("A.brep", a_shape), ("B.brep", b_shape)):
        with (root / name).open("wb") as f:
            BRepTools.Write_s(shape, f)
    del parts_a, parts_b
    gc.collect()
    process_args = [str(exe), "--native-brep-compare"]
    started = time.monotonic()
    if operation == "common":
        result = guarded_common(a_shape, b_shape, 0.01, timeout_s=args.timeout,
                                process_args=process_args)
        report["common_volume"] = float(volume(result))
        report["native_operation_result"] = "completed"
    else:
        from dsac29.geometry import describe
        a_info = describe(a_shape, "A", "probe/A")
        b_info = describe(b_shape, "B", "probe/B")
        matched, rot, vec = guarded_rigid(a_info, b_info, 0.01,
                                          timeout_s=args.timeout,
                                          process_args=process_args)
        report["rigid_match"] = bool(matched)
        report["native_operation_result"] = "completed"
    report["native_seconds"] = round(time.monotonic() - started, 3)
    report["status"] = "PROBE_COMPLETE_NOT_A_COMPARISON_PASS"
    save()
    print(json.dumps(report, ensure_ascii=False), flush=True)
except BaseException:
    report["status"] = "PROBE_FAILED_NOT_A_COMPARISON_VERDICT"
    report["error"] = traceback.format_exc()
    report["native_seconds"] = round(time.monotonic() - started, 3) if "started" in globals() else None
    save()
    raise
