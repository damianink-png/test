"""Bounded, diagnostic-only replay of failed OCCT Common B-Reps.

No result from this tool is used for SAME, MOVED, material changes or exports.
"""
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time

VARIANTS = ('standard', 'obb_off', 'parallel')


def child(folder, variant):
    from OCP.BRep import BRep_Builder
    from OCP.BRepTools import BRepTools
    from OCP.TopoDS import TopoDS_Shape
    from OCP.BRepCheck import BRepCheck_Analyzer
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Common
    from OCP.BRepGProp import BRepGProp
    from OCP.GProp import GProp_GProps
    from OCP.TopTools import TopTools_ListOfShape

    def read(name):
        shape = TopoDS_Shape()
        with (folder / name).open('rb') as stream:
            ok = BRepTools.Read_s(shape, stream, BRep_Builder())
        if ok is False or shape.IsNull():
            raise ValueError('Cannot load diagnostic BRep')
        return shape

    a, b = read('A.brep'), read('B.brep')
    valid_inputs = [bool(BRepCheck_Analyzer(s).IsValid()) for s in (a, b)]
    arguments, tools = TopTools_ListOfShape(), TopTools_ListOfShape()
    arguments.Append(a)
    tools.Append(b)
    op = BRepAlgoAPI_Common()
    op.SetArguments(arguments)
    op.SetTools(tools)
    op.SetNonDestructive(True)
    op.SetUseOBB(variant != 'obb_off')
    op.SetRunParallel(variant == 'parallel')
    op.SetFuzzyValue(0.0001)  # diagnostic only; production remains 0.01 mm
    started = time.monotonic()
    op.Build()
    result = {'variant': variant, 'input_valid': valid_inputs,
              'seconds': round(time.monotonic() - started, 3),
              'is_done': bool(op.IsDone())}
    if op.IsDone():
        shape = op.Shape()
        result['null'] = bool(shape.IsNull())
        if not shape.IsNull():
            properties = GProp_GProps()
            BRepGProp.VolumeProperties_s(shape, properties)
            signed = float(properties.Mass())
            result['signed_volume_mm3'] = signed if math.isfinite(signed) else str(signed)
            result['topology_valid'] = bool(BRepCheck_Analyzer(shape).IsValid())
            result['potentially_valid'] = bool(
                math.isfinite(signed) and signed >= 0 and result['topology_valid'])
    print(json.dumps(result), flush=True)
    os._exit(0)  # Avoid hanging in C++ destructor of an invalid diagnostic result.


def probe(folder, output, deadline=12):
    report = {'kind': 'diagnostic_only_no_geometry_verdict', 'input': {}, 'probes': []}
    output.parent.mkdir(parents=True, exist_ok=True)
    for name in ('A.brep', 'B.brep'):
        file = folder / name
        if not file.is_file():
            report['error'] = 'Missing ' + name
            output.write_text(json.dumps(report, indent=2), encoding='utf-8')
            return
        report['input'][name] = {'bytes': file.stat().st_size,
                                 'sha256': hashlib.sha256(file.read_bytes()).hexdigest()}
    variants = VARIANTS
    if max(item['bytes'] for item in report['input'].values()) > 2_000_000:
        variants = ('standard', 'parallel')
    for variant in variants:
        started = time.monotonic()
        try:
            proc = subprocess.run([sys.executable, str(Path(__file__).resolve()),
                                   '--child', str(folder), variant],
                                  capture_output=True, text=True,
                                  timeout=deadline, check=False)
            item = {'variant': variant, 'exit_code': proc.returncode,
                    'elapsed_s': round(time.monotonic()-started, 3)}
            if proc.returncode == 0:
                try:
                    item.update(json.loads(proc.stdout))
                except (TypeError, ValueError):
                    item['error'] = 'Malformed diagnostic output'
            else:
                item['error'] = 'Native diagnostic process failed'
            if proc.stderr:
                item['stderr_tail'] = proc.stderr[-1000:]
        except subprocess.TimeoutExpired:
            item = {'variant': variant, 'timeout_s': deadline,
                    'error': 'Native diagnostic timeout; no conclusion'}
        report['probes'].append(item)
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2),
                          encoding='utf-8')


if __name__ == '__main__':
    if len(sys.argv) >= 4 and sys.argv[1] == '--child':
        if sys.argv[3] not in VARIANTS:
            raise SystemExit('Unknown diagnostic variant')
        child(Path(sys.argv[2]), sys.argv[3])
    elif len(sys.argv) in (3, 4):
        probe(Path(sys.argv[1]), Path(sys.argv[2]),
              int(sys.argv[3]) if len(sys.argv) == 4 else 12)
    else:
        raise SystemExit('Usage: rc9_common_probe.py PAIR_DIR OUTPUT_JSON [TIMEOUT_SECONDS]')
