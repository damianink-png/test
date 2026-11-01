"""Scoped, recyclable world-proof worker. No result survives an analysis.

Only transport is reused. Each request reloads its own B-Rep and runs the same
proof. A crash, timeout or malformed answer aborts and destroys the worker.
"""
from contextlib import contextmanager
from contextvars import ContextVar
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

_current = ContextVar('dscompare_world_session', default=None)

def current():
    return _current.get()

class WorldSession:
    def __init__(self, max_requests=16):
        self.max_requests=max_requests
        self.process=None
        self.directory=None
        self.sequence=0
        self.starts=0

    def close(self, preserve_to=None):
        if self.process is not None:
            if self.process.poll() is None:
                self.process.terminate()
                try:self.process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    self.process.kill();self.process.wait()
            self.process=None
        if self.directory is not None:
            # The process has stopped: preserve its stable journal on failure
            # before deleting the session, without retargeting it to a request.
            if preserve_to is not None:
                import shutil
                source=Path(self.directory.name)/'_ETAPY_DIAGNOSTYKA.jsonl'
                try:
                    if source.is_file():
                        shutil.copyfile(source,Path(preserve_to)/'NATIVE_SESSION_DIAGNOSTYKA.jsonl')
                except OSError:pass
            self.directory.cleanup();self.directory=None

    def _start(self):
        self.close()
        self.directory=tempfile.TemporaryDirectory(prefix='dscompare_world_session_')
        root=Path(self.directory.name)
        request=root/'session.json'
        request.write_text(json.dumps({'operation':'world_session','directory':str(root)}),encoding='utf-8')
        argv=([sys.executable,'--native-brep-compare'] if getattr(sys,'frozen',False)
              else [sys.executable,'-m','dsac29.native_guard'])
        self.process=subprocess.Popen([*argv,str(request),str(root/'unused.json')],
            stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        self.sequence=0;self.starts+=1

    def execute(self, request, reply, timeout_s):
        from .native_guard import NativeGeometryFailure
        if self.process is None or self.sequence>=self.max_requests:
            self._start()
        # A dead worker is a failed proof, never an excuse to retry as SAME.
        if self.process.poll() is not None:
            code=self.process.returncode;self.close()
            raise NativeGeometryFailure(f'Awaria procesu weryfikacji STEP: {code}')
        self.sequence+=1
        root=Path(self.directory.name)
        # Each request is immutable and has its own mailbox filename.
        # Replacing a shared command.json races the Windows reader (WinError 5).
        completion=root/f'completed_{self.sequence:08d}.json'
        command=root/f'command_{self.sequence:08d}.json'
        partial=root/f'.command_{self.sequence:08d}.partial'
        try:
            partial.write_text(json.dumps({
                'sequence':self.sequence,'request':str(request),'reply':str(reply)
            }), encoding='utf-8')
            deadline=time.monotonic()+1.0
            while True:
                try:
                    partial.replace(command)
                    break
                except PermissionError as exc:
                    if time.monotonic()>=deadline:
                        raise NativeGeometryFailure(
                            'Nie mozna opublikowac polecenia B-Rep (WinError 5)'
                        ) from exc
                    time.sleep(.02)
        except BaseException:
            self.close(preserve_to=Path(request).parent)
            raise
        started=time.monotonic()
        try:
            while not completion.exists():
                code=self.process.poll()
                if code is not None:
                    raise NativeGeometryFailure(f'Awaria procesu weryfikacji STEP: {code}')
                if time.monotonic()-started>=timeout_s:
                    raise NativeGeometryFailure('Timeout odizolowanej weryfikacji STEP — analiza niekompletna')
                time.sleep(.01)
            # A reply can be published before the worker function returns.
            # Completion is separately committed only after ALL request I/O.
            try:
                done=json.loads(completion.read_text(encoding='utf-8'))
            except (OSError,ValueError) as exc:
                raise NativeGeometryFailure('Nieprawidlowe potwierdzenie zakonczenia B-Rep') from exc
            if not isinstance(done,dict) or type(done.get('sequence')) is not int or done['sequence']!=self.sequence or not Path(reply).is_file():
                raise NativeGeometryFailure('Niezgodne potwierdzenie zakonczenia B-Rep')
            if self.process.poll() is not None:
                raise NativeGeometryFailure('Proces weryfikacji STEP zakonczyl sie po publikacji odpowiedzi')
        except BaseException:
            self.close(preserve_to=Path(request).parent);raise

@contextmanager
def world_session(enabled=True):
    existing=current()
    if not enabled or existing is not None:
        yield existing
        return
    session=WorldSession();token=_current.set(session)
    try:yield session
    finally:
        _current.reset(token);session.close()

def serve(directory):
    from .native_guard import worker
    # Read each immutable command once, in strict sequence order.
    root=Path(directory);last=0
    while True:
        next_number=last+1
        command=root/f'command_{next_number:08d}.json'
        try:
            payload=json.loads(command.read_text(encoding='utf-8'))
        except FileNotFoundError:
            time.sleep(.01)
            continue
        except PermissionError:
            time.sleep(.02)
            continue
        if payload.get('sequence') != next_number:
            raise ValueError('Nieprawidlowa kolejnosc zadan B-Rep')
        # The outer world_session dispatch already initialized diagnostics
        # in this session directory. Its heartbeat must never retain a path
        # into a disposable per-request folder.
        worker(payload['request'],payload['reply'],initialize_trace=False)
        completion=root/f'completed_{next_number:08d}.json'
        partial=root/f'.completed_{next_number:08d}.partial'
        partial.write_text(json.dumps({'sequence':next_number}),encoding='utf-8')
        partial.replace(completion)
        last=next_number
