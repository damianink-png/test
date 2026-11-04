"""Apply minimal, auditable dispatch patch after checking frozen ZIP manifest."""
import sys
from pathlib import Path
p=Path(sys.argv[1])
s=p.read_text(encoding='utf8')
needle="    if req.get('operation') == 'material_regions':\n"
replacement=("    if req.get('operation') == 'common_exclusion':\n"
             "        from .common_exclusion import worker as exclude_worker\n"
             "        return exclude_worker(req,result_path)\n"+needle)
# Older pinned source snapshots may already contain the correct
# Common exclusion dispatch. Reapplying the same patch must be harmless,
# while any unknown/partial dispatch still fails closed.
existing=replacement[:replacement.index(needle)]
if s.count(existing)==1:
    if s.count(needle)!=1:
        raise RuntimeError('Native worker dispatch changed after exclusion')
    print('COMMON_EXCLUSION_DISPATCH_ALREADY_APPLIED_PASS')
elif 'common_exclusion' in s:
    raise RuntimeError('Unexpected or partial Common exclusion dispatch')
else:
    if s.count(needle)!=1:
        raise RuntimeError('Native worker dispatch changed')
    p.write_text(s.replace(needle,replacement),encoding='utf8')
    print('COMMON_EXCLUSION_DISPATCH_PATCH_PASS')
