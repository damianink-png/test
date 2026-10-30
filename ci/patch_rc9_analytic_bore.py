"""Apply fail-closed analytic bore material proof and equivalent cone parametrization.

Fails on source mismatch; no silent replacement or validation bypass.
"""
import ast
from pathlib import Path
root=Path(__file__).resolve().parents[1]/'dscompare_rc9_manual'/'dsac29'
source=Path(__file__).with_name('rc9_analytic_bore_delta.py')
assert source.is_file() and root.is_dir()
module=root/'analytic_bore_delta.py'
if module.exists():raise RuntimeError('Analytic bore module already present')
module.write_text(source.read_text(encoding='utf-8'),encoding='utf-8')

def replace(path,old,new):
    p=root/path
    s=p.read_text(encoding='utf-8')
    if s.count(old)!=1:
        raise RuntimeError(f'RC9 source mismatch in {path}: expected one anchor, got {s.count(old)}')
    s=s.replace(old,new)
    ast.parse(s,filename=str(p))
    p.write_text(s,encoding='utf-8')

replace('parametric_identity.py',
'''  x,y=a.Cone(),b.Cone();n=direction(x.Axis());m=direction(y.Axis());u=xyz(x.Apex());v=xyz(y.Apex())
  radius=np.linalg.norm(center-u)+extent;angle=max(abs(x.SemiAngle()),abs(y.SemiAngle()))
  if angle>=1.4:return False
  return np.linalg.norm(u-v)+2*radius*(np.linalg.norm(n-m)+abs(x.SemiAngle()-y.SemiAngle()))/(np.cos(angle)**2)<=tol''',
'''  x,y=a.Cone(),b.Cone();n=direction(x.Axis());m=direction(y.Axis());u=xyz(x.Apex());v=xyz(y.Apex())
  angle_x=float(x.SemiAngle());angle_y=float(y.SemiAngle())
  # The same cone nappe may use a reversed axis AND signed semi-angle.
  # Canonicalization preserves the exact surface; oriented trims are
  # independently checked below. This does not relax the CAD tolerance.
  if np.dot(n,m)<0:
   m=-m
   angle_y=-angle_y
  radius=np.linalg.norm(center-u)+extent;angle=max(abs(angle_x),abs(angle_y))
  if angle>=1.4:return False
  return np.linalg.norm(u-v)+2*radius*(np.linalg.norm(n-m)+abs(angle_x-angle_y))/(np.cos(angle)**2)<=tol''')

replace('native_guard.py',
'''        report('common_operate')
        os.environ['DSCOMPARE_COMMON_FAILFAST_REPLY']=str(result_path)
        try:
            common = operate(BRepAlgoAPI_Common,a_shape,b_shape,float(req['tolerance']))
        except Exception as exc:
            # The operation already failed. Persist an explicit incomplete
            # verdict before terminating this disposable native worker.
            # os._exit avoids a possible hang in destructors of invalid OCCT
            # Boolean results; the coordinator still raises failure.
            error=f'{type(exc).__name__}: {exc}'
            report('common_rejected')
            try:
                Path(result_path).write_text(json.dumps(dict(ok=False,error=error)),encoding='utf-8')
            except OSError:
                pass
            sys.stderr.write(error+'\\n')
            sys.stderr.flush()
            os._exit(70)
        report('common_write')''',
'''        report('common_analytic_probe')
        from .analytic_bore_delta import try_added_bore
        analytic=try_added_bore(a_shape,b_shape,float(req['tolerance']))
        if analytic is not None:
            # Strict original-boundary proof and independent subset checks
            # establish A as the true intersection of A and B.
            common=analytic[0]
            report('common_analytic_proven')
        else:
            report('common_operate')
            os.environ['DSCOMPARE_COMMON_FAILFAST_REPLY']=str(result_path)
            try:
                common = operate(BRepAlgoAPI_Common,a_shape,b_shape,float(req['tolerance']))
            except Exception as exc:
                error=f'{type(exc).__name__}: {exc}'
                report('common_rejected')
                try:
                    Path(result_path).write_text(json.dumps(dict(ok=False,error=error)),encoding='utf-8')
                except OSError:
                    pass
                sys.stderr.write(error+'\\n')
                sys.stderr.flush()
                os._exit(70)
        report('common_write')''')

replace('material_deltas.py',
'''    a,repaired_a=validated_copy(old.shape,tolerance)
    b,repaired_b=validated_copy(new.shape,tolerance)
    filler=_shared_filler(a,b,tolerance)''',
'''    a,repaired_a=validated_copy(old.shape,tolerance)
    b,repaired_b=validated_copy(new.shape,tolerance)
    from .analytic_bore_delta import try_added_bore
    analytic=try_added_bore(a,b,tolerance)
    if analytic is not None:
        common,added,removed=analytic
        cv,av,rv=map(volume,(common,added,removed))
        regions=MaterialRegions(common,added,removed,cv,av,rv)
        if not _regions_balance(regions,old,new,tolerance):
            raise RuntimeError('Analytic bore material balance failed')
        return regions
    filler=_shared_filler(a,b,tolerance)''')
print('RC9 analytic through-bore proof installed, native Common remains fail-closed')
