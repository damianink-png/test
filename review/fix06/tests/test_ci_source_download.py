"""Offline regression for transient HTTP 503 and corrupt ZIP handling."""
import ast
import io
import os
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace
import urllib.error
import urllib.request
import hashlib
import time

SCRIPT = Path(__file__).resolve().parents[1] / "ci" / "large_exe.py"

def make_downloader(opener):
    tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "download")
    scope = {
        "MODELS": {"fixture": ("Repo", "commit", "assembly.zip")},
        "Path": Path, "urllib": urllib, "zipfile": zipfile, "time": time,
        "sha256_file": lambda p: hashlib.sha256(p.read_bytes()).hexdigest(),
        "expected_count": lambda ref, digest: 1,
        "result": {"sources": []}, "save": lambda: None,
    }
    exec(compile(ast.Module(body=[fn], type_ignores=[]), str(SCRIPT), "exec"), scope)
    return scope["download"], scope["result"]

def fixture_zip():
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as z:
        z.writestr("part.step", "ISO-10303-21;END-ISO-10303-21;")
    return buffer.getvalue()

class DownloadTests(unittest.TestCase):
    def test_retry_503_then_valid_zip(self):
        attempts = []
        payload = fixture_zip()
        def opener(req, timeout):
            attempts.append(1)
            if len(attempts) == 1:
                raise urllib.error.HTTPError(req.full_url, 503, "transient", None, None)
            return io.BytesIO(payload)
        download, result = make_downloader(opener)
        with tempfile.TemporaryDirectory() as tmp, patch("os.getcwd", return_value=tmp):
            cwd = Path.cwd()
            os.chdir(tmp)
            try:
                with patch("time.sleep", return_value=None), patch("urllib.request.urlopen", side_effect=opener):
                    output = download("fixture")
                self.assertEqual(len(attempts), 2)
                self.assertTrue(output.is_file())
                self.assertEqual(len(result["sources"]), 1)
                self.assertFalse((Path("models") / "fixture" / "source.zip.partial").exists())
            finally:
                os.chdir(cwd)

    def test_corrupt_zip_never_committed(self):
        download, result = make_downloader(None)
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path.cwd()
            os.chdir(tmp)
            try:
                with patch("time.sleep", return_value=None), patch("urllib.request.urlopen", return_value=io.BytesIO(b"broken")) as call:
                    with self.assertRaises(RuntimeError):
                        download("fixture")
                self.assertEqual(call.call_count, 4)
                self.assertFalse((Path("models") / "fixture" / "source.zip").exists())
                self.assertFalse((Path("models") / "fixture" / "source.zip.partial").exists())
                self.assertEqual(result["sources"], [])
            finally:
                os.chdir(cwd)

if __name__ == "__main__":
    unittest.main()
