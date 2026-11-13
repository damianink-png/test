"""Add isolated surface-only registration dispatch after baseline verification."""
from pathlib import Path
import sys
p=Path(sys.argv[1]);s=p.read_text(encoding='utf-8')
old="    if req.get('operation') == 'world_session':\n"
new="""    if req.get('operation') in ('registration_face_features','registration_face_proofs'):
        from .surface_registration import native_worker
        return native_worker(req,result_path)
"""+old
if s.count(old)!=1:raise RuntimeError('Native surface dispatch anchor changed')
s=s.replace(old,new)
old='allow_boolean=False, process_args=None):'
if s.count(old)!=1:raise RuntimeError('Native world API anchor changed')
s=s.replace(old,'allow_boolean=False, process_args=None, allow_solid_set_proof=False):')
old="            'allow_boolean': bool(allow_boolean),"
if s.count(old)!=1:raise RuntimeError('Native world request anchor changed')
s=s.replace(old,old+"\n            'allow_solid_set_proof': bool(allow_solid_set_proof),")
old='        response = dict(ok=True, match=matched)'
new="""        if not matched and bool(req.get('allow_solid_set_proof',False)) and not original_invalid:
            # STEP can split faces without changing the solid set. Only
            # validated originals and two empty native differences prove it.
            from .step_reexport_tolerance import _verified_difference_empty
            from OCP.TopExp import TopExp_Explorer
            from OCP.TopAbs import TopAbs_SOLID
            if TopExp_Explorer(a_shape,TopAbs_SOLID).More() and TopExp_Explorer(b_shape,TopAbs_SOLID).More():
                from .same_domain import equivalent as same_domain_equivalent
                try:
                    matched=same_domain_equivalent(a_shape,b_shape,proof_tolerance,progress=report)
                except (RuntimeError,ValueError):
                    # Optional normalization failure must retain the original
                    # solid-set proof, never become a positive result.
                    report('same_domain_normalization_unavailable')
                    matched=False
                if matched:
                    report('same_domain_boundary_proven')
                else:
                    report('validated_solid_symmetric_difference')
                    matched=bool(_verified_difference_empty(a_shape,b_shape,proof_tolerance))
                    report('solid_symmetric_difference_proven' if matched else 'solid_symmetric_difference_unproven')
        response = dict(ok=True, match=matched)"""
if s.count(old)!=1:raise RuntimeError('Native world response anchor changed')
s=s.replace(old,new)
old='def _worker_metrics(root):'
new="""def guarded_registered_world(a,b,tolerance,**kwargs):
    # Explicit opt-in for registration/verified-frame solid-set checks.
    return guarded_world_reexport(a,b,tolerance,allow_solid_set_proof=True,**kwargs)

"""+old
if s.count(old)!=1:raise RuntimeError('Native registered wrapper anchor changed')
s=s.replace(old,new)
old="        trace.mark('native_world', 'END', match=data['match'],\n                   seconds=round(time.monotonic()-started, 3))"
new="""        phase=reply.with_suffix('.phase')
        try:last_phase=phase.read_text(encoding='utf-8') if phase.exists() else 'unknown'
        except (OSError,UnicodeError):last_phase='unavailable'
        trace.mark('native_world', 'END', match=data['match'],phase=last_phase,
                   seconds=round(time.monotonic()-started, 3))"""
if s.count(old)!=1:raise RuntimeError('Native proof phase anchor changed')
p.write_text(s.replace(old,new),encoding='utf-8')
print('SURFACE_REGISTRATION_NATIVE_DISPATCH_PASS')
