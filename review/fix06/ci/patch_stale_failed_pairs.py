"""Reconcile failed speculative CAD matches against finally matched occurrences.

An incomplete test is never treated as a negative proof while both endpoints
remain unmatched. If one endpoint later receives a separately VERIFIED match,
that unsuccessful speculative pair cannot taint the remaining occurrence.
"""
from pathlib import Path
import sys


def patch(path):
    target=Path(path)
    source=target.read_text(encoding='utf-8')
    if 'failed_pairs=set()' in source and "revision_candidate_errors','RECONCILE" in source:
        print('DSCOMPARE_STALE_FAILED_PAIR_PATCH_ALREADY_APPLIED',target)
        return
    def one(old,new):
        nonlocal source
        if source.count(old)!=1:
            raise RuntimeError('Unexpected comparator source; refusing patch: '+old[:80])
        source=source.replace(old,new)
    one("    failed_a=set();failed_b=set()\n    failed_groups = set()",
        "    failed_a=set();failed_b=set()\n    # Errors are pair-local: a later independent positive match may invalidate\n    # the speculative candidate, but never an unproven pair still in play.\n    failed_pairs=set()\n    failed_groups = set()")
    one("                        failed_a.add(i);failed_b.add(j)\n                        if progress: progress(f'B-Rep test błędny {i}/{j}: {exc}')",
        "                        failed_a.add(i);failed_b.add(j);failed_pairs.add((i,j))\n                        if progress: progress(f'B-Rep test błędny {i}/{j}: {exc}')")
    one("                        failed_a.add(i);failed_b.add(j)\n                        if progress:progress(f'Test ustawienia {i}/{j}: {exc}')",
        "                        failed_a.add(i);failed_b.add(j);failed_pairs.add((i,j))\n                        if progress:progress(f'Test ustawienia {i}/{j}: {exc}')")
    one("    if revision_only:\n        trace.mark('revision_only_classification'",
        "    if revision_only:\n        # A failed candidate is irrelevant once EITHER endpoint was matched\n        # independently.  Only failure pairs with BOTH operands still free\n        # can keep either occurrence as UNCERTAIN.  No failed proof is reused.\n        stale_errors=sum(i not in free_a or j not in free_b for i,j in failed_pairs)\n        failed_a={i for i,j in failed_pairs if i in free_a and j in free_b}\n        failed_b={j for i,j in failed_pairs if i in free_a and j in free_b}\n        trace.mark('revision_candidate_errors','RECONCILE',stale_errors=stale_errors,unresolved_pair_errors=len(failed_pairs)-stale_errors)\n        trace.mark('revision_only_classification'")
    compile(source,str(target),'exec')
    target.write_text(source,encoding='utf-8')
    print('DSCOMPARE_STALE_FAILED_PAIR_PATCH_PASS',target)


if __name__=='__main__':
    if len(sys.argv)!=2:raise SystemExit('usage: patch_stale_failed_pairs.py ROOT/dsac29/compare.py')
    patch(sys.argv[1])
