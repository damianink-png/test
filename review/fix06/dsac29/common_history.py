"""Disk reuse of source-bound Common/Cut partitions in identical world coordinates."""
from contextlib import ExitStack
from pathlib import Path
from tempfile import TemporaryDirectory
import hashlib
import json
import sqlite3
import sys

from .brep_transport import brep_digest, read_brep, write_brep
from .import_cache import root_dir, _occt_version
from .material_deltas import MaterialRegions, bind_regions, volume

MAX_ENTRY = 8 * 1024**2
MAX_TOTAL = 128 * 1024**2
CACHE_ERRORS = (OSError, ValueError, RuntimeError, sqlite3.Error)


class CommonHistory(ExitStack):
    def __init__(self):
        super().__init__()
        self.db = None
        self.disabled = False
        self.digests = {}

    def _open(self):
        root = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parents[1]))
        build = json.loads((root / 'build_info.json').read_text('utf-8-sig'))
        self.version = (build['revision'], build['source_commit'], _occt_version())
        folder = root_dir()
        folder.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(folder / 'common-v2.sqlite', timeout=.2)
        self.callback(db.close)
        db.execute('CREATE TABLE IF NOT EXISTS proofs (key TEXT PRIMARY KEY, digest BLOB NOT NULL, common BLOB NOT NULL, added BLOB NOT NULL, removed BLOB NOT NULL)')
        self.path = Path(self.enter_context(TemporaryDirectory(prefix='dscompare_common_history_'))) / 'shape.brep'
        self.has_entries = db.execute('SELECT 1 FROM proofs LIMIT 1').fetchone() is not None
        self.db = db

    def _digest(self, part):
        identity = id(part)
        if identity not in self.digests:
            write_brep(part.shape, self.path)
            self.digests[identity] = (part, brep_digest(self.path))
        return self.digests[identity][1]

    def _key(self, left, right, tolerance, *, lookup=False):
        if self.disabled:
            return None
        if self.db is None:
            try:
                self._open()
            except (OSError, ValueError, RuntimeError, sqlite3.Error, KeyError):
                self.disabled = True
                return None
        if lookup and not self.has_entries:
            return None
        try:
            fields = [self.version, self._digest(left), self._digest(right), float(tolerance).hex()]
            return hashlib.sha256(json.dumps(fields).encode()).hexdigest()
        except CACHE_ERRORS:
            return None

    @staticmethod
    def _checksum(key, blobs):
        digest = hashlib.sha256(key.encode())
        for blob in blobs:
            digest.update(len(blob).to_bytes(8, 'big'))
            digest.update(blob)
        return digest.digest()

    def load(self, left, right, tolerance):
        key = self._key(left, right, tolerance, lookup=True)
        if key is None:
            return None
        try:
            row = self.db.execute(
                'SELECT digest,common,added,removed FROM proofs WHERE key=? AND '
                'length(common)+length(added)+length(removed)<=?', (key, MAX_ENTRY)).fetchone()
            if row is None:
                return None
            checksum, *blobs = row
            if not all(isinstance(blob, bytes) for blob in blobs) or checksum != self._checksum(key, blobs):
                return None
            shapes = []
            for blob in blobs:
                self.path.write_bytes(blob)
                shapes.append(read_brep(self.path))
            regions = MaterialRegions(*shapes, *(volume(shape) for shape in shapes))
            bind_regions(regions, left, right, tolerance)
            return regions
        except CACHE_ERRORS:
            return None

    def save(self, left, right, tolerance, regions):
        key = self._key(left, right, tolerance)
        if key is None:
            return
        try:
            blobs = []
            total_size = 0
            for shape in (regions.common, regions.added, regions.removed):
                write_brep(shape, self.path)
                total_size += self.path.stat().st_size
                if total_size > MAX_ENTRY:
                    return
                blobs.append(self.path.read_bytes())
            checksum = self._checksum(key, blobs)
            with self.db:
                self.db.execute('INSERT OR REPLACE INTO proofs VALUES (?,?,?,?,?)', (key, checksum, *blobs))
                sizes = 'length(common)+length(added)+length(removed)'
                count, total = self.db.execute(f'SELECT count(*),sum({sizes}) FROM proofs').fetchone()
                while count > 2048 or total > MAX_TOTAL:
                    row, size = self.db.execute(f'SELECT rowid,{sizes} FROM proofs ORDER BY rowid LIMIT 1').fetchone()
                    self.db.execute('DELETE FROM proofs WHERE rowid=?', (row,))
                    total -= size
                    count -= 1
        except CACHE_ERRORS:
            return
