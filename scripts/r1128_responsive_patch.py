"""R11.28 adaptive layout: keep vertical scrolling primary; provide horizontal
fallback only on screens too narrow for the 2 settings forms to fit safely.
"""
import os
from pathlib import Path
root=Path(os.environ['DS_COMPARE_SOURCE'])
p=root/'dsac29/gui_modern.py'
s=p.read_text('utf8')
old="  min_w=min(760,max(560,area.width()-64))"
assert s.count(old)==1
s=s.replace(old,"  min_w=min(980,max(560,area.width()-48))",1)
old="  wrapper.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)"
assert s.count(old)==1
s=s.replace(old,
"""  # Only exceptionally narrow settings screens can exceed the viewport.
  # Do not clip options: enable a horizontal fallback when they cannot wrap.
  wrapper.setHorizontalScrollBarPolicy(
   Qt.ScrollBarAsNeeded if key=='settings' else Qt.ScrollBarAlwaysOff)""",1)
p.write_text(s,'utf8')
print('R11.28 adaptive min width 980px when available, and safe fallback for narrow settings viewport')
