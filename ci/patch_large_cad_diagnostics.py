"""Capture real failure evidence from the frozen EXE in all six large CAD tests.

Keep full worker stdout/stderr and preserve diagnostic journals on failures.
No tolerance, matching, alignment or classification rule is changed.
"""
from pathlib import Path

root=Path(__file__).resolve().parents[1]/'dscompare_rc9_manual'/'ci'
for filename in ('large_exe.py','real_revision_without_shift.py'):
    path=root/filename
    src=path.read_text(encoding='utf-8')
    if filename=='large_exe.py':
        old="start=time.monotonic();proc=subprocess.Popen(cmd)"
        new="""start=time.monotonic()
 stdout_path=root/'EXE_STDOUT.log'
 stderr_path=root/'EXE_STDERR.log'
 stdout_handle=open(stdout_path,'wb')
 stderr_handle=open(stderr_path,'wb')
 proc=subprocess.Popen(cmd,stdout=stdout_handle,stderr=stderr_handle)"""
        src=src.replace(old,new)
        old="result.update(seconds=round(time.monotonic()-start,2),exit_code=proc.returncode,decisions=responses);save()"
        new="""stdout_handle.close();stderr_handle.close()
 result.update(seconds=round(time.monotonic()-start,2),exit_code=proc.returncode,decisions=responses);save()
 if proc.returncode!=0:
  for name in ('EXE_STDOUT.log','EXE_STDERR.log'):
   p=root/name
   if p.exists():print('DIAGNOSTIC '+name+': '+p.read_text(encoding='utf-8',errors='replace')[-15000:],flush=True)"""
        src=src.replace(old,new)
    else:
        old="proc=subprocess.Popen(args)"
        new="""stdout_handle=open(root/'EXE_STDOUT.log','wb')
    stderr_handle=open(root/'EXE_STDERR.log','wb')
    proc=subprocess.Popen(args,stdout=stdout_handle,stderr=stderr_handle)"""
        src=src.replace(old,new)
        old='report["returncode"]=proc.returncode'
        new="""stdout_handle.close()
    stderr_handle.close()
    report["returncode"]=proc.returncode
    if proc.returncode!=0:
        for name in ('EXE_STDOUT.log','EXE_STDERR.log'):
            p=root/name
            if p.exists():print('DIAGNOSTIC '+name+': '+p.read_text(encoding='utf-8',errors='replace')[-15000:],flush=True)"""
        src=src.replace(old,new)
    if src==path.read_text(encoding='utf-8'):
        raise RuntimeError('No changes in '+filename)
    path.write_text(src,encoding='utf-8')
    print('Instrumented '+filename)
