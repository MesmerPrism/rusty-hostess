//! Camera source-sampling contract family.

use super::{
    Vec2, HOSTESS_SOURCE_SAMPLING_CONTRACT_SCHEMA, LEGACY_RUSTY_XR_SOURCE_SAMPLING_CONTRACT_SCHEMA,
};

/// Quarter-turn texture rotation applied to sampled camera images.
///
/// This is separate from Camera2 `SENSOR_ORIENTATION`: opaque GPU camera
/// textures can arrive with an implementation-defined texture orientation even
/// when sensor orientation metadata is zero.
#[cfg_attr(feature = "serde", derive(serde::Deserialize, serde::Serialize))]
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub enum CameraImageRotation {
    #[default]
    Rotate0,
    Rotate90,
    Rotate180,
    Rotate270,
}

impl CameraImageRotation {
    pub const fn stable_id(self) -> &'static str {
        match self {
            Self::Rotate0 => "rotate0",
            Self::Rotate90 => "rotate90",
            Self::Rotate180 => "rotate180",
            Self::Rotate270 => "rotate270",
        }
    }

    pub fn parse(value: &str) -> Option<Self> {
        match value {
            "0" | "rotate0" | "none" => Some(Self::Rotate0),
            "90" | "rotate90" => Some(Self::Rotate90),
            "180" | "rotate180" => Some(Self::Rotate180),
            "270" | "rotate270" => Some(Self::Rotate270),
            _ => None,
        }
    }

    pub const fn shader_bits(self) -> u32 {
        match self {
            Self::Rotate0 => 0,
            Self::Rotate90 => 1,
            Self::Rotate180 => 2,
            Self::Rotate270 => 3,
        }
    }
}

/// Mapping from a display eye to the sampled stereo source eye.
#[cfg_attr(feature = "serde", derive(serde::Deserialize, serde::Serialize))]
#[cfg_attr(feature = "serde", serde(rename_all = "kebab-case"))]
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub enum StereoSourceEyeMapping {
    #[default]
    DisplayLeftFromLeftSource,
    DisplayLeftFromRightSource,
}

impl StereoSourceEyeMapping {
    pub fn parse(value: &str) -> Option<Self> {
        match value.trim().to_ascii_lowercase().as_str() {
            "left-right"
            | "display-left-from-left"
            | "display-left-from-left-source"
            | "displayleftfromleft"
            | "natural"
            | "camera50-left" => Some(Self::DisplayLeftFromLeftSource),
            "right-left"
            | "display-left-from-right"
            | "display-left-from-right-source"
            | "displayleftfromright"
            | "swapped"
            | "swap"
            | "camera51-left" => Some(Self::DisplayLeftFromRightSource),
            _ => None,
        }
    }

    pub const fn stable_id(self) -> &'static str {
        match self {
            Self::DisplayLeftFromLeftSource => "display-left-from-left-source",
            Self::DisplayLeftFromRightSource => "display-left-from-right-source",
        }
    }

    pub const fn swaps_display_source_eyes(self) -> bool {
        matches!(self, Self::DisplayLeftFromRightSource)
    }
}

/// Explicit post-projection camera texture transform.
#[cfg_attr(feature = "serde", derive(serde::Deserialize, serde::Serialize))]
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct CameraTextureTransform {
    pub rotation: CameraImageRotation,
    pub flip_x: bool,
    pub flip_y: bool,
    pub mirror: bool,
    pub source_label: String,
    pub reason: String,
}

impl CameraTextureTransform {
    pub fn new(source_label: impl Into<String>, reason: impl Into<String>) -> Self {
        Self {
            rotation: CameraImageRotation::Rotate0,
            flip_x: false,
            flip_y: false,
            mirror: false,
            source_label: source_label.into(),
            reason: reason.into(),
        }
    }

    pub const fn with_rotation(mut self, rotation: CameraImageRotation) -> Self {
        self.rotation = rotation;
        self
    }

    pub const fn with_flip_x(mut self, flip_x: bool) -> Self {
        self.flip_x = flip_x;
        self
    }

    pub const fn with_flip_y(mut self, flip_y: bool) -> Self {
        self.flip_y = flip_y;
        self
    }

    pub const fn with_mirror(mut self, mirror: bool) -> Self {
        self.mirror = mirror;
        self
    }

    pub fn is_explicit_visual_check(&self) -> bool {
        !self.source_label.trim().is_empty()
            && !self.reason.trim().is_empty()
            && self.source_label != "default"
            && self.reason != "unspecified"
    }

    pub fn shader_flags(&self) -> u32 {
        self.rotation.shader_bits()
            | ((self.flip_x as u32) << 2)
            | ((self.flip_y as u32) << 3)
            | ((self.mirror as u32) << 4)
    }

    pub fn label(&self) -> String {
        let mut parts = vec![self.rotation.stable_id().to_string()];
        if self.flip_x {
            parts.push("flipX".to_string());
        }
        if self.flip_y {
            parts.push("flipY".to_string());
        }
        if self.mirror {
            parts.push("mirror".to_string());
        }
        parts.join("+")
    }

    pub fn apply_uv(&self, uv: Vec2) -> Vec2 {
        let mut result = match self.rotation {
            CameraImageRotation::Rotate0 => uv,
            CameraImageRotation::Rotate90 => Vec2::new(uv.y, 1.0 - uv.x),
            CameraImageRotation::Rotate180 => Vec2::new(1.0 - uv.x, 1.0 - uv.y),
            CameraImageRotation::Rotate270 => Vec2::new(1.0 - uv.y, uv.x),
        };
        if self.flip_x || self.mirror {
            result.x = 1.0 - result.x;
        }
        if self.flip_y {
            result.y = 1.0 - result.y;
        }
        result
    }
}

impl Default for CameraTextureTransform {
    fn default() -> Self {
        Self::new("default", "unspecified")
    }
}

/// Normalized UV rectangle in the source image domain.
#[cfg_attr(feature = "serde", derive(serde::Deserialize, serde::Serialize))]
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct SourceUvRect {
    pub origin_uv: Vec2,
    pub size_uv: Vec2,
}

impl SourceUvRect {
    pub const FULL: Self = Self::new(Vec2::ZERO, Vec2::ONE);

    pub const fn new(origin_uv: Vec2, size_uv: Vec2) -> Self {
        Self { origin_uv, size_uv }
    }

    pub fn is_valid(self) -> bool {
        const EPSILON: f32 = 1.0e-5;
        self.origin_uv.is_finite()
            && self.size_uv.is_finite()
            && self.origin_uv.x >= -EPSILON
            && self.origin_uv.y >= -EPSILON
            && self.size_uv.x > 0.0
            && self.size_uv.y > 0.0
            && self.origin_uv.x + self.size_uv.x <= 1.0 + EPSILON
            && self.origin_uv.y + self.size_uv.y <= 1.0 + EPSILON
    }
}

impl Default for SourceUvRect {
    fn default() -> Self {
        Self::FULL
    }
}

/// Stage where renderer source-sampling transforms are applied.
#[cfg_attr(feature = "serde", derive(serde::Deserialize, serde::Serialize))]
#[cfg_attr(feature = "serde", serde(rename_all = "kebab-case"))]
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub enum SourceSamplingTransformStage {
    #[default]
    None,
    PostHomographyPreTextureSample,
    PostHomographyPreOesSample,
    PostHomographyPreYuvSample,
    PostHomographyPreSourceVisibleRectThenTextureSample,
    Other,
}

impl SourceSamplingTransformStage {
    pub const fn stable_id(self) -> &'static str {
        match self {
            Self::None => "none",
            Self::PostHomographyPreTextureSample => "post-homography-pre-texture-sample",
            Self::PostHomographyPreOesSample => "post-homography-pre-oes-sample",
            Self::PostHomographyPreYuvSample => "post-homography-pre-yuv-sample",
            Self::PostHomographyPreSourceVisibleRectThenTextureSample => {
                "post-homography-pre-source-visible-rect-then-texture-sample"
            }
            Self::Other => "other",
        }
    }

    pub fn parse(value: &str) -> Option<Self> {
        match value {
            "none" | "off" => Some(Self::None),
            "post-homography-pre-texture-sample" | "post_homography_pre_texture_sample" => {
                Some(Self::PostHomographyPreTextureSample)
            }
            "post-homography-pre-oes-sample" | "post_homography_pre_oes_sample" => {
                Some(Self::PostHomographyPreOesSample)
            }
            "post-homography-pre-yuv-sample" | "post_homography_pre_yuv_sample" => {
                Some(Self::PostHomographyPreYuvSample)
            }
            "post-homography-pre-source-visible-rect-then-texture-sample"
            | "post_homography_pre_source_visible_rect_then_texture_sample" => {
                Some(Self::PostHomographyPreSourceVisibleRectThenTextureSample)
            }
            "other" => Some(Self::Other),
            _ => None,
        }
    }
}

/// Y-axis convention observed at the final sampler input.
#[cfg_attr(feature = "serde", derive(serde::Deserialize, serde::Serialize))]
#[cfg_attr(feature = "serde", serde(rename_all = "kebab-case"))]
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub enum SourceSamplerYAxis {
    #[default]
    RendererDefined,
    SurfaceTextureTransformDefined,
    ContentTopLeftYDown,
    MakepadSamplerOriginConvention,
    Other,
}

impl SourceSamplerYAxis {
    pub const fn stable_id(self) -> &'static str {
        match self {
            Self::RendererDefined => "renderer-defined",
            Self::SurfaceTextureTransformDefined => "surface-texture-transform-defined",
            Self::ContentTopLeftYDown => "content-top-left-y-down",
            Self::MakepadSamplerOriginConvention => "makepad-sampler-origin-convention",
            Self::Other => "other",
        }
    }

    pub fn parse(value: &str) -> Option<Self> {
        match value.trim().to_ascii_lowercase().as_str() {
            "renderer-defined" | "renderer_defined" => Some(Self::RendererDefined),
            "surface-texture-transform-defined" | "surface_texture_transform_defined" => {
                Some(Self::SurfaceTextureTransformDefined)
            }
            "content-top-left-y-down" | "content_top_left_y_down" => {
                Some(Self::ContentTopLeftYDown)
            }
            "makepad-sampler-origin-convention" | "makepad_sampler_origin_convention" => {
                Some(Self::MakepadSamplerOriginConvention)
            }
            "other" => Some(Self::Other),
            _ => None,
        }
    }
}

/// Backend-neutral source-sampling contract for a resolved projection path.
///
/// This records how content UV becomes sampler UV. It intentionally does not
/// include a source-kind switch; projection behavior should come from source
/// metadata and resolved rectangles/transforms.
#[cfg_attr(feature = "serde", derive(serde::Deserialize, serde::Serialize))]
#[derive(Clone, Debug, PartialEq)]
pub struct SourceSamplingContract {
    pub schema_version: String,
    pub backend: String,
    pub mode: String,
    pub source_eye_mapping: StereoSourceEyeMapping,
    pub content_uv_rect: SourceUvRect,
    pub source_visible_uv_rect: SourceUvRect,
    pub transform_stage: SourceSamplingTransformStage,
    pub transform_label: String,
    pub transform_owner: String,
    pub transform_applied: bool,
    pub output_uv_label: String,
    pub sampler_uv_origin: String,
    pub sampler_y_axis: SourceSamplerYAxis,
    pub texture_transform_stage: SourceSamplingTransformStage,
    pub texture_transform_owner: String,
}

impl SourceSamplingContract {
    pub fn new(
        backend: impl Into<String>,
        mode: impl Into<String>,
        source_eye_mapping: StereoSourceEyeMapping,
        transform_stage: SourceSamplingTransformStage,
    ) -> Self {
        Self {
            schema_version: HOSTESS_SOURCE_SAMPLING_CONTRACT_SCHEMA.to_string(),
            backend: backend.into(),
            mode: mode.into(),
            source_eye_mapping,
            content_uv_rect: SourceUvRect::FULL,
            source_visible_uv_rect: SourceUvRect::FULL,
            transform_stage,
            transform_label: "identity".to_string(),
            transform_owner: "renderer".to_string(),
            transform_applied: false,
            output_uv_label: "sampler-uv".to_string(),
            sampler_uv_origin: "renderer-defined".to_string(),
            sampler_y_axis: SourceSamplerYAxis::RendererDefined,
            texture_transform_stage: SourceSamplingTransformStage::PostHomographyPreTextureSample,
            texture_transform_owner: "renderer".to_string(),
        }
    }

    pub const fn with_content_uv_rect(mut self, rect: SourceUvRect) -> Self {
        self.content_uv_rect = rect;
        self
    }

    pub const fn with_source_visible_uv_rect(mut self, rect: SourceUvRect) -> Self {
        self.source_visible_uv_rect = rect;
        self
    }

    pub fn with_transform(
        mut self,
        label: impl Into<String>,
        owner: impl Into<String>,
        applied: bool,
    ) -> Self {
        self.transform_label = label.into();
        self.transform_owner = owner.into();
        self.transform_applied = applied;
        self
    }

    pub fn with_sampler(
        mut self,
        output_uv_label: impl Into<String>,
        sampler_uv_origin: impl Into<String>,
        sampler_y_axis: SourceSamplerYAxis,
    ) -> Self {
        self.output_uv_label = output_uv_label.into();
        self.sampler_uv_origin = sampler_uv_origin.into();
        self.sampler_y_axis = sampler_y_axis;
        self
    }

    pub fn with_texture_transform(
        mut self,
        stage: SourceSamplingTransformStage,
        owner: impl Into<String>,
    ) -> Self {
        self.texture_transform_stage = stage;
        self.texture_transform_owner = owner.into();
        self
    }

    pub fn is_valid(&self) -> bool {
        source_sampling_schema_supported(&self.schema_version)
            && !self.backend.trim().is_empty()
            && !self.mode.trim().is_empty()
            && self.content_uv_rect.is_valid()
            && self.source_visible_uv_rect.is_valid()
            && !self.transform_label.trim().is_empty()
            && !self.transform_owner.trim().is_empty()
            && !self.output_uv_label.trim().is_empty()
            && !self.sampler_uv_origin.trim().is_empty()
            && !self.texture_transform_owner.trim().is_empty()
    }
}

fn source_sampling_schema_supported(schema: &str) -> bool {
    schema == HOSTESS_SOURCE_SAMPLING_CONTRACT_SCHEMA
        || schema == LEGACY_RUSTY_XR_SOURCE_SAMPLING_CONTRACT_SCHEMA
}
