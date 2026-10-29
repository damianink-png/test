"""Apply independent OpenAssembly v0.6 STEP round-trip regression fix.

The source is shipped as an archive; patch it deterministically after extraction.
No DS Compare code or branches are touched.
"""
from pathlib import Path
import sys

def replace_once(s, old, new, where):
    count = s.count(old)
    if count != 1:
        raise RuntimeError(f'{where}: expected exactly one anchor, found {count}')
    return s.replace(old, new, 1)

def apply(root):
    align = root / 'src/openassembly/alignment.py'
    s = align.read_text(encoding='utf-8')
    s = replace_once(s,
        """    if baseline>=total-1:
        return Alignment(False,IDENTITY,(0.,0.,0.),baseline,baseline,baseline_types,len(a),len(b),0,'original')
""",
        """    # A strong majority already matches in the original frame: do not
    # score hundreds of speculative global shifts for a local CAD revision.
    if baseline>=total-1 or (total>=100 and baseline>=math.ceil(.985*total)
                             and baseline_types>=20):
        return Alignment(False,IDENTITY,(0.,0.,0.),baseline,baseline,baseline_types,len(a),len(b),0,'original (strong majority)')
""", 'alignment')
    align.write_text(s, encoding='utf-8')

    model = root / 'src/openassembly/model.py'
    s = model.read_text(encoding='utf-8')
    s = replace_once(s,
        """    if (alignment and alignment.applied and alignment.matching >= max(20, math.ceil(.985 * min(len(a),len(b))))
            and alignment.fingerprint_types >= 20):
""",
        """    if (alignment and min(len(a),len(b)) >= 100
            and max(len(a),len(b)) <= 1.10*min(len(a),len(b))
            and alignment.matching >= math.ceil(.985 * min(len(a),len(b)))
            and alignment.fingerprint_types >= 20):
""", 'original-frame recovery')
    s = replace_once(s,
        "        permitted=max(4,math.ceil(.03*min(len(a),len(b))))",
        "        permitted=max(4,math.ceil(.10*min(len(a),len(b))))",
        'roundtrip residual budget')
    s = replace_once(s,
        "                        if v_rel>.006 or a_rel>.003:continue",
        """                        # Empirically bounded re-export residuals:
                        # Voron/Trident <0.047% volume and <0.023% area.
                        # Do not silently erase ordinary design revisions.
                        if v_rel>.0006 or a_rel>.0003:continue""",
        'strict mass/area gate')
    s = replace_once(s,
        """                            if any(abs(x-y)>max(1., .30*max(abs(x),abs(y)))
""",
        """                            if any(abs(x-y)>max(1., .35*max(abs(x),abs(y)))
""", 'STEP bounding-box drift')
    s = replace_once(s,
        "    # Revision: same/very similar name, co-located, distinct geometry.",
        """    # Some exact-fingerprint parts look 'moved' because STEP rewrites
    # TopLoc and AABB metadata. For same-centroid candidates, require
    # actual common-material proof in the isolated B-Rep worker before
    # undoing the move. Genuine translations/rotations remain moved.
    if (revision_overlap is not None and alignment
            and min(len(a),len(b)) >= 100
            and alignment.matching >= math.ceil(.985 * min(len(a),len(b)))
            and alignment.fingerprint_types >= 20):
        by_id={p.uid:p for p in b}
        ambiguous=[old for old in a if old.status=='moved' and old.match in by_id
                   and _dist(old,by_id[old.match])<=max(pos_tol,.08)
                   and old.name.casefold()==by_id[old.match].name.casefold()
                   and old.fingerprint==by_id[old.match].fingerprint]
        for old in ambiguous[:12]:
            new=by_id[old.match]
            try:
                measured=revision_overlap(old,new)
                if not isinstance(measured,dict) or not measured.get('ok',False):
                    continue
                va=max(old.volume,new.volume)
                if (measured.get('overlap',0)>=.9999
                    and measured.get('added_mm3',va)/va<=.0005
                    and measured.get('removed_mm3',va)/va<=.0005):
                    old.status=new.status='unchanged'
                    old.match_quality=new.match_quality='boolean_verified_roundtrip'
            except Exception:
                # Fail closed: never reclassify a move on a failed Boolean.
                continue
    # Revision: same/very similar name, co-located, distinct geometry.""",
        'moved false-positive verification')
    model.write_text(s, encoding='utf-8')
    print('OpenAssembly roundtrip recovery patch applied:', root)

if __name__=='__main__':
    if len(sys.argv)!=2:
        raise SystemExit('Usage: apply_roundtrip_recovery.py EXTRACTED_SOURCE_DIR')
    apply(Path(sys.argv[1]).resolve())
