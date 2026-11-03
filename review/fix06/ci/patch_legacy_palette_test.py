"""Update frozen RC9 palette test for neutral Common, without weakening proof rules."""
from pathlib import Path
import sys

p = Path(sys.argv[1])
source = p.read_text(encoding='utf-8')
old = "    assert COLORS['SAME']==REVISION_COLORS['SAME']==MATERIAL_COLORS['CHANGED_COMMON']"
new = ("    assert COLORS['SAME']==REVISION_COLORS['SAME']\n"
       "    assert MATERIAL_COLORS['CHANGED_COMMON']==REVISION_COLORS['CHANGED_COMMON']\n"
       "    assert MATERIAL_COLORS['CHANGED_COMMON'] not in (COLORS['ADDED'],COLORS['REMOVED'])")
if source.count(old) != 1:
    raise RuntimeError('Frozen palette test changed; review before patching')
source=source.replace(old,new)
legacy="    assert COLORS['REMOVED']==MATERIAL_COLORS['CHANGED_REMOVED']"
updated="    assert COLORS['REMOVED']!=MATERIAL_COLORS['CHANGED_REMOVED']  # Orange whole part, red cut material"
if source.count(legacy)!=1:
    raise RuntimeError('Frozen removed/material color assertion changed; review before patching')
source=source.replace(legacy,updated)
p.write_text(source,encoding='utf-8')
print('NEUTRAL_COMMON_PALETTE_TEST_PATCH_PASS')
