"""Isolated, optional pair-wise STEP import for DS Compare R11.8.

Open CASCADE STEP readers and XCAF documents never share a Python process.
A native BREP compound + small metadata JSON is the IPC representation.
Failure always returns to the established serial import, never silently drops solids.
"""
from __future__ import annotations

import ctypes
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from time import perf_counter

import numpy as np

from .geometry import SolidInfo


def _free_memory_bytes():
    """Conservative, dependency-free available RAM estimate."""
    if sys.platform == 'win32':
        from ctypes import wintypes
        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [('dwLength', wintypes.DWORD), ('dwMemoryLoad', wintypes.DWORD),
                        ('ullTotalPhys', ctypes.c_ulonglong), ('ullAvailPhys', ctypes.c_ulonglong),
                        ('ullTotalPageFile', ctypes.c_ulonglong), ('ullAvailPageFile', ctypes.c_ulonglong),
                        ('ullTotalVirtual', ctypes.c_ulonglong), ('ullAvailVirtual', ctypes.c_ulonglong),
                        ('ullAvailExtendedVirtual', ctypes.c_ulonglong)]
        state = MEMORYSTATUSEX()
        state.dwLength = ctypes.sizeof(state)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(state)):
            return int(state.ullAvailPhys)
    elif sys.platform.startswith('linux'):
        try:
            for line in Path('/proc/meminfo').read_text().splitlines():
                if line.startswith('MemAvailable:'):
                    return int(line.split()[1]) * 1024
        except OSError:
            pass
    return None


def should_parallel(a_path, b_path):
    mode = os.environ.get('DSCOMPARE_PARALLEL_IMPORT', 'auto').strip().lower()
    if mode in ('off', '0', 'false', 'nie'):
        return False, 'tryb wyłączony'
    if mode not in ('auto', 'on', '1', 'true'):
        mode = 'auto'
    a, b = Path(a_path), Path(b_path)
    sizes = a.stat().st_size, b.stat().st_size
    if mode == 'auto':
        # For tiny files process startup + native BREP transfer costs more than saved STEP time.
        if max(sizes) < 8 * 1024**2:
            return False, 'małe pliki STEP — import sekwencyjny jest zwykle szybszy'
        ram = _free_memory_bytes()
        if ram is None:
            return False, 'brak wiarygodnej informacji o dostępnej pamięci RAM'
        if ram < max(2 * 1024**3, 8 * sum(sizes)):
            return False, 'za mało wolnej pamięci RAM na dwa importery'
    return True, 'dwa niezależne procesy Open CASCADE'


def write_cache(path, solids, diagnostics):
    """Write every exact native shape in occurrence order, preserving BREP sharing."""
    from OCP.BRep import BRep_Builder
    from OCP.BRepTools import BRepTools
    from OCP.TopoDS import TopoDS_Compound
    folder = Path(path)
    folder.mkdir(parents=True, exist_ok=True)
    builder = BRep_Builder()
    compound = TopoDS_Compound()
    builder.MakeCompound(compound)
    metadata = []
    for item in solids:
        builder.Add(compound, item.shape)
        metadata.append(dict(name=item.name, path=item.path, volume=item.volume, area=item.area,
                             center=item.center.tolist(), inertia=item.inertia.tolist(),
                             eigenvalues=item.eigenvalues.tolist(), axes=item.axes.tolist(),
                             bbox=list(item.bbox), source=item.source, name_origin=item.name_origin,
                             step_definition_key=getattr(item,'step_definition_key',None)))
    if not BRepTools.Write_s(compound, str(folder / 'shapes.brep')):
        raise RuntimeError('Nie udało się zapisać pośredniego BREP')
    (folder / 'shapes.json').write_text(json.dumps({'schema': 2, 'solids': metadata,
                                                       'diagnostics': diagnostics}, ensure_ascii=False), encoding='utf-8')


def read_cache(path):
    from OCP.BRep import BRep_Builder
    from OCP.BRepTools import BRepTools
    from OCP.TopoDS import TopoDS_Shape, TopoDS_Iterator
    from OCP.TopAbs import TopAbs_SOLID
    folder = Path(path)
    meta = json.loads((folder / 'shapes.json').read_text(encoding='utf-8'))
    if meta.get('schema') != 2:
        raise RuntimeError('Nieobsługiwana wersja bufora BREP')
    compound = TopoDS_Shape()
    if not BRepTools.Read_s(compound, str(folder / 'shapes.brep'), BRep_Builder()):
        raise RuntimeError('Błąd odczytu pośredniego BREP')
    it = TopoDS_Iterator(compound, True, True)
    solids = []
    for item in meta['solids']:
        if not it.More():
            raise RuntimeError('BRAK BRYŁ: niespójna liczba elementów bufora BREP')
        shape = it.Value()
        if shape.IsNull() or shape.ShapeType() != TopAbs_SOLID:
            raise RuntimeError('Nieprawidłowa bryła w buforze BREP')
        solids.append(SolidInfo(shape=shape, name=item['name'], path=item['path'],
                                volume=float(item['volume']), area=float(item['area']),
                                center=np.asarray(item['center'], dtype=float),
                                inertia=np.asarray(item['inertia'], dtype=float),
                                eigenvalues=np.asarray(item['eigenvalues'], dtype=float),
                                axes=np.asarray(item['axes'], dtype=float),
                                bbox=tuple(item['bbox']), source=item['source'],
                                name_origin=item['name_origin']))
        identity=item.get('step_definition_key')
        if identity is not None:
            if (not isinstance(identity,list) or len(identity)!=3
                    or not all(isinstance(x,str) and x for x in identity[:2])
                    or type(identity[2]) is not int or identity[2]<1):
                raise ValueError('Nieprawidłowa tożsamość definicji XCAF w buforze')
            solids[-1].step_definition_key=tuple(identity)
        it.Next()
    if it.More() or not solids:
        raise RuntimeError('Niespójna liczba brył — bezpieczny powrót do importu sekwencyjnego')
    return solids, meta['diagnostics']


def import_worker(input_path, folder, max_solids, progress=None, source_proof=None):
    """Entry point for --worker import; persistent exact cache before STEP read."""
    from .step_io import load_step
    from .import_cache import cache_key, try_load, publish
    before = perf_counter()
    diagnostics = {}
    source_proof=source_proof or {}
    key = cache_key(input_path,source_sha256=source_proof.get("sha256"),source_stat=source_proof.get("stat"))
    solids = try_load(input_path, max_solids, progress, diagnostics, precomputed=key)
    cache_hit = solids is not None
    if not cache_hit:
        def sampled_progress(message):
            from re import search
            match = search(r'wczytano (\d+) brył', str(message))
            if progress and (not match or int(match.group(1)) % 100 == 0):
                progress(message)
        solids = load_step(input_path, progress=sampled_progress, diagnostics=diagnostics, max_solids=max_solids)
    import_s = perf_counter() - before
    write_cache(folder, solids, diagnostics)
    if not cache_hit and key:
        publish(input_path, solids, diagnostics, prepared_folder=folder, precomputed=key)
        diagnostics['persistent_cache'] = 'MISS'
    (Path(folder) / 'import_timing.json').write_text(json.dumps({'import_s': import_s,
                'count': len(solids), 'persistent_cache': 'HIT' if cache_hit else 'MISS'}), encoding='utf-8')


def _worker_command(input_path, cache_folder, max_solids, source_proof=None):
    proof_args=['--source-proof',json.dumps(source_proof)] if source_proof else []
    if getattr(sys, 'frozen', False):
        return [sys.executable, '--worker', 'import', '--input', str(input_path),
                '--output', str(cache_folder), '--max-solids', str(max_solids)]+proof_args
    # During tests and local source runs launch through the same entry script as GUI.
    script = Path(__file__).resolve().parents[1] / 'DSCompareV3.py'
    return [sys.executable, str(script), '--worker', 'import', '--input', str(input_path),
            '--output', str(cache_folder), '--max-solids', str(max_solids)]+proof_args


def load_pair(a_path, b_path, output, max_solids=20000, progress=None, cancelled=None, source_proofs=None, timeout_s=None):
    """Return (A, B, diagnostics, per-file import time, wall time).

    Raises on worker or cache failures so caller can retry with the proven serial loader.
    """
    import math
    timeout_s=float(timeout_s if timeout_s is not None else os.environ.get('DSCOMPARE_IMPORT_TIMEOUT_S','1800'))
    if not math.isfinite(timeout_s) or timeout_s<=0:
        raise ValueError('Limit czasu importu musi być dodatni i skończony.')
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    # Native BRep cache can be substantially larger than the STEP input.
    # Insufficient disk space must not corrupt the comparison folder.
    step_bytes = Path(a_path).stat().st_size + Path(b_path).stat().st_size
    if shutil.disk_usage(output).free < max(512 * 1024**2, 6 * step_bytes):
        raise RuntimeError('Zbyt mało wolnego miejsca na pośrednie pliki BREP')
    with tempfile.TemporaryDirectory(prefix='DSCompare_import_', dir=str(output)) as tmp:
        tmp = Path(tmp)
        running = []
        began = perf_counter()
        try:
            for role, path in (('A', a_path), ('B', b_path)):
                cache = tmp / role
                cache.mkdir()
                log = (cache / 'worker.log').open('w', encoding='utf-8')
                try:
                    command=(_worker_command(path,cache,max_solids,source_proofs[role])
                             if source_proofs and role in source_proofs else _worker_command(path,cache,max_solids))
                    proc = subprocess.Popen(command,
                                            stdout=log, stderr=subprocess.STDOUT,
                                            stdin=subprocess.DEVNULL)
                except BaseException:
                    log.close()
                    raise
                running.append((role, proc, cache, log))
            if progress:
                progress('Import równoległy: model A i B otwierane jednocześnie (oddzielne procesy).')
            positions = {'A': 0, 'B': 0}
            while any(proc.poll() is None for _, proc, _, _ in running):
                if perf_counter()-began>=timeout_s:
                    raise TimeoutError(f'Import przekroczył limit {timeout_s:g} s. Przerwano procesy importerów; nie opublikowano wyniku.')
                if cancelled and callable(cancelled) and cancelled():
                    raise InterruptedError('Import anulowany przez użytkownika')
                for role, proc, cache, _ in running:
                    events = cache / '_POSTEP_V37.jsonl'
                    if events.exists() and progress:
                        with events.open('r', encoding='utf-8', errors='replace') as event_stream:
                            event_stream.seek(positions[role])
                            for row in event_stream:
                                try:
                                    message = json.loads(row).get('tekst', '')
                                    if message:
                                        progress(f'Model {role}: {message}')
                                except ValueError:
                                    pass
                            positions[role] = event_stream.tell()
                if any(proc.poll() not in (None, 0) for _, proc, _, _ in running):
                    raise RuntimeError('Jeden z procesów importu zakończył się niepowodzeniem')
                time.sleep(0.15)
            wall = perf_counter() - began
            for role, proc, cache, log in running:
                log.close()
                if proc.returncode:
                    message = (cache / 'worker.log').read_text(encoding='utf-8', errors='replace')[-2000:]
                    result = cache / '_WYNIK_V37.json'
                    if result.exists():
                        try:
                            payload=json.loads(result.read_text(encoding='utf-8'))
                            message = str(payload.get('error', message))[-2000:]
                        except (OSError, ValueError):
                            pass
                    raise RuntimeError(f'Importer {role} zakończył się błędem {proc.returncode}: {message}')
            (a, da), (b, db) = (read_cache(tmp / 'A'), read_cache(tmp / 'B'))
            ta = json.loads((tmp / 'A' / 'import_timing.json').read_text(encoding='utf-8'))['import_s']
            tb = json.loads((tmp / 'B' / 'import_timing.json').read_text(encoding='utf-8'))['import_s']
            total = perf_counter() - began
            if progress:
                progress(f'Import równoległy zakończony: A {len(a)} brył ({ta:.1f} s), B {len(b)} brył ({tb:.1f} s); wraz z odczytem BREP {total:.1f} s.')
            return a, b, {'A': da, 'B': db}, {'A': ta, 'B': tb}, total
        finally:
            for _, proc, _, log in running:
                if proc.poll() is None:
                    proc.terminate()
                    try:proc.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                        proc.wait()
                if not log.closed:
                    log.close()
