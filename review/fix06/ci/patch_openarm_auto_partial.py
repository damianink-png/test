"""Update frozen OpenArm audit for the user-requested automatic partial report.

Keep every geometry, STEP, completeness, identity, and occurrence assertion.
Only replace the obsolete expectation that the user must click "review".
"""
from pathlib import Path
import sys
p=Path(sys.argv[1])
s=p.read_text(encoding='utf-8')
old="assert any(x['decision']=='review' for x in decisions),'Review was not explicitly approved'"
new="assert not any(x['decision']=='review' for x in decisions),'Partial report unexpectedly requested interactive confirmation'"
if s.count(old)!=1:raise RuntimeError('Frozen OpenArm audit changed: expected exactly one decision assertion')
s=s.replace(old,new)
p.write_text(s,encoding='utf-8')
print('OPENARM_AUTOMATIC_PARTIAL_AUDIT_PATCH_PASS',flush=True)
