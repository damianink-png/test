"""R22.3 crash-guard overlay on top of the exact R22.2 SAFE RC1 ZIP.
Fail closed if upstream code layout changes; never silently omit a fix.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent
def patch(filename, replacements, append=""):
    path = ROOT / filename
    old = path.read_text(encoding="utf-8")
    new = old
    for before, after in replacements:
        occurrences = new.count(before)
        if occurrences != 1:
            raise RuntimeError(f"Patch mismatch {filename}: expected once, got {occurrences}: {before[:90]}")
        new = new.replace(before, after, 1)
    if append:
        if "def guarded_world_reexport(" in new:
            raise RuntimeError("guarded_world_reexport already defined")
        new += append
    path.write_text(new, encoding="utf-8")
    print("R22.3 patched:", filename)

patch("dsac29/native_guard.py", [
    ("    if req.get('operation') == 'common':", """    if req.get('operation') == 'world_reexport':
        from .step_reexport_tolerance import reexport_equivalent_world
        a = describe(a_shape, 'A', 'native-guard/A')
        b = describe(b_shape, 'B', 'native-guard/B')
        matched = bool(reexport_equivalent_world(
            a, b, float(req['tolerance']),
            allow_boolean=bool(req.get('allow_boolean', False))))
        response = dict(ok=True, match=matched)
    elif req.get('operation') == 'common':""")
], append='''

def guarded_world_reexport(a, b, tolerance, *, timeout_s=35,
                           allow_boolean=False, process_args=None):
    """Subprocess-only B-Rep world equivalence proof for large STEP assemblies.

    A crash/timeout is always INCOMPLETE, never SAME, CHANGED or REMOVED.
    """
    from OCP.BRepTools import BRepTools
    from . import trace_r22 as trace
    if not 0 < float(tolerance) <= 1:
        raise ValueError('Invalid B-Rep tolerance')
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix='dscompare_world_') as td:
        root = Path(td)
        for name, part in (('A', a), ('B', b)):
            with (root / (name + '.brep')).open('wb') as handle:
                BRepTools.Write_s(part.shape, handle)
        request = root / 'request.json'
        reply = root / 'reply.json'
        request.write_text(json.dumps({
            'operation': 'world_reexport',
            'a': str(root / 'A.brep'),
            'b': str(root / 'B.brep'),
            'tolerance': float(tolerance),
            'allow_boolean': bool(allow_boolean),
        }), encoding='utf-8')
        argv = process_args or (
            [sys.executable, '--native-brep-compare'] if getattr(sys, 'frozen', False)
            else [sys.executable, '-m', 'dsac29.native_guard'])
        trace.mark('native_world', 'BEGIN', timeout_s=timeout_s)
        try:
            proc = subprocess.run([*argv, str(request), str(reply)],
                timeout=timeout_s, stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE, check=False)
        except subprocess.TimeoutExpired as exc:
            trace.mark('native_world', 'TIMEOUT',
                       seconds=round(time.monotonic()-started, 2))
            raise NativeGeometryFailure(
                'Timeout odizolowanej weryfikacji STEP — analiza niekompletna') from exc
        if proc.returncode != 0 or not reply.exists():
            trace.mark('native_world', 'CRASH', exit_code=proc.returncode)
            raise NativeGeometryFailure(
                'Awaria odizolowanej weryfikacji STEP: '+str(proc.returncode))
        try:
            data = json.loads(reply.read_text(encoding='utf-8'))
            if data.get('ok') is not True or type(data.get('match')) is not bool:
                raise ValueError('Invalid world equality response')
        except (ValueError, OSError, TypeError) as exc:
            raise NativeGeometryFailure(
                'Nieprawidłowy wynik weryfikacji STEP — analiza niekompletna') from exc
        trace.mark('native_world', 'END', match=data['match'],
                   seconds=round(time.monotonic()-started, 3))
        return data['match']
''')

patch("dsac29/registration_gate.py", [
    (" from .compare import _relative_location_is_same,Cancelled",
     " from .compare import _relative_location_is_same,_location_matrix,Cancelled\n from . import native_guard"),
    ("""  same=trace.brep_call('verify_reexport',i,j,reexport_equivalent_world,left,right,tolerance,allow_boolean=False)
  if not same:same=trace.brep_call('verify_world',i,j,equivalent_world,left,right,tolerance)""",
     """  # Exact local B-Rep equality and equal CAD placement are full proof.
  # Numerical descriptors and names by themselves are never proof.
  same=bool(registry.same_definition(left,right) and
      np.allclose(_location_matrix(left),_location_matrix(right),rtol=0,atol=1e-8))
  if not same:
   if max(len(a),len(b))>=600:
    # Crash-prone OCCT face/edge comparison MUST run in a child process.
    same=trace.brep_call('verify_reexport_guarded',i,j,
        native_guard.guarded_world_reexport,left,right,tolerance,allow_boolean=False)
   else:
    same=trace.brep_call('verify_reexport',i,j,
        reexport_equivalent_world,left,right,tolerance,allow_boolean=False)
    if not same:same=trace.brep_call('verify_world',i,j,equivalent_world,left,right,tolerance)""")
])

patch("dsac29/compare.py", [
    ("from .native_guard import NativeGeometryFailure\n\n\nclass Cancelled",
     "from .native_guard import NativeGeometryFailure,guarded_world_reexport\n\n\nclass Cancelled"),
    ("same=trace.brep_call('reexport_world',i,j,reexport_equivalent_world,s,b[j],tolerance)",
     "same=trace.brep_call('reexport_world',i,j,(guarded_world_reexport if len(a)>=600 and step_reexport_tolerance else reexport_equivalent_world),s,b[j],tolerance)"),
    ("same=trace.brep_call('reexport_world_fallback',i,j,reexport_equivalent_world,s,b[j],tolerance)",
     "same=trace.brep_call('reexport_world_fallback',i,j,(guarded_world_reexport if len(a)>=600 else reexport_equivalent_world),s,b[j],tolerance)")
])
