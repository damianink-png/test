"""Explicit noninteractive diagnostic continuation for failed material pairs.

No default strict/interactive caller is changed. Diagnostic mode preserves
UNCERTAIN occurrences, never approves material evidence, and must fail audit.
"""
from pathlib import Path
import sys

def replace_once(s, old, new, path):
    count=s.count(old)
    if count!=1:
        raise RuntimeError(f'Refusing unsafe diagnostic patch for {path}: expected 1 anchor, got {count}: {old[:120]!r}')
    return s.replace(old,new,1)

def apply(root: Path):
    root=Path(root)
    rev=root/'dsac29'/'revision_overlap.py'
    cli=root/'dsac29'/'cli.py'
    s=rev.read_text(encoding='utf-8')
    s=replace_once(s,
      'def merge_material_revisions(a,b,records,tolerance=0.01,progress=None,cancelled=None,review_approval=None,geometry_context=None):',
      'def merge_material_revisions(a,b,records,tolerance=0.01,progress=None,cancelled=None,review_approval=None,geometry_context=None,diagnostic_only=False):',rev)
    s=replace_once(s,
      '        recover_failures=review_approval is not None)',
      '        recover_failures=(review_approval is not None or diagnostic_only))',rev)
    s=replace_once(s,
      "    if not stat.get('incomplete'):\n        return result,regions,stat\n    proposal=",
      "    if not stat.get('incomplete'):\n        return result,regions,stat\n    if diagnostic_only:\n        # No user consent is inferred. This is incomplete diagnostic output, never PASS.\n        stat['diagnostic_only']=True\n        trace.mark('revision_overlap_guard','INCOMPLETE_DIAGNOSTIC',**stat)\n        if progress:progress('DIAGNOSTIC_ONLY_INCOMPLETE: niezbadane pary UNCERTAIN; nie jest to zatwierdzony raport.')\n        return result,regions,stat\n    proposal=",rev)
    compile(s,str(rev),'exec')
    t=cli.read_text(encoding='utf-8')
    t=replace_once(t,
      'alignment_approval=None,force_unrelated=False,material_approval=None):',
      'alignment_approval=None,force_unrelated=False,material_approval=None,diagnostic_only=False):',cli)
    t=replace_once(t,
      'review_approval=material_approval,geometry_context=geometry_context)',
      'review_approval=material_approval,geometry_context=geometry_context,diagnostic_only=diagnostic_only)',cli)
    compile(t,str(cli),'exec')
    rev.write_text(s,encoding='utf-8')
    cli.write_text(t,encoding='utf-8')
    print('TRIDENT_DIAGNOSTIC_CONTINUATION_PATCH_PASS',flush=True)

if __name__=='__main__':
    if len(sys.argv)!=2:raise SystemExit('usage: patch_trident_diagnostic_continuation.py <engine root>')
    apply(Path(sys.argv[1]))
