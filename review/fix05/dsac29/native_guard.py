"""Crash-contained OCCT rigid equality for large assemblies.

The parent NEVER turns native crashes, timeouts or malformed replies into SAME.
Only a positive verdict from the unmodified equivalent_rigid B-Rep routine
may be used as an equality proof. Each invocation uses its own process so an
Open CASCADE access violation cannot terminate the comparison coordinator.
"""
from __future__ import annotations
import json, os, subprocess, sys, tempfile, time
from pathlib import Path


_negative_saved=0

class NativeGeometryFailure(RuntimeError):
    """Geometry comparison incomplete; caller must fail the whole comparison."""


def _preserve_failure(root,operation):
    if os.getenv('DSCOMPARE_SAVE_FAILED_BREP','0')!='1':return
    try:
        import shutil
        from . import trace_r22 as trace
        if trace._path is None:return
        destination=trace._path.parent/'FAILED_BREP'/operation
        destination.mkdir(parents=True,exist_ok=True)
        # Stop after the first failure of each operation; preserve exact bytes.
        if (destination/'request.json').exists():return
        for file in Path(root).iterdir():
            if file.is_file():shutil.copy2(file,destination/file.name)
    except OSError:pass



_active_capture_counter=0
_active_capture_lock=__import__('threading').Lock()

def _capture_active_world(root,a,b,tolerance):
    """Durably keep the last two world-proof requests for native crash analysis.

    Uses locked two-slot updates and already-serialized B-Rep bytes. This is
    evidence only; never returns a geometry verdict.
    """
    if os.getenv('DSCOMPARE_CAPTURE_ACTIVE_BREP','0')!='1':return
    from . import trace_r22 as trace
    if trace._path is None:return
    import shutil
    global _active_capture_counter
    # Keep both B-Rep files and their metadata as one synchronized snapshot.
    # Without this lock another thread could overwrite a slot midway and
    # leave a mismatched A/B pair in the crash evidence.
    with _active_capture_lock:
        _active_capture_counter += 1
        count = _active_capture_counter
        slot = count % 2
        destination = trace._path.parent / 'FAILED_BREP' / 'active_world'
        try:
            destination.mkdir(parents=True, exist_ok=True)
            # Keep the existing two-slot evidence format for CI readers.
            # Remove the completion marker before overwriting either input.
            marker = destination / f'slot{slot}.complete'
            marker.unlink(missing_ok=True)
            for name in ('A', 'B'):
                temporary = destination / f'.slot{slot}_{name}_{count}.partial'
                try:
                    shutil.copyfile(Path(root) / (name + '.brep'), temporary)
                    os.replace(temporary, destination / f'slot{slot}_{name}.brep')
                finally:
                    temporary.unlink(missing_ok=True)
            metadata = {'sequence': count, 'slot': slot,
                        'a_path': str(a.path), 'b_path': str(b.path),
                        'tolerance_mm': float(tolerance)}
            temporary = destination / f'.current_{count}.partial'
            try:
                temporary.write_text(json.dumps(metadata, ensure_ascii=False), encoding='utf-8')
                os.replace(temporary, destination / 'current.json')
            finally:
                temporary.unlink(missing_ok=True)
            marker.write_text(str(count), encoding='ascii')
        except (OSError, ValueError, TypeError, AttributeError) as exc:
            trace.mark('native_world_capture', 'ERROR', reason=str(exc), sequence=count)

def _load_brep(path):
    from .brep_transport import read_brep
    return read_brep(path)


def worker(request_path, result_path):
    """Dedicated EXE dispatch mode; no Qt and no export files are loaded."""
    req = json.loads(Path(request_path).read_text(encoding='utf-8'))
    from . import trace_r22 as trace
    trace.setup(Path(result_path).parent)
    from .geometry import describe, equivalent_rigid
    if req.get('operation') == 'material_regions':
        from .material_guard import worker as material_worker
        return material_worker(req,result_path)
    if req.get('operation') == 'world_session':
        from .native_session import serve
        return serve(req['directory'])
    def report(phase):
        Path(result_path).with_suffix('.phase').write_text(phase,encoding='utf-8')
    report('load_brep')
    a_shape = _load_brep(req['a'])
    b_shape = _load_brep(req['b'])
    if req.get('operation') == 'world_reexport':
        from .step_reexport_tolerance import reexport_equivalent_world
        from .brep_safety import is_valid,validated_copy
        valid_a=is_valid(a_shape)
        valid_b=is_valid(b_shape)
        original_invalid=not valid_a or not valid_b
        proof_tolerance=float(req['tolerance'])
        direct_same=False
        if not valid_a and not valid_b:
            # Serialized full world B-Rep identity is exact, including
            # location, topology, trims and geometric definitions. No
            # bbox, mass or volume heuristic and no tolerance relaxation.
            from .exact_brep_identity import identical_serialized_brep
            if identical_serialized_brep(Path(req['a']),Path(req['b'])):
                report('exact_invalid_world_brep_proven')
                direct_same=True
        if original_invalid and not direct_same:
            # Full original-oriented face AND trimming-wire identity is
            # sufficient for SAME even when a STEP re-export changes formal
            # validity on only one side. Every original surface and trim
            # must still pass; invalidity alone never establishes equality. No volume-only or bbox shortcut.
            # An unproven result falls through to copy-only repair.
            report('direct_invalid_pair_oriented_proof')
            original_a=describe(a_shape,'A','native-guard/original-A')
            original_b=describe(b_shape,'B','native-guard/original-B')
            direct_same=bool(reexport_equivalent_world(
                original_a,original_b,proof_tolerance,
                allow_boolean=False,_original_boundary_only=True,progress=report))
        if direct_same:
            report('direct_invalid_pair_proven')
            matched=True
        else:
            if original_invalid:
                # validated_copy proves original->copy within 0.25t per
                # side; final repaired-to-repaired proof uses 0.50t.
                repair_tolerance=proof_tolerance/2.
                from .brep_safety import UnprovenRepair
                try:
                    report('validate_copy_repair_A')
                    a_shape,_=validated_copy(a_shape,repair_tolerance,max_source_tolerance=proof_tolerance)
                    report('validate_copy_repair_B')
                    b_shape,_=validated_copy(b_shape,repair_tolerance,max_source_tolerance=proof_tolerance)
                except UnprovenRepair as exc:
                    # Fail BEFORE invalid OCCT objects unwind; otherwise
                    # native teardown can consume the entire 90-second cap.
                    # This is an INCOMPLETE proof, never a negative match.
                    error=f'UnprovenRepair: {exc}'
                    report('repair_rejected')
                    try:
                        Path(result_path).write_text(json.dumps(dict(ok=False,error=error)),encoding='utf-8')
                    except OSError:
                        pass  # Native failure remains authoritative even if diagnostic disk I/O fails.
                    sys.stderr.write(error+'\n')
                    sys.stderr.flush()
                    os._exit(70)
                proof_tolerance/=2.
            report('describe_shapes')
            a = describe(a_shape, 'A', 'native-guard/A')
            b = describe(b_shape, 'B', 'native-guard/B')
            matched = bool(reexport_equivalent_world(
                a, b, proof_tolerance,
                allow_boolean=(bool(req.get('allow_boolean', False)) and not original_invalid),
                _repair_boundary_only=False,progress=report))
        response = dict(ok=True, match=matched)
    elif req.get('operation') == 'common':
        from OCP.BRepAlgoAPI import BRepAlgoAPI_Common
        from .material_deltas import operate, volume
        report('common_analytic_probe')
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
                sys.stderr.write(error+'\n')
                sys.stderr.flush()
                os._exit(70)
        report('common_write')
        from .brep_transport import write_brep
        write_brep(common,req['common_shape'])
        report('common_volume')
        common_volume=float(volume(common))
        report('common_done')
        response = dict(ok=True, common_volume=common_volume)
    else:
        a = describe(a_shape, 'A', 'native-guard/A')
        b = describe(b_shape, 'B', 'native-guard/B')
        if req.get('operation') == 'registered_rigid':
            from .registered_rigid import prove_native_placement
            match,r,t=prove_native_placement(a,b,float(req['tolerance']))
            if not match:
                match,r,t=equivalent_rigid(a,b,float(req['tolerance']))
        else:
            match,r,t=equivalent_rigid(a,b,float(req['tolerance']))
        response = dict(ok=True, match=bool(match),
                        rotation=None if r is None else r.tolist(),
                        translation=None if t is None else t.tolist())
    target = Path(result_path)
    tmp = target.with_suffix('.partial')
    tmp.write_text(json.dumps(response),encoding='utf-8')
    tmp.replace(target)
    return 0


def guarded_rigid(a, b, tolerance, *, timeout_s=35, process_args=None, registered_reexport=False):
    """Serialized independent B-Rep check with a hard per-call timeout.

    The OCC shape data is passed via binary .brep files, not Python pickles.
    A child can crash without changing the source parts or recording a match.
    """
    import numpy as np
    from . import trace_r22 as trace
    started=time.monotonic()
    with tempfile.TemporaryDirectory(prefix='dscompare_rigid_') as td:
        root=Path(td)
        for name,part in (('A',a),('B',b)):
            from .brep_transport import write_brep
            write_brep(part.shape,root/(name+'.brep'))
        request=root/'request.json'; reply=root/'reply.json'
        request.write_text(json.dumps({'a':str(root/'A.brep'), 'b':str(root/'B.brep'),
                                       'operation':'registered_rigid' if registered_reexport else 'rigid',
                                       'tolerance':float(tolerance)}),encoding='utf-8')
        argv=process_args or ([sys.executable,'--native-brep-compare'] if getattr(sys,'frozen',False) else [sys.executable,'-m','dsac29.native_guard'])
        trace.mark('native_guard','BEGIN',timeout_s=timeout_s)
        try:
            result=subprocess.run([*argv,str(request),str(reply)],timeout=timeout_s,
                                  stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,check=False)
        except subprocess.TimeoutExpired as exc:
            _preserve_failure(root,'rigid')
            trace.mark('native_guard','TIMEOUT',seconds=round(time.monotonic()-started,2))
            raise NativeGeometryFailure('Przekroczono limit odizolowanego testu B-Rep '+str(timeout_s)+' s; analiza niekompletna') from exc
        if result.returncode!=0 or not reply.exists():
            _preserve_failure(root,'rigid')
            trace.mark('native_guard','CRASH',exit_code=result.returncode)
            err=(result.stderr or b'')[-700:].decode('utf-8',errors='replace')
            raise NativeGeometryFailure(f'Proces B-Rep zakończył się błędem {result.returncode}; {err}')
        try:
            data=json.loads(reply.read_text(encoding='utf-8'))
            if not isinstance(data.get('match'),bool) or data.get('ok') is not True:
                raise ValueError('Nieprawidłowy wynik child B-Rep')
            r=None if data.get('rotation') is None else np.asarray(data['rotation'],float)
            t=None if data.get('translation') is None else np.asarray(data['translation'],float)
            if data['match'] and (r is None or r.shape!=(3,3) or t is None or t.shape!=(3,) or not np.isfinite(r).all() or not np.isfinite(t).all()):
                raise ValueError('Nieprawidłowa transformacja testu B-Rep')
            if data['match'] and (not np.allclose(r.T@r,np.eye(3),rtol=0,atol=1e-9) or abs(np.linalg.det(r)-1.)>1e-9):
                raise ValueError('Transformacja B-Rep nie jest właściwym obrotem')
        except (OSError,ValueError,TypeError,KeyError) as exc:
            raise NativeGeometryFailure('Wynik procesu geometrycznego uszkodzony — brak rozstrzygnięcia') from exc
        trace.mark('native_guard','END',seconds=round(time.monotonic()-started,2),match=data['match'])
        return data['match'],r,t


if __name__ == '__main__':
    if len(sys.argv)!=3:raise SystemExit(2)
    raise SystemExit(worker(sys.argv[1],sys.argv[2]))


def guarded_common(shape_a, shape_b, tolerance, *, timeout_s=90, process_args=None):
    """Boolean Common in an isolated native process; return validated B-Rep shape.

    Any failed or slow native operation aborts the comparison. Returning zero
    intersection when a worker crashed would conceal real material changes.
    """
    from . import trace_r22 as trace
    with tempfile.TemporaryDirectory(prefix='dscompare_common_') as td:
        root=Path(td)
        for name,shape in (('A',shape_a),('B',shape_b)):
            from .brep_transport import write_brep
            write_brep(shape,root/(name+'.brep'))
        common=root/'common.brep'
        req=root/'request.json'; reply=root/'reply.json'
        req.write_text(json.dumps(dict(operation='common',a=str(root/'A.brep'),
            b=str(root/'B.brep'),common_shape=str(common),tolerance=float(tolerance))),encoding='utf-8')
        argv=process_args or ([sys.executable,'--native-brep-compare'] if getattr(sys,'frozen',False) else [sys.executable,'-m','dsac29.native_guard'])
        trace.mark('native_common','BEGIN',timeout_s=timeout_s)
        try:
            proc=subprocess.run([*argv,str(req),str(reply)],timeout=timeout_s,
                                stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,check=False)
        except subprocess.TimeoutExpired as exc:
            _preserve_failure(root,'common')
            trace.mark('native_common','TIMEOUT',timeout_s=timeout_s)
            raise NativeGeometryFailure('Timeout odizolowanej operacji Common — wynik rewizji niekompletny') from exc
        if proc.returncode!=0 or not reply.exists() or not common.exists():
            _preserve_failure(root,'common')
            trace.mark('native_common','CRASH',exit_code=proc.returncode)
            error=''
            if reply.exists():
                try:
                    payload=json.loads(reply.read_text(encoding='utf-8'))
                    if payload.get('ok') is False:
                        error=str(payload.get('error',''))[:2000]
                except (OSError,ValueError,TypeError):
                    pass
            raise NativeGeometryFailure('Odizolowany OCC Common zakończył się błędem '+str(proc.returncode)+' '+(error or proc.stderr.decode('utf8',errors='replace')[-2000:]))
        try:
            data=json.loads(reply.read_text(encoding='utf-8'))
            if data.get('ok') is not True or not isinstance(data.get('common_volume'),(int,float)):
                raise ValueError('Nieprawidłowa odpowiedź')
            import math
            if not math.isfinite(data['common_volume']) or data['common_volume']<0:
                raise ValueError('Invalid Common reply volume')
            result=_load_brep(common)
            from .material_deltas import volume
            if abs(volume(result)-float(data['common_volume']))>max(1.e-5,abs(data['common_volume'])*1.e-6):
                raise ValueError('Weryfikacja przekazanego kształtu Common nie powiodła się')
        except (ValueError,OSError,TypeError) as exc:
            raise NativeGeometryFailure('Nie udało się zweryfikować odizolowanego Common') from exc
        trace.mark('native_common','END',common_volume=data['common_volume'],native_operations=_worker_metrics(root))
        return result


def guarded_world_reexport(a, b, tolerance, *, timeout_s=90,
                           allow_boolean=False, process_args=None):
    """Subprocess-only B-Rep world equivalence proof for large STEP assemblies.

    A crash/timeout is always INCOMPLETE, never SAME, CHANGED or REMOVED.
    """
    from . import trace_r22 as trace
    if not 0 < float(tolerance) <= 1:
        raise ValueError('Invalid B-Rep tolerance')
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix='dscompare_world_') as td:
        root = Path(td)
        for name, part in (('A', a), ('B', b)):
            from .brep_transport import write_brep
            write_brep(part.shape,root/(name+'.brep'))
        request = root / 'request.json'
        reply = root / 'reply.json'
        request.write_text(json.dumps({
            'operation': 'world_reexport',
            'a': str(root / 'A.brep'),
            'b': str(root / 'B.brep'),
            'tolerance': float(tolerance),
            'allow_boolean': bool(allow_boolean),
        }), encoding='utf-8')
        # Save current B-Rep pair BEFORE a possible native access violation.
        _capture_active_world(root,a,b,tolerance)
        argv = process_args or (
            [sys.executable, '--native-brep-compare'] if getattr(sys, 'frozen', False)
            else [sys.executable, '-m', 'dsac29.native_guard'])
        trace.mark('native_world', 'BEGIN', timeout_s=timeout_s)
        try:
            from .native_session import current
            session = current() if process_args is None else None
            if session is not None:
                session.execute(request, reply, timeout_s)
                from types import SimpleNamespace
                proc = SimpleNamespace(returncode=0)
            else:
                proc = subprocess.run([*argv, str(request), str(reply)],
                    timeout=timeout_s, stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE, check=False)
        except subprocess.TimeoutExpired as exc:
            _preserve_failure(root,'world')
            trace.mark('native_world', 'TIMEOUT',
                       seconds=round(time.monotonic()-started, 2))
            raise NativeGeometryFailure(
                'Timeout odizolowanej weryfikacji STEP — analiza niekompletna; etap: '+
                (reply.with_suffix('.phase').read_text(encoding='utf-8') if reply.with_suffix('.phase').exists() else 'start procesu')) from exc
        except NativeGeometryFailure as exc:
            _preserve_failure(root,'world')
            phase=reply.with_suffix('.phase')
            detail=phase.read_text(encoding='utf-8') if phase.exists() else 'start procesu'
            raise NativeGeometryFailure(f'{exc}; etap: {detail}; A: {a.path}; B: {b.path}') from exc
        if proc.returncode != 0 or not reply.exists():
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
        try:
            data = json.loads(reply.read_text(encoding='utf-8'))
            if data.get('ok') is not True or type(data.get('match')) is not bool:
                raise ValueError('Invalid world equality response')
        except (ValueError, OSError, TypeError) as exc:
            raise NativeGeometryFailure(
                'Nieprawidłowy wynik weryfikacji STEP — analiza niekompletna') from exc
        trace.mark('native_world', 'END', match=data['match'],
                   seconds=round(time.monotonic()-started, 3))
        global _negative_saved
        if not data['match'] and os.getenv('DSCOMPARE_SAVE_FAILED_BREP','0')=='1' and _negative_saved<20:
            _negative_saved+=1
            _preserve_failure(root,f'world_negative_{_negative_saved:02d}')
        return data['match']

def _worker_metrics(root):
    try:
        entries=[json.loads(line) for line in (Path(root)/'_ETAPY_DIAGNOSTYKA.jsonl').read_text(encoding='utf8').splitlines()]
        return [entry for entry in entries if str(entry.get('stage','')).startswith('occt_') or entry.get('stage')=='brep_repair']
    except (OSError,ValueError):return []
