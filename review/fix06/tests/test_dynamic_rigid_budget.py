"""Prevent the legacy 240s assembly-wide rigid safeguard from truncating
large STEP revision matching while preserving the per-operation native guard.
"""
from dsac29.compare import native_rigid_stage_budget


def test_small_assembly_keeps_minimum_watchdog():
    assert native_rigid_stage_budget(80)==240.0
    assert native_rigid_stage_budget(480)==240.0


def test_big_assembly_uses_size_scaled_watchdog():
    assert native_rigid_stage_budget(1000)==500.0
    assert native_rigid_stage_budget(1600)==800.0
    assert native_rigid_stage_budget(2400)==1200.0
