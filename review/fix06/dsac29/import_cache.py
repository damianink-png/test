"""Persistent exact B-Rep import cache, separate from per-run temporary B-Rep transfer.

A hit is authorized by SHA-256 of entire source STEP + OCCT version + schema.
Never treat size, mtime, path, filename or numeric properties as a proof of
content equality. All native TopoDS shapes and numeric properties are preserved.
Failures are cache misses, never comparison failures.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
import time

SCHEMA = 'dscompare-step-occt-v2-xcaf-definitions'
MIN_BYTES = 2 * 1024**2
MAX_CACHE_BYTES = 3 * 1024**3


def mode():
    value = os.environ.get('DSCOMPARE_IMPORT_CACHE', 'off').strip().lower()
    return value if value in ('off', 'auto', 'on') else 'off'


def root_dir():
    custom = os.environ.get('DSCOMPARE_CACHE_DIR', '').strip()
    if custom:
        return Path(custom).expanduser().resolve()
    base = Path(os.environ.get('LOCALAPPDATA', '')) if os.name == 'nt' else Path.home()/'.cache'
    if not str(base).strip() or str(base) == '.':
        base = Path.home()/'.cache'
    return base/'DSCompare'/'geometry_cache_v1'


def _occt_version():
    try:
        from OCP.Standard import Standard_Version_s
        return str(Standard_Version_s())
    except (ImportError, AttributeError):
        from importlib.metadata import version, PackageNotFoundError
        try:return 'cadquery-ocp-' + version('cadquery-ocp')
        except PackageNotFoundError:
            import OCP
            return 'OCP-' + str(getattr(OCP,'__version__','unknown'))


def _key(path, progress=None, source_sha256=None, source_stat=None):
    src = Path(path)
    if not src.is_file():
        return None
    size = src.stat().st_size
    if mode() == 'off' or (mode() == 'auto' and size < MIN_BYTES):
        return None
    before = src.stat()
    proof=(before.st_size,before.st_mtime_ns)
    if (isinstance(source_sha256,str) and len(source_sha256)==64 and
            all(ch in '0123456789abcdef' for ch in source_sha256.lower()) and
            source_stat is not None and tuple(source_stat)==proof):
        digest=source_sha256.lower()
        after=src.stat()
        if (after.st_size,after.st_mtime_ns)!=proof:return None
    else:
        h = hashlib.sha256()
        with src.open('rb') as input_file:
            for block in iter(lambda: input_file.read(4*1024**2), b''):
                h.update(block)
        after = src.stat()
        if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
            return None
        digest=h.hexdigest()
    key = hashlib.sha256((SCHEMA + '\0' + _occt_version() + '\0' + digest).encode()).hexdigest()
    return key, digest, after.st_size


def cache_key(path, source_sha256=None, source_stat=None):
    """Stable content identifier; None for disabled or tiny files."""
    try:
        return _key(path, source_sha256=source_sha256, source_stat=source_stat)
    except (OSError, ValueError):
        return None


def try_load(path, max_solids, progress=None, diagnostics=None, precomputed=None):
    key = precomputed if precomputed is not None else cache_key(path)
    if not key:
        return None
    folder = root_dir()/key[0][:2]/key[0]
    if not (folder/'READY.json').is_file():
        return None
    try:
        saved = json.loads((folder/'READY.json').read_text('utf-8'))
        if saved.get('schema') != SCHEMA or saved.get('source_sha256') != key[1] or saved.get('size') != key[2]:
            return None
        if saved.get('count', 0) > max_solids:
            raise ValueError(f'Limit bezpieczenstwa: {max_solids} bryl na plik')
        from .parallel_import import read_cache
        solids, cached_diagnostics = read_cache(folder)
        if len(solids) != saved['count']:
            raise ValueError('Inconsistent persisted solid count')
        for solid in solids:
            solid.source = str(Path(path))
        if diagnostics is not None:
            diagnostics.update(cached_diagnostics)
            diagnostics['persistent_cache'] = 'HIT'
        if progress:
            progress(f'Cache STEP: {Path(path).name}: odczytano {len(solids)} brył z lokalnej pamięci B-Rep')
        try:
            os.utime(folder/'READY.json', None)
        except OSError:
            pass
        return solids
    except ValueError as exc:
        if str(exc).startswith('Limit bezpieczenstwa:'):
            raise
        return None
    except (OSError, RuntimeError, TypeError, KeyError, IndexError):
        return None


def publish(path, solids, diagnostics, prepared_folder=None, precomputed=None):
    """Atomic publish after successful import; optionally reuse worker BREP bytes."""
    key = precomputed if precomputed is not None else cache_key(path)
    if not key:
        return False
    dest = root_dir()/key[0][:2]/key[0]
    if (dest/'READY.json').is_file():
        return True
    tmp = None
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = Path(tempfile.mkdtemp(prefix='.build-', dir=dest.parent))
        if prepared_folder:
            source = Path(prepared_folder)
            shutil.copy2(source/'shapes.brep', tmp/'shapes.brep')
            shutil.copy2(source/'shapes.json', tmp/'shapes.json')
        else:
            from .parallel_import import write_cache
            write_cache(tmp, solids, diagnostics)
        marker = dict(schema=SCHEMA, source_sha256=key[1], size=key[2],
                      count=len(solids), created=time.time(), occt=_occt_version())
        (tmp/'READY.json').write_text(json.dumps(marker), encoding='utf-8')
        try:
            tmp.rename(dest)
        except FileExistsError:
            pass  # Another importer published the same exact content.
        _prune(root_dir())
        return True
    except (OSError, ValueError, RuntimeError):
        return False
    finally:
        if tmp is not None and tmp.exists():
            shutil.rmtree(tmp, ignore_errors=True)


def _prune(root, limit=MAX_CACHE_BYTES):
    try:
        entries=[]
        for ready in root.glob('*/*/READY.json'):
            folder=ready.parent
            bytes_used=sum(p.stat().st_size for p in folder.iterdir() if p.is_file())
            entries.append((ready.stat().st_mtime,folder,bytes_used))
        total=sum(x[2] for x in entries)
        for _, folder, size in sorted(entries):
            if total <= limit:
                break
            shutil.rmtree(folder, ignore_errors=True)
            total -= size
    except OSError:
        pass


def load_step_persistent(path, max_solids=20000, progress=None, diagnostics=None, precomputed_sha256=None, source_stat=None):
    """Drop-in serial importer; exact fallback on cache miss or corruption."""
    key = cache_key(path, source_sha256=precomputed_sha256, source_stat=source_stat)
    shapes = try_load(path, max_solids, progress, diagnostics, precomputed=key)
    if shapes is not None:
        return shapes
    from .step_io import load_step
    actual_diagnostics = diagnostics if diagnostics is not None else {}
    shapes = load_step(path, max_solids=max_solids, progress=progress, diagnostics=actual_diagnostics)
    if key:
        publish(path, shapes, actual_diagnostics, precomputed=key)
        if diagnostics is not None:
            diagnostics['persistent_cache'] = 'MISS'
    return shapes
