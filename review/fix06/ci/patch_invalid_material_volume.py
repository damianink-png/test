"""Fail-closed native Cut volume diagnostics for re-export/world equality.

Applied AFTER existing native/session/material/surface patches, only to the
verified extracted Windows engine. Never repairs or approves invalid shapes.
"""
from pathlib import Path
import re
import sys

root=Path(sys.argv[1])
native=root/'dsac29/native_guard.py'
step=root/'dsac29/step_reexport_tolerance.py'
source=native.read_text(encoding='utf-8')
pattern=r'(?m)^def worker\(([^\n]*)\):'
found=re.findall(pattern,source)
if len(found)!=1:
    raise RuntimeError('Unexpected native worker signature; refusing unverified patch')
source,n=re.subn(pattern,lambda m: 'def _worker_unchecked('+m.group(1)+'):',source,count=1)
if n!=1 or source.count('def guarded_rigid(')!=1:
    raise RuntimeError('Unexpected native guard function boundaries')

wrapper='''def worker(request_path, result_path, *args, **kwargs):
    """Worker entry: publish a durable UNKNOWN result before a forced reset.

    PyInstaller must never open an uncaught Python exception dialog. The
    coordinator sees failure code 70, discards the native session and MUST NOT
    count this as a successful SAME or completed negative comparison.
    """
    try:
        return _worker_unchecked(request_path, result_path, *args, **kwargs)
    except Exception as exc:
        import traceback
        reply=Path(result_path)
        # The material worker already publishes an explicit fail-closed reply
        # before its real os._exit(70). Do not replace that reply in tests
        # where os._exit is deliberately patched to raise an exception.
        try:
            prior=json.loads(reply.read_text(encoding='utf-8'))
        except (OSError, UnicodeError, ValueError, TypeError):
            prior={}
        if isinstance(prior,dict) and prior.get('ok') is False:
            raise
        phase=reply.with_suffix('.phase')
        try:
            stage=phase.read_text(encoding='utf-8') if phase.exists() else 'unknown'
        except (OSError, UnicodeError):
            stage='unavailable'
        try:
            req=json.loads(Path(request_path).read_text(encoding='utf-8'))
        except (OSError, UnicodeError, ValueError, TypeError):
            req={}
        error=str(exc)
        code=('INVALID_MATERIAL_VOLUME' if 'invalid material volume' in error.lower()
              else 'NATIVE_PROOF_INCOMPLETE')
        payload={'ok':False,'status':'UNVERIFIED','error_code':code,
                 'error':type(exc).__name__+': '+error,
                 'operation':req.get('operation','unknown'),
                 'a':req.get('a'),'b':req.get('b'),
                 'stage':stage,'traceback':traceback.format_exc()[-5000:]}
        try:
            reply.parent.mkdir(parents=True,exist_ok=True)
            partial=reply.with_suffix('.unverified')
            partial.write_text(json.dumps(payload,ensure_ascii=False),encoding='utf-8')
            partial.replace(reply)
        except (OSError, TypeError):
            pass
        sys.stderr.write(code+': '+payload['error']+'; stage='+stage+'\\n')
        sys.stderr.flush()
        os._exit(70)


'''
source=source.replace('def guarded_rigid(',wrapper+'def guarded_rigid(')
old="""            detail=phase.read_text(encoding='utf-8') if phase.exists() else 'start procesu'
            raise NativeGeometryFailure(f'{exc}; etap: {detail}; A: {a.path}; B: {b.path}') from exc"""
new="""            detail=phase.read_text(encoding='utf-8') if phase.exists() else 'start procesu'
            # A child can publish a complete negative diagnostic then exit 70.
            # The session completion mailbox is intentionally never written.
            try:
                problem=json.loads(reply.read_text(encoding='utf-8'))
                if problem.get('ok') is False:
                    detail+='; '+str(problem.get('error_code','NATIVE_PROOF_INCOMPLETE'))
                    detail+='; '+str(problem.get('error',''))[:1800]
            except (OSError,ValueError,TypeError,AttributeError):
                pass
            raise NativeGeometryFailure(f'{exc}; etap: {detail}; A: {a.path}; B: {b.path}') from exc"""
if source.count(old)!=1:
    raise RuntimeError('Native parent error-propagation anchor changed')
source=source.replace(old,new)
compile(source,str(native),'exec')

s=step.read_text(encoding='utf-8')
marker='def _verified_difference_empty(a,b,tolerance):'
if s.count(marker)!=1:
    raise RuntimeError('Unexpected solid symmetric-difference verifier')
helper='''def _ds_checked_cut_volume(residual, direction, operation, tolerance, volume_fn=None):
    """Reject non-finite/signed residual volume with original diagnostic.

    Source B-Rep, validity, orientation, Cut stage and both directions are
    preserved. abs(value) and silent zero substitution are forbidden.
    """
    import math
    from OCP.GProp import GProp_GProps
    from OCP.BRepGProp import BRepGProp
    from .material_deltas import volume
    raw=None
    try:
        properties=GProp_GProps()
        BRepGProp.VolumeProperties_s(residual,properties)
        raw=float(properties.Mass())
    except Exception:
        pass
    try:
        measured=float((volume_fn or volume)(residual))
        if not math.isfinite(measured) or measured<0:
            raise ValueError('non-finite or negative residual volume: '+repr(measured))
    except Exception as exc:
        orientation=str(residual.Orientation()) if not residual.IsNull() else 'NULL'
        valid=shape_valid(residual)
        cut_done=bool(operation.IsDone())
        raise ValueError(
            'Invalid material volume: direction='+direction+
            '; raw='+repr(raw)+'; valid='+str(valid)+
            '; orientation='+orientation+'; CutDone='+str(cut_done)+
            '; tolerance='+repr(tolerance)+'; cause='+str(exc)
        ) from exc
    return measured


'''
s=s.replace(marker,helper+marker)
old='for first,second in ((a,b),(b,a)):'
if s.count(old)!=1:raise RuntimeError('Missing expected bidirectional Cut iteration')
s=s.replace(old,'for direction,(first,second) in zip(("A_minus_B","B_minus_A"),((a,b),(b,a))):')
old='if volume(residual)>tolerance**3:return False'
if s.count(old)!=1:raise RuntimeError('Unexpected Cut volume decision; refusing unsafe patch')
s=s.replace(old,'if _ds_checked_cut_volume(residual,direction,op,tolerance)>tolerance**3:return False')
compile(s,str(step),'exec')
native.write_text(source,encoding='utf-8')
step.write_text(s,encoding='utf-8')
print('INVALID_MATERIAL_VOLUME_FAILCLOSED_PATCH_PASS',flush=True)
