"""Reject impossible STEP face correspondences before costly augmenting paths.

A necessary Hall-condition precheck on the union of candidate right faces is
safe: if fewer distinct right faces exist than left faces, a perfect matching
cannot exist. This never certifies SAME; the original full oriented proof
remains mandatory. Also reject empty candidate lists immediately.
"""
from pathlib import Path
import ast

p = Path(__file__).resolve().parents[1] / "dscompare_rc9_manual" / "dsac29" / "step_reexport_tolerance.py"
s = p.read_text(encoding="utf-8")
anchor = '    owner, reverse = {}, {}\n    for first in sorted(range(len(options)), key=lambda i: len(options[i])):'
assert s.count(anchor) == 1, "Unexpected perfect-face matcher; refusing patch"
replacement = '''    # Necessary, never sufficient, perfect-matching conditions.
    # A repeated trimmed face may produce dense candidate lists, but
    # missing/empty right-face coverage means matching is impossible.
    if any(not candidates for candidates in options):
        return None
    if len(set().union(*(set(candidates) for candidates in options))) < len(options):
        return None
    owner, reverse = {}, {}
    for first in sorted(range(len(options)), key=lambda i: len(options[i])):'''
s = s.replace(anchor, replacement)
ast.parse(s, filename=str(p))
p.write_text(s, encoding="utf-8")
print("RC9: necessary face-candidate coverage prefilter installed")
