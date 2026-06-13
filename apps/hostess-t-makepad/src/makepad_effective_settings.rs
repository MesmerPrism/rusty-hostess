use crate::runtime_settings::marker_token;
use rusty_makepad_settings::{EffectiveSettingsReport, EFFECTIVE_SETTINGS_SCHEMA};
use rusty_quest_makepad_camera_shell::{
    camera_shell_runtime_bundle_from_effective_settings_json_with_replay_asset_dir,
    CameraShellEffectiveConfig, MeshReplayRuntime, ParticleRenderAnimationMode,
    QuestMakepadForceAuthorityMode, QuestMakepadGpuForceProviderAbReceipt,
    QuestMakepadMatterSurfaceRuntime, SdfAdfRuntimeMode, REPLAY_MARKER_PREFIX, REPLAY_SCHEMA_ID,
};
use serde_json::{Map, Value};
use std::collections::BTreeMap;
use std::path::{Path, PathBuf};
use std::time::UNIX_EPOCH;

pub(crate) const EFFECTIVE_SETTINGS_RECEIPT_SCHEMA: &str =
    "rusty.hostess.makepad_effective_settings_receipt.v1";
const MARKER_PREFIX: &str = "RUSTY_HOSTESS_MAKEPAD_EFFECTIVE_SETTINGS";
const ADOPTION_MARKER_PREFIX: &str = "RUSTY_HOSTESS_MAKEPAD_EFFECTIVE_SETTINGS_ADOPTION";
const EFFECTIVE_SETTINGS_ADOPTION_SCHEMA: &str =
    "rusty.hostess.makepad_effective_settings_adoption.v1";
const NOT_CONFIGURED_ISSUE: &str = "hostess.issue.makepad_effective_settings_not_configured";
const READ_ISSUE: &str = "hostess.issue.makepad_effective_settings_read";
const PARSE_ISSUE: &str = "hostess.issue.makepad_effective_settings_parse";
const SCHEMA_ISSUE: &str = "hostess.issue.makepad_effective_settings_schema";
const MESH_REPLAY_ADAPTER: &str = "rusty-quest-makepad-camera-shell";
const EFFECTIVE_SETTINGS_REVISION_FILE_NAME: &str = "makepad-effective-settings.revision.json";
const EFFECTIVE_SETTINGS_REVISION_SCHEMA: &str = "rusty.gui.makepad.effective_settings_revision.v1";
const EFFECTIVE_SETTINGS_RUNTIME_SCOPES: &[&str] = &[
    "mesh_replay",
    "camera_projection",
    "matter_surface",
    "particles",
];
const EFFECTIVE_SETTINGS_GPU_PROOF_SCOPES: &[&str] = &["gpu_proof"];

macro_rules! insert_json_field {
    ($object:expr, $key:expr, $value:expr $(,)?) => {{
        let value = serde_json::to_value(&$value).unwrap_or(Value::Null);
        $object.insert($key.to_string(), value);
    }};
}

#[cfg(target_os = "android")]
const ANDROID_INTERNAL_SETTINGS_ROOT: &str =
    "/data/user/0/io.github.mesmerprism.rustyhostess.makepad/files/hostess-t/settings";
#[cfg(target_os = "android")]
const ANDROID_EXTERNAL_SETTINGS_ROOT: &str =
    "/sdcard/Android/data/io.github.mesmerprism.rustyhostess.makepad/files/hostess-t/settings";

#[derive(Clone, Debug, Default)]
pub(crate) struct MakepadEffectiveSettingsReceipt {
    status: String,
    issue_code: Option<String>,
    issue_evidence: Option<String>,
    source_effective_settings_path: Option<String>,
    source_effective_settings_schema: Option<String>,
    source_app_id: Option<String>,
    source_surface_schema: Option<String>,
    source_surface_version: Option<u32>,
    source_revision: Option<u64>,
    source_generated_at: Option<String>,
    setting_count: usize,
    canonical_effective_settings_consumed: bool,
    mesh_replay_settings_present: bool,
    mesh_replay_adapter: Option<String>,
    mesh_replay_adapter_status: Option<String>,
    mesh_replay_adapter_error: Option<String>,
    mesh_replay_enabled: Option<bool>,
    mesh_replay_source: Option<String>,
    mesh_replay_speed: Option<f64>,
    mesh_replay_opacity: Option<f64>,
    render_scale: Option<f64>,
    camera_streaming_enabled: Option<bool>,
    collision_enabled: Option<bool>,
    sdf_adf_overlay_mode: Option<String>,
    sdf_adf_runtime_mode: Option<String>,
    sdf_adf_unsupported_future_mode: Option<bool>,
    particles_enabled: Option<bool>,
    particle_render_draw_limit: Option<usize>,
    particle_render_animation_mode: Option<String>,
    particle_render_size_scale: Option<f64>,
    matter_surface_native_runtime_configured: Option<bool>,
    matter_surface_adf_debug_enabled: Option<bool>,
    matter_surface_adf_max_depth: Option<u32>,
    matter_surface_adf_max_cells: Option<usize>,
    matter_surface_adf_error_tolerance: Option<f64>,
    matter_surface_sdf_adf_debug_update_interval_frames: Option<usize>,
    matter_surface_particle_count: Option<usize>,
    matter_surface_leaf_triangle_count: Option<usize>,
    matter_surface_particle_distance_refresh_policy: Option<String>,
    matter_surface_particle_force_authority: Option<String>,
    matter_surface_gpu_force_provider_ab_receipt: Option<String>,
    matter_surface_gpu_force_provider_ab_ready: Option<bool>,
    matter_surface_particle_force_source: Option<String>,
    matter_surface_particle_force_update_interval_frames: Option<usize>,
    matter_surface_particle_force_compare_probe_count: Option<usize>,
    matter_surface_particle_execution_backend: Option<String>,
    matter_surface_particle_execution_batch_size: Option<usize>,
    matter_surface_particle_execution_max_threads: Option<usize>,
    matter_surface_particle_max_frame_delta_seconds: Option<f64>,
    legacy_settings_fallback_used: bool,
    receipt_written: bool,
}

#[derive(Clone, Copy, Debug, Default, PartialEq)]
pub(crate) struct MakepadCameraShellFeatureUniforms {
    pub(crate) collision_enabled: f32,
    pub(crate) sdf_adf_overlay_mode: f32,
    pub(crate) particles_enabled: f32,
}

impl MakepadCameraShellFeatureUniforms {
    fn from_effective_config(config: &CameraShellEffectiveConfig) -> Self {
        let runtime_mode = SdfAdfRuntimeMode::from_overlay_mode(config.sdf_adf_overlay_mode);
        Self {
            collision_enabled: if config.collision_enabled { 1.0 } else { 0.0 },
            sdf_adf_overlay_mode: match runtime_mode {
                SdfAdfRuntimeMode::Sdf => 1.0,
                SdfAdfRuntimeMode::Adf => 2.0,
                _ => 0.0,
            },
            particles_enabled: if config.particles_enabled { 1.0 } else { 0.0 },
        }
    }
}

#[derive(Debug)]
pub(crate) struct MakepadMeshReplayRuntimeSelection {
    pub(crate) status: String,
    pub(crate) issue_code: Option<String>,
    pub(crate) issue_evidence: Option<String>,
    pub(crate) source_effective_settings_path: Option<String>,
    pub(crate) source_modified_ns: Option<u128>,
    pub(crate) render_scale: Option<f32>,
    pub(crate) camera_streaming_enabled: Option<bool>,
    pub(crate) particle_render_draw_limit: Option<usize>,
    pub(crate) particle_render_animation_mode: Option<ParticleRenderAnimationMode>,
    pub(crate) particle_render_size_scale: Option<f32>,
    pub(crate) particle_force_authority: Option<QuestMakepadForceAuthorityMode>,
    pub(crate) gpu_force_provider_ab_receipt: Option<QuestMakepadGpuForceProviderAbReceipt>,
    pub(crate) feature_uniforms: MakepadCameraShellFeatureUniforms,
    pub(crate) runtime: Option<MeshReplayRuntime>,
    pub(crate) matter_surface_runtime: Option<QuestMakepadMatterSurfaceRuntime>,
}

#[derive(Clone, Debug, Default, PartialEq, Eq)]
pub(crate) struct MakepadEffectiveSettingsIdentity {
    pub(crate) source_effective_settings_path: Option<String>,
    pub(crate) source_modified_ns: Option<u128>,
    pub(crate) source_revision_key: Option<String>,
    pub(crate) scope_revision_keys: BTreeMap<String, String>,
    pub(crate) source_revision_manifest_path: Option<String>,
    pub(crate) source_revision_manifest_modified_ns: Option<u128>,
}

impl MakepadEffectiveSettingsIdentity {
    pub(crate) fn runtime_settings_revision_key(&self) -> Option<String> {
        self.scoped_revision_key(EFFECTIVE_SETTINGS_RUNTIME_SCOPES)
    }

    pub(crate) fn gpu_proof_settings_revision_key(&self) -> Option<String> {
        self.scoped_revision_key(EFFECTIVE_SETTINGS_GPU_PROOF_SCOPES)
    }

    pub(crate) fn gpu_proof_settings_changed_from(
        &self,
        previous_path: Option<&str>,
        previous_gpu_proof_revision_key: Option<&str>,
    ) -> bool {
        if self.source_effective_settings_path.as_deref() != previous_path {
            return false;
        }
        if let Some(gpu_proof_revision_key) =
            self.scoped_revision_key(EFFECTIVE_SETTINGS_GPU_PROOF_SCOPES)
        {
            return Some(gpu_proof_revision_key.as_str()) != previous_gpu_proof_revision_key;
        }
        false
    }

    pub(crate) fn runtime_settings_changed_from(
        &self,
        previous_path: Option<&str>,
        previous_modified_ns: Option<u128>,
        previous_runtime_revision_key: Option<&str>,
    ) -> bool {
        self.changed_from_scopes(
            previous_path,
            previous_modified_ns,
            previous_runtime_revision_key,
            EFFECTIVE_SETTINGS_RUNTIME_SCOPES,
        )
    }

    pub(crate) fn changed_from_scopes(
        &self,
        previous_path: Option<&str>,
        previous_modified_ns: Option<u128>,
        previous_scoped_revision_key: Option<&str>,
        scopes: &[&str],
    ) -> bool {
        if self.source_effective_settings_path.as_deref() != previous_path {
            return true;
        }
        if let Some(scoped_revision_key) = self.scoped_revision_key(scopes) {
            return Some(scoped_revision_key.as_str()) != previous_scoped_revision_key;
        }
        self.source_modified_ns != previous_modified_ns
    }

    pub(crate) fn scoped_revision_key(&self, scopes: &[&str]) -> Option<String> {
        let mut parts = Vec::new();
        for scope in scopes {
            if let Some(scope_revision_key) = self.scope_revision_keys.get(*scope) {
                parts.push(format!("{scope}={scope_revision_key}"));
            }
        }
        if parts.is_empty() {
            None
        } else {
            Some(parts.join("|"))
        }
    }
}

impl MakepadMeshReplayRuntimeSelection {
    pub(crate) fn marker_line(&self, phase: &str) -> String {
        format!(
            "{} schema={} phase={} status={} issue={} evidence={} sourcePath={} sourceModifiedNs={} matterSurfaceRuntimeSelected={} particleForceAuthority={} gpuForceProviderAbReceipt={} gpuForceProviderAbReady={} particleRenderDrawLimit={} particleRenderAnimationMode={} particleRenderSizeScale={}",
            REPLAY_MARKER_PREFIX,
            REPLAY_SCHEMA_ID,
            marker_token(phase),
            marker_token(&self.status),
            marker_option(self.issue_code.as_deref()),
            marker_option(self.issue_evidence.as_deref()),
            marker_option(self.source_effective_settings_path.as_deref()),
            self.source_modified_ns
                .map(|value| value.to_string())
                .unwrap_or_else(|| "none".to_string()),
            self.matter_surface_runtime.is_some(),
            marker_option(
                self.particle_force_authority
                    .map(QuestMakepadForceAuthorityMode::as_str)
            ),
            marker_option(
                self.gpu_force_provider_ab_receipt
                    .map(QuestMakepadGpuForceProviderAbReceipt::as_str)
            ),
            self.gpu_force_provider_ab_receipt
                .map(QuestMakepadGpuForceProviderAbReceipt::live_recorded_provider_ab_ready)
                .map(|value| value.to_string())
                .unwrap_or_else(|| "none".to_string()),
            marker_usize(self.particle_render_draw_limit),
            marker_option(
                self.particle_render_animation_mode
                    .map(ParticleRenderAnimationMode::as_str)
            ),
            marker_f32(self.particle_render_size_scale),
        )
    }

    pub(crate) fn adoption_marker_line(
        &self,
        phase: &str,
        identity: &MakepadEffectiveSettingsIdentity,
        scoped_revision_key: Option<&str>,
    ) -> String {
        let adoption_status = if self.status == "ready" && self.runtime.is_some() {
            "applied"
        } else {
            self.status.as_str()
        };
        format!(
            "{} schema={} phase={} status={} issue={} sourcePath={} sourceRevisionKey={} scopedRevisionKey={} scopeCount={} scopes={} revisionGate={} detailRead=true highRateJsonPayload=false",
            ADOPTION_MARKER_PREFIX,
            EFFECTIVE_SETTINGS_ADOPTION_SCHEMA,
            marker_token(phase),
            marker_token(adoption_status),
            marker_option(self.issue_code.as_deref()),
            marker_option(identity.source_effective_settings_path.as_deref()),
            marker_option(identity.source_revision_key.as_deref()),
            marker_option(scoped_revision_key),
            EFFECTIVE_SETTINGS_RUNTIME_SCOPES.len(),
            marker_token(&EFFECTIVE_SETTINGS_RUNTIME_SCOPES.join(",")),
            if scoped_revision_key.is_some() {
                "scoped_revision_hash"
            } else {
                "path_mtime_fallback"
            },
        )
    }
}

impl MakepadEffectiveSettingsReceipt {
    pub(crate) fn marker_line(&self, phase: &str) -> String {
        format!(
            "{} schema={} phase={} status={} issue={} sourcePath={} app={} revision={} settingCount={} canonicalEffectiveSettingsConsumed={} meshReplaySettingsPresent={} meshReplayAdapter={} meshReplayAdapterStatus={} meshReplayAdapterError={} meshReplayEnabled={} meshReplaySource={} meshReplaySpeed={} meshReplayOpacity={} renderScale={} cameraStreamingEnabled={} collisionEnabled={} sdfAdfOverlayMode={} sdfAdfRuntimeMode={} sdfAdfUnsupportedFutureMode={} particlesEnabled={} particleRenderDrawLimit={} particleRenderAnimationMode={} particleRenderSizeScale={} matterSurfaceNativeRuntimeConfigured={} matterSurfaceAdfDebugEnabled={} matterSurfaceAdfMaxDepth={} matterSurfaceAdfMaxCells={} matterSurfaceAdfErrorTolerance={} matterSurfaceSdfAdfDebugUpdateIntervalFrames={} matterSurfaceParticleCount={} matterSurfaceLeafTriangleCount={} matterSurfaceParticleDistanceRefreshPolicy={} matterSurfaceParticleForceAuthority={} matterSurfaceGpuForceProviderAbReceipt={} matterSurfaceGpuForceProviderAbReady={} matterSurfaceParticleForceSource={} matterSurfaceParticleForceUpdateIntervalFrames={} matterSurfaceParticleForceCompareProbeCount={} matterSurfaceParticleExecutionBackend={} matterSurfaceParticleExecutionBatchSize={} matterSurfaceParticleExecutionMaxThreads={} matterSurfaceParticleMaxFrameDeltaSeconds={} legacySettingsFallbackUsed={}",
            MARKER_PREFIX,
            EFFECTIVE_SETTINGS_RECEIPT_SCHEMA,
            marker_token(phase),
            marker_token(&self.status),
            marker_option(self.issue_code.as_deref()),
            marker_option(self.source_effective_settings_path.as_deref()),
            marker_option(self.source_app_id.as_deref()),
            self.source_revision
                .map(|value| value.to_string())
                .unwrap_or_else(|| "none".to_string()),
            self.setting_count,
            self.canonical_effective_settings_consumed,
            self.mesh_replay_settings_present,
            marker_option(self.mesh_replay_adapter.as_deref()),
            marker_option(self.mesh_replay_adapter_status.as_deref()),
            marker_option(self.mesh_replay_adapter_error.as_deref()),
            self.mesh_replay_enabled
                .map(|value| value.to_string())
                .unwrap_or_else(|| "none".to_string()),
            marker_option(self.mesh_replay_source.as_deref()),
            marker_f64(self.mesh_replay_speed),
            marker_f64(self.mesh_replay_opacity),
            marker_f64(self.render_scale),
            marker_bool(self.camera_streaming_enabled),
            marker_bool(self.collision_enabled),
            marker_option(self.sdf_adf_overlay_mode.as_deref()),
            marker_option(self.sdf_adf_runtime_mode.as_deref()),
            marker_bool(self.sdf_adf_unsupported_future_mode),
            marker_bool(self.particles_enabled),
            marker_usize(self.particle_render_draw_limit),
            marker_option(self.particle_render_animation_mode.as_deref()),
            marker_f64(self.particle_render_size_scale),
            marker_bool(self.matter_surface_native_runtime_configured),
            marker_bool(self.matter_surface_adf_debug_enabled),
            marker_u32(self.matter_surface_adf_max_depth),
            marker_usize(self.matter_surface_adf_max_cells),
            marker_f64(self.matter_surface_adf_error_tolerance),
            marker_usize(self.matter_surface_sdf_adf_debug_update_interval_frames),
            marker_usize(self.matter_surface_particle_count),
            marker_usize(self.matter_surface_leaf_triangle_count),
            marker_option(self.matter_surface_particle_distance_refresh_policy.as_deref()),
            marker_option(self.matter_surface_particle_force_authority.as_deref()),
            marker_option(self.matter_surface_gpu_force_provider_ab_receipt.as_deref()),
            marker_bool(self.matter_surface_gpu_force_provider_ab_ready),
            marker_option(self.matter_surface_particle_force_source.as_deref()),
            marker_usize(self.matter_surface_particle_force_update_interval_frames),
            marker_usize(self.matter_surface_particle_force_compare_probe_count),
            marker_option(self.matter_surface_particle_execution_backend.as_deref()),
            marker_usize(self.matter_surface_particle_execution_batch_size),
            marker_usize(self.matter_surface_particle_execution_max_threads),
            marker_f64(self.matter_surface_particle_max_frame_delta_seconds),
            self.legacy_settings_fallback_used,
        )
    }

    pub(crate) fn render_scale(&self) -> Option<f64> {
        self.render_scale
    }

    pub(crate) fn camera_streaming_enabled(&self) -> Option<bool> {
        self.camera_streaming_enabled
    }

    fn to_json_value(&self) -> Value {
        let mut object = Map::new();
        insert_json_field!(&mut object, "$schema", EFFECTIVE_SETTINGS_RECEIPT_SCHEMA);
        insert_json_field!(&mut object, "status", &self.status);
        insert_json_field!(&mut object, "issue_code", &self.issue_code);
        insert_json_field!(&mut object, "issue_evidence", &self.issue_evidence);
        insert_json_field!(
            &mut object,
            "source_effective_settings_path",
            &self.source_effective_settings_path,
        );
        insert_json_field!(
            &mut object,
            "source_effective_settings_schema",
            &self.source_effective_settings_schema,
        );
        insert_json_field!(&mut object, "source_app_id", &self.source_app_id);
        insert_json_field!(
            &mut object,
            "source_surface_schema",
            &self.source_surface_schema,
        );
        insert_json_field!(
            &mut object,
            "source_surface_version",
            self.source_surface_version,
        );
        insert_json_field!(&mut object, "source_revision", self.source_revision);
        insert_json_field!(
            &mut object,
            "source_generated_at",
            &self.source_generated_at,
        );
        insert_json_field!(&mut object, "setting_count", self.setting_count);
        insert_json_field!(
            &mut object,
            "canonical_effective_settings_consumed",
            self.canonical_effective_settings_consumed,
        );
        insert_json_field!(
            &mut object,
            "mesh_replay_settings_present",
            self.mesh_replay_settings_present,
        );
        insert_json_field!(
            &mut object,
            "mesh_replay_adapter",
            &self.mesh_replay_adapter,
        );
        insert_json_field!(
            &mut object,
            "mesh_replay_adapter_status",
            &self.mesh_replay_adapter_status,
        );
        insert_json_field!(
            &mut object,
            "mesh_replay_adapter_error",
            &self.mesh_replay_adapter_error,
        );
        insert_json_field!(&mut object, "mesh_replay_enabled", self.mesh_replay_enabled);
        insert_json_field!(&mut object, "mesh_replay_source", &self.mesh_replay_source);
        insert_json_field!(&mut object, "mesh_replay_speed", self.mesh_replay_speed);
        insert_json_field!(&mut object, "mesh_replay_opacity", self.mesh_replay_opacity);
        insert_json_field!(&mut object, "render_scale", self.render_scale);
        insert_json_field!(
            &mut object,
            "camera_streaming_enabled",
            self.camera_streaming_enabled,
        );
        insert_json_field!(&mut object, "collision_enabled", self.collision_enabled);
        insert_json_field!(
            &mut object,
            "sdf_adf_overlay_mode",
            &self.sdf_adf_overlay_mode,
        );
        insert_json_field!(
            &mut object,
            "sdf_adf_runtime_mode",
            &self.sdf_adf_runtime_mode,
        );
        insert_json_field!(
            &mut object,
            "sdf_adf_unsupported_future_mode",
            self.sdf_adf_unsupported_future_mode,
        );
        insert_json_field!(&mut object, "particles_enabled", self.particles_enabled);
        insert_json_field!(
            &mut object,
            "particle_render_draw_limit",
            self.particle_render_draw_limit,
        );
        insert_json_field!(
            &mut object,
            "particle_render_animation_mode",
            &self.particle_render_animation_mode,
        );
        insert_json_field!(
            &mut object,
            "particle_render_size_scale",
            self.particle_render_size_scale,
        );
        insert_json_field!(
            &mut object,
            "matter_surface_native_runtime_configured",
            self.matter_surface_native_runtime_configured,
        );
        insert_json_field!(
            &mut object,
            "matter_surface_adf_debug_enabled",
            self.matter_surface_adf_debug_enabled,
        );
        insert_json_field!(
            &mut object,
            "matter_surface_adf_max_depth",
            self.matter_surface_adf_max_depth,
        );
        insert_json_field!(
            &mut object,
            "matter_surface_adf_max_cells",
            self.matter_surface_adf_max_cells,
        );
        insert_json_field!(
            &mut object,
            "matter_surface_adf_error_tolerance",
            self.matter_surface_adf_error_tolerance,
        );
        insert_json_field!(
            &mut object,
            "matter_surface_sdf_adf_debug_update_interval_frames",
            self.matter_surface_sdf_adf_debug_update_interval_frames,
        );
        insert_json_field!(
            &mut object,
            "matter_surface_particle_count",
            self.matter_surface_particle_count,
        );
        insert_json_field!(
            &mut object,
            "matter_surface_leaf_triangle_count",
            self.matter_surface_leaf_triangle_count,
        );
        insert_json_field!(
            &mut object,
            "matter_surface_particle_distance_refresh_policy",
            &self.matter_surface_particle_distance_refresh_policy,
        );
        insert_json_field!(
            &mut object,
            "matter_surface_particle_force_authority",
            &self.matter_surface_particle_force_authority,
        );
        insert_json_field!(
            &mut object,
            "matter_surface_gpu_force_provider_ab_receipt",
            &self.matter_surface_gpu_force_provider_ab_receipt,
        );
        insert_json_field!(
            &mut object,
            "matter_surface_gpu_force_provider_ab_ready",
            self.matter_surface_gpu_force_provider_ab_ready,
        );
        insert_json_field!(
            &mut object,
            "matter_surface_particle_force_source",
            &self.matter_surface_particle_force_source,
        );
        insert_json_field!(
            &mut object,
            "matter_surface_particle_force_update_interval_frames",
            self.matter_surface_particle_force_update_interval_frames,
        );
        insert_json_field!(
            &mut object,
            "matter_surface_particle_force_compare_probe_count",
            self.matter_surface_particle_force_compare_probe_count,
        );
        insert_json_field!(
            &mut object,
            "matter_surface_particle_execution_backend",
            &self.matter_surface_particle_execution_backend,
        );
        insert_json_field!(
            &mut object,
            "matter_surface_particle_execution_batch_size",
            self.matter_surface_particle_execution_batch_size,
        );
        insert_json_field!(
            &mut object,
            "matter_surface_particle_execution_max_threads",
            self.matter_surface_particle_execution_max_threads,
        );
        insert_json_field!(
            &mut object,
            "matter_surface_particle_max_frame_delta_seconds",
            self.matter_surface_particle_max_frame_delta_seconds,
        );
        insert_json_field!(
            &mut object,
            "legacy_settings_fallback_used",
            self.legacy_settings_fallback_used,
        );
        insert_json_field!(&mut object, "receipt_written", self.receipt_written);
        Value::Object(object)
    }
}

pub(crate) fn selected_makepad_effective_settings_identity() -> MakepadEffectiveSettingsIdentity {
    selected_effective_settings_path()
        .map(|path| makepad_effective_settings_identity_from_path(&path))
        .unwrap_or_default()
}

pub(crate) fn makepad_effective_settings_identity_from_path(
    path: &Path,
) -> MakepadEffectiveSettingsIdentity {
    let revision_identity = effective_settings_revision_identity_from_path(path);
    MakepadEffectiveSettingsIdentity {
        source_effective_settings_path: Some(path.display().to_string()),
        source_modified_ns: file_modified_ns(path),
        source_revision_key: revision_identity
            .as_ref()
            .map(|identity| identity.revision_key.clone()),
        scope_revision_keys: revision_identity
            .as_ref()
            .map(|identity| identity.scope_revision_keys.clone())
            .unwrap_or_default(),
        source_revision_manifest_path: revision_identity
            .as_ref()
            .map(|identity| identity.manifest_path.display().to_string()),
        source_revision_manifest_modified_ns: revision_identity
            .as_ref()
            .and_then(|identity| identity.manifest_modified_ns),
    }
}

pub(crate) fn read_selected_makepad_effective_settings() -> MakepadEffectiveSettingsReceipt {
    let Some(path) = selected_effective_settings_path() else {
        return not_configured_receipt();
    };
    read_makepad_effective_settings_from_path(&path)
}

pub(crate) fn read_makepad_effective_settings_from_path(
    path: &Path,
) -> MakepadEffectiveSettingsReceipt {
    let text = match std::fs::read_to_string(path) {
        Ok(text) => text,
        Err(error) => {
            return rejected_receipt(Some(path), READ_ISSUE, &format!("read failed: {error}"))
        }
    };
    let report = match serde_json::from_str::<EffectiveSettingsReport>(&text) {
        Ok(report) => report,
        Err(error) => {
            return rejected_receipt(Some(path), PARSE_ISSUE, &format!("parse failed: {error}"))
        }
    };
    if report.schema != EFFECTIVE_SETTINGS_SCHEMA {
        return rejected_receipt(
            Some(path),
            SCHEMA_ISSUE,
            &format!("unsupported schema {}", report.schema),
        );
    }
    ready_receipt(path, report, &text)
}

pub(crate) fn read_selected_mesh_replay_runtime() -> MakepadMeshReplayRuntimeSelection {
    let Some(path) = selected_effective_settings_path() else {
        return MakepadMeshReplayRuntimeSelection {
            status: "not_configured".to_string(),
            issue_code: Some(NOT_CONFIGURED_ISSUE.to_string()),
            issue_evidence: Some("No Makepad effective-settings path was configured".to_string()),
            source_effective_settings_path: None,
            source_modified_ns: None,
            render_scale: None,
            camera_streaming_enabled: None,
            particle_render_draw_limit: None,
            particle_render_animation_mode: None,
            particle_render_size_scale: None,
            particle_force_authority: None,
            gpu_force_provider_ab_receipt: None,
            feature_uniforms: MakepadCameraShellFeatureUniforms::default(),
            runtime: None,
            matter_surface_runtime: None,
        };
    };
    read_mesh_replay_runtime_from_path(&path)
}

pub(crate) fn read_mesh_replay_runtime_from_path(path: &Path) -> MakepadMeshReplayRuntimeSelection {
    let source_modified_ns = file_modified_ns(path);
    let text = match std::fs::read_to_string(path) {
        Ok(text) => text,
        Err(error) => {
            return MakepadMeshReplayRuntimeSelection {
                status: "rejected".to_string(),
                issue_code: Some(READ_ISSUE.to_string()),
                issue_evidence: Some(format!("read failed: {error}")),
                source_effective_settings_path: Some(path.display().to_string()),
                source_modified_ns,
                render_scale: None,
                camera_streaming_enabled: None,
                particle_render_draw_limit: None,
                particle_render_animation_mode: None,
                particle_render_size_scale: None,
                particle_force_authority: None,
                gpu_force_provider_ab_receipt: None,
                feature_uniforms: MakepadCameraShellFeatureUniforms::default(),
                runtime: None,
                matter_surface_runtime: None,
            };
        }
    };
    let replay_asset_dir = path.parent().unwrap_or_else(|| Path::new("."));
    match camera_shell_runtime_bundle_from_effective_settings_json_with_replay_asset_dir(
        &text,
        replay_asset_dir,
    ) {
        Ok(bundle) => {
            let feature_uniforms =
                MakepadCameraShellFeatureUniforms::from_effective_config(&bundle.effective_config);
            MakepadMeshReplayRuntimeSelection {
                status: "ready".to_string(),
                issue_code: None,
                issue_evidence: None,
                source_effective_settings_path: Some(path.display().to_string()),
                source_modified_ns,
                render_scale: Some(bundle.effective_config.render_scale),
                camera_streaming_enabled: Some(bundle.effective_config.camera_streaming_enabled),
                particle_render_draw_limit: Some(
                    bundle.effective_config.particle_render_draw_limit,
                ),
                particle_render_animation_mode: Some(
                    bundle.effective_config.particle_render_animation_mode,
                ),
                particle_render_size_scale: Some(
                    bundle.effective_config.particle_render_size_scale,
                ),
                particle_force_authority: Some(bundle.effective_config.particle_force_authority),
                gpu_force_provider_ab_receipt: Some(
                    bundle.effective_config.gpu_force_provider_ab_receipt,
                ),
                feature_uniforms,
                runtime: Some(bundle.mesh_replay_runtime),
                matter_surface_runtime: Some(bundle.matter_surface_runtime),
            }
        }
        Err(error) => MakepadMeshReplayRuntimeSelection {
            status: "rejected".to_string(),
            issue_code: Some(PARSE_ISSUE.to_string()),
            issue_evidence: Some(error.to_string()),
            source_effective_settings_path: Some(path.display().to_string()),
            source_modified_ns,
            render_scale: None,
            camera_streaming_enabled: None,
            particle_render_draw_limit: None,
            particle_render_animation_mode: None,
            particle_render_size_scale: None,
            particle_force_authority: None,
            gpu_force_provider_ab_receipt: None,
            feature_uniforms: MakepadCameraShellFeatureUniforms::default(),
            runtime: None,
            matter_surface_runtime: None,
        },
    }
}

pub(crate) fn write_selected_makepad_effective_settings_receipt(
    receipt: &MakepadEffectiveSettingsReceipt,
) -> Result<Option<PathBuf>, String> {
    let Some(path) = selected_effective_settings_receipt_output_path() else {
        return Ok(None);
    };
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent)
            .map_err(|error| format!("create {}: {error}", parent.display()))?;
    }
    let mut writable = receipt.clone();
    writable.receipt_written = true;
    let json = serde_json::to_string_pretty(&writable.to_json_value())
        .map_err(|error| format!("encode Makepad effective-settings receipt: {error}"))?;
    std::fs::write(&path, format!("{json}\n"))
        .map_err(|error| format!("write {}: {error}", path.display()))?;
    Ok(Some(path))
}

fn ready_receipt(
    path: &Path,
    report: EffectiveSettingsReport,
    raw_json: &str,
) -> MakepadEffectiveSettingsReceipt {
    let mesh_replay_adapter = Some(MESH_REPLAY_ADAPTER.to_string());
    let (
        mesh_replay_adapter_status,
        mesh_replay_adapter_error,
        mesh_replay_settings_present,
        mesh_replay_enabled,
        mesh_replay_source,
        mesh_replay_speed,
        mesh_replay_opacity,
        render_scale,
        camera_streaming_enabled,
        collision_enabled,
        sdf_adf_overlay_mode,
        sdf_adf_runtime_mode,
        sdf_adf_unsupported_future_mode,
        particles_enabled,
        particle_render_draw_limit,
        particle_render_animation_mode,
        particle_render_size_scale,
        matter_surface_native_runtime_configured,
        matter_surface_adf_debug_enabled,
        matter_surface_adf_max_depth,
        matter_surface_adf_max_cells,
        matter_surface_adf_error_tolerance,
        matter_surface_sdf_adf_debug_update_interval_frames,
        matter_surface_particle_count,
        matter_surface_leaf_triangle_count,
        matter_surface_particle_distance_refresh_policy,
        matter_surface_particle_force_authority,
        matter_surface_gpu_force_provider_ab_receipt,
        matter_surface_gpu_force_provider_ab_ready,
        matter_surface_particle_force_source,
        matter_surface_particle_force_update_interval_frames,
        matter_surface_particle_force_compare_probe_count,
        matter_surface_particle_execution_backend,
        matter_surface_particle_execution_batch_size,
        matter_surface_particle_execution_max_threads,
        matter_surface_particle_max_frame_delta_seconds,
    ) = match CameraShellEffectiveConfig::from_effective_settings_json(raw_json) {
        Ok(config) => {
            let runtime_mode = SdfAdfRuntimeMode::from_overlay_mode(config.sdf_adf_overlay_mode);
            (
                Some("ready".to_string()),
                None,
                true,
                Some(config.replay.enabled),
                Some(config.replay.source),
                Some(f64::from(config.replay.speed)),
                Some(f64::from(config.replay.opacity)),
                Some(f64::from(config.render_scale)),
                Some(config.camera_streaming_enabled),
                Some(config.collision_enabled),
                Some(config.sdf_adf_overlay_mode.as_str().to_string()),
                Some(runtime_mode.as_str().to_string()),
                Some(runtime_mode.is_unsupported_adf_placeholder()),
                Some(config.particles_enabled),
                Some(config.particle_render_draw_limit),
                Some(config.particle_render_animation_mode.as_str().to_string()),
                Some(f64::from(config.particle_render_size_scale)),
                Some(config.matter_surface.enabled),
                Some(config.matter_surface.adf_debug_enabled),
                Some(config.matter_surface.adf_debug_config.max_depth),
                Some(config.matter_surface.adf_debug_config.max_cells),
                Some(f64::from(
                    config.matter_surface.adf_debug_config.error_tolerance,
                )),
                Some(
                    config
                        .matter_surface
                        .sdf_adf_debug_update_interval_frames
                        .get(),
                ),
                Some(config.matter_surface.particle_count),
                Some(config.matter_surface.leaf_triangle_count),
                Some(
                    config
                        .matter_surface
                        .particle_distance_refresh_policy
                        .marker_value()
                        .to_string(),
                ),
                Some(config.particle_force_authority.as_str().to_string()),
                Some(config.gpu_force_provider_ab_receipt.as_str().to_string()),
                Some(
                    config
                        .gpu_force_provider_ab_receipt
                        .live_recorded_provider_ab_ready(),
                ),
                Some(
                    config
                        .matter_surface
                        .particle_force_source
                        .marker_value()
                        .to_string(),
                ),
                Some(
                    config
                        .matter_surface
                        .particle_force_update_interval_frames
                        .get(),
                ),
                Some(config.matter_surface.particle_force_compare_probe_count),
                Some(
                    config
                        .matter_surface
                        .particle_execution_backend
                        .marker_value()
                        .to_string(),
                ),
                Some(config.matter_surface.particle_execution_batch_size.get()),
                config.matter_surface.particle_execution_max_threads,
                config
                    .matter_surface
                    .particle_max_frame_delta_seconds
                    .map(f64::from),
            )
        }
        Err(error) => (
            Some("rejected".to_string()),
            Some(error.to_string()),
            false,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
        ),
    };

    MakepadEffectiveSettingsReceipt {
        status: "ready".to_string(),
        issue_code: None,
        issue_evidence: None,
        source_effective_settings_path: Some(path.display().to_string()),
        source_effective_settings_schema: Some(report.schema),
        source_app_id: Some(report.app_id),
        source_surface_schema: Some(report.surface_schema),
        source_surface_version: Some(report.surface_version),
        source_revision: Some(report.revision),
        source_generated_at: Some(report.generated_at),
        setting_count: report.settings.len(),
        canonical_effective_settings_consumed: true,
        mesh_replay_settings_present,
        mesh_replay_adapter,
        mesh_replay_adapter_status,
        mesh_replay_adapter_error,
        mesh_replay_enabled,
        mesh_replay_source,
        mesh_replay_speed,
        mesh_replay_opacity,
        render_scale,
        camera_streaming_enabled,
        collision_enabled,
        sdf_adf_overlay_mode,
        sdf_adf_runtime_mode,
        sdf_adf_unsupported_future_mode,
        particles_enabled,
        particle_render_draw_limit,
        particle_render_animation_mode,
        particle_render_size_scale,
        matter_surface_native_runtime_configured,
        matter_surface_adf_debug_enabled,
        matter_surface_adf_max_depth,
        matter_surface_adf_max_cells,
        matter_surface_adf_error_tolerance,
        matter_surface_sdf_adf_debug_update_interval_frames,
        matter_surface_particle_count,
        matter_surface_leaf_triangle_count,
        matter_surface_particle_distance_refresh_policy,
        matter_surface_particle_force_authority,
        matter_surface_gpu_force_provider_ab_receipt,
        matter_surface_gpu_force_provider_ab_ready,
        matter_surface_particle_force_source,
        matter_surface_particle_force_update_interval_frames,
        matter_surface_particle_force_compare_probe_count,
        matter_surface_particle_execution_backend,
        matter_surface_particle_execution_batch_size,
        matter_surface_particle_execution_max_threads,
        matter_surface_particle_max_frame_delta_seconds,
        legacy_settings_fallback_used: false,
        receipt_written: false,
    }
}

fn not_configured_receipt() -> MakepadEffectiveSettingsReceipt {
    MakepadEffectiveSettingsReceipt {
        status: "not_configured".to_string(),
        issue_code: Some(NOT_CONFIGURED_ISSUE.to_string()),
        issue_evidence: Some("No Makepad effective-settings path was configured".to_string()),
        legacy_settings_fallback_used: false,
        ..Default::default()
    }
}

fn rejected_receipt(
    path: Option<&Path>,
    issue_code: &str,
    evidence: &str,
) -> MakepadEffectiveSettingsReceipt {
    MakepadEffectiveSettingsReceipt {
        status: "rejected".to_string(),
        issue_code: Some(issue_code.to_string()),
        issue_evidence: Some(evidence.to_string()),
        source_effective_settings_path: path.map(|path| path.display().to_string()),
        legacy_settings_fallback_used: false,
        ..Default::default()
    }
}

fn file_modified_ns(path: &Path) -> Option<u128> {
    std::fs::metadata(path)
        .ok()
        .and_then(|metadata| metadata.modified().ok())
        .and_then(|modified| modified.duration_since(UNIX_EPOCH).ok())
        .map(|duration| duration.as_nanos())
}

#[derive(Debug)]
struct EffectiveSettingsRevisionIdentity {
    revision_key: String,
    scope_revision_keys: BTreeMap<String, String>,
    manifest_path: PathBuf,
    manifest_modified_ns: Option<u128>,
}

fn effective_settings_revision_identity_from_path(
    effective_settings_path: &Path,
) -> Option<EffectiveSettingsRevisionIdentity> {
    let manifest_path =
        effective_settings_path.with_file_name(EFFECTIVE_SETTINGS_REVISION_FILE_NAME);
    let text = std::fs::read_to_string(&manifest_path).ok()?;
    let value = serde_json::from_str::<Value>(text.trim_start_matches('\u{feff}')).ok()?;
    if value.get("schema").and_then(Value::as_str) != Some(EFFECTIVE_SETTINGS_REVISION_SCHEMA) {
        return None;
    }

    let mut parts = Vec::new();
    if let Some(source_sha) = value.get("source_sha256").and_then(Value::as_str) {
        parts.push(format!("source_sha256={source_sha}"));
    }
    if let Some(source_revision) = json_scalar_token(value.get("source_revision")) {
        parts.push(format!("source_revision={source_revision}"));
    }
    if let Some(scopes) = value.get("scopes").and_then(Value::as_object) {
        for scope in EFFECTIVE_SETTINGS_RUNTIME_SCOPES {
            if let Some(scope_hash) = scopes
                .get(*scope)
                .and_then(|scope_value| scope_value.get("revision_hash_sha256"))
                .and_then(Value::as_str)
            {
                parts.push(format!("{scope}={scope_hash}"));
            }
        }
    }
    let scope_revision_keys = value
        .get("scopes")
        .and_then(Value::as_object)
        .map(|scopes| {
            scopes
                .iter()
                .filter_map(|(scope, scope_value)| {
                    scope_value
                        .get("revision_hash_sha256")
                        .and_then(Value::as_str)
                        .map(|scope_hash| (scope.clone(), scope_hash.to_string()))
                })
                .collect::<BTreeMap<_, _>>()
        })
        .unwrap_or_default();
    if parts.is_empty() {
        return None;
    }

    Some(EffectiveSettingsRevisionIdentity {
        revision_key: parts.join("|"),
        scope_revision_keys,
        manifest_modified_ns: file_modified_ns(&manifest_path),
        manifest_path,
    })
}

fn json_scalar_token(value: Option<&Value>) -> Option<String> {
    match value? {
        Value::String(value) => Some(value.clone()),
        Value::Number(value) => Some(value.to_string()),
        Value::Bool(value) => Some(value.to_string()),
        _ => None,
    }
}

fn selected_effective_settings_path() -> Option<PathBuf> {
    if let Some(path) = arg_value("--makepad-effective-settings") {
        return Some(PathBuf::from(path));
    }
    if let Ok(path) = std::env::var("HOSTESS_MAKEPAD_EFFECTIVE_SETTINGS") {
        return Some(PathBuf::from(path));
    }
    if let Ok(path) = std::env::var("RUSTY_MAKEPAD_EFFECTIVE_SETTINGS") {
        return Some(PathBuf::from(path));
    }
    default_effective_settings_candidates()
        .into_iter()
        .find(|path| path.is_file())
}

fn selected_effective_settings_receipt_output_path() -> Option<PathBuf> {
    if let Some(path) = arg_value("--makepad-effective-settings-receipt-out") {
        return Some(PathBuf::from(path));
    }
    if let Ok(path) = std::env::var("HOSTESS_MAKEPAD_EFFECTIVE_SETTINGS_RECEIPT_OUT") {
        return Some(PathBuf::from(path));
    }
    default_effective_settings_receipt_output_path()
}

fn arg_value(flag: &str) -> Option<String> {
    let mut args = std::env::args().skip(1);
    while let Some(arg) = args.next() {
        if arg == flag {
            return args.next();
        }
    }
    None
}

#[cfg(target_os = "android")]
fn default_effective_settings_candidates() -> Vec<PathBuf> {
    vec![
        PathBuf::from(format!(
            "{ANDROID_INTERNAL_SETTINGS_ROOT}/makepad-effective-settings.json"
        )),
        PathBuf::from(format!(
            "{ANDROID_EXTERNAL_SETTINGS_ROOT}/makepad-effective-settings.json"
        )),
    ]
}

#[cfg(not(target_os = "android"))]
fn default_effective_settings_candidates() -> Vec<PathBuf> {
    Vec::new()
}

#[cfg(target_os = "android")]
fn default_effective_settings_receipt_output_path() -> Option<PathBuf> {
    Some(PathBuf::from(format!(
        "{ANDROID_INTERNAL_SETTINGS_ROOT}/makepad-effective-settings-receipt.json"
    )))
}

#[cfg(not(target_os = "android"))]
fn default_effective_settings_receipt_output_path() -> Option<PathBuf> {
    None
}

fn marker_option(value: Option<&str>) -> String {
    value
        .map(marker_token)
        .unwrap_or_else(|| "none".to_string())
}

fn marker_f64(value: Option<f64>) -> String {
    match value {
        Some(value) if value.is_finite() => format!("{value:.3}"),
        _ => "none".to_string(),
    }
}

fn marker_f32(value: Option<f32>) -> String {
    match value {
        Some(value) if value.is_finite() => format!("{value:.3}"),
        _ => "none".to_string(),
    }
}

fn marker_bool(value: Option<bool>) -> String {
    value
        .map(|value| value.to_string())
        .unwrap_or_else(|| "none".to_string())
}

fn marker_u32(value: Option<u32>) -> String {
    value
        .map(|value| value.to_string())
        .unwrap_or_else(|| "none".to_string())
}

fn marker_usize(value: Option<usize>) -> String {
    value
        .map(|value| value.to_string())
        .unwrap_or_else(|| "none".to_string())
}

#[cfg(test)]
mod tests {
    use super::*;
    use rusty_quest_makepad_camera_shell::{
        CAMERA_SHELL_APP_ID, MESH_REPLAY_SOURCE_PUBLIC_SYNTHETIC_HAND_SEQUENCE,
        MESH_REPLAY_SOURCE_RECORDED_META_QUEST_HAND_LEFT,
        RECORDED_META_QUEST_HAND_LEFT_SEQUENCE_FILE,
    };
    use std::time::{SystemTime, UNIX_EPOCH};

    const EFFECTIVE_SETTINGS_FIXTURE: &str = include_str!(
        "../../../../rusty-quest-makepad/fixtures/effective-settings/mesh-replay.effective-settings.json"
    );
    const SYNTHETIC_SEQUENCE_FIXTURE: &str = include_str!(
        "../../../../rusty-quest-makepad/fixtures/mesh-replay/synthetic-hand-mesh-sequence.json"
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
        assert!(selection_marker
            .contains("gpuForceProviderAbReceipt=live-recorded-provider-ab-check-v1"));
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
        write_revision_sidecar_with_hashes(&path, "mesh-a", "camera-a", "matter-a", "particles-a");
        let first = makepad_effective_settings_identity_from_path(&path);
        let mesh_key = first.scoped_revision_key(&["mesh_replay"]);
        let camera_key = first.scoped_revision_key(&["camera_projection"]);

        write_revision_sidecar_with_hashes(&path, "mesh-a", "camera-b", "matter-a", "particles-a");
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
        let different_app = EFFECTIVE_SETTINGS_FIXTURE
            .replace(CAMERA_SHELL_APP_ID, "rusty-quest-makepad.other-shell");
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
        let different_app = EFFECTIVE_SETTINGS_FIXTURE
            .replace(CAMERA_SHELL_APP_ID, "rusty-quest-makepad.other-shell");
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
            "matter-a",
            "particles-a",
        );
    }

    fn write_revision_sidecar_with_hashes(
        settings_path: &Path,
        mesh_replay_hash: &str,
        camera_projection_hash: &str,
        matter_surface_hash: &str,
        particles_hash: &str,
    ) {
        write_revision_sidecar_with_hashes_and_optional_gpu_proof(
            settings_path,
            mesh_replay_hash,
            camera_projection_hash,
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
            matter_surface_hash,
            particles_hash,
            Some(gpu_proof_hash),
        );
    }

    fn write_revision_sidecar_with_hashes_and_optional_gpu_proof(
        settings_path: &Path,
        mesh_replay_hash: &str,
        camera_projection_hash: &str,
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
}
