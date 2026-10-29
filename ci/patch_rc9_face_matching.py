"""Bounded face correspondence for complex STEP re-exports.

A real Voron V2 pair contains 718 faces and a one-face B-Spline orientation
count mismatch. The old recursive augmenting-path matcher could explore
dense candidates for >90 seconds even though a bijection is impossible.
Reject impossible face type/orientation multisets before matching, and
replace recursion with deterministic iterative augmenting paths.

No tolerance, face correspondence, surface or trim acceptance is relaxed.
"""
from pathlib import Path
import ast

p = Path(__file__).resolve().parents[1] / "dscompare_rc9_manual" / "dsac29" / "step_reexport_tolerance.py"
s = p.read_text(encoding="utf-8")
helper = '''
def _face_type_orientation_compatible(left, right):
    from collections import Counter
    return Counter((f[0], f[1]) for f in left) == Counter((f[0], f[1]) for f in right)


def _perfect_face_owner(options):
    """Iterative augmenting paths; return right-face -> left-face matching."""
    from collections import deque
    owner, reverse = {}, {}
    for first in sorted(range(len(options)), key=lambda i: len(options[i])):
        queue = deque([first])
        seen_left, seen_right, parent = {first}, set(), {}
        free = None
        while queue and free is None:
            i = queue.popleft()
            for j in options[i]:
                if j in seen_right:
                    continue
                seen_right.add(j)
                parent[j] = i
                if j not in owner:
                    free = j
                    break
                other = owner[j]
                if other not in seen_left:
                    seen_left.add(other)
                    queue.append(other)
        if free is None:
            return None
        while True:
            i = parent[free]
            old = reverse.get(i)
            owner[free] = i
            reverse[i] = free
            if old is None:
                break
            free = old
    return owner

'''
old = "\ndef coarse_candidate("
if s.count(old) != 1:
    raise SystemExit("Unexpected STEP face matching helper insertion point")
s = s.replace(old, "\n" + helper + "def coarse_candidate(")
old = "    if len(fa)!=len(fb) or not fa:return False"
new = old + "\n    if not _face_type_orientation_compatible(fa,fb):return False"
if s.count(old) != 1:
    raise SystemExit("Unexpected STEP face descriptor count")
s = s.replace(old, new)
start = s.index("    # Perfect face correspondence:")
end = s.index("    if len(owner)!=len(fa):return False", start)
old_match = s[start:end]
if "def assign(i,visited):" not in old_match or "for i in sorted(range(len(fa))" not in old_match:
    raise SystemExit("Unexpected recursive face matcher")
s = s[:start] + (
    "    # Maximum bipartite matching, no recursion or geometric shortcuts.\n"
    "    owner=_perfect_face_owner(options)\n"
    "    if owner is None:return False\n"
) + s[end:]
ast.parse(s, filename=str(p))
p.write_text(s, encoding="utf-8")
print("RC9 face multiset precheck and iterative perfect matching installed")
