//! Camera texture-lane contract family.

use super::{
    ImageSize, SourceSamplingTransformStage, SourceUvRect, StereoSourceEyeMapping,
    HOSTESS_CAMERA_TEXTURE_LANE_CONTRACT_SCHEMA,
    LEGACY_RUSTY_XR_CAMERA_TEXTURE_LANE_CONTRACT_SCHEMA,
};

/// Canonical camera texture lane families used for cross-renderer diagnostics.
///
/// These names identify the resource architecture, not a specific application
/// package or launch wrapper. Older runner/profile aliases should resolve into
/// one of these values before producing shared summaries.
#[cfg_attr(feature = "serde", derive(serde::Deserialize, serde::Serialize))]
#[cfg_attr(feature = "serde", serde(rename_all = "kebab-case"))]
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq, PartialOrd, Ord)]
pub enum CameraTextureLaneKind {
    VulkanHwbDirectCamera2Raw,
    GlesOesDirectCamera2Raw,
    MakepadCpuYuvDirectCamera2Raw,
    MakepadHwbExternalDirectCamera2Raw,
    #[default]
    Other,
}

impl CameraTextureLaneKind {
    pub const fn stable_id(self) -> &'static str {
        match self {
            Self::VulkanHwbDirectCamera2Raw => "vulkan-hwb-direct-camera2-raw",
            Self::GlesOesDirectCamera2Raw => "gles-oes-direct-camera2-raw",
            Self::MakepadCpuYuvDirectCamera2Raw => "makepad-cpuyuv-direct-camera2-raw",
            Self::MakepadHwbExternalDirectCamera2Raw => "makepad-hwb-external-direct-camera2-raw",
            Self::Other => "other",
        }
    }

    pub fn parse(value: &str) -> Option<Self> {
        match value.trim().to_ascii_lowercase().as_str() {
            "vulkan-hwb-direct-camera2-raw" | "direct-hwb" | "hwb" => {
                Some(Self::VulkanHwbDirectCamera2Raw)
            }
            "gles-oes-direct-camera2-raw" | "direct-oes" | "oes" => {
                Some(Self::GlesOesDirectCamera2Raw)
            }
            "makepad-cpuyuv-direct-camera2-raw"
            | "makepad-cpu-yuv-direct-camera2-raw"
            | "makepad-cpu-yuv"
            | "cpu-yuv" => Some(Self::MakepadCpuYuvDirectCamera2Raw),
            "makepad-hwb-external-direct-camera2-raw"
            | "makepad-hardware-buffer-external-direct-camera2-raw"
            | "makepad-hwb-external"
            | "hardware-buffer-external" => Some(Self::MakepadHwbExternalDirectCamera2Raw),
            "other" => Some(Self::Other),
            _ => None,
        }
    }
}

/// Source family that produced a camera texture frame.
#[cfg_attr(feature = "serde", derive(serde::Deserialize, serde::Serialize))]
#[cfg_attr(feature = "serde", serde(rename_all = "kebab-case"))]
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub enum CameraTextureSourceKind {
    DirectCamera2,
    BrokerH264,
    Synthetic,
    #[default]
    Other,
}

impl CameraTextureSourceKind {
    pub const fn stable_id(self) -> &'static str {
        match self {
            Self::DirectCamera2 => "direct-camera2",
            Self::BrokerH264 => "broker-h264",
            Self::Synthetic => "synthetic",
            Self::Other => "other",
        }
    }
}

/// Texture or upload resource shape after camera/decoder handoff.
#[cfg_attr(feature = "serde", derive(serde::Deserialize, serde::Serialize))]
#[cfg_attr(feature = "serde", serde(rename_all = "kebab-case"))]
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub enum CameraTextureResourceKind {
    AndroidHardwareBufferVulkan,
    SurfaceTextureOes,
    CpuYuvPlaneTextures,
    MakepadHardwareBufferExternal,
    #[default]
    Other,
}

impl CameraTextureResourceKind {
    pub const fn stable_id(self) -> &'static str {
        match self {
            Self::AndroidHardwareBufferVulkan => "android-hardware-buffer-vulkan",
            Self::SurfaceTextureOes => "surface-texture-oes",
            Self::CpuYuvPlaneTextures => "cpu-yuv-plane-textures",
            Self::MakepadHardwareBufferExternal => "makepad-hardware-buffer-external",
            Self::Other => "other",
        }
    }
}

/// Shader-visible descriptor or sampler contract for the camera resource.
#[cfg_attr(feature = "serde", derive(serde::Deserialize, serde::Serialize))]
#[cfg_attr(feature = "serde", serde(rename_all = "kebab-case"))]
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub enum CameraTextureDescriptorShape {
    #[default]
    Unknown,
    CpuYuvPlaneTextures,
    HardwareBufferYuvPlaneTextures,
    SampledImageAndSampler,
    CombinedImageSampler,
    SamplerExternalOes,
    NotApplicable,
}

impl CameraTextureDescriptorShape {
    pub const fn stable_id(self) -> &'static str {
        match self {
            Self::Unknown => "unknown",
            Self::CpuYuvPlaneTextures => "cpu-yuv-plane-textures",
            Self::HardwareBufferYuvPlaneTextures => "hardware-buffer-yuv-plane-textures",
            Self::SampledImageAndSampler => "sampled-image-and-sampler",
            Self::CombinedImageSampler => "combined-image-sampler",
            Self::SamplerExternalOes => "sampler-external-oes",
            Self::NotApplicable => "not-applicable",
        }
    }
}

/// Visual/color acceptance status is deliberately separate from resource
/// cadence and descriptor correctness.
#[cfg_attr(feature = "serde", derive(serde::Deserialize, serde::Serialize))]
#[cfg_attr(feature = "serde", serde(rename_all = "kebab-case"))]
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub enum CameraTextureColorStatus {
    AcceptedReference,
    Experimental,
    DiagnosticOnly,
    #[default]
    Unknown,
}

impl CameraTextureColorStatus {
    pub const fn stable_id(self) -> &'static str {
        match self {
            Self::AcceptedReference => "accepted-reference",
            Self::Experimental => "experimental",
            Self::DiagnosticOnly => "diagnostic-only",
            Self::Unknown => "unknown",
        }
    }
}

/// Source-side information that all camera texture lanes should expose.
#[cfg_attr(feature = "serde", derive(serde::Deserialize, serde::Serialize))]
#[derive(Clone, Debug, PartialEq)]
pub struct CameraTextureLaneSource {
    pub source_kind: CameraTextureSourceKind,
    pub source_label: String,
    pub delivered_size: ImageSize,
    pub handoff_label: String,
    pub source_eye_mapping: StereoSourceEyeMapping,
}

impl CameraTextureLaneSource {
    pub fn new(
        source_kind: CameraTextureSourceKind,
        source_label: impl Into<String>,
        delivered_size: ImageSize,
        handoff_label: impl Into<String>,
    ) -> Self {
        Self {
            source_kind,
            source_label: source_label.into(),
            delivered_size,
            handoff_label: handoff_label.into(),
            source_eye_mapping: StereoSourceEyeMapping::DisplayLeftFromLeftSource,
        }
    }

    pub const fn with_source_eye_mapping(mut self, mapping: StereoSourceEyeMapping) -> Self {
        self.source_eye_mapping = mapping;
        self
    }

    pub fn is_valid(&self) -> bool {
        self.delivered_size.is_non_empty()
            && !self.source_label.trim().is_empty()
            && !self.handoff_label.trim().is_empty()
    }
}

/// Renderer/framework texture resource facts for one lane.
#[cfg_attr(feature = "serde", derive(serde::Deserialize, serde::Serialize))]
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct CameraTextureLaneResource {
    pub resource_kind: CameraTextureResourceKind,
    pub resource_label: String,
    pub descriptor_shape: CameraTextureDescriptorShape,
    pub texture_label: String,
    pub buffer_id: Option<u64>,
    pub import_cache_size: Option<u32>,
    pub shader_interface_label: String,
}

impl CameraTextureLaneResource {
    pub fn new(
        resource_kind: CameraTextureResourceKind,
        resource_label: impl Into<String>,
        descriptor_shape: CameraTextureDescriptorShape,
    ) -> Self {
        let resource_label = resource_label.into();
        Self {
            resource_kind,
            texture_label: resource_label.clone(),
            resource_label,
            descriptor_shape,
            buffer_id: None,
            import_cache_size: None,
            shader_interface_label: descriptor_shape.stable_id().to_string(),
        }
    }

    pub const fn with_buffer_id(mut self, buffer_id: u64) -> Self {
        self.buffer_id = Some(buffer_id);
        self
    }

    pub const fn with_import_cache_size(mut self, import_cache_size: u32) -> Self {
        self.import_cache_size = Some(import_cache_size);
        self
    }

    pub fn with_texture_label(mut self, texture_label: impl Into<String>) -> Self {
        self.texture_label = texture_label.into();
        self
    }

    pub fn with_shader_interface_label(mut self, label: impl Into<String>) -> Self {
        self.shader_interface_label = label.into();
        self
    }

    pub fn is_valid(&self) -> bool {
        !self.resource_label.trim().is_empty()
            && !self.texture_label.trim().is_empty()
            && !self.shader_interface_label.trim().is_empty()
    }
}

/// Source-to-sampler transform facts that are comparable across HWB, OES, and
/// framework-owned texture upload paths.
#[cfg_attr(feature = "serde", derive(serde::Deserialize, serde::Serialize))]
#[derive(Clone, Debug, PartialEq)]
pub struct CameraTextureLaneTransform {
    pub source_visible_uv_rect: SourceUvRect,
    pub transform_stage: SourceSamplingTransformStage,
    pub transform_label: String,
    pub transform_owner: String,
    pub oes_transform_matrix: Option<[f32; 16]>,
    pub hwb_transform_flags: Option<u32>,
    pub yuv_rotation_steps: Option<u32>,
}

impl CameraTextureLaneTransform {
    pub fn new(
        transform_stage: SourceSamplingTransformStage,
        transform_label: impl Into<String>,
        transform_owner: impl Into<String>,
    ) -> Self {
        Self {
            source_visible_uv_rect: SourceUvRect::FULL,
            transform_stage,
            transform_label: transform_label.into(),
            transform_owner: transform_owner.into(),
            oes_transform_matrix: None,
            hwb_transform_flags: None,
            yuv_rotation_steps: None,
        }
    }

    pub const fn with_source_visible_uv_rect(mut self, rect: SourceUvRect) -> Self {
        self.source_visible_uv_rect = rect;
        self
    }

    pub const fn with_oes_transform_matrix(mut self, matrix: [f32; 16]) -> Self {
        self.oes_transform_matrix = Some(matrix);
        self
    }

    pub const fn with_hwb_transform_flags(mut self, flags: u32) -> Self {
        self.hwb_transform_flags = Some(flags);
        self
    }

    pub const fn with_yuv_rotation_steps(mut self, steps: u32) -> Self {
        self.yuv_rotation_steps = Some(steps);
        self
    }

    pub fn is_valid(&self) -> bool {
        self.source_visible_uv_rect.is_valid()
            && !self.transform_label.trim().is_empty()
            && !self.transform_owner.trim().is_empty()
            && self
                .oes_transform_matrix
                .map(|matrix| matrix.iter().all(|value| value.is_finite()))
                .unwrap_or(true)
            && self
                .yuv_rotation_steps
                .map(|steps| steps <= 3)
                .unwrap_or(true)
    }
}

/// Color/visual acceptance facts for a camera texture lane.
#[cfg_attr(feature = "serde", derive(serde::Deserialize, serde::Serialize))]
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct CameraTextureLaneColor {
    pub color_status: CameraTextureColorStatus,
    pub color_reference: String,
    pub color_matrix: String,
    pub color_range: String,
    pub color_transfer: String,
}

impl CameraTextureLaneColor {
    pub fn new(color_status: CameraTextureColorStatus, color_reference: impl Into<String>) -> Self {
        Self {
            color_status,
            color_reference: color_reference.into(),
            color_matrix: "unspecified".to_string(),
            color_range: "unspecified".to_string(),
            color_transfer: "unspecified".to_string(),
        }
    }

    pub fn with_yuv_model(mut self, matrix: impl Into<String>, range: impl Into<String>) -> Self {
        self.color_matrix = matrix.into();
        self.color_range = range.into();
        self
    }

    pub fn with_transfer(mut self, transfer: impl Into<String>) -> Self {
        self.color_transfer = transfer.into();
        self
    }

    pub fn is_valid(&self) -> bool {
        !self.color_reference.trim().is_empty()
            && !self.color_matrix.trim().is_empty()
            && !self.color_range.trim().is_empty()
            && !self.color_transfer.trim().is_empty()
    }
}

/// Timing identity for acquisition, upload/import, texture update, and XR
/// submission. Clock-domain mapping is owned by the adapter.
#[cfg_attr(feature = "serde", derive(serde::Deserialize, serde::Serialize))]
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub struct CameraTextureLaneTiming {
    pub camera_frame_sequence: Option<u64>,
    pub camera_timestamp_ns: Option<i64>,
    pub acquire_time_ns: Option<i64>,
    pub upload_time_ns: Option<i64>,
    pub import_time_ns: Option<i64>,
    pub texture_update_sequence: Option<u64>,
    pub texture_submit_sequence: Option<u64>,
    pub xr_end_frame_time_ns: Option<i64>,
}

impl CameraTextureLaneTiming {
    pub const fn with_camera_frame(mut self, sequence: u64, timestamp_ns: i64) -> Self {
        self.camera_frame_sequence = Some(sequence);
        self.camera_timestamp_ns = Some(timestamp_ns);
        self
    }

    pub const fn with_acquire_time_ns(mut self, acquire_time_ns: i64) -> Self {
        self.acquire_time_ns = Some(acquire_time_ns);
        self
    }

    pub const fn with_upload_time_ns(mut self, upload_time_ns: i64) -> Self {
        self.upload_time_ns = Some(upload_time_ns);
        self
    }

    pub const fn with_import_time_ns(mut self, import_time_ns: i64) -> Self {
        self.import_time_ns = Some(import_time_ns);
        self
    }

    pub const fn with_texture_update_sequence(mut self, sequence: u64) -> Self {
        self.texture_update_sequence = Some(sequence);
        self
    }

    pub const fn with_texture_submit_sequence(mut self, sequence: u64) -> Self {
        self.texture_submit_sequence = Some(sequence);
        self
    }

    pub const fn with_xr_end_frame_time_ns(mut self, time_ns: i64) -> Self {
        self.xr_end_frame_time_ns = Some(time_ns);
        self
    }

    pub const fn has_frame_identity(self) -> bool {
        self.camera_frame_sequence.is_some() || self.camera_timestamp_ns.is_some()
    }

    pub fn is_valid(self) -> bool {
        [
            self.camera_timestamp_ns,
            self.acquire_time_ns,
            self.upload_time_ns,
            self.import_time_ns,
            self.xr_end_frame_time_ns,
        ]
        .into_iter()
        .flatten()
        .all(|value| value >= 0)
    }
}

/// Lifecycle and fallback policy for a camera texture lane.
#[cfg_attr(feature = "serde", derive(serde::Deserialize, serde::Serialize))]
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct CameraTextureLaneLifecycle {
    pub first_frame_seen: bool,
    pub fallback_active: bool,
    pub fallback_reason: Option<String>,
    pub frame_reuse_policy: String,
    pub resource_release_policy: String,
    pub app_focused: Option<bool>,
}

impl CameraTextureLaneLifecycle {
    pub fn new(
        frame_reuse_policy: impl Into<String>,
        resource_release_policy: impl Into<String>,
    ) -> Self {
        Self {
            first_frame_seen: false,
            fallback_active: false,
            fallback_reason: None,
            frame_reuse_policy: frame_reuse_policy.into(),
            resource_release_policy: resource_release_policy.into(),
            app_focused: None,
        }
    }

    pub const fn with_first_frame_seen(mut self, first_frame_seen: bool) -> Self {
        self.first_frame_seen = first_frame_seen;
        self
    }

    pub fn with_fallback(mut self, reason: impl Into<String>) -> Self {
        self.fallback_active = true;
        self.fallback_reason = Some(reason.into());
        self
    }

    pub const fn with_app_focused(mut self, app_focused: bool) -> Self {
        self.app_focused = Some(app_focused);
        self
    }

    pub fn is_valid(&self) -> bool {
        !self.frame_reuse_policy.trim().is_empty()
            && !self.resource_release_policy.trim().is_empty()
            && (!self.fallback_active
                || self
                    .fallback_reason
                    .as_deref()
                    .map(|reason| !reason.trim().is_empty())
                    .unwrap_or(false))
    }
}

/// Projection/run state needed to compare raw diagnostic lanes without
/// reintroducing visual-effect border modes as diagnostic defaults.
#[cfg_attr(feature = "serde", derive(serde::Deserialize, serde::Serialize))]
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct CameraTextureLaneProjection {
    pub projection_border_policy: String,
    pub processing_layer: String,
    pub projection_surface_label: String,
    pub projection_status_label: String,
}

impl CameraTextureLaneProjection {
    pub fn raw_diagnostic(projection_border_policy: impl Into<String>) -> Self {
        Self {
            projection_border_policy: projection_border_policy.into(),
            processing_layer: "raw".to_string(),
            projection_surface_label: "camera-projection-surface".to_string(),
            projection_status_label: "ready".to_string(),
        }
    }

    pub fn is_valid(&self) -> bool {
        !self.projection_border_policy.trim().is_empty()
            && !self.processing_layer.trim().is_empty()
            && !self.projection_surface_label.trim().is_empty()
            && !self.projection_status_label.trim().is_empty()
    }
}

/// Shared lane-level contract for comparing camera texture architectures.
#[cfg_attr(feature = "serde", derive(serde::Deserialize, serde::Serialize))]
#[derive(Clone, Debug, PartialEq)]
pub struct CameraTextureLaneContract {
    pub schema_version: String,
    pub lane_kind: CameraTextureLaneKind,
    pub source: CameraTextureLaneSource,
    pub resource: CameraTextureLaneResource,
    pub transform: CameraTextureLaneTransform,
    pub color: CameraTextureLaneColor,
    pub timing: CameraTextureLaneTiming,
    pub lifecycle: CameraTextureLaneLifecycle,
    pub projection: CameraTextureLaneProjection,
}

impl CameraTextureLaneContract {
    pub fn new(
        lane_kind: CameraTextureLaneKind,
        source: CameraTextureLaneSource,
        resource: CameraTextureLaneResource,
    ) -> Self {
        Self {
            schema_version: HOSTESS_CAMERA_TEXTURE_LANE_CONTRACT_SCHEMA.to_string(),
            lane_kind,
            source,
            resource,
            transform: CameraTextureLaneTransform::new(
                SourceSamplingTransformStage::None,
                "identity",
                "adapter",
            ),
            color: CameraTextureLaneColor::new(CameraTextureColorStatus::Unknown, "unspecified"),
            timing: CameraTextureLaneTiming::default(),
            lifecycle: CameraTextureLaneLifecycle::new("latest-frame", "adapter-owned"),
            projection: CameraTextureLaneProjection::raw_diagnostic("solid-red"),
        }
    }

    pub fn with_transform(mut self, transform: CameraTextureLaneTransform) -> Self {
        self.transform = transform;
        self
    }

    pub fn with_color(mut self, color: CameraTextureLaneColor) -> Self {
        self.color = color;
        self
    }

    pub const fn with_timing(mut self, timing: CameraTextureLaneTiming) -> Self {
        self.timing = timing;
        self
    }

    pub fn with_lifecycle(mut self, lifecycle: CameraTextureLaneLifecycle) -> Self {
        self.lifecycle = lifecycle;
        self
    }

    pub fn with_projection(mut self, projection: CameraTextureLaneProjection) -> Self {
        self.projection = projection;
        self
    }

    pub fn is_valid(&self) -> bool {
        camera_texture_lane_schema_supported(&self.schema_version)
            && self.source.is_valid()
            && self.resource.is_valid()
            && self.transform.is_valid()
            && self.color.is_valid()
            && self.timing.is_valid()
            && self.lifecycle.is_valid()
            && self.projection.is_valid()
    }
}

fn camera_texture_lane_schema_supported(schema: &str) -> bool {
    schema == HOSTESS_CAMERA_TEXTURE_LANE_CONTRACT_SCHEMA
        || schema == LEGACY_RUSTY_XR_CAMERA_TEXTURE_LANE_CONTRACT_SCHEMA
}
