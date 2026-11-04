"""Durability regression for progress markers used during native OCCT crash triage."""
import json
from pathlib import Path
from unittest.mock import patch

from dsac29.progress_events import ProgressEvents


def test_durable_phase_transitions_only(tmp_path, monkeypatch):
    monkeypatch.setenv("DSCOMPARE_DURABLE_PHASES", "1")
    log = tmp_path / "progress.jsonl"
    progress = ProgressEvents(log)
    with patch("dsac29.progress_events.os.fsync") as sync:
        progress("Wczytywanie modelu A")
        progress("Wczytywanie modelu B")
        progress("budowanie kolorowego STEP")
        progress("budowanie kolorowego STEP 2")
        progress("Gotowe:")
    assert sync.call_count == 3
    records = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()]
    assert [r["phase"] for r in records] == [
        "Import STEP", "Import STEP", "Eksport STEP", "Eksport STEP", "Zakończono"
    ]


def test_default_progress_does_not_fsync(tmp_path, monkeypatch):
    monkeypatch.delenv("DSCOMPARE_DURABLE_PHASES", raising=False)
    progress = ProgressEvents(tmp_path / "progress.jsonl")
    with patch("dsac29.progress_events.os.fsync") as sync:
        progress("Wczytywanie modelu")
    sync.assert_not_called()
