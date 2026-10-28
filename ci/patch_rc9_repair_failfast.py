"""Fail closed immediately when copy-only B-Rep repair is unprovable.

Some malformed STEP shapes hang in OCCT C++ destructor unwinding after
ShapeFix has already been rejected. Only the disposable isolated worker exits;
no SAME, changed-material verdict, or fabricated geometry is produced.
"""
from pathlib import Path
import ast
root=Path(__file__).resolve().parents[1]/'dscompare_rc9_manual'
p=root/'dsac29'/'native_guard.py'
s=p.read_text(encoding='utf-8')
old="""            if original_invalid:
                # validated_copy proves original->copy within 0.25t per
                # side; final repaired-to-repaired proof uses 0.50t.
                repair_tolerance=proof_tolerance/2.
                report('validate_copy_repair_A')
                a_shape,_=validated_copy(a_shape,repair_tolerance)
                report('validate_copy_repair_B')
                b_shape,_=validated_copy(b_shape,repair_tolerance)
                proof_tolerance/=2.
"""
new="""            if original_invalid:
                # validated_copy proves original->copy within 0.25t per
                # side; final repaired-to-repaired proof uses 0.50t.
                repair_tolerance=proof_tolerance/2.
                from .brep_safety import UnprovenRepair
                try:
                    report('validate_copy_repair_A')
                    a_shape,_=validated_copy(a_shape,repair_tolerance)
                    report('validate_copy_repair_B')
                    b_shape,_=validated_copy(b_shape,repair_tolerance)
                except UnprovenRepair as exc:
                    # Fail BEFORE invalid OCCT objects unwind; otherwise
                    # native teardown can consume the entire 90-second cap.
                    # This is an INCOMPLETE proof, never a negative match.
                    error=f'UnprovenRepair: {exc}'
                    report('repair_rejected')
                    Path(result_path).write_text(json.dumps(dict(ok=False,error=error)),encoding='utf-8')
                    sys.stderr.write(error+'\\n')
                    sys.stderr.flush()
                    os._exit(70)
                proof_tolerance/=2.
"""
if s.count(old)!=1:raise SystemExit(f'Unexpected repair worker anchor: {s.count(old)}')
s=s.replace(old,new)
old_parent="""        if proc.returncode != 0 or not reply.exists():
            trace.mark('native_world', 'CRASH', exit_code=proc.returncode)
            raise NativeGeometryFailure(
                'Awaria odizolowanej weryfikacji STEP: '+str(proc.returncode))
"""
new_parent="""        if proc.returncode != 0 or not reply.exists():
            _preserve_failure(root,'world')
            trace.mark('native_world', 'CRASH', exit_code=proc.returncode)
            detail=''
            if reply.exists():
                try:
                    response=json.loads(reply.read_text(encoding='utf-8'))
                    if response.get('ok') is False:
                        detail=str(response.get('error',''))[:2000]
                except (OSError,ValueError,TypeError):
                    pass
            raise NativeGeometryFailure(
                'Niekompletna weryfikacja STEP: '+str(proc.returncode)+
                (('; '+detail) if detail else ' (native crash without proof)'))
"""
if s.count(old_parent)!=1:raise SystemExit(f'Unexpected world parent anchor: {s.count(old_parent)}')
s=s.replace(old_parent,new_parent)
ast.parse(s)
p.write_text(s,encoding='utf-8')
print('RC9 rejected copy repairs now terminate isolated native worker without a false SAME')
