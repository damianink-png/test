"""Patch the exact RC9 ZIP extraction: retain repair provenance and 0.01 mm budget.

Fail on source mismatch instead of silently compiling stale geometry code.
"""
from pathlib import Path

root=Path(__file__).resolve().parents[1]/'dscompare_rc9_manual'
source=root/'dsac29'/'native_guard.py'
s=source.read_text(encoding='utf-8')
old="""        original_invalid=not is_valid(a_shape) or not is_valid(b_shape)
        if original_invalid:
            report('validate_copy_repair')
            validated_copy(a_shape,float(req['tolerance']))
            validated_copy(b_shape,float(req['tolerance']))
        report('describe_shapes')
        a = describe(a_shape, 'A', 'native-guard/A')
        b = describe(b_shape, 'B', 'native-guard/B')
        matched = bool(reexport_equivalent_world(
            a, b, float(req['tolerance']),
            allow_boolean=(bool(req.get('allow_boolean', False)) and not original_invalid),
            _repair_boundary_only=original_invalid,progress=report))"""
new="""        original_invalid=not is_valid(a_shape) or not is_valid(b_shape)
        proof_tolerance=float(req['tolerance'])
        if original_invalid:
            # validated_copy independently proves original->copy boundaries
            # within half of its input tolerance. Two such repairs plus the
            # final strict repaired-to-repaired proof fit the ORIGINAL budget:
            # 0.25t + 0.50t + 0.25t <= t.
            repair_tolerance=proof_tolerance/2.
            report('validate_copy_repair_A')
            a_shape,_=validated_copy(a_shape,repair_tolerance)
            report('validate_copy_repair_B')
            b_shape,_=validated_copy(b_shape,repair_tolerance)
            proof_tolerance/=2.
        report('describe_shapes')
        a = describe(a_shape, 'A', 'native-guard/A')
        b = describe(b_shape, 'B', 'native-guard/B')
        matched = bool(reexport_equivalent_world(
            a, b, proof_tolerance,
            allow_boolean=(bool(req.get('allow_boolean', False)) and not original_invalid),
            _repair_boundary_only=False,progress=report))"""
if s.count(old)!=1:raise RuntimeError('Native world proof source does not match audited RC9')
s=s.replace(old,new)
if s.count('def guarded_world_reexport(a, b, tolerance, *, timeout_s=35,')!=1:
    raise RuntimeError('Unexpected guarded_world_reexport timeout signature')
s=s.replace('def guarded_world_reexport(a, b, tolerance, *, timeout_s=35,',
            'def guarded_world_reexport(a, b, tolerance, *, timeout_s=90,')
if s.count('def guarded_common(shape_a, shape_b, tolerance, *, timeout_s=35,')!=1:
    raise RuntimeError('Unexpected guarded_common timeout signature')
s=s.replace('def guarded_common(shape_a, shape_b, tolerance, *, timeout_s=35,',
            'def guarded_common(shape_a, shape_b, tolerance, *, timeout_s=90,')
old="""        except subprocess.TimeoutExpired as exc:
            trace.mark('native_world', 'TIMEOUT',
                       seconds=round(time.monotonic()-started, 2))"""
new="""        except subprocess.TimeoutExpired as exc:
            _preserve_failure(root,'world')
            trace.mark('native_world', 'TIMEOUT',
                       seconds=round(time.monotonic()-started, 2))"""
if s.count(old)!=1:raise RuntimeError('Native timeout failure preservation mismatch')
s=s.replace(old,new)
source.write_text(s,encoding='utf-8')
rev=root/'dsac29'/'revision_overlap.py'
s=rev.read_text(encoding='utf-8')
if s.count('limit 35 s')!=2:raise RuntimeError('Unexpected revision progress messages')
rev.write_text(s.replace('limit 35 s','limit 90 s'),encoding='utf-8')
print('RC9 repaired B-Reps are used for final proof, with conserved tolerance budget.')
