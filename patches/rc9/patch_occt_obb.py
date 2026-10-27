"""Enable OCCT oriented bounding boxes in the existing isolated Boolean pipeline.

No classification or tolerance change. The production worker already uses
NonDestructive; OBB only filters potential face intersections.
"""
from pathlib import Path
import ast
import sys

root = Path(sys.argv[1])
path = root / "boolean_ops.py"
source = path.read_text(encoding="utf-8")
needle = "    op.SetNonDestructive(True)\n"
if source.count(needle) != 1:
    raise RuntimeError("Unexpected RC9 boolean_ops interface")
source = source.replace(
    needle,
    needle + "    op.SetUseOBB(True)\n",
)
ast.parse(source)
path.write_text(source, encoding="utf-8")
print("OCCT Boolean configured with NonDestructive and OBB; original tolerance retained")
