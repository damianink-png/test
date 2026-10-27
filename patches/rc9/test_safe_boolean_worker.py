import importlib.util
from pathlib import Path
from unittest.mock import patch
import subprocess
import pytest

spec = importlib.util.spec_from_file_location("safe_boolean_worker", Path(__file__).resolve().parent.parent / "dsac29" / "safe_boolean_worker.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def test_rejects_unknown_operation():
    with pytest.raises(ValueError):
        mod.run_boolean("a", "b", "c", operation="union")


def test_rejects_nonpositive_timeout():
    with pytest.raises(ValueError):
        mod.run_boolean("a", "b", "c", timeout=0)


def test_timeout_never_proves_same():
    with patch.object(mod.subprocess, "run", side_effect=subprocess.TimeoutExpired("cmd", 1)):
        result = mod.run_boolean("a", "b", "c", timeout=1)
    assert result["status"] == "timeout"
    assert result["same_proven"] is False


def test_native_crash_is_error_not_same():
    with patch.object(mod.subprocess, "run", return_value=subprocess.CompletedProcess([], 3221225477, "", "access violation")):
        result = mod.run_boolean("a", "b", "c")
    assert result["status"] == "error"
    assert result["exit_code"] == 3221225477
    assert result["same_proven"] is False


def test_success_is_not_same_proof():
    with patch.object(mod.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, "", "")):
        result = mod.run_boolean("a", "b", "c")
    assert result["status"] == "ok"
    assert result["same_proven"] is False


def test_no_fuzzy_flag_and_process_timeout():
    with patch.object(mod.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, "", "")) as call:
        mod.run_boolean("a", "b", "c", operation="cut_ba", timeout=12)
    cmd = call.call_args.args[0]
    assert "--operation" in cmd and "cut_ba" in cmd
    assert not any("fuzzy" in str(part).lower() for part in cmd)
    assert call.call_args.kwargs["timeout"] == 12
