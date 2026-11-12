"""Assemble the exact current CAD overlays for portable builds and regressions."""
from pathlib import Path
import shutil
import json
import os
import subprocess
import sys

MODULES = ['revision_overlap.py', 'overlap_evidence.py', 'candidate_policy.py', 'worker_v37.py', 'common_exclusion.py', 'palette.py', 'preview3d.py', 'preview_template.html', 'cli.py', 'report.py', 'material_mass_report.py', 'standalone_mass_materials.py', 'name_encoding.py', 'step_io.py', 'step_diagnostics.py', 'occurrence_identity.py', 'deferred_alignment.py', 'fingerprint_priority.py', 'rigid_registration.py', 'registration_gate.py', 'progress_events.py', 'repeated_geometry.py', 'revision_rules.py', 'material_names.py', 'registration_search.py', 'translation_refinement.py', 'cad_pose_search.py', 'cad_registration.py', 'surface_registration.py', 'unique_anchors.py', 'local_tests.py', 'model_diagnostic.py']
TESTS = ['test_overlap_evidence.py', 'test_candidate_policy.py', 'test_fingerprint_priority.py', 'test_revision_overlap_policy.py', 'test_gui_minimal.py', 'test_partial_material_continue.py', 'test_material_worker_failclosed.py', 'test_material_timeout_policy.py', 'test_stale_failed_pair_guard.py', 'test_audit_legacy_guards.py', 'test_progress_durable_phases.py', 'test_streamed_preview.py', 'test_translated_proof_index.py', 'test_semantic_palette_export.py', 'test_spatial_index_oracle.py', 'test_spatial_index_2500.py', 'test_spatial_index_dense.py', 'test_20261104_audit_fixes.py', 'test_alignment_stage2_guard.py', 'test_mass_html_materials.py', 'test_large_frame_sampling.py', 'test_native_completion_read.py', 'test_rigid_registration.py', 'test_shift_proof_candidates.py', 'test_registration_continuation.py', 'test_translation_refinement.py', 'test_cad_pose_search.py', 'test_surface_registration.py', 'test_unique_anchors.py', 'test_population_preparation.py', 'test_frame_with_local_moves.py', 'test_incomplete_registration_retry.py', 'test_operation_reuse.py', 'test_registration_placement.py', 'test_registered_solid_sets.py', 'test_r14_sparse_shift.py', 'test_repeated_revision_policy.py', 'test_repeated_material_exception.py', 'test_20261109_volume_alignment.py', 'test_20261109_21of24.py', 'test_world_stage_379.py', 'test_zw3d_ap203_shift_efficiency.py', 'test_no_duplicate_pose_proofs.py', 'test_occurrence_placement_zw3d.py', 'test_occurrence_identity.py', 'test_occurrence_bucket_neighbourhood.py', 'test_dynamic_rigid_budget.py']
PATCHES = [('patch_geometry_registry_streaming.py', 'dsac29/geometry_registry.py'), ('patch_native_completion_read.py', 'dsac29/native_session.py'), ('patch_alignment_stage2.py', 'dsac29/alignment.py'), ('patch_common_exclusion_dispatch.py', 'dsac29/native_guard.py'), ('patch_material_worker_failclosed.py', ''), ('patch_material_timeout.py', 'dsac29/material_guard.py'), ('patch_stale_failed_pairs.py', 'dsac29/compare.py'), ('patch_assignment_uniqueness.py', 'dsac29/assignment.py'), ('patch_legacy_audit_tests.py', ''), ('patch_gui_minimal.py', ''), ('patch_legacy_ui_tests.py', ''), ('patch_step_polish_names.py', ''), ('patch_compare_revision_policy.py', 'dsac29/compare.py'), ('patch_registered_world_lookup.py', 'dsac29/compare.py'), ('patch_surface_registration_worker.py', 'dsac29/native_guard.py'), ('patch_invalid_material_volume.py', ''), ('patch_world_stage_379.py', ''), ('patch_occurrence_placement_zw3d.py', ''), ('patch_occurrence_identity.py', '')]


def assemble(target):
    repo=Path(__file__).resolve().parent.parent
    overlays=repo/'review/fix06'
    for directory,names in [('dsac29',MODULES),('tests',TESTS)]:
        for name in names:
            shutil.copyfile(overlays/directory/name,target/directory/name)
    for name,relative in PATCHES:
        subprocess.run([sys.executable,str(overlays/'ci'/name),str(target/relative)],check=True)
    # The runnable CAD engine must receive the same AP203/AP214/AP242
    # diagnostic implementation as the unit-tested review sources. A
    # baseline copy lacks schema_header and caused 31 false-negative CI
    # failures via import error. Verify the actual shipped bytecode API.
    import ast
    step_diag=target/'dsac29/step_diagnostics.py'
    tree=ast.parse(step_diag.read_text(encoding='utf-8'))
    exported={node.name for node in tree.body if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef))}
    if not {'schema_header','_schema_from_bytes'}.issubset(exported):
        raise RuntimeError('Portable CAD engine missing current STEP schema diagnostics')
    cache_test=target/'tests/test_frame_proof_cache.py'
    cache_test.write_text(cache_test.read_text().replace('simulated timeout','simulated transient native error'))
    import compileall
    if not compileall.compile_dir(str(target/'dsac29'),quiet=1):
        raise RuntimeError('CAD source syntax failed')
    info_path=target/'build_info.json'
    info=json.loads(info_path.read_text(encoding='utf-8-sig'))
    info.update(revision='Portable 0.6.15 — wznowienie prób B-Rep i warunkowe wyrównanie 2026-11-12',
                source_commit=os.environ.get('GITHUB_SHA','local_uncommitted'),
                source_assembly='portable/prepare_source.py + portable/assemble_engine.py')
    info_path.write_text(json.dumps(info,indent=2,ensure_ascii=False),encoding='utf-8')
    print('CURRENT_PORTABLE_ENGINE_ASSEMBLED',flush=True)


if __name__=='__main__':
    assemble(Path(sys.argv[1]).resolve())
