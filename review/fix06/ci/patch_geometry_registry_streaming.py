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
    if source.count(old)!=1:
        if source.count(replacement)==1:
            return
        raise RuntimeError('Unknown geometry_registry.py; streamed digest patch NOT applied')
    path.write_text(source.replace(old,replacement),encoding='utf-8')
    print('DSCOMPARE_GEOMETRY_REGISTRY_STREAMING_DIGEST_PASS',path)


if __name__=='__main__':
    if len(sys.argv)!=2:
        raise SystemExit('usage: patch_geometry_registry_streaming.py <dsac29/geometry_registry.py>')
    patch(sys.argv[1])
