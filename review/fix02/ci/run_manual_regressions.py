import os,sys,subprocess
from pathlib import Path
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
import TESTUJ
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
small=['test_stability.py','test_efficient.py','test_robust_translation.py','test_face_candidates.py','test_safe_boolean_worker.py','test_occt_integration.py','test_manual_audit.py','test_manual_preview_audit.py',
       'test_ui_polish.py','test_output_palette.py','test_frame_proof_cache.py','test_step_boundary_proof.py',
       'test_revision_common_recovery.py','test_shift_user_results.py',
       'test_registered_centroid_reexport.py','test_fractional_shift_topology.py']
for names,report in [(small,'integration.xml'),(TESTUJ.tests,'full-regressions.xml')]:
 try:
  run=subprocess.run([sys.executable,'-m','pytest','-vv','--junitxml='+report,*[str(root/'tests'/n) for n in names]],cwd=root,timeout=1800)
 except subprocess.TimeoutExpired:
  print('INCOMPLETE: aggregate regression timeout',file=sys.stderr);raise SystemExit(2)
 if run.returncode:raise SystemExit(run.returncode)
run=subprocess.run([sys.executable,'-m','pytest','-q','--junitxml=ci-regressions.xml',
                    str(root/'ci'),'--ignore='+str(root/'ci/test_rc9_original_boundary.py')],cwd=root,timeout=240)
raise SystemExit(run.returncode)
