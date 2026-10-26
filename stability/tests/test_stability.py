import os, subprocess, sys, time
from pathlib import Path
import pytest
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from dsac29.geometry import describe
from dsac29.material_guard import calculate_isolated
from dsac29.native_guard import NativeGeometryFailure

def parts():
    return [describe(BRepPrimAPI_MakeBox(n,10,10).Shape(),'plate','root') for n in (20,25)]

def test_material_proof():
    r=calculate_isolated(*parts())
    assert abs(r.common_mm3-2000)<.001
    assert abs(r.added_mm3-500)<.001
    assert r.removed_mm3<.001

@pytest.mark.parametrize('code',["import time;time.sleep(20)","raise SystemExit(23)","import pathlib,sys;pathlib.Path(sys.argv[2]).write_text('{}')"])
def test_incomplete_never_returns_material(code):
    with pytest.raises(NativeGeometryFailure):
        calculate_isolated(*parts(),timeout_s=.5,process_args=[sys.executable,'-c',code])

def test_small_overlap_is_guarded(monkeypatch):
    import dsac29.native_guard as ng
    from dsac29.revision_overlap import merge_material_revisions
    from dsac29.compare import Record
    def fail(*args,**kwargs):raise NativeGeometryFailure('injected timeout')
    monkeypatch.setattr(ng,'guarded_common',fail)
    a,b=parts()
    with pytest.raises(NativeGeometryFailure):
        merge_material_revisions([a],[b],[Record(0,None,'REMOVED',''),Record(None,0,'ADDED','')])

@pytest.mark.skipif(os.name!='nt',reason='Windows Job Object integration')
def test_descendant_exits_when_parent_killed(tmp_path):
    pidfile=tmp_path/'pid'
    code="from dsac29.process_lifetime import contain_children; contain_children(); import subprocess,sys,time,pathlib; p=subprocess.Popen([sys.executable,'-c','import time;time.sleep(90)']); pathlib.Path(sys.argv[1]).write_text(str(p.pid)); time.sleep(90)"
    p=subprocess.Popen([sys.executable,'-c',code,str(pidfile)])
    import ctypes
    from ctypes import wintypes as w
    k=ctypes.WinDLL('kernel32',use_last_error=True)
    k.OpenProcess.argtypes=[w.DWORD,w.BOOL,w.DWORD];k.OpenProcess.restype=w.HANDLE
    k.WaitForSingleObject.argtypes=[w.HANDLE,w.DWORD];k.CloseHandle.argtypes=[w.HANDLE]
    child=None
    try:
        deadline=time.monotonic()+15
        while not pidfile.exists() and time.monotonic()<deadline:time.sleep(.1)
        assert pidfile.exists()
        child=k.OpenProcess(0x100000,False,int(pidfile.read_text()))
        assert child
        p.kill();p.wait(timeout=5)
        assert k.WaitForSingleObject(child,5000)==0
    finally:
        if p.poll() is None:p.kill();p.wait()
        if child:k.CloseHandle(child)
