"""Reuse import hints in isolated boundary checks and keep bounded proof traces."""
from pathlib import Path
import sys
p=Path(sys.argv[1])/'dsac29/native_guard.py';s=p.read_text()
def replace(old,new):
 global s
 if s.count(old)!=1:raise RuntimeError('Boundary patch anchor missing: '+old[:90])
 s=s.replace(old,new)
replace("    def report(phase):\n        Path(result_path).with_suffix('.phase').write_text(phase,encoding='utf-8')", "    proof_stages=[]\n    def report(phase):\n        if len(proof_stages)<128 and (not proof_stages or proof_stages[-1]!=phase):\n            proof_stages.append(phase)\n        Path(result_path).with_suffix('.phase').write_text(phase,encoding='utf-8')")
replace("        from .step_reexport_tolerance import reexport_equivalent_world\n", "        from .step_reexport_tolerance import reexport_equivalent_world\n        from .boundary_descriptor import describe_boundary\n        hints=req.get('boundary_properties') or {}\n")
replace("original_a=describe(a_shape,'A','native-guard/original-A')", "original_a=describe_boundary(a_shape,hints.get('a'))")
replace("original_b=describe(b_shape,'B','native-guard/original-B')", "original_b=describe_boundary(b_shape,hints.get('b'))")
replace("            a = describe(a_shape, 'A', 'native-guard/A')", "            a = describe_boundary(a_shape,None if original_invalid else hints.get('a'))")
replace("            b = describe(b_shape, 'B', 'native-guard/B')", "            b = describe_boundary(b_shape,None if original_invalid else hints.get('b'))")
replace("same_domain_equivalent(a_shape,b_shape,proof_tolerance,progress=report)","same_domain_equivalent(a_shape,b_shape,proof_tolerance,progress=report,properties=(a,b))")
replace("nurbs_boundary_equivalent(a_shape,b_shape,proof_tolerance,progress=report)","nurbs_boundary_equivalent(a_shape,b_shape,proof_tolerance,progress=report,properties=(a,b))")
replace("response = dict(ok=True, match=matched)","response = dict(ok=True, match=matched, proof_stages=proof_stages)")
replace("            'allow_solid_set_proof': bool(allow_solid_set_proof),", "            'allow_solid_set_proof': bool(allow_solid_set_proof),\n            'boundary_properties': {key: {'volume':getattr(part,'volume',None),'area':getattr(part,'area',None)} for key,part in (('a',a),('b',b))},")
replace("trace.mark('native_world', 'END', match=data['match'],phase=last_phase,", "trace.mark('native_world', 'END', match=data['match'],phase=last_phase,proof_stages=data.get('proof_stages',[]),")
replace("        Path(result_path).with_suffix('.phase').write_text(phase,encoding='utf-8')", "        stages_path=Path(result_path).with_suffix('.stages.json')\n        pending=stages_path.with_suffix('.tmp')\n        pending.write_text(json.dumps(proof_stages),encoding='utf-8')\n        pending.replace(stages_path)\n        Path(result_path).with_suffix('.phase').write_text(phase,encoding='utf-8')")
replace("        if proc.returncode != 0 or not reply.exists():", "        finally:\n            try:\n                stages=json.loads(reply.with_suffix('.stages.json').read_text(encoding='utf-8'))\n            except (OSError,ValueError):\n                stages=[]\n            trace.mark('native_world','PROOF_STAGES',proof_stages=stages if isinstance(stages,list) and all(isinstance(v,str) for v in stages) else [])\n        if proc.returncode != 0 or not reply.exists():")
compile(s,str(p),'exec');p.write_text(s)
print('BOUNDARY_DESCRIPTOR_REUSE_PATCH_PASS')
