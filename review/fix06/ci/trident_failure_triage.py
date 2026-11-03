#!/usr/bin/env python3
"""Classify exact-Trident material failures without converting uncertainty to PASS.

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
    """Independent flags: a repair failure can also have a fallback timeout."""
    s = message.lower()
    flags = []
    if 'timeout' in s or 'limit czasu' in s or 'timeoutexpired' in s:
        flags.append('TIMEOUT_OR_BUDGET')
    if 'negative' in s or 'ujemn' in s:
        flags.append('NEGATIVE_VOLUME')
    if 'invalid' in s or 'unprovenrepair' in s or 'wire' in s:
        flags.append('INVALID_TOPOLOGY')
    if 'exit 139' in s or 'segmentation' in s:
        flags.append('NATIVE_CRASH')
    return flags or ['OTHER_UNPROVEN']

def analyze(audit, summary):
    inputs = audit['inputs']
    for name, (size, digest) in EXPECTED.items():
        entry = inputs[name]
        assert entry['bytes'] == size and entry['sha256'] == digest and entry['verified'] is True, f'Input mismatch: {name}'
    assert summary['source_fingerprints']['A'] == EXPECTED['Trident_Assembly1.step'][1]
    assert summary['source_fingerprints']['B'] == EXPECTED['trident_assembly.step'][1]
    comparison = audit['comparison']
    assert comparison['solids_A'] == summary['solids_A']
    assert comparison['solids_B'] == summary['solids_B']
    assert comparison['covered_A'] == comparison['solids_A']
    assert comparison['covered_B'] == comparison['solids_B']
    assert comparison['statuses'] == summary['statuses']
    failures = comparison['failed_pairs']
    counts = collections.Counter(tag for f in failures for tag in categories(f['error']))
    incomplete = (not summary['analysis_complete'] or not summary['material_analysis_complete']
                  or not comparison['strict_pass'] or comparison['uncertain_records'] > 0)
    return {'status': 'INCOMPLETE' if incomplete else 'PASS',
            'failure_flags_in_sample': dict(counts), 'sample_size': len(failures),
            'failed_pairs_total': comparison['failed_pairs_total'],
            'failed_pairs_not_in_sample': comparison['failed_pairs_total']-len(failures),
            'statuses': summary['statuses'], 'accounting': 'PASS',
            'recommendation': 'Isolate timeout/budget pairs in bounded per-pair tests; never relax tolerance or mark them SAME.'}

def main():
    if len(sys.argv) != 3:
        raise SystemExit('usage: trident_failure_triage.py audit.json summary.json')
    a = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding='utf-8'))
    s = json.loads(pathlib.Path(sys.argv[2]).read_text(encoding='utf-8'))
    print(json.dumps(analyze(a,s), ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
