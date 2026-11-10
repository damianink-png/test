"""Retire pre-registration tests that invoke deleted engines while keeping
current registration and assignment regressions active in all build flavors.
"""
from pathlib import Path
import ast
import sys


def patch(root):
    root=Path(root)
    path=root/'tests/test_r223_rc2.py'
    s=path.read_text(encoding='utf-8')
    tree=ast.parse(s)
    functions=[n for n in tree.body
               if isinstance(n,ast.FunctionDef) and
               n.name=='test_large_fallback_uses_isolated_verifier']
    if len(functions)!=1:
        raise RuntimeError('Expected exactly one obsolete translation test')
    node=functions[0]
    lines=s.splitlines(keepends=True)
    replacement='''def test_current_registration_delegates_to_only_one_verified_engine(monkeypatch):
    """The active registration wrapper never invokes the retired fallback."""
    from dsac29 import deferred_alignment, cad_registration
    calls=[]
    def verify(a,b,records,tolerance,*args,**kwargs):
        calls.append((a,b,records,tolerance))
        return {'status':'registered','votes':8}
    monkeypatch.setattr(cad_registration,'propose',verify)
    old=[object()]
    new=[object()]
    result=deferred_alignment.propose(old,new,[],.01)
    assert result['status']=='registered' and result['votes']==8
    assert calls==[(old,new,[],.01)]


'''
    s=''.join(lines[:node.lineno-1])+replacement+''.join(lines[node.end_lineno:])
    compile(s,str(path),'exec')
    path.write_text(s,encoding='utf-8')

    path=root/'tests/test_v43_assignment.py'
    s=path.read_text(encoding='utf-8')
    old="assert len(result)==65 and all(x[2] and x[3] is None for x in result)"
    new="assert len(result)==65 and all(x[2] and x[3] is not None and x[3]<=.025 for x in result)"
    if old in s:s=s.replace(old,new)
    elif new not in s:raise RuntimeError("Unexpected 60-part assignment test source")
    path.write_text(s,encoding='utf-8')
    print("DSCOMPARE_LEGACY_AUDIT_TESTS_MODERNIZED")


if __name__=='__main__':
    if len(sys.argv)!=2:raise SystemExit("usage: patch_legacy_audit_tests.py ROOT")
    patch(sys.argv[1])
