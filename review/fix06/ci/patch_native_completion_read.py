"""Bounded Windows completion-mailbox read retry (never accepts an unproven reply)."""
from pathlib import Path
import sys

def patch(path: Path) -> None:
    original = path.read_text(encoding="utf-8")
    old = """            try:
                done=json.loads(completion.read_text(encoding='utf-8'))
            except (OSError,ValueError) as exc:
                raise NativeGeometryFailure('Nieprawidlowe potwierdzenie zakonczenia B-Rep') from exc"""
    new = """            # Windows antivirus/indexing can briefly deny access to a freshly
            # published completion mailbox. Retry only transient read locks;
            # invalid JSON, dead workers and expired deadlines remain failures.
            read_deadline = min(started + timeout_s, time.monotonic() + 1.0)
            while True:
                try:
                    done=json.loads(completion.read_text(encoding='utf-8'))
                    break
                except PermissionError as exc:
                    if self.process.poll() is not None or time.monotonic() >= read_deadline:
                        raise NativeGeometryFailure('Nieprawidlowe potwierdzenie zakonczenia B-Rep') from exc
                    time.sleep(.02)
                except (OSError,ValueError) as exc:
                    raise NativeGeometryFailure('Nieprawidlowe potwierdzenie zakonczenia B-Rep') from exc"""
    if new in original:
        print("NATIVE_SESSION_COMPLETION_READ_PATCH_PASS (already applied)")
        return
    if original.count(old) != 1:
        raise SystemExit("Unexpected native_session completion read; refusing unsafe patch")
    updated = original.replace(old, new)
    compile(updated, str(path), "exec")
    path.write_text(updated, encoding="utf-8")
    print("NATIVE_SESSION_COMPLETION_READ_PATCH_PASS")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: patch_native_completion_read.py PATH")
    patch(Path(sys.argv[1]))
