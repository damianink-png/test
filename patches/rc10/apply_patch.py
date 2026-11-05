"""Apply the RC10 overlay to either unpacked RC10 archive, with base checks."""
import hashlib
import json
from pathlib import Path
import sys


def apply(root):
    here = Path(__file__).resolve().parent
    manifest = json.loads((here / 'manifest.json').read_text(encoding='utf-8'))
    pending = []
    for name, hashes in manifest.items():
        target = root / name
        source = here / 'overlay' / name
        payload = source.read_bytes()
        if hashlib.sha256(payload).hexdigest() != hashes['after']:
            raise ValueError(f'Corrupt overlay: {name}')
        current = hashlib.sha256(target.read_bytes()).hexdigest() if target.exists() else None
        if current == hashes['after']:
            continue
        if current != hashes['before']:
            raise ValueError(f'Unexpected source version; no files changed: {name}')
        pending.append((target, payload))
    for target, payload in pending:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
    print(f'RC10 geometry fixes: {len(pending)} files applied to {root}')


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('Usage: python patches/rc10/apply_patch.py UNPACKED_RC10_ROOT')
    apply(Path(sys.argv[1]).resolve())
