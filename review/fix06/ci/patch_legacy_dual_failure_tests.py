"""Update frozen RC9 test fixtures for two independent Common/Cut paths.

A single injected guarded_common failure is no longer proof that the material
analysis must fail: the new validated calculate() fallback may still succeed.
These tests must inject both failures before expecting UNCERTAIN or an error.
The frozen source ZIP itself is never modified.
"""
from pathlib import Path
import sys

PATCHES = (
    ("test_partial_material_review.py", "monkeypatch.setattr(native_guard,'guarded_common',fail)", "fail", 2, False),
    ("test_stability.py", "monkeypatch.setattr(ng,'guarded_common',fail)", "fail", 1, True),
    ("test_registered_rigid_reexport.py", "monkeypatch.setattr(native_guard,'guarded_common',failed)", "failed", 1, True),
)


def apply(folder: Path) -> None:
    for filename, original, callback, expected, needs_import in PATCHES:
        path = folder / filename
        content = path.read_text(encoding="utf-8")
        if content.count(original) != expected:
            raise RuntimeError(f"Unexpected frozen test source: {filename}: {content.count(original)} occurrences")
        if needs_import:
            anchor = "from dsac29.revision_overlap import merge_material_revisions"
            if content.count(anchor) != 1:
                raise RuntimeError(f"Missing revision import in {filename}")
            indent = content.split(anchor, 1)[0].rsplit("\n", 1)[-1]
            content = content.replace(anchor, "from dsac29 import revision_overlap\n" + indent + anchor, 1)
        new = original + f";monkeypatch.setattr(revision_overlap,'calculate',{callback})"
        content = content.replace(original, new)
        compile(content, str(path), "exec")
        path.write_text(content, encoding="utf-8")
        print(f"DUAL_FAILURE_TEST_PATCH_PASS {filename} {expected}", flush=True)

    # The old source-text test required the exact spelling
    # "except NativeGeometryFailure:". The verified recovery uses
    # "except NativeGeometryFailure as exc:"; validate the AST instead.
    probe = folder.parent / "ci" / "test_rc9_isolated_pair_recovery.py"
    body = probe.read_text(encoding="utf-8")
    needle = ("assert 'except NativeGeometryFailure:' in a\n"
              "assert 'except NativeGeometryFailure:' in b")
    if body.count(needle) != 1:
        raise RuntimeError("Unexpected frozen native exception probe")
    replacement = ("def has_native_failure_handler(source):\n"
                   "    return any(isinstance(node, ast.ExceptHandler) and\n"
                   "               isinstance(node.type, ast.Name) and\n"
                   "               node.type.id == 'NativeGeometryFailure'\n"
                   "               for node in ast.walk(ast.parse(source)))\n"
                   "assert has_native_failure_handler(a)\n"
                   "assert has_native_failure_handler(b)")
    body = body.replace(needle, replacement)
    compile(body, str(probe), "exec")
    probe.write_text(body, encoding="utf-8")
    print("NATIVE_EXCEPTION_AST_PROBE_PASS", flush=True)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: patch_legacy_dual_failure_tests.py <extracted-tests-dir>")
    apply(Path(sys.argv[1]))
