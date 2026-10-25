"""Bounded reuse of isolated OCC Common subprocesses (never reuse a proof)."""
import sys
from pathlib import Path
root=Path(sys.argv[1])
overlap=root/'dsac29/revision_overlap.py'
guard=root/'dsac29/native_guard.py'
s=overlap.read_text(encoding='utf-8')
old='def merge_material_revisions(a,b,records,tolerance=0.01,progress=None,cancelled=None):'
new='''def merge_material_revisions(a,b,records,tolerance=0.01,progress=None,cancelled=None):
    # Recycle ONLY the isolated transport process; every Common result is
    # independently computed from B-Rep inputs and validated before use.
    # A failed/slow child aborts rather than producing a false match.
    from .native_session import world_session
    with world_session(enabled=max(len(a),len(b))>=600):
        return _merge_material_revisions(a,b,records,tolerance,progress,cancelled)


def _merge_material_revisions(a,b,records,tolerance=0.01,progress=None,cancelled=None):'''
assert s.count(old)==1
s=s.replace(old,new)
overlap.write_text(s,encoding='utf-8')
s=guard.read_text(encoding='utf-8')
old='''        try:
            proc=subprocess.run([*argv,str(req),str(reply)],timeout=timeout_s,
                                stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,check=False)
        except subprocess.TimeoutExpired as exc:
            _preserve_failure(root,'common')
            trace.mark('native_common','TIMEOUT',timeout_s=timeout_s)
            raise NativeGeometryFailure('Timeout odizolowanej operacji Common — wynik rewizji niekompletny') from exc
        if proc.returncode!=0 or not reply.exists() or not common.exists():'''
new='''        try:
            from .native_session import current
            session=current() if process_args is None else None
            if session is not None:
                session.execute(req,reply,timeout_s)
                from types import SimpleNamespace
                proc=SimpleNamespace(returncode=0)
            else:
                proc=subprocess.run([*argv,str(req),str(reply)],timeout=timeout_s,
                                    stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,check=False)
        except (subprocess.TimeoutExpired, NativeGeometryFailure) as exc:
            _preserve_failure(root,'common')
            trace.mark('native_common','TIMEOUT_OR_CRASH',timeout_s=timeout_s,error=str(exc)[:220])
            raise NativeGeometryFailure('Nieukończona odizolowana operacja Common — wynik rewizji niekompletny') from exc
        if proc.returncode!=0 or not reply.exists() or not common.exists():'''
assert s.count(old)==1
s=s.replace(old,new)
guard.write_text(s,encoding='utf-8')
print('RC7 session patch applied: bounded child reuse for OCC Common; no change to timeout or geometry rules')
