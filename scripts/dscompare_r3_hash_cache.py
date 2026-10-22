"""R3: share verified SHA-256 between CLI fingerprint and persistent import cache.

A digest is reused ONLY if file size and mtime_ns still match the stat
obtained during fingerprinting; if it changed, calculate SHA from bytes again.
"""
import os
from pathlib import Path
root=Path(os.environ['DS_COMPARE_SOURCE'])
p=root/'dsac29/import_cache.py'
s=p.read_text('utf8')
old="def _key(path, progress=None):"
new="def _key(path, progress=None, source_sha256=None, source_stat=None):"
assert s.count(old)==1;s=s.replace(old,new,1)
old="""    h = hashlib.sha256()
    before = src.stat()
    with src.open('rb') as input_file:
        for block in iter(lambda: input_file.read(4*1024**2), b''):
            h.update(block)
    after = src.stat()
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        return None
    key = hashlib.sha256((SCHEMA + '\\0' + _occt_version() + '\\0' + h.hexdigest()).encode()).hexdigest()
    return key, h.hexdigest(), after.st_size"""
new="""    before = src.stat()
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
    key = hashlib.sha256((SCHEMA + '\\0' + _occt_version() + '\\0' + digest).encode()).hexdigest()
    return key, digest, after.st_size"""
assert s.count(old)==1,s.count(old);s=s.replace(old,new,1)
old="def cache_key(path):"
new="def cache_key(path, source_sha256=None, source_stat=None):"
assert s.count(old)==1;s=s.replace(old,new,1)
old="        return _key(path)"
new="        return _key(path, source_sha256=source_sha256, source_stat=source_stat)"
assert s.count(old)==1;s=s.replace(old,new,1)
old="def load_step_persistent(path, max_solids=20000, progress=None, diagnostics=None):"
new="def load_step_persistent(path, max_solids=20000, progress=None, diagnostics=None, precomputed_sha256=None, source_stat=None):"
assert s.count(old)==1;s=s.replace(old,new,1)
old="    key = cache_key(path)\n    shapes = try_load("
new="    key = cache_key(path, source_sha256=precomputed_sha256, source_stat=source_stat)\n    shapes = try_load("
assert s.count(old)==1;s=s.replace(old,new,1)
p.write_text(s,'utf8')

p=root/'dsac29/cli.py'
s=p.read_text('utf8')
old="""    fingerprints={'A':fingerprint(a_path),'B':fingerprint(b_path)}"""
new="""    # One validated full-file digest per distinct STEP input. Share with the
    # serial import cache; never trust merely path/size/mtime as identity.
    source_stats={};fingerprints={};memo={}
    for role,raw in (('A',a_path),('B',b_path)):
        src=Path(raw);before=src.stat()
        stat_key=(str(src.resolve()),before.st_size,before.st_mtime_ns)
        digest=memo.get(stat_key)
        if digest is None:
            digest=fingerprint(src)
        after=src.stat()
        if (before.st_size,before.st_mtime_ns)!=(after.st_size,after.st_mtime_ns):
            raise RuntimeError('Plik STEP został zmieniony w trakcie obliczania SHA-256: '+src.name)
        source_stats[role]=(after.st_size,after.st_mtime_ns)
        fingerprints[role]=digest
        memo[stat_key]=digest"""
assert s.count(old)==1,s.count(old);s=s.replace(old,new,1)
old="""a=load_step(a_path,progress=progress,diagnostics=import_stats["A"],max_solids=max_solids)"""
new="""a=load_step(a_path,progress=progress,diagnostics=import_stats["A"],max_solids=max_solids,
                    precomputed_sha256=fingerprints['A'],source_stat=source_stats['A'])"""
assert s.count(old)==1;s=s.replace(old,new,1)
old="""b=load_step(b_path,progress=progress,diagnostics=import_stats["B"],max_solids=max_solids)"""
new="""b=load_step(b_path,progress=progress,diagnostics=import_stats["B"],max_solids=max_solids,
                        precomputed_sha256=fingerprints['B'],source_stat=source_stats['B'])"""
assert s.count(old)==1;s=s.replace(old,new,1)
p.write_text(s,'utf8')
print('R3 SHA: serial cache uses preverified digest and stat; unchanged data still content-authenticated')
