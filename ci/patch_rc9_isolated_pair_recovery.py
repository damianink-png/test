"""Fail-closed, pair-local recovery for isolated OCCT failures."""
from pathlib import Path
import ast
root=Path(__file__).resolve().parents[1]/'dscompare_rc9_manual'/'dsac29'
changes={
 'compare.py': [(
"""                    except NativeGeometryFailure:
                        raise
                    except Exception as exc:
                        failed_a.add(i);failed_b.add(j)""",
"""                    except NativeGeometryFailure as exc:
                        failed_a.add(i);failed_b.add(j)
                        if progress:progress(f'Niezweryfikowana para B-Rep {i}/{j}: {exc}')
                        continue
                    except Exception as exc:
                        failed_a.add(i);failed_b.add(j)""")],
 'revision_overlap.py': [(
"""            except NativeGeometryFailure:
                raise
            except Exception as exc:
                raise NativeGeometryFailure('Niekompletna analiza wspólnego materiału: '+str(exc)) from exc
            score=_score(common,ref,b[j],_name_eq(ref,b[j]))""",
"""            except NativeGeometryFailure as exc:
                stat['invalid_boolean']+=1
                if progress:progress(f'Common A[{i}] / B[{j}] niezweryfikowany: {exc}')
                continue
            except Exception as exc:
                stat['invalid_boolean']+=1
                if progress:progress(f'Common A[{i}] / B[{j}] błąd: {exc}')
                continue
            score=_score(common,ref,b[j],_name_eq(ref,b[j]))""")]
}
for name,edits in changes.items():
 p=root/name;s=p.read_text(encoding='utf-8')
 for old,new in edits:
  if old not in s:raise SystemExit('Missing safety anchor in '+name)
  s=s.replace(old,new,1)
 ast.parse(s)
 p.write_text(s,encoding='utf-8')
 print('Conservative pair recovery:',name)
