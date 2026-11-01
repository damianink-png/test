"""Crash-resistant DS Compare diagnostic journal.

Records durable BEFORE/AFTER markers; positive geometry matches are NEVER
inferred from diagnostics. Intentionally stdlib-only for frozen Windows EXE.
"""
from __future__ import annotations
from contextlib import contextmanager
from datetime import datetime,timezone
from pathlib import Path
import faulthandler,json,os,sys,time,threading,tempfile

_path=None
_enabled=False
_pair_enabled=False
_lock=threading.RLock()
_start=time.perf_counter()
_brep_count=0
_fault_log=None
_last_stage=None
_last_event=None
_heartbeat_started=False

def memory_mib():
    """Current/peak resident memory, as available for the host platform."""
    if sys.platform=='win32':
        try:
            import ctypes
            from ctypes import wintypes
            SIZE=ctypes.c_size_t
            class PMC(ctypes.Structure):
                _fields_=[('cb',wintypes.DWORD),('PageFaultCount',wintypes.DWORD),
                    ('PeakWorkingSetSize',SIZE),('WorkingSetSize',SIZE),
                    ('QuotaPeakPagedPoolUsage',SIZE),('QuotaPagedPoolUsage',SIZE),
                    ('QuotaPeakNonPagedPoolUsage',SIZE),('QuotaNonPagedPoolUsage',SIZE),
                    ('PagefileUsage',SIZE),('PeakPagefileUsage',SIZE),('PrivateUsage',SIZE)]
            info=PMC();info.cb=ctypes.sizeof(info)
            api=ctypes.WinDLL('psapi');api.GetProcessMemoryInfo.argtypes=[ctypes.c_void_p,ctypes.c_void_p,wintypes.DWORD]
            api.GetProcessMemoryInfo.restype=wintypes.BOOL
            kernel=ctypes.WinDLL('kernel32');kernel.GetCurrentProcess.restype=ctypes.c_void_p
            if api.GetProcessMemoryInfo(kernel.GetCurrentProcess(),ctypes.byref(info),info.cb):
                return round(info.WorkingSetSize/1048576,2),round(info.PeakWorkingSetSize/1048576,2)
        except Exception:pass
    try:
        with open('/proc/self/status',encoding='utf-8') as f:
            d={x.partition(':')[0]:x.partition(':')[2].strip().split()[0] for x in f if x.startswith(('VmRSS:','VmHWM:'))}
        return round(int(d.get('VmRSS','0'))/1024,2),round(int(d.get('VmHWM','0'))/1024,2)
    except (OSError,ValueError):return None,None

def setup(output):
    """Open a separate faulthandler file; never rely on Python try/except for native crashes."""
    global _path,_enabled,_pair_enabled,_fault_log,_start,_brep_count,_heartbeat_started
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    _path=output/'_ETAPY_DIAGNOSTYKA.jsonl'
    _start=time.perf_counter();_brep_count=0
    _enabled=True
    _pair_enabled=os.getenv('DSCOMPARE_TRACE_BREP','1')=='1'
    try:
        # Keep the live Windows handle outside disposable output/test folders.
        # A running worker may outlive the session and lock TemporaryDirectory.
        if os.name == 'nt':
            from datetime import datetime
            diagnostic_dir = Path(os.environ.get('LOCALAPPDATA') or tempfile.gettempdir()) / 'DSCompare' / 'logs'
            diagnostic_dir.mkdir(parents=True, exist_ok=True)
            fault_path = diagnostic_dir / ('AWARIA_PYTHON_FAULTHANDLER_%s_%s.txt' %
                                           (os.getpid(), datetime.now().strftime('%Y%m%d_%H%M%S_%f')))
        else:
            fault_path = output / 'AWARIA_PYTHON_FAULTHANDLER.txt'
        _fault_log=open(fault_path,'a',encoding='utf-8',buffering=1)
        faulthandler.enable(file=_fault_log,all_threads=True)
        # A native hang may never raise Python exception; dump current stacks every 180s.
        faulthandler.dump_traceback_later(180,repeat=True,file=_fault_log)
    except (OSError,RuntimeError,ValueError):pass
    mark('worker','BEGIN',trace_brep=_pair_enabled)
    if not _heartbeat_started:
        _heartbeat_started=True
        def heartbeat():
            while True:
                time.sleep(15)
                try:mark('heartbeat','ALIVE',active_stage=_last_stage,last_event=_last_event)
                except Exception:pass
        threading.Thread(target=heartbeat,name='DSCompare-Diagnostics-Heartbeat',daemon=True).start()

def mark(stage,event,**metadata):
    if not _enabled or _path is None:return
    global _last_stage,_last_event
    with _lock:
        if stage!='heartbeat':
            _last_stage=str(stage);_last_event=str(event)
        rss,peak=memory_mib()
        record={'utc':datetime.now(timezone.utc).isoformat(timespec='milliseconds'),
                'elapsed_s':round(time.perf_counter()-_start,3),'pid':os.getpid(),
                'stage':str(stage),'event':str(event),
                'rss_mib':rss,'peak_rss_mib':peak,'brep_calls':_brep_count}
        record.update(metadata)
        data=(json.dumps(record,ensure_ascii=False,default=str)+'\n').encode('utf-8')
        try:
            fd=os.open(str(_path),os.O_WRONLY|os.O_APPEND|os.O_CREAT,0o644)
            try:
                os.write(fd,data)
                os.fsync(fd)
            finally:os.close(fd)
        except OSError:
            # A logging failure must never change matching semantics.
            pass

@contextmanager
def phase(stage,**metadata):
    mark(stage,'BEGIN',**metadata)
    t=time.perf_counter()
    try:
        yield
    except BaseException as exc:
        mark(stage,'ERROR',elapsed_stage_s=round(time.perf_counter()-t,3),error=repr(exc))
        raise
    else:
        mark(stage,'END',elapsed_stage_s=round(time.perf_counter()-t,3))

def brep_call(stage,i,j,func,*args,**kwargs):
    """Trace a potentially unsafe native call without changing its outcome."""
    global _brep_count
    if not _enabled:return func(*args,**kwargs)
    with _lock:_brep_count+=1;number=_brep_count
    start=time.perf_counter()
    if _pair_enabled:mark(stage,'PAIR_BEGIN',a_id=i,b_id=j,call=number)
    try:answer=func(*args,**kwargs)
    except BaseException as exc:
        mark(stage,'PAIR_ERROR',a_id=i,b_id=j,call=number,
             duration_s=round(time.perf_counter()-start,3),error=repr(exc))
        raise
    if _pair_enabled:mark(stage,'PAIR_END',a_id=i,b_id=j,call=number,
                           duration_s=round(time.perf_counter()-start,3),result=(bool(answer[0]) if isinstance(answer,tuple) and isinstance(answer[0],(bool,int,float)) else (answer if isinstance(answer,(bool,int,float)) else None)))
    return answer
