"""Localize native worker failures to uncertain pairs, never false SAME/REMOVED."""
from pathlib import Path
import sys

def apply(path):
    s=path.read_text(encoding='utf-8')
    patches=[
        (
            "    failed_a=set();failed_b=set()\n    failed_groups = set()\n",
            "    failed_a=set();failed_b=set()\n    failed_world_groups=set()\n    failed_rigid_groups=set()\n    failed_groups = set()\n"
        ),
        (
            "                else:\n                    if checks >= max_checks: raise RuntimeError(f'Limit testów B-Rep ({max_checks}) — analiza niekompletna')\n",
            "                elif (gs,gt) in failed_world_groups:\n                    # Do not retry the same unproven definition for every occurrence.\n                    failed_a.add(i);failed_b.add(j);memo_hits+=1\n                    continue\n                else:\n                    if checks >= max_checks: raise RuntimeError(f'Limit testów B-Rep ({max_checks}) — analiza niekompletna')\n"
        ),
        (
            "                    except NativeGeometryFailure:\n                        raise\n                    except Exception as exc:\n                        failed_a.add(i);failed_b.add(j)\n                        if progress: progress(f'B-Rep test błędny {i}/{j}: {exc}')\n                        continue\n",
            "                    except NativeGeometryFailure as exc:\n                        failed_a.add(i);failed_b.add(j)\n                        failed_world_groups.add((gs,gt))\n                        if progress: progress(f'NIEZWERYFIKOWANA para world {i}/{j}: {exc}')\n                        continue\n                    except Exception as exc:\n                        failed_a.add(i);failed_b.add(j)\n                        if progress: progress(f'B-Rep test błędny {i}/{j}: {exc}')\n                        continue\n"
        ),
        (
            "                elif pair in failed_groups:\n                    match=False;memo_hits+=1\n",
            "                elif pair in failed_groups:\n                    match=False;memo_hits+=1\n                    if pair in failed_rigid_groups:\n                        failed_a.add(i);failed_b.add(j)\n"
        ),
        (
            "                    except NativeGeometryFailure:\n                        raise\n                    except Exception as exc:\n                        failed_a.add(i);failed_b.add(j)\n                        if progress:progress(f'Test ustawienia {i}/{j}: {exc}')\n                        continue\n",
            "                    except NativeGeometryFailure as exc:\n                        # Exhausting the global native budget remains fatal.\n                        if 'Budżet izolowanych' in str(exc):\n                            raise\n                        failed_a.add(i);failed_b.add(j)\n                        failed_groups.add(pair)\n                        failed_rigid_groups.add(pair)\n                        if progress:progress(f'NIEZWERYFIKOWANA para rigid {i}/{j}: {exc}')\n                        continue\n                    except Exception as exc:\n                        failed_a.add(i);failed_b.add(j)\n                        if progress:progress(f'Test ustawienia {i}/{j}: {exc}')\n                        continue\n"
        ),
    ]
    for before,after in patches:
        if s.count(before)!=1:
            raise RuntimeError('Refusing patch: unexpected compare.py source: '+before[:80])
        s=s.replace(before,after,1)
    compile(s,str(path),'exec')
    path.write_text(s,encoding='utf-8')
    print('TRIDENT_NATIVE_PAIR_FAILURE_ISOLATION_PATCH_PASS')

if __name__=='__main__':
    if len(sys.argv)!=2:
        raise SystemExit('usage: patch_trident_native_failures.py <compare.py>')
    apply(Path(sys.argv[1]))
