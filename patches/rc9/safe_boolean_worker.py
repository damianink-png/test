"""Isolated OCCT Boolean operations for RC9 experiments.

Never returns SAME: Boolean results are optional evidence, not classification.
Inputs are BREP files produced by the caller; outputs live in a separate directory.
"""
from __future__ import annotations
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path


def run_boolean(a: str, b: str, output: str, operation: str = "common",
                timeout: float = 35.0, python: str | None = None) -> dict:
    """Run OCCT in a killable subprocess. No fuzzy tolerance is introduced."""
    if operation not in {"common", "cut_ab", "cut_ba"}:
        raise ValueError("Unsupported operation")
    if timeout <= 0:
        raise ValueError("Timeout must be positive")
    command = [python or sys.executable, str(Path(__file__).resolve()),
               "--worker", "--a", str(a), "--b", str(b),
               "--out", str(output), "--operation", operation]
    started = time.monotonic()
    try:
        completed = subprocess.run(command, capture_output=True, text=True,
                                   timeout=timeout, check=False)
    except subprocess.TimeoutExpired:
        return {"status": "timeout", "elapsed_s": round(time.monotonic()-started, 3),
                "same_proven": False}
    return {"status": "ok" if completed.returncode == 0 else "error",
            "exit_code": completed.returncode,
            "elapsed_s": round(time.monotonic()-started, 3),
            "diagnostics": (completed.stderr or "")[-4000:],
            "same_proven": False}


def _worker(a: str, b: str, out: str, operation: str) -> None:
    from OCP.BRep import BRep_Builder
    from OCP.BRepTools import BRepTools
    from OCP.TopoDS import TopoDS_Shape
    from OCP.BRepCheck import BRepCheck_Analyzer
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Common, BRepAlgoAPI_Cut

    def load(path: str):
        shape = TopoDS_Shape()
        builder = BRep_Builder()
        if not BRepTools.Read_s(shape, path, builder):
            raise RuntimeError("BREP read failed")
        if shape.IsNull():
            raise RuntimeError("Null input shape")
        if not BRepCheck_Analyzer(shape).IsValid():
            raise RuntimeError("Invalid input topology; no automatic tolerance change")
        return shape

    sa, sb = load(a), load(b)
    if operation == "common":
        algo = BRepAlgoAPI_Common(sa, sb)
    elif operation == "cut_ab":
        algo = BRepAlgoAPI_Cut(sa, sb)
    else:
        algo = BRepAlgoAPI_Cut(sb, sa)
    algo.SetNonDestructive(True)
    algo.SetUseOBB(True)
    algo.Build()
    if not algo.IsDone():
        raise RuntimeError("Boolean operation failed")
    result = algo.Shape()
    if result.IsNull() or not BRepCheck_Analyzer(result).IsValid():
        raise RuntimeError("Null or invalid Boolean result")
    destination = Path(out)
    destination.parent.mkdir(parents=True, exist_ok=True)
    # OCCT Python bindings may expose Write_s as void rather than bool.
    # Validate the actual file instead of treating None as failure.
    BRepTools.Write_s(result, str(destination))
    if not destination.is_file() or destination.stat().st_size == 0:
        raise RuntimeError("BREP write failed: missing or empty output")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--worker", action="store_true")
    parser.add_argument("--a", required=True)
    parser.add_argument("--b", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--operation", choices=["common", "cut_ab", "cut_ba"], required=True)
    args = parser.parse_args()
    try:
        _worker(args.a, args.b, args.out, args.operation)
    except Exception as exc:
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(2)
