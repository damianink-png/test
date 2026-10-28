"""RC9: diagnose isolated Common and reject impossible signed volumes.

No tolerance, SAME, MOVED, or material classification is relaxed.
Applied to the extracted source before frozen Windows compilation.
"""
from pathlib import Path
root=Path(__file__).resolve().parents[1]/'dscompare_rc9_manual'

def replace_once(path,old,new):
    p=root/path
    source=p.read_text(encoding='utf-8')
    if source.count(old)!=1:
        raise RuntimeError(f'Unexpected RC9 source {p}: expected one exact anchor, got {source.count(old)}')
    p.write_text(source.replace(old,new),encoding='utf-8')

replace_once('dsac29/native_guard.py', """        common = operate(BRepAlgoAPI_Common,a_shape,b_shape,float(req['tolerance']))
        with Path(req['common_shape']).open('wb') as handle:
            BRepTools.Write_s(common,handle)
        response = dict(ok=True, common_volume=float(volume(common)))""", """        report('common_operate')
        common = operate(BRepAlgoAPI_Common,a_shape,b_shape,float(req['tolerance']))
        report('common_write')
        with Path(req['common_shape']).open('wb') as handle:
            BRepTools.Write_s(common,handle)
        report('common_volume')
        common_volume=float(volume(common))
        report('common_done')
        response = dict(ok=True, common_volume=common_volume)""")
replace_once('dsac29/material_deltas.py', """    if not op.IsDone():
        raise RuntimeError('OCCT Boolean did not complete')
    return _check_result(op.Shape())""", """    if not op.IsDone():
        raise RuntimeError('OCCT Boolean did not complete')
    result=op.Shape()
    # A negative signed intersection volume is impossible for two valid,
    # positive-volume solids. OCCT may return IsDone=True with malformed
    # Common topology; reject before a costly BRepCheck_Analyzer traversal.
    # Never convert an invalid intersection into a zero intersection.
    if klass is BRepAlgoAPI_Common:
        from OCP.BRepGProp import BRepGProp
        from OCP.GProp import GProp_GProps
        from . import trace_r22 as trace
        trace.mark('occt_common_output','VOLUME_BEGIN')
        properties=GProp_GProps()
        BRepGProp.VolumeProperties_s(result,properties)
        signed=float(properties.Mass())
        trace.mark('occt_common_output','VOLUME_END',signed_volume_mm3=signed)
        import math
        if not math.isfinite(signed) or signed < -max(1e-5,float(tolerance)**3):
            raise RuntimeError(f'OCCT Common returned impossible signed volume {signed:.9g} mm3; no valid material intersection')
    from . import trace_r22 as trace
    trace.mark('occt_boolean_result','VALIDATE_BEGIN')
    checked=_check_result(result)
    trace.mark('occt_boolean_result','VALIDATE_END')
    return checked""")
print('RC9 Common phase markers and fail-closed negative-volume preflight installed')
