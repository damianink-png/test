"""Deterministic bounded-memory hashing patch for the verified RC9 ZIP.

Apply only to a pinned source bundle. Refuse unknown implementations so the
built EXE cannot silently omit the memory fix.
"""
from pathlib import Path
import sys


def patch(path):
    path=Path(path)
    source=path.read_text(encoding='utf-8')
    old='self._digests[key]=hashlib.sha256(path.read_bytes()).digest()'
    replacement="""digest=hashlib.sha256()
                    with path.open('rb') as source:
                        for chunk in iter(lambda:source.read(1024*1024),b''):
                            digest.update(chunk)
                    self._digests[key]=digest.digest()"""
    if source.count(old)==1:
        source=source.replace(old,replacement)
    elif source.count(replacement)!=1:
        raise RuntimeError('Unknown geometry_registry.py; streamed digest patch NOT applied')
    # Placed temporary SolidInfo instances can disappear between alignment
    # hypotheses. Keep the object alive and validate its identity before using
    # an id-keyed native definition; Python may recycle ids immediately.
    old_cache="""        if identifier in self._part_ids:
            return self._part_ids[identifier]"""
    new_cache="""        cached=self._part_ids.get(identifier)
        if cached is not None and cached[1] is part:
            return cached[0]"""
    if old_cache in source:
        source=source.replace(old_cache,new_cache)
        source=source.replace('self._part_ids[identifier] = index',
                              'self._part_ids[identifier] = (index, part)')
    elif new_cache not in source:
        raise RuntimeError('Unknown registry identity cache; refusing patch')
    compile(source,str(path),'exec')
    path.write_text(source,encoding='utf-8')
    print('DSCOMPARE_GEOMETRY_REGISTRY_STREAMING_DIGEST_PASS',path)


if __name__=='__main__':
    if len(sys.argv)!=2:
        raise SystemExit('usage: patch_geometry_registry_streaming.py <dsac29/geometry_registry.py>')
    patch(sys.argv[1])
