"""Identical physical CAD assemblies encoded as AP203/AP214/AP242.

Reads unchanged official Trident STEP or unchanged public aerospace bent STEP,
writes the SAME XCAF document using three STEP schemas, and performs real
DS Compare comparisons. No artificial material change, shift, or tolerance
relaxation. Any CHANGED, MOVED, ADDED, REMOVED, UNCERTAIN, or incomplete
comparison is a FAIL. Use dedicated Windows jobs with JSON diagnostics.
"""
from __future__ import annotations

import argparse
from collections import Counter
from hashlib import hashlib, md5, sha256
from io import BytesIO
import json
import os
from pathlib import Path
import re
import time
import traceback
import urllib.request
import zipfile

from OCP.STEPControl import STEPControl_Controller
from OCP.STEPCAFControl import STEPCAFControl_Reader, STEPCAFControl_Writer
from OCP.IFSelect import IFSelect_RetDone
from OCP.Interface import Interface_Static
from OCP.TDocStd import TDocStd_Document
from OCP.TCollection import TCollection_ExtendedString
from OCP.TDataStd import TDataStd_Name
from OCP.TDF import TDF_LabelSequence
from OCP.XCAFDoc import XCAFDoc_DocumentTool
from OCP.TopoDS import TopoDS_Compound, TopoDS
from OCP.BRep import BRep_Builder
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_FACE
from OCP.gp import gp_Trsf, gp_Vec
from OCP.TopLoc import TopLoc_Location

from dsac29.cli import process
from dsac29.step_io import load_step

SCHEMAS = {"AP203": "AP203", "AP214": "AP214IS", "AP242": "AP242DIS"}
HEADERS = {
    "AP203": "CONFIG_CONTROL_DESIGN",
    "AP214": "AUTOMOTIVE_DESIGN",
    "AP242": "AP242_MANAGED_MODEL_BASED_3D_ENGINEERING_MIM_LF",
}
ROOT = Path("evidence/identical_protocols")
RESULT = {}
WORKDIR = None


def save():
    WORKDIR.mkdir(parents=True, exist_ok=True)
    (WORKDIR / "RESULT.json").write_text(
        json.dumps(RESULT, indent=2, ensure_ascii=False, default=str), encoding="utf-8")


def digest(path):
    d = sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1048576), b""):
            d.update(block)
    return d.hexdigest()


def download(url, dest):
    dest.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(
        urllib.request.Request(url, headers={"User-Agent": "DSCompare-STEP-protocol-regression"}),
        timeout=150,
    ) as response, dest.open("wb") as stream:
        while block := response.read(1048576):
            stream.write(block)
    assert dest.stat().st_size > 1000, ("missing public CAD input", url)
    RESULT["inputs"].append(
        {"url": url, "sha256": digest(dest), "size_bytes": dest.stat().st_size})
    save()
    return dest


def read_xcaf(path):
    doc = TDocStd_Document(TCollection_ExtendedString("BinXCAF"))
    reader = STEPCAFControl_Reader()
    reader.SetNameMode(True)
    reader.SetColorMode(False)
    assert reader.ReadFile(str(path)) == IFSelect_RetDone, path
    assert reader.Transfer(doc), path
    return doc


def original_trident():
    # Same fixed official Trident revision used by the genuine two-revision CI.
    url = ("https://raw.githubusercontent.com/VoronDesign/Voron-Trident/"
           "1a49bdc2c524cd6f4491a01e8fd566d0bd6acd0a/CAD/trident_assembly.step.zip")
    archive = download(url, WORKDIR / "source" / "trident.zip")
    with zipfile.ZipFile(archive) as zf:
        names = [n for n in zf.namelist() if n.lower().endswith((".step", ".stp"))]
        assert names
        name = max(names, key=lambda n: zf.getinfo(n).file_size)
        output = WORKDIR / "source" / "trident_original.step"
        with zf.open(name) as src, output.open("wb") as dst:
            while block := src.read(1048576):
                dst.write(block)
    RESULT["original_sha256"] = digest(output)
    save()
    return read_xcaf(output), 1595


def bent_source():
    # Same public real aerospace sheet-metal corpus as bent STEP CI.
    url = ("https://zenodo.org/records/7799961/files/"
           "AFR%20source%20code%2C%20STEP%20files%20and%20solved%20examples.zip?download=1")
    archive = download(url, WORKDIR / "source" / "aerospace_bent.zip")
    expected = "d6ef1bd2bc197c36d74bb706915ae11f"
    assert md5(archive.read_bytes()).hexdigest() == expected, "external STEP corpus changed"
    candidates = []
    with zipfile.ZipFile(archive) as outer:
        for entry in outer.infolist():
            if entry.file_size > 60_000_000:
                continue
            files = []
            if entry.filename.lower().endswith((".step", ".stp")):
                files = [(entry.filename, outer.read(entry))]
            elif entry.filename.lower().endswith(".zip"):
                try:
                    with zipfile.ZipFile(BytesIO(outer.read(entry))) as inner:
                        files = [(x.filename, inner.read(x)) for x in inner.infolist()
                                 if x.filename.lower().endswith((".step", ".stp"))
                                 and 200 < x.file_size < 60_000_000]
                except (zipfile.BadZipFile, RuntimeError):
                    continue
            for name, blob in files:
                if len(blob) < 200:
                    continue
                path = WORKDIR / "source" / f"bent_{len(candidates):02d}.step"
                path.write_bytes(blob)
                candidates.append((path, name, sha256(blob).hexdigest()))

    assert candidates, "no authentic bent CAD data"
    selected = []
    for path, name, checksum in candidates:
        try:
            for part in load_step(str(path)):
                explorer = TopExp_Explorer(part.shape, TopAbs_FACE)
                curved = 0
                faces = 0
                while explorer.More() and faces < 350:
                    kind = str(BRepAdaptor_Surface(TopoDS.Face_s(explorer.Current())).GetType())
                    curved += any(x in kind for x in ("Cylinder", "Cone", "Torus"))
                    faces += 1
                    explorer.Next()
                if curved:
                    selected.append((curved, float(part.volume), part.shape, name, checksum))
        except (ValueError, RuntimeError):
            continue
    assert selected, "source corpus has no curved sheet-metal B-Rep"
    selected.sort(key=lambda value: (-value[0], -value[1]))
    curved, volume, shape, source_name, source_sha = selected[0]
    RESULT["bent_source"] = {
        "entry": source_name, "sha256": source_sha, "curved_faces": curved, "volume_mm3": volume,
    }

    # Build 40 occurrences from a real curved solid, without any shape edits.
    doc = TDocStd_Document(TCollection_ExtendedString("BinXCAF"))
    tool = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())
    template = tool.AddShape(shape.Located(TopLoc_Location()), False)
    TDataStd_Name.Set_s(template, TCollection_ExtendedString("BENT_REAL_PART"))
    compound = TopoDS_Compound()
    BRep_Builder().MakeCompound(compound)
    root = tool.AddShape(compound, True)
    TDataStd_Name.Set_s(root, TCollection_ExtendedString("BENT_ASSEMBLY_40"))
    for i in range(40):
        trsf = gp_Trsf()
        trsf.SetTranslation(gp_Vec(float((i % 8) * 400.0), float((i // 8) * 400.0), float((i % 3) * 21.0)))
        occurrence = tool.AddComponent(root, template, TopLoc_Location(trsf))
        TDataStd_Name.Set_s(occurrence, TCollection_ExtendedString("BENT_REAL_PART"))
    tool.UpdateAssemblies()
    save()
    return doc, 40


def write_variant(document, name):
    STEPControl_Controller.Init_s()
    schema = SCHEMAS[name]
    assert Interface_Static.SetCVal_s("write.step.schema", schema)
    assert Interface_Static.SetIVal_s("write.surfacecurve.mode", 1)
    assert Interface_Static.SetIVal_s("write.step.assembly", 1)
    writer = STEPCAFControl_Writer()
    writer.SetNameMode(True)
    writer.SetColorMode(False)
    writer.SetLayerMode(False)
    assert writer.Transfer(document), name
    path = WORKDIR / (name + ".step")
    assert writer.Write(str(path)) == IFSelect_RetDone, name
    with path.open("rb") as stream:
        header = stream.read(8192).decode("latin1", "replace")
    match = re.search(r"FILE_SCHEMA\s*\(.*?\)\s*;", header, re.DOTALL)
    assert match is not None, "STEP schema header absent"
    assert HEADERS[name] in match.group(0), (name, match.group(0))
    return path, match.group(0)


def check_pair(a, b, expected):
    name = f"{a}_vs_{b}"
    target = WORKDIR / name
    started = time.perf_counter()
    path, rows, error = process(
        str(WORKDIR / (a + ".step")), str(WORKDIR / (b + ".step")), str(target),
        tolerance=0.01, auto_align=False, force_unrelated=True,
        step=False, diff_step=False, preview3d=False,
        revision_style=True, full_bom=False, bom_csv=False,
        alignment_approval=lambda _: "original",
        material_approval=lambda _: "review",
        progress=lambda msg: print(f"{name}: {msg}", flush=True)
            if any(word in str(msg) for word in ("Etap 1:", "Gotowe:", "Porównanie rewizji:"))
            else None,
    )
    statuses = dict(Counter(row.status for row in rows))
    summary_file = path / "PODSUMOWANIE.json"
    summary = json.loads(summary_file.read_text(encoding="utf-8"))
    result = {
        "pair": name, "status_counts": statuses, "seconds": round(time.perf_counter() - started, 3),
        "analysis_complete": summary.get("analysis_complete"),
        "solids_A": summary.get("solids_A"), "solids_B": summary.get("solids_B"),
        "error": str(error) if error else None,
    }
    RESULT["pairs"].append(result)
    save()
    assert not error, result
    assert result["solids_A"] == result["solids_B"] == expected, result
    assert summary.get("analysis_complete") is True, result
    assert sum(statuses.get(k, 0) for k in ("SAME", "RENAMED")) == expected, result
    assert not any(v for k, v in statuses.items() if k not in ("SAME", "RENAMED")), result
    result["verdict"] = "PASS"
    save()
    print("IDENTICAL_PROTOCOL_PAIR_PASS", json.dumps(result, ensure_ascii=False), flush=True)


def main():
    global RESULT, WORKDIR
    args = argparse.ArgumentParser()
    args.add_argument("assembly", choices=("bent", "trident"))
    name = args.parse_args().assembly
    WORKDIR = (ROOT / name).resolve()
    RESULT = {
        "source": name, "sha": os.environ.get("GITHUB_SHA"),
        "scope": "same CAD assembly, different STEP schema; no geometry/material/position changes",
        "verdict": "RUNNING", "inputs": [], "formats": {}, "pairs": [],
    }
    save()
    try:
        doc, expected = bent_source() if name == "bent" else original_trident()
        RESULT["expected_solids"] = expected
        save()
        for schema in SCHEMAS:
            started = time.perf_counter()
            path, header = write_variant(doc, schema)
            parts = load_step(str(path))
            actual = len(parts)
            detail = {
                "sha256": digest(path), "bytes": path.stat().st_size,
                "schema_header": header, "solids": actual,
                "import_export_seconds": round(time.perf_counter() - started, 3),
                "volume_sum_mm3": round(sum(float(p.volume) for p in parts), 5),
            }
            RESULT["formats"][schema] = detail
            save()
            assert actual == expected, detail
            print("IDENTICAL_PROTOCOL_FORMAT_PASS", schema, json.dumps(detail, ensure_ascii=False), flush=True)

        sums = [entry["volume_sum_mm3"] for entry in RESULT["formats"].values()]
        assert max(sums) - min(sums) <= max(0.001, max(sums) * 1e-7), sums
        for a, b in (("AP203", "AP214"), ("AP214", "AP242"), ("AP203", "AP242")):
            check_pair(a, b, expected)
        RESULT["verdict"] = "PASS"
    except BaseException:
        RESULT["verdict"] = "FAIL"
        RESULT["traceback"] = traceback.format_exc()
        raise
    finally:
        save()
        print("IDENTICAL_PROTOCOL_SUMMARY", json.dumps({
            "source": name, "verdict": RESULT["verdict"],
            "expected": RESULT.get("expected_solids"),
            "pairs": RESULT["pairs"]}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
