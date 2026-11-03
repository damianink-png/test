#!/usr/bin/env python3
"""Fail-closed triage of the exact user Trident STEP comparison.

The output is diagnostic, never a substitute for the strict CAD audit.
Usage: python trident_failure_triage.py strict_final_audit.json PODSUMOWANIE.json
"""
import collections
import json
import pathlib
import sys

EXPECTED = {
    'Trident_Assembly1.step': (192710725, 'e26006c887004d1dcacac36e08ca083268336d80668ea2d868a16e2b20aee370'),
    'trident_assembly.step': (185183500, '416eda4e9212b894ed6f78ad3a6af55757115ebfcc4c18db933743d97dd48ccf'),
}


def categories(message):
    s = str(message).lower()
    flags = []
    if any(x in s for x in ('timeout', 'limit czasu', 'timeoutexpired')):
        flags.append('TIMEOUT_OR_BUDGET')
    if 'negative' in s or 'ujemn' in s:
        flags.append('NEGATIVE_VOLUME')
    if any(x in s for x in ('invalid', 'unprovenrepair', 'wire')):
        flags.append('INVALID_TOPOLOGY')
    if 'exit 139' in s or 'segmentation' in s:
        flags.append('NATIVE_CRASH')
    return flags or ['OTHER_UNPROVEN']


def require(condition, message):
    # Do not use assert: Python -O disables assertions and must never turn
    # a malformed/partial CAD report into an apparent PASS.
    if not condition:
        raise ValueError(message)


def analyze(audit, summary):
    inputs = audit.get('inputs', {})
    for name, (size, digest) in EXPECTED.items():
        entry = inputs.get(name, {})
        require(entry.get('bytes') == size and entry.get('sha256') == digest
                and entry.get('verified') is True, 'Input mismatch: ' + name)
    fingerprints = summary.get('source_fingerprints', {})
    require(fingerprints.get('A') == EXPECTED['Trident_Assembly1.step'][1], 'A SHA mismatch')
    require(fingerprints.get('B') == EXPECTED['trident_assembly.step'][1], 'B SHA mismatch')

    comparison = audit.get('comparison', {})
    for side in ('A', 'B'):
        count = comparison.get('solids_' + side)
        require(type(count) is int and count >= 0, 'Invalid solids_' + side)
        require(count == summary.get('solids_' + side), 'Solids mismatch: ' + side)
        require(comparison.get('covered_' + side) == count, 'Occurrence coverage mismatch: ' + side)
    require(comparison.get('statuses') == summary.get('statuses'), 'Status totals mismatch')
    statuses = comparison.get('statuses', {})
    require(isinstance(statuses, dict), 'Invalid statuses')
    require(all(type(n) is int and n >= 0 for n in statuses.values()), 'Invalid status count')

    failures = comparison.get('failed_pairs', [])
    total = comparison.get('failed_pairs_total')
    uncertain = comparison.get('uncertain_records')
    require(isinstance(failures, list) and all(isinstance(f, dict) for f in failures),
            'Invalid failed-pair sample')
    require(type(total) is int and total >= len(failures), 'Invalid failed-pair total')
    require(type(uncertain) is int and uncertain >= 0, 'Invalid UNCERTAIN count')
    flags = collections.Counter(tag for f in failures for tag in categories(f.get('error', '')))
    incomplete = (summary.get('analysis_complete') is not True
                  or summary.get('material_analysis_complete') is not True
                  or comparison.get('strict_pass') is not True
                  or uncertain > 0 or total > 0)
    return {
        'status': 'INCOMPLETE' if incomplete else 'PASS',
        'failure_flags_in_sample': dict(flags),
        'sample_size': len(failures),
        'failed_pairs_total': total,
        'failed_pairs_not_in_sample': total - len(failures),
        'statuses': statuses,
        'accounting': 'PASS',
        'recommendation': 'Isolate timeout/budget pairs in bounded per-pair tests; never relax tolerance or mark them SAME.',
    }


def main():
    if len(sys.argv) != 3:
        raise SystemExit('usage: trident_failure_triage.py audit.json summary.json')
    a = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding='utf-8'))
    s = json.loads(pathlib.Path(sys.argv[2]).read_text(encoding='utf-8'))
    try:
        result = analyze(a, s)
    except (ValueError, KeyError, TypeError) as exc:
        print(json.dumps({'status': 'INVALID_EVIDENCE', 'error': str(exc)}, ensure_ascii=False))
        raise SystemExit(2)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
