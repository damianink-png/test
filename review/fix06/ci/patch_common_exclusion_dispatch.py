"""Apply minimal, auditable dispatch patch after checking frozen ZIP manifest."""
import sys
from pathlib import Path
p=Path(sys.argv[1])
s=p.read_text(encoding='utf8')
needle="    if req.get('operation') == 'material_regions':\n"
replacement=("    if req.get('operation') == 'common_exclusion':\n"
             "        from .common_exclusion import worker as exclude_worker\n"
             "        return exclude_worker(req,result_path)\n"+needle)
if s.count(needle)!=1:raise RuntimeError('Native worker dispatch changed')
if 'common_exclusion' in s:raise RuntimeError('Exclusion already present')
p.write_text(s.replace(needle,replacement),encoding='utf8')
print('COMMON_EXCLUSION_DISPATCH_PATCH_PASS')
