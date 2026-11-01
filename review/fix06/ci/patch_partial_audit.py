"""Narrow compatibility patch for the frozen OpenArm partial-output audit.

The legacy audit assumed a partial result could contain only SAME/MOVED and
UNCERTAIN. Validated, unmatched ADDED/REMOVED occurrences are independent of
unresolved Common/Cut pairs and must remain visible, never silently rewritten
as UNCERTAIN. This patch keeps the strict checks for every other category.
"""
from pathlib import Path
import sys

OLD = "assert s['statuses'].get('UNCERTAIN') and not set(s['statuses'])-{'SAME','RENAMED','MOVED','UNCERTAIN'}"
NEW = '''assert s['statuses'].get('UNCERTAIN', 0) > 0
assert not set(s['statuses']) - {'SAME','RENAMED','MOVED','UNCERTAIN','ADDED','REMOVED'}
for record in s['records']:
    status = record['status']
    if status in ('ADDED', 'REMOVED'):
        # A partial material analysis may still prove unrelated unmatched parts.
        # Never accept an unresolved boolean as an ADDED/REMOVED verdict.
        assert record.get('verification') == 'confirmed', record
        assert not record.get('diagnostic_reason') and not record.get('blocked_operation_operand'), record
        assert (record.get('a_index') is None) != (record.get('b_index') is None), record
        assert record.get('a_index') is None if status == 'ADDED' else record.get('b_index') is None, record
'''.rstrip()

def patch(path: Path) -> None:
    text = path.read_text(encoding='utf-8')
    if text.count(OLD) != 1:
        if NEW in text:
            print('PARTIAL_AUDIT_PATCH_ALREADY_APPLIED')
            return
        raise ValueError('Frozen partial-audit assertion not found exactly once; refusing unsafe patch')
    path.write_text(text.replace(OLD, NEW), encoding='utf-8')
    print('PARTIAL_AUDIT_PATCH_APPLIED')

if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('Usage: patch_partial_audit.py <frozen audit_partial_artifacts.py>')
    patch(Path(sys.argv[1]))
