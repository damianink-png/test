"""Fast strict original-boundary proof for two invalid STEP B-Reps.

An invalid CAD solid can still be the exact same invalid boundary representation
on both sides. The existing parametric oriented face+trim proof is a full
geometric identity proof, not a bbox/volume/mesh heuristic. Run it before
expensive copy repair, but ONLY when BOTH originals are invalid.
Any inconclusive or false proof continues through the existing validated
copy repair and final reduced-tolerance proof. No Boolean or tolerance shortcut.
"""
from pathlib import Path
root=Path(__file__).resolve().parents[1]/'dscompare_rc9_manual'
path=root/'dsac29'/'native_guard.py'
s=path.read_text(encoding='utf-8')
old="""        original_invalid=not is_valid(a_shape) or not is_valid(b_shape)
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
new="""        valid_a=is_valid(a_shape)
        valid_b=is_valid(b_shape)
        original_invalid=not valid_a or not valid_b
        proof_tolerance=float(req['tolerance'])
        direct_same=False
        if not valid_a and not valid_b:
            # Full original-oriented face AND trimming-wire identity is
            # sufficient for SAME even when both imported solids have the
            # identical invalid topology. No volume-only or bbox shortcut.
            # An unproven result falls through to copy-only repair.
            report('direct_invalid_pair_oriented_proof')
            original_a=describe(a_shape,'A','native-guard/original-A')
            original_b=describe(b_shape,'B','native-guard/original-B')
            direct_same=bool(reexport_equivalent_world(
                original_a,original_b,proof_tolerance,
                allow_boolean=False,_repair_boundary_only=True,progress=report))
        if direct_same:
            report('direct_invalid_pair_proven')
            matched=True
        else:
            if original_invalid:
                # validated_copy proves original->copy within 0.25t per
                # side; final repaired-to-repaired proof uses 0.50t.
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
if s.count(old)!=1:
    raise RuntimeError(f'Expected exact audited native proof anchor once, found {s.count(old)}')
path.write_text(s.replace(old,new),encoding='utf-8')
print('Installed strict two-invalid-BRep original boundary fastpath')
