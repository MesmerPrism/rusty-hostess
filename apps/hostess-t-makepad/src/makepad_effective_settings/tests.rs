use super::revision::{EFFECTIVE_SETTINGS_REVISION_FILE_NAME, EFFECTIVE_SETTINGS_REVISION_SCHEMA};
use super::*;
use rusty_quest_makepad_camera_shell::{
    CAMERA_SHELL_APP_ID, MESH_REPLAY_SOURCE_PUBLIC_SYNTHETIC_HAND_SEQUENCE,
    MESH_REPLAY_SOURCE_RECORDED_META_QUEST_HAND_LEFT, RECORDED_META_QUEST_HAND_LEFT_SEQUENCE_FILE,
};
use std::time::{SystemTime, UNIX_EPOCH};

const EFFECTIVE_SETTINGS_FIXTURE: &str = include_str!(
    "../../../../../rusty-quest-makepad/fixtures/effective-settings/mesh-replay.effective-settings.json"
);
const SYNTHETIC_SEQUENCE_FIXTURE: &str = include_str!(
    "../../../../../rusty-quest-makepad/fixtures/mesh-replay/synthetic-hand-mesh-sequence.json"
);

#[test]
fn reads_canonical_effective_settings_with_mesh_replay_values() {
    let path = write_temp_json("effective-settings", EFFECTIVE_SETTINGS_FIXTURE);

    let receipt = read_makepad_effective_settings_from_path(&path);

    assert_eq!(receipt.status, "ready");
    assert!(receipt.canonical_effective_settings_consumed);
    assert!(receipt.mesh_replay_settings_present);
    assert_eq!(
        receipt.mesh_replay_adapter.as_deref(),
        Some(MESH_REPLAY_ADAPTER)
    );
    assert_eq!(receipt.mesh_replay_adapter_status.as_deref(), Some("ready"));
    assert_eq!(receipt.source_app_id.as_deref(), Some(CAMERA_SHELL_APP_ID));
    assert_eq!(receipt.mesh_replay_enabled, Some(true));
    assert_eq!(
        receipt.mesh_replay_source.as_deref(),
        Some("public-synthetic-hand-sequence")
    );
    assert_eq!(receipt.mesh_replay_speed, Some(1.5));
    assert_eq!(receipt.mesh_replay_opacity, Some(0.75));
    assert!(receipt
        .render_scale
        .is_some_and(|value| (value - 0.9).abs() < 0.000_001));
    assert_eq!(receipt.camera_streaming_enabled, Some(false));
    assert_eq!(receipt.collision_enabled, Some(true));
    assert_eq!(receipt.sdf_adf_overlay_mode.as_deref(), Some("sdf"));
    assert_eq!(receipt.sdf_adf_runtime_mode.as_deref(), Some("sdf"));
    assert_eq!(receipt.sdf_adf_unsupported_future_mode, Some(false));
    assert_eq!(receipt.particles_enabled, Some(true));
    assert_eq!(receipt.particle_render_draw_limit, Some(192));
    assert_eq!(
        receipt.particle_render_animation_mode.as_deref(),
        Some("procedural-morph-ring")
    );
    assert_eq!(receipt.particle_render_size_scale, Some(1.0));
    assert_eq!(receipt.matter_surface_native_runtime_configured, Some(true));
    assert_eq!(
        receipt.matter_surface_sdf_adf_debug_update_interval_frames,
        Some(1)
    );
    assert_eq!(receipt.matter_surface_particle_count, Some(1000));
    assert_eq!(receipt.matter_surface_leaf_triangle_count, Some(8));
    assert_eq!(
        receipt
            .matter_surface_particle_distance_refresh_policy
            .as_deref(),
        Some("step-only")
    );
    assert_eq!(
        receipt.matter_surface_particle_force_authority.as_deref(),
        Some("matter-cpu")
    );
    assert_eq!(
        receipt
            .matter_surface_gpu_force_provider_ab_receipt
            .as_deref(),
        Some("none")
    );
    assert_eq!(
        receipt.matter_surface_gpu_force_provider_ab_ready,
        Some(false)
    );
    assert_eq!(
        receipt.matter_surface_particle_force_source.as_deref(),
        Some("mesh-distance")
    );
    assert_eq!(
        receipt.matter_surface_particle_force_update_interval_frames,
        Some(1)
    );
    assert_eq!(
        receipt.matter_surface_particle_force_compare_probe_count,
        Some(0)
    );
    assert_eq!(
        receipt.matter_surface_particle_execution_backend.as_deref(),
        Some("serial")
    );
    assert_eq!(
        receipt.matter_surface_particle_execution_batch_size,
        Some(256)
    );
    assert_eq!(receipt.matter_surface_particle_execution_max_threads, None);
    assert_eq!(
        receipt.matter_surface_particle_max_frame_delta_seconds,
        None
    );
    assert!(!receipt.legacy_settings_fallback_used);

    let marker = receipt.marker_line("test");
    assert!(marker.contains("schema=rusty.hostess.makepad_effective_settings_receipt.v1"));
    assert!(marker.contains("canonicalEffectiveSettingsConsumed=true"));
    assert!(marker.contains("meshReplaySettingsPresent=true"));
    assert!(marker.contains("meshReplayAdapter=rusty-quest-makepad-camera-shell"));
    assert!(marker.contains("meshReplayAdapterStatus=ready"));
    assert!(marker.contains("renderScale=0.900"));
    assert!(marker.contains("cameraStreamingEnabled=false"));
    assert!(marker.contains("collisionEnabled=true"));
    assert!(marker.contains("sdfAdfOverlayMode=sdf"));
    assert!(marker.contains("sdfAdfRuntimeMode=sdf"));
    assert!(marker.contains("matterSurfaceNativeRuntimeConfigured=true"));
    assert!(marker.contains("matterSurfaceAdfDebugEnabled=false"));
    assert!(marker.contains("matterSurfaceAdfMaxDepth=4"));
    assert!(marker.contains("matterSurfaceAdfMaxCells=4096"));
    assert!(marker.contains("matterSurfaceAdfErrorTolerance=0.025"));
    assert!(marker.contains("matterSurfaceSdfAdfDebugUpdateIntervalFrames=1"));
    assert!(marker.contains("matterSurfaceParticleCount=1000"));
    assert!(marker.contains("matterSurfaceParticleDistanceRefreshPolicy=step-only"));
    assert!(marker.contains("matterSurfaceParticleForceAuthority=matter-cpu"));
    assert!(marker.contains("matterSurfaceGpuForceProviderAbReceipt=none"));
    assert!(marker.contains("matterSurfaceGpuForceProviderAbReady=false"));
    assert!(marker.contains("matterSurfaceParticleForceSource=mesh-distance"));
    assert!(marker.contains("matterSurfaceParticleForceUpdateIntervalFrames=1"));
    assert!(marker.contains("matterSurfaceParticleForceCompareProbeCount=0"));
    assert!(marker.contains("matterSurfaceParticleExecutionBackend=serial"));
    assert!(marker.contains("matterSurfaceParticleExecutionBatchSize=256"));
    assert!(marker.contains("matterSurfaceParticleExecutionMaxThreads=none"));
    assert!(marker.contains("matterSurfaceParticleMaxFrameDeltaSeconds=none"));
    assert!(marker.contains("particlesEnabled=true"));
    assert!(marker.contains("particleRenderDrawLimit=192"));
    assert!(marker.contains("particleRenderAnimationMode=procedural-morph-ring"));
    assert!(marker.contains("particleRenderSizeScale=1.000"));
    assert!(!marker.contains("rustyxr"));
    assert!(!marker.contains("rusty.xr"));

    let json = receipt.to_json_value();
    assert_eq!(
        json["matter_surface_sdf_adf_debug_update_interval_frames"],
        serde_json::json!(1)
    );
    assert_eq!(
        json["matter_surface_particle_force_authority"],
        serde_json::json!("matter-cpu")
    );
    assert_eq!(
        json["matter_surface_gpu_force_provider_ab_receipt"],
        serde_json::json!("none")
    );
    assert_eq!(
        json["matter_surface_gpu_force_provider_ab_ready"],
        serde_json::json!(false)
    );
    assert_eq!(
        json["matter_surface_particle_force_source"],
        serde_json::json!("mesh-distance")
    );
    assert_eq!(
        json["matter_surface_particle_force_update_interval_frames"],
        serde_json::json!(1)
    );
    assert_eq!(
        json["matter_surface_particle_force_compare_probe_count"],
        serde_json::json!(0)
    );
}

#[test]
fn adf_effective_settings_select_matter_adf_debug() {
    let adf_settings =
        EFFECTIVE_SETTINGS_FIXTURE.replace("\"value\": \"sdf\"", "\"value\": \"adf\"");
    let path = write_temp_json("effective-settings-adf", &adf_settings);

    let receipt = read_makepad_effective_settings_from_path(&path);

    assert_eq!(receipt.status, "ready");
    assert_eq!(receipt.sdf_adf_overlay_mode.as_deref(), Some("adf"));
    assert_eq!(receipt.sdf_adf_runtime_mode.as_deref(), Some("adf"));
    assert_eq!(receipt.sdf_adf_unsupported_future_mode, Some(false));
    assert_eq!(receipt.matter_surface_native_runtime_configured, Some(true));
    assert_eq!(receipt.matter_surface_adf_debug_enabled, Some(true));
    assert_eq!(receipt.matter_surface_adf_max_depth, Some(4));
    assert_eq!(receipt.matter_surface_adf_max_cells, Some(4096));
    assert!(receipt
        .matter_surface_adf_error_tolerance
        .is_some_and(|value| (value - 0.025).abs() < 0.000_001));
    assert_eq!(
        receipt.matter_surface_sdf_adf_debug_update_interval_frames,
        Some(1)
    );

    let marker = receipt.marker_line("test-adf");
    assert!(marker.contains("sdfAdfOverlayMode=adf"));
    assert!(marker.contains("sdfAdfRuntimeMode=adf"));
    assert!(marker.contains("sdfAdfUnsupportedFutureMode=false"));
    assert!(marker.contains("matterSurfaceNativeRuntimeConfigured=true"));
    assert!(marker.contains("matterSurfaceAdfDebugEnabled=true"));
    assert!(marker.contains("matterSurfaceAdfMaxDepth=4"));
    assert!(marker.contains("matterSurfaceAdfMaxCells=4096"));
    assert!(marker.contains("matterSurfaceAdfErrorTolerance=0.025"));
    assert!(marker.contains("matterSurfaceSdfAdfDebugUpdateIntervalFrames=1"));

    let selection = read_mesh_replay_runtime_from_path(&path);
    assert_eq!(
        selection.feature_uniforms,
        MakepadCameraShellFeatureUniforms {
            collision_enabled: 1.0,
            sdf_adf_overlay_mode: 2.0,
            particles_enabled: 1.0,
        }
    );
    assert!(selection.matter_surface_runtime.is_some());
}

#[test]
fn builds_mesh_replay_runtime_from_canonical_effective_settings() {
    let path = write_temp_json("effective-settings-runtime", EFFECTIVE_SETTINGS_FIXTURE);

    let mut selection = read_mesh_replay_runtime_from_path(&path);

    assert_eq!(selection.status, "ready");
    assert!(selection.issue_code.is_none());
    assert!(selection.source_modified_ns.is_some());
    assert!(selection.source_effective_settings_path.is_some());
    assert_eq!(selection.render_scale, Some(0.9));
    assert_eq!(selection.camera_streaming_enabled, Some(false));
    assert_eq!(selection.particle_render_draw_limit, Some(192));
    assert_eq!(
        selection.particle_render_animation_mode,
        Some(ParticleRenderAnimationMode::ProceduralMorphRing)
    );
    assert_eq!(selection.particle_render_size_scale, Some(1.0));
    assert_eq!(
        selection.particle_force_authority,
        Some(QuestMakepadForceAuthorityMode::MatterCpu)
    );
    assert_eq!(
        selection.feature_uniforms,
        MakepadCameraShellFeatureUniforms {
            collision_enabled: 1.0,
            sdf_adf_overlay_mode: 1.0,
            particles_enabled: 1.0,
        }
    );
    let runtime = selection.runtime.as_mut().expect("runtime selected");
    assert!(selection.matter_surface_runtime.is_some());
    let first = runtime.step(0.0);
    assert!(first.enabled);
    assert_eq!(first.frame_index, 0);
    let marker = runtime.config_marker_line("test");
    assert!(marker.contains("schema=rusty.quest.makepad.mesh_replay.v1"));
    assert!(marker.contains("source=public-synthetic-hand-sequence"));
    assert!(!marker.contains("rusty.xr"));
}

#[test]
fn reads_gpu_force_authority_as_profile_gate_without_replacing_matter_source() {
    let gpu_authority_settings = EFFECTIVE_SETTINGS_FIXTURE.replace(
        "\"value\": \"matter-cpu\"",
        "\"value\": \"gpu-dense-sdf-field-particle-force\"",
    );
    let path = write_temp_json("gpu-authority-effective-settings", &gpu_authority_settings);

    let receipt = read_makepad_effective_settings_from_path(&path);
    let selection = read_mesh_replay_runtime_from_path(&path);

    assert_eq!(
        receipt.matter_surface_particle_force_authority.as_deref(),
        Some("gpu-dense-sdf-field-particle-force")
    );
    assert_eq!(
        receipt.matter_surface_particle_force_source.as_deref(),
        Some("mesh-distance")
    );
    assert_eq!(
        selection.particle_force_authority,
        Some(QuestMakepadForceAuthorityMode::GpuDenseSdfFieldParticleForce)
    );
    assert_eq!(
        selection.gpu_force_provider_ab_receipt,
        Some(QuestMakepadGpuForceProviderAbReceipt::None)
    );
    assert!(selection.matter_surface_runtime.is_some());

    let marker = selection.marker_line("gpu-authority-test");
    assert!(marker.contains("particleForceAuthority=gpu-dense-sdf-field-particle-force"));
    assert!(marker.contains("gpuForceProviderAbReceipt=none"));
    assert!(marker.contains("gpuForceProviderAbReady=false"));
    assert!(marker.contains("matterSurfaceRuntimeSelected=true"));
}

#[test]
fn reads_gpu_force_provider_ab_receipt_as_promotion_gate_evidence() {
    let provider_ab_settings = EFFECTIVE_SETTINGS_FIXTURE.replace(
        "\"setting_id\": \"makepad.particles.force.live_recorded_provider_ab_receipt\",\n      \"value\": \"none\"",
        "\"setting_id\": \"makepad.particles.force.live_recorded_provider_ab_receipt\",\n      \"value\": \"live-recorded-provider-ab-check-v1\"",
    );
    let path = write_temp_json("gpu-provider-ab-effective-settings", &provider_ab_settings);

    let receipt = read_makepad_effective_settings_from_path(&path);
    let selection = read_mesh_replay_runtime_from_path(&path);

    assert_eq!(
        receipt
            .matter_surface_gpu_force_provider_ab_receipt
            .as_deref(),
        Some("live-recorded-provider-ab-check-v1")
    );
    assert_eq!(
        receipt.matter_surface_gpu_force_provider_ab_ready,
        Some(true)
    );
    assert_eq!(
        selection.gpu_force_provider_ab_receipt,
        Some(QuestMakepadGpuForceProviderAbReceipt::LiveRecordedProviderAbCheckV1)
    );

    let receipt_marker = receipt.marker_line("gpu-provider-ab-test");
    assert!(receipt_marker
        .contains("matterSurfaceGpuForceProviderAbReceipt=live-recorded-provider-ab-check-v1"));
    assert!(receipt_marker.contains("matterSurfaceGpuForceProviderAbReady=true"));

    let selection_marker = selection.marker_line("gpu-provider-ab-test");
    assert!(
        selection_marker.contains("gpuForceProviderAbReceipt=live-recorded-provider-ab-check-v1")
    );
    assert!(selection_marker.contains("gpuForceProviderAbReady=true"));
}

#[test]
fn reads_effective_settings_identity_without_parsing_settings_payload() {
    let path = write_temp_json("effective-settings-identity-only", "{not json");

    let identity = makepad_effective_settings_identity_from_path(&path);
    let expected_path = path.display().to_string();

    assert_eq!(
        identity.source_effective_settings_path.as_deref(),
        Some(expected_path.as_str())
    );
    assert!(identity.source_modified_ns.is_some());
    assert!(identity.runtime_settings_changed_from(None, None, None));
    assert!(!identity.runtime_settings_changed_from(
        identity.source_effective_settings_path.as_deref(),
        identity.source_modified_ns,
        identity.runtime_settings_revision_key().as_deref()
    ));

    let parsed = read_mesh_replay_runtime_from_path(&path);
    assert_eq!(parsed.status, "rejected");
    assert_eq!(parsed.issue_code.as_deref(), Some(PARSE_ISSUE));
}

#[test]
fn effective_settings_identity_changes_when_file_modified() {
    let path = write_temp_json("effective-settings-identity-modified", "{not json");
    let first = makepad_effective_settings_identity_from_path(&path);

    wait_for_file_timestamp_tick();
    std::fs::write(&path, EFFECTIVE_SETTINGS_FIXTURE).expect("rewrite effective settings");
    let second = makepad_effective_settings_identity_from_path(&path);

    assert_eq!(
        second.source_effective_settings_path,
        first.source_effective_settings_path
    );
    assert!(second.runtime_settings_changed_from(
        first.source_effective_settings_path.as_deref(),
        first.source_modified_ns,
        first.runtime_settings_revision_key().as_deref()
    ));
}

#[test]
fn effective_settings_identity_prefers_revision_sidecar_scope_hashes() {
    let path = write_temp_json("effective-settings-identity-revision", "{not json");
    write_revision_sidecar(&path, "mesh-a");
    let first = makepad_effective_settings_identity_from_path(&path);

    wait_for_file_timestamp_tick();
    std::fs::write(&path, EFFECTIVE_SETTINGS_FIXTURE).expect("rewrite effective settings");
    let same_revision = makepad_effective_settings_identity_from_path(&path);

    assert!(first.source_revision_key.is_some());
    assert_eq!(same_revision.source_revision_key, first.source_revision_key);
    assert!(!same_revision.runtime_settings_changed_from(
        first.source_effective_settings_path.as_deref(),
        first.source_modified_ns,
        first.runtime_settings_revision_key().as_deref()
    ));

    write_revision_sidecar(&path, "mesh-b");
    let changed_revision = makepad_effective_settings_identity_from_path(&path);

    assert!(changed_revision.runtime_settings_changed_from(
        first.source_effective_settings_path.as_deref(),
        first.source_modified_ns,
        first.runtime_settings_revision_key().as_deref()
    ));
}

#[test]
fn effective_settings_identity_filters_unowned_scope_changes() {
    let path = write_temp_json("effective-settings-scoped-identity", "{not json");
    write_revision_sidecar_with_hashes(
        &path,
        "mesh-a",
        "camera-a",
        "stimulus-a",
        "matter-a",
        "particles-a",
    );
    let first = makepad_effective_settings_identity_from_path(&path);
    let mesh_key = first.scoped_revision_key(&["mesh_replay"]);
    let camera_key = first.scoped_revision_key(&["camera_projection"]);

    write_revision_sidecar_with_hashes(
        &path,
        "mesh-a",
        "camera-b",
        "stimulus-a",
        "matter-a",
        "particles-a",
    );
    let camera_changed = makepad_effective_settings_identity_from_path(&path);

    assert!(!camera_changed.changed_from_scopes(
        first.source_effective_settings_path.as_deref(),
        first.source_modified_ns,
        mesh_key.as_deref(),
        &["mesh_replay"]
    ));
    assert!(camera_changed.changed_from_scopes(
        first.source_effective_settings_path.as_deref(),
        first.source_modified_ns,
        camera_key.as_deref(),
        &["camera_projection"]
    ));

    std::fs::write(&path, EFFECTIVE_SETTINGS_FIXTURE).expect("rewrite effective settings");
    let adoption_identity = makepad_effective_settings_identity_from_path(&path);
    let selection = read_mesh_replay_runtime_from_path(&path);
    let adoption_key = adoption_identity.runtime_settings_revision_key();
    let adoption_marker =
        selection.adoption_marker_line("test", &adoption_identity, adoption_key.as_deref());
    assert!(adoption_marker.contains("status=applied"));
    assert!(adoption_marker.contains("revisionGate=scoped_revision_hash"));
    assert!(adoption_marker.contains("highRateJsonPayload=false"));
}

#[test]
fn effective_settings_identity_tracks_gpu_proof_scope_without_runtime_reload() {
    let path = write_temp_json("effective-settings-gpu-proof-identity", "{not json");
    write_revision_sidecar_with_hashes_and_gpu_proof(
        &path,
        "mesh-a",
        "camera-a",
        "matter-a",
        "particles-a",
        "proof-a",
    );
    let first = makepad_effective_settings_identity_from_path(&path);

    write_revision_sidecar_with_hashes_and_gpu_proof(
        &path,
        "mesh-a",
        "camera-a",
        "matter-a",
        "particles-a",
        "proof-b",
    );
    let proof_changed = makepad_effective_settings_identity_from_path(&path);

    assert!(!proof_changed.runtime_settings_changed_from(
        first.source_effective_settings_path.as_deref(),
        first.source_modified_ns,
        first.runtime_settings_revision_key().as_deref()
    ));
    assert!(proof_changed.gpu_proof_settings_changed_from(
        first.source_effective_settings_path.as_deref(),
        first.gpu_proof_settings_revision_key().as_deref()
    ));
    assert_eq!(
        proof_changed.gpu_proof_settings_revision_key().as_deref(),
        Some("gpu_proof=proof-b")
    );
}

#[test]
fn effective_settings_identity_accepts_bom_prefixed_revision_sidecar() {
    let path = write_temp_json("effective-settings-bom-identity", "{not json");
    write_revision_sidecar_with_hashes_and_gpu_proof(
        &path,
        "mesh-a",
        "camera-a",
        "matter-a",
        "particles-a",
        "proof-a",
    );
    let sidecar_path = path.with_file_name(EFFECTIVE_SETTINGS_REVISION_FILE_NAME);
    let sidecar_text = std::fs::read_to_string(&sidecar_path).expect("read generated sidecar");
    std::fs::write(&sidecar_path, format!("\u{feff}{sidecar_text}"))
        .expect("rewrite sidecar with BOM");

    let identity = makepad_effective_settings_identity_from_path(&path);

    assert!(identity.source_revision_key.is_some());
    assert_eq!(
        identity.gpu_proof_settings_revision_key().as_deref(),
        Some("gpu_proof=proof-a")
    );
}

#[test]
fn builds_recorded_replay_runtime_from_staged_sequence() {
    let recorded_settings = EFFECTIVE_SETTINGS_FIXTURE.replace(
        MESH_REPLAY_SOURCE_PUBLIC_SYNTHETIC_HAND_SEQUENCE,
        MESH_REPLAY_SOURCE_RECORDED_META_QUEST_HAND_LEFT,
    );
    let path = write_temp_json("recorded-effective-settings-runtime", &recorded_settings);
    write_mesh_replay_asset(
        &path,
        RECORDED_META_QUEST_HAND_LEFT_SEQUENCE_FILE,
        SYNTHETIC_SEQUENCE_FIXTURE,
    );

    let mut selection = read_mesh_replay_runtime_from_path(&path);

    assert_eq!(selection.status, "ready");
    assert!(selection.issue_code.is_none());
    assert!(selection.matter_surface_runtime.is_some());
    let runtime = selection.runtime.as_mut().expect("runtime selected");
    let first = runtime.step(0.0);
    assert!(first.enabled);
    let marker = runtime.config_marker_line("recorded-source-test");
    assert!(marker.contains("source=recorded-meta-quest-hand-left"));
    assert!(!marker.contains("rusty.xr"));
}

#[test]
fn recorded_replay_runtime_rejects_missing_staged_sequence() {
    let recorded_settings = EFFECTIVE_SETTINGS_FIXTURE.replace(
        MESH_REPLAY_SOURCE_PUBLIC_SYNTHETIC_HAND_SEQUENCE,
        MESH_REPLAY_SOURCE_RECORDED_META_QUEST_HAND_LEFT,
    );
    let path = write_temp_json(
        "recorded-effective-settings-missing-asset",
        &recorded_settings,
    );

    let selection = read_mesh_replay_runtime_from_path(&path);

    assert_eq!(selection.status, "rejected");
    assert!(selection.runtime.is_none());
    assert_eq!(selection.issue_code.as_deref(), Some(PARSE_ISSUE));
    assert!(selection
        .issue_evidence
        .as_deref()
        .is_some_and(|error| error.contains(RECORDED_META_QUEST_HAND_LEFT_SEQUENCE_FILE)));
}

#[test]
fn builds_feature_uniforms_from_canonical_effective_settings() {
    let unsupported_combined =
        EFFECTIVE_SETTINGS_FIXTURE.replace("\"value\": \"sdf\"", "\"value\": \"combined\"");
    let path = write_temp_json("effective-settings-feature-uniforms", &unsupported_combined);

    let selection = read_mesh_replay_runtime_from_path(&path);

    assert_eq!(
        selection.feature_uniforms,
        MakepadCameraShellFeatureUniforms {
            collision_enabled: 1.0,
            sdf_adf_overlay_mode: 0.0,
            particles_enabled: 1.0,
        }
    );
    assert!(selection.runtime.is_some());
    assert!(selection.matter_surface_runtime.is_some());
}

#[test]
fn records_mesh_replay_adapter_rejection_without_legacy_fallback() {
    let different_app =
        EFFECTIVE_SETTINGS_FIXTURE.replace(CAMERA_SHELL_APP_ID, "rusty-quest-makepad.other-shell");
    let path = write_temp_json("wrong-effective-settings-app", &different_app);

    let receipt = read_makepad_effective_settings_from_path(&path);

    assert_eq!(receipt.status, "ready");
    assert!(receipt.canonical_effective_settings_consumed);
    assert!(!receipt.mesh_replay_settings_present);
    assert_eq!(
        receipt.mesh_replay_adapter_status.as_deref(),
        Some("rejected")
    );
    assert!(receipt
        .mesh_replay_adapter_error
        .as_deref()
        .is_some_and(|error| error.contains("unexpected effective-settings app id")));
    assert!(!receipt.legacy_settings_fallback_used);
}

#[test]
fn records_mesh_replay_runtime_rejection_without_legacy_fallback() {
    let different_app =
        EFFECTIVE_SETTINGS_FIXTURE.replace(CAMERA_SHELL_APP_ID, "rusty-quest-makepad.other-shell");
    let path = write_temp_json("wrong-effective-settings-runtime-app", &different_app);

    let selection = read_mesh_replay_runtime_from_path(&path);

    assert_eq!(selection.status, "rejected");
    assert!(selection.runtime.is_none());
    assert_eq!(selection.issue_code.as_deref(), Some(PARSE_ISSUE));
    assert!(selection
        .issue_evidence
        .as_deref()
        .is_some_and(|error| error.contains("unexpected effective-settings app id")));
    let marker = selection.marker_line("test");
    assert!(marker.contains("schema=rusty.quest.makepad.mesh_replay.v1"));
    assert!(marker.contains("status=rejected"));
    assert!(!marker.contains("rusty.xr"));
}

#[test]
fn rejects_wrong_effective_settings_schema() {
    let damaged = EFFECTIVE_SETTINGS_FIXTURE.replace(
        EFFECTIVE_SETTINGS_SCHEMA,
        "rusty.gui.makepad.old_settings.v1",
    );
    let path = write_temp_json("wrong-effective-settings-schema", &damaged);

    let receipt = read_makepad_effective_settings_from_path(&path);

    assert_eq!(receipt.status, "rejected");
    assert_eq!(receipt.issue_code.as_deref(), Some(SCHEMA_ISSUE));
    assert!(!receipt.canonical_effective_settings_consumed);
    assert!(!receipt.legacy_settings_fallback_used);
}

#[test]
fn not_configured_receipt_does_not_use_legacy_fallback() {
    let receipt = not_configured_receipt();

    assert_eq!(receipt.status, "not_configured");
    assert_eq!(receipt.issue_code.as_deref(), Some(NOT_CONFIGURED_ISSUE));
    assert!(!receipt.legacy_settings_fallback_used);
}

fn write_temp_json(name: &str, text: &str) -> PathBuf {
    let stamp = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .expect("system clock before Unix epoch")
        .as_nanos();
    let root = std::env::temp_dir().join(format!("{name}-{stamp}"));
    std::fs::create_dir_all(&root).expect("create temp root");
    let path = root.join("settings.json");
    std::fs::write(&path, text).expect("write effective settings fixture");
    path
}

fn write_revision_sidecar(settings_path: &Path, mesh_replay_hash: &str) {
    write_revision_sidecar_with_hashes(
        settings_path,
        mesh_replay_hash,
        "camera-a",
        "stimulus-a",
        "matter-a",
        "particles-a",
    );
}

fn write_revision_sidecar_with_hashes(
    settings_path: &Path,
    mesh_replay_hash: &str,
    camera_projection_hash: &str,
    stimulus_hash: &str,
    matter_surface_hash: &str,
    particles_hash: &str,
) {
    write_revision_sidecar_with_hashes_and_optional_gpu_proof(
        settings_path,
        mesh_replay_hash,
        camera_projection_hash,
        stimulus_hash,
        matter_surface_hash,
        particles_hash,
        None,
    );
}

fn write_revision_sidecar_with_hashes_and_gpu_proof(
    settings_path: &Path,
    mesh_replay_hash: &str,
    camera_projection_hash: &str,
    matter_surface_hash: &str,
    particles_hash: &str,
    gpu_proof_hash: &str,
) {
    write_revision_sidecar_with_hashes_and_optional_gpu_proof(
        settings_path,
        mesh_replay_hash,
        camera_projection_hash,
        "stimulus-a",
        matter_surface_hash,
        particles_hash,
        Some(gpu_proof_hash),
    );
}

fn write_revision_sidecar_with_hashes_and_optional_gpu_proof(
    settings_path: &Path,
    mesh_replay_hash: &str,
    camera_projection_hash: &str,
    stimulus_hash: &str,
    matter_surface_hash: &str,
    particles_hash: &str,
    gpu_proof_hash: Option<&str>,
) {
    let sidecar_path = settings_path.with_file_name(EFFECTIVE_SETTINGS_REVISION_FILE_NAME);
    let gpu_proof_scope = gpu_proof_hash
        .map(|hash| {
            format!(
                r#",
"gpu_proof": {{ "revision_hash_sha256": "{hash}" }}"#
            )
        })
        .unwrap_or_default();
    let text = format!(
        r#"{{
  "schema": "{EFFECTIVE_SETTINGS_REVISION_SCHEMA}",
  "source_sha256": "source-a",
  "source_revision": 1,
  "scopes": {{
"mesh_replay": {{ "revision_hash_sha256": "{mesh_replay_hash}" }},
"camera_projection": {{ "revision_hash_sha256": "{camera_projection_hash}" }},
"stimulus": {{ "revision_hash_sha256": "{stimulus_hash}" }},
"matter_surface": {{ "revision_hash_sha256": "{matter_surface_hash}" }},
"particles": {{ "revision_hash_sha256": "{particles_hash}" }}{gpu_proof_scope}
  }}
}}"#
    );
    std::fs::write(sidecar_path, text).expect("write effective settings revision sidecar");
}

fn wait_for_file_timestamp_tick() {
    std::thread::sleep(std::time::Duration::from_millis(20));
}

fn write_mesh_replay_asset(settings_path: &Path, file_name: &str, text: &str) {
    let mesh_replay_dir = settings_path
        .parent()
        .expect("settings path has parent")
        .join("mesh-replay");
    std::fs::create_dir_all(&mesh_replay_dir).expect("create mesh replay dir");
    std::fs::write(mesh_replay_dir.join(file_name), text).expect("write mesh replay asset");
}
