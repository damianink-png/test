"""Revision comparison does not infer individual identities of repeated parts.

Keep world-position B-Rep matching first. Exclude repeated candidates only
from rigid-motion search; preserve all failed world proofs as unknown.
"""
from pathlib import Path
import sys
p=Path(sys.argv[1])/'dsac29/compare.py'
s=p.read_text()
anchor="    trace.mark('rigid_candidates','BEGIN',remaining_a=len(free_a),remaining_b=len(free_b))"
assert s.count(anchor)==1
s=s.replace(anchor,'''    # Count the FULL revisions, not the leftovers after stationary matching.
    # Names here only disable heuristic motion search, never prove equality.
    from collections import Counter
    from .material_names import material_name_key
    counts_a,counts_b=Counter(group_a),Counter(group_b)
    keys_a=[material_name_key(p.name) for p in a]
    keys_b=[material_name_key(p.name) for p in b]
    names_a,names_b=Counter(keys_a),Counter(keys_b)
    repeated_motion_a={i for i,g in enumerate(group_a)
        if counts_a[g]>1 or (keys_a[i] and names_a[keys_a[i]]>1)} if revision_only else set()
    repeated_motion_b={j for j,g in enumerate(group_b)
        if counts_b[g]>1 or (keys_b[j] and names_b[keys_b[j]]>1)} if revision_only else set()
    trace.mark('repeated_motion_policy','EXCLUDED',
        old_occurrences=len(free_a & repeated_motion_a),
        new_occurrences=len(free_b & repeated_motion_b))
'''+anchor)
anchor='    volume_index = _VolumeIndex(b, free_b)'
assert s.count(anchor)==1
s=s.replace(anchor,'    volume_index = _VolumeIndex(b, free_b - repeated_motion_b)')
anchor='''        for idx,i in enumerate(sorted(free_a)):
            if i not in free_a:continue'''
assert s.count(anchor)==1
s=s.replace(anchor,'''        for idx,i in enumerate(sorted(free_a)):
            if i not in free_a or i in repeated_motion_a:continue''')
anchor='''                  if j in free_b
                  and (norm_a[i] == norm_b[j]) == names_equal'''
assert s.count(anchor)==2
head,tail=s.split("    trace.mark('rigid_candidates','BEGIN'",1)
s=head+"    trace.mark('rigid_candidates','BEGIN'"+tail.replace(anchor,'''                  if j in free_b and j not in repeated_motion_b
                  and (norm_a[i] == norm_b[j]) == names_equal''')
compile(s,str(p),'exec');p.write_text(s)
print('REPEATED_REVISION_MOTION_POLICY_PASS')
