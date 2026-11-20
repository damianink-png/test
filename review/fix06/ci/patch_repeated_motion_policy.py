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
    def motion_exclusions(parts, groups):
        if not revision_only:
            return set()
        counts=Counter(groups)
        keys=[material_name_key(p.name) for p in parts]
        names=Counter(keys)
        return {i for i,group in enumerate(groups)
                if counts[group]>1 or (keys[i] and names[keys[i]]>1)}
    repeated_motion_a=motion_exclusions(a,group_a)
    repeated_motion_b=motion_exclusions(b,group_b)
    motion_old=sorted(free_a-repeated_motion_a)
    motion_new=sorted(free_b-repeated_motion_b)
    trace.mark('repeated_motion_policy','EXCLUDED',
        old_occurrences=len(free_a & repeated_motion_a),
        new_occurrences=len(free_b & repeated_motion_b))
'''+anchor)
anchor='    volume_index = _VolumeIndex(b, free_b)'
assert s.count(anchor)==1
s=s.replace(anchor,'    volume_index = _VolumeIndex(b, motion_new)')
anchor='''        for idx,i in enumerate(sorted(free_a)):
            if i not in free_a:continue'''
assert s.count(anchor)==1
s=s.replace(anchor,'''        for idx,i in enumerate(motion_old):''')
anchor='lookup=(sorted(free_b) if use_native_guard else'
assert s.count(anchor)==1
s=s.replace(anchor,'lookup=(motion_new if use_native_guard else')
compile(s,str(p),'exec');p.write_text(s)
print('REPEATED_REVISION_MOTION_POLICY_PASS')
