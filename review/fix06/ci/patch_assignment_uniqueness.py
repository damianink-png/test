"""Certify mathematically unambiguous assignments in large components.

Legacy matching skipped ALL uniqueness checks above 60 parts, making every
large repeated cohort UNCERTAIN. Strict row-wise minima are sufficient proof:
no other complete assignment can improve any row, and changing a certified
row must add at least its runner-up cost gap. Non-certifiable groups remain
conservatively UNCERTAIN. This patch is applied to the unzipped CAD sources.
"""
from pathlib import Path
import sys


def patch(path):
    target=Path(path)
    src=target.read_text(encoding='utf-8')
    marker="        # A legacy 60-part limit skipped ALL uniqueness checks"
    if marker in src:
        print("DSCOMPARE_ASSIGNMENT_GUARD_ALREADY_APPLIED",target)
        return
    old="""        chosen,best=_hungarian(matrix)
        for i,j in chosen:
"""
    new="""        chosen,best=_hungarian(matrix)
        # A legacy 60-part limit skipped ALL uniqueness checks in large
        # components, marking even a uniquely placed 200-part assembly
        # as UNCERTAIN. Certify only this sufficient mathematical condition:
        # every A is matched to a real B and every chosen edge is a row minimum.
        # Any alternative complete assignment must increase a changed row by
        # at least its row runner-up gap. Never guess ambiguous assignments.
        row_gaps=None
        if not audit and len(chosen)==len(aa) and all(
                j<len(bb) and (aa[i],bb[j]) in local for i,j in chosen):
            if all(matrix[i,j] <= float(np.min(matrix[i,:len(bb)]))+1e-10
                   for i,j in chosen):
                row_gaps={}
                for i,j in chosen:
                    second=min((float(value) for col,value in enumerate(matrix[i,:len(bb)])
                                if col!=j),default=float('inf'))
                    row_gaps[i]=max(0.,second-float(matrix[i,j]))
        for i,j in chosen:
"""
    if src.count(old)!=1:raise RuntimeError("Unexpected legacy assignment source")
    src=src.replace(old,new)
    old="""            if not audit:
                # Global optimum is exact; uniqueness is conservatively unverified.
                answer.append((aa[i],bb[j],True,None));continue
"""
    new="""            if not audit:
                if row_gaps is not None:
                    gap=row_gaps[i]
                    answer.append((aa[i],bb[j],gap<=margin,gap))
                else:
                    # Non-certifiable large assignments stay UNCERTAIN.
                    answer.append((aa[i],bb[j],True,None))
                continue
"""
    if src.count(old)!=1:raise RuntimeError("Unexpected uniqueness audit source")
    src=src.replace(old,new)
    compile(src,str(target),'exec')
    target.write_text(src,encoding='utf-8')
    print("DSCOMPARE_LARGE_ASSIGNMENT_PROOF_PASS",target)


if __name__=='__main__':
    if len(sys.argv)!=2:raise SystemExit("usage: patch_assignment_uniqueness.py DSAC/assignment.py")
    patch(sys.argv[1])
