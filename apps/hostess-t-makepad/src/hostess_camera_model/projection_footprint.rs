//! Renderer-neutral projection footprint and border layout helpers.

use super::homography::{apply_homography_uv, homography_unit_square_bounding_rect};
use super::{
    ColorRgba, Eye, ImageSize, Rect2, StereoMediaLayout, Vec2,
    LEGACY_RUSTY_XR_TARGET_FOOTPRINT_DEBUG_REGION_COLORS_SCHEMA,
};

/// Public projection/profile defaults for a Quest camera-driven custom layer.
#[cfg_attr(feature = "serde", derive(serde::Deserialize, serde::Serialize))]
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct CameraProjectionProfile {
    pub camera_fov_y_degrees: f32,
    pub preview_fov_y_degrees: f32,
    pub projection_scale: f32,
    pub raw_overlay_overscan: f32,
    pub full_view_overlay_overscan: f32,
    pub edge_fade: f32,
    pub center_offset_uv: Vec2,
}

impl CameraProjectionProfile {
    pub const QUEST_RAW_CAMERA_COMPOSITE: Self = Self {
        camera_fov_y_degrees: 92.0,
        preview_fov_y_degrees: 60.0,
        projection_scale: 1.0,
        raw_overlay_overscan: 1.06,
        full_view_overlay_overscan: 2.10,
        edge_fade: 0.12,
        center_offset_uv: Vec2::ZERO,
    };

    pub fn sanitized(self) -> Self {
        Self {
            camera_fov_y_degrees: finite_positive_or(self.camera_fov_y_degrees, 92.0),
            preview_fov_y_degrees: finite_positive_or(self.preview_fov_y_degrees, 60.0),
            projection_scale: finite_positive_or(self.projection_scale, 1.0),
            raw_overlay_overscan: finite_positive_or(self.raw_overlay_overscan, 1.0).max(1.0),
            full_view_overlay_overscan: finite_positive_or(self.full_view_overlay_overscan, 1.0)
                .max(1.0),
            edge_fade: finite_positive_or(self.edge_fade, 0.0).clamp(0.0, 0.5),
            center_offset_uv: if self.center_offset_uv.is_finite() {
                self.center_offset_uv
            } else {
                Vec2::ZERO
            },
        }
    }
}

impl Default for CameraProjectionProfile {
    fn default() -> Self {
        Self::QUEST_RAW_CAMERA_COMPOSITE
    }
}

/// Floating source window used to fill a target image while preserving aspect.
#[cfg_attr(feature = "serde", derive(serde::Deserialize, serde::Serialize))]
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct SourcePixelWindow {
    pub origin_px: Vec2,
    pub size_px: Vec2,
}

impl SourcePixelWindow {
    pub const fn new(origin_px: Vec2, size_px: Vec2) -> Self {
        Self { origin_px, size_px }
    }

    pub fn is_valid(self) -> bool {
        self.origin_px.is_finite()
            && self.size_px.is_finite()
            && self.size_px.x > 0.0
            && self.size_px.y > 0.0
    }
}

/// Legacy schema id for renderer-neutral video projection geometry logs.
pub const LEGACY_RUSTY_XR_VIDEO_PROJECTION_GEOMETRY_SCHEMA: &str =
    "rusty.xr.video_projection_geometry.v1";

/// Explicit source-to-surface mapping behavior requested by a video feed.
///
/// This is deliberately separate from provenance. A feed may come from a live
/// camera, a broker, a remote headset, or a synthetic generator, but the
/// geometry layer should only branch on this explicit behavior.
#[cfg_attr(feature = "serde", derive(serde::Deserialize, serde::Serialize))]
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub enum VideoProjectionMapping {
    /// Source UV is supplied by a screen-to-source homography.
    #[default]
    ScreenToSourceHomography,
    /// Source UV is supplied by a surface-to-source homography composed with
    /// the display-eye surface mapping.
    SurfaceToSourceHomography,
    /// The feed fills the chosen surface or canvas area directly.
    FullFrameSurface,
}

/// Coordinate space used by metadata-authored target footprint requests.
#[cfg_attr(feature = "serde", derive(serde::Deserialize, serde::Serialize))]
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub enum TargetFootprintCoordinateSpace {
    /// Per-eye display screen UV, top-left origin, positive Y down.
    #[default]
    DisplayEyeScreenUv,
    /// Per-eye visible region mapped to X/Y in `[-1, 1]`, positive Y down.
    VisibleEyeNormalizedYDown,
}

impl TargetFootprintCoordinateSpace {
    pub const fn stable_id(self) -> &'static str {
        match self {
            Self::DisplayEyeScreenUv => "display-eye-screen-uv",
            Self::VisibleEyeNormalizedYDown => "visible-eye-normalized-y-down",
        }
    }
}

/// How a target footprint that leaves the visible eye region is handled.
#[cfg_attr(feature = "serde", derive(serde::Deserialize, serde::Serialize))]
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub enum TargetFootprintClipPolicy {
    /// Draw the visible intersection and log that the requested target clipped.
    #[default]
    ClipToVisibleEye,
}

impl TargetFootprintClipPolicy {
    pub const fn stable_id(self) -> &'static str {
        match self {
            Self::ClipToVisibleEye => "clip-to-visible-eye",
        }
    }
}

/// Explicit target footprint requested by a source or stimulus.
///
/// This is the metadata-owned screen placement. It is deliberately separate
/// from source validity: a target can be clipped by the visible eye bounds,
/// while a source sample can still be valid or invalid inside the visible part.
#[cfg_attr(feature = "serde", derive(serde::Deserialize, serde::Serialize))]
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct TargetScreenFootprint {
    pub coordinate_space: TargetFootprintCoordinateSpace,
    pub requested_screen_uv_rect: Rect2,
    pub visible_screen_uv_rect: Rect2,
    pub clip_policy: TargetFootprintClipPolicy,
    pub clipped: bool,
}

impl TargetScreenFootprint {
    pub fn from_display_eye_screen_uv_rect(rect: Rect2) -> Option<Self> {
        Self::from_display_eye_screen_uv_rect_with_policy(
            rect,
            TargetFootprintClipPolicy::ClipToVisibleEye,
        )
    }

    pub fn from_display_eye_screen_uv_rect_with_policy(
        rect: Rect2,
        clip_policy: TargetFootprintClipPolicy,
    ) -> Option<Self> {
        if !rect_is_non_empty(rect) {
            return None;
        }
        let visible = rect_intersection(rect, Rect2::UNIT)?;
        let clipped = rect_xywh(visible) != rect_xywh(rect);
        Some(Self {
            coordinate_space: TargetFootprintCoordinateSpace::DisplayEyeScreenUv,
            requested_screen_uv_rect: rect,
            visible_screen_uv_rect: visible,
            clip_policy,
            clipped,
        })
    }

    pub fn from_visible_eye_normalized_center_height(
        center: Vec2,
        height: f32,
        aspect_ratio: f32,
    ) -> Option<Self> {
        if !center.is_finite()
            || !height.is_finite()
            || height <= 0.0
            || !aspect_ratio.is_finite()
            || aspect_ratio <= 0.0
        {
            return None;
        }
        let center_uv = Vec2::new((center.x + 1.0) * 0.5, (center.y + 1.0) * 0.5);
        let size = Vec2::new(height * aspect_ratio * 0.5, height * 0.5);
        let rect = Rect2::new(center_uv - size * 0.5, size);
        let mut footprint = Self::from_display_eye_screen_uv_rect(rect)?;
        footprint.coordinate_space = TargetFootprintCoordinateSpace::VisibleEyeNormalizedYDown;
        Some(footprint)
    }

    pub fn is_valid(self) -> bool {
        rect_is_non_empty(self.requested_screen_uv_rect)
            && rect_is_non_empty(self.visible_screen_uv_rect)
    }
}

/// Diagnostic roles that must stay visually distinct from the stimulus itself.
#[cfg_attr(feature = "serde", derive(serde::Deserialize, serde::Serialize))]
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum ProjectionDebugRegion {
    ValidSourceSample,
    BorderFill,
    SourceInvalid,
    TargetClipped,
    EffectExterior,
}

impl ProjectionDebugRegion {
    pub const fn stable_id(self) -> &'static str {
        match self {
            Self::ValidSourceSample => "valid-source-sample",
            Self::BorderFill => "border-fill",
            Self::SourceInvalid => "source-invalid",
            Self::TargetClipped => "target-clipped",
            Self::EffectExterior => "effect-exterior",
        }
    }

    pub const fn debug_rgb(self) -> [f32; 3] {
        match self {
            Self::ValidSourceSample => [0.0, 0.85, 0.10],
            Self::BorderFill => [1.0, 0.0, 0.0],
            Self::SourceInvalid => [1.0, 0.0, 1.0],
            Self::TargetClipped => [0.0, 0.45, 1.0],
            Self::EffectExterior => [0.0, 1.0, 1.0],
        }
    }

    pub fn debug_rgb_token(self) -> String {
        let [r, g, b] = self.debug_rgb();
        format!("{r:.3},{g:.3},{b:.3}")
    }
}

pub fn target_footprint_debug_region_marker_fields() -> String {
    let regions = [
        ProjectionDebugRegion::ValidSourceSample,
        ProjectionDebugRegion::BorderFill,
        ProjectionDebugRegion::SourceInvalid,
        ProjectionDebugRegion::TargetClipped,
        ProjectionDebugRegion::EffectExterior,
    ];
    let mut fields = format!(
        "targetFootprintDebugRegionColorsSchema={}",
        LEGACY_RUSTY_XR_TARGET_FOOTPRINT_DEBUG_REGION_COLORS_SCHEMA
    );
    for region in regions {
        fields.push(' ');
        fields.push_str("debugRegionColor_");
        fields.push_str(region.stable_id());
        fields.push('=');
        fields.push_str(&region.debug_rgb_token());
    }
    fields
}

impl VideoProjectionMapping {
    pub const fn stable_id(self) -> &'static str {
        match self {
            Self::ScreenToSourceHomography => "screen-to-source-homography",
            Self::SurfaceToSourceHomography => "surface-to-source-homography",
            Self::FullFrameSurface => "full-frame-surface",
        }
    }
}

/// Informational source provenance that must not control projection behavior.
#[cfg_attr(feature = "serde", derive(serde::Deserialize, serde::Serialize))]
#[derive(Clone, Debug, Default, PartialEq, Eq)]
pub struct VideoSourceProvenance {
    pub source_kind: String,
    pub transport_kind: String,
    pub provider_label: String,
}

impl VideoSourceProvenance {
    pub fn new(
        source_kind: impl Into<String>,
        transport_kind: impl Into<String>,
        provider_label: impl Into<String>,
    ) -> Self {
        Self {
            source_kind: source_kind.into(),
            transport_kind: transport_kind.into(),
            provider_label: provider_label.into(),
        }
    }

    pub fn is_valid(&self) -> bool {
        !self.source_kind.trim().is_empty()
            && !self.transport_kind.trim().is_empty()
            && !self.provider_label.trim().is_empty()
    }
}

/// Concrete projection behavior exposed by any video feed before renderer
/// geometry is built.
#[cfg_attr(feature = "serde", derive(serde::Deserialize, serde::Serialize))]
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct VideoProjectionBehavior {
    pub mapping: VideoProjectionMapping,
    pub source_valid_uv_rect: Rect2,
    pub content_aspect_ratio: f32,
    pub desired_projection_aspect_ratio: f32,
}

impl VideoProjectionBehavior {
    pub const fn new(
        mapping: VideoProjectionMapping,
        source_valid_uv_rect: Rect2,
        content_aspect_ratio: f32,
        desired_projection_aspect_ratio: f32,
    ) -> Self {
        Self {
            mapping,
            source_valid_uv_rect,
            content_aspect_ratio,
            desired_projection_aspect_ratio,
        }
    }

    pub fn full_source(mapping: VideoProjectionMapping, aspect_ratio: f32) -> Self {
        Self::new(mapping, Rect2::UNIT, aspect_ratio, aspect_ratio)
    }

    pub fn is_valid(self) -> bool {
        rect_is_non_empty(self.source_valid_uv_rect)
            && rect_is_inside_unit(self.source_valid_uv_rect)
            && self.content_aspect_ratio.is_finite()
            && self.content_aspect_ratio > 0.0
            && self.desired_projection_aspect_ratio.is_finite()
            && self.desired_projection_aspect_ratio > 0.0
    }
}

/// Renderer-neutral video feed descriptor.
#[cfg_attr(feature = "serde", derive(serde::Deserialize, serde::Serialize))]
#[derive(Clone, Debug, PartialEq)]
pub struct VideoFeedDescriptor {
    pub source_id: String,
    pub delivered_size: ImageSize,
    pub content_size: ImageSize,
    pub provenance: VideoSourceProvenance,
    pub behavior: VideoProjectionBehavior,
}

impl VideoFeedDescriptor {
    pub fn new(
        source_id: impl Into<String>,
        delivered_size: ImageSize,
        content_size: ImageSize,
        provenance: VideoSourceProvenance,
        behavior: VideoProjectionBehavior,
    ) -> Self {
        Self {
            source_id: source_id.into(),
            delivered_size,
            content_size,
            provenance,
            behavior,
        }
    }

    pub fn is_valid(&self) -> bool {
        !self.source_id.trim().is_empty()
            && self.delivered_size.is_non_empty()
            && self.content_size.is_non_empty()
            && self.provenance.is_valid()
            && self.behavior.is_valid()
    }
}

/// Coverage allocated by the renderer before the feed is placed inside it.
#[cfg_attr(feature = "serde", derive(serde::Deserialize, serde::Serialize))]
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct ProjectionSurfaceDescriptor {
    pub surface_uv_rect: Rect2,
    pub depth_meters: f32,
    pub preview_fov_y_degrees: f32,
    pub preview_offset_y_meters: f32,
    pub raw_overlay_overscan: f32,
}

impl ProjectionSurfaceDescriptor {
    pub const fn new(
        surface_uv_rect: Rect2,
        depth_meters: f32,
        preview_fov_y_degrees: f32,
        preview_offset_y_meters: f32,
        raw_overlay_overscan: f32,
    ) -> Self {
        Self {
            surface_uv_rect,
            depth_meters,
            preview_fov_y_degrees,
            preview_offset_y_meters,
            raw_overlay_overscan,
        }
    }

    pub fn is_valid(self) -> bool {
        rect_is_non_empty(self.surface_uv_rect)
            && self.depth_meters.is_finite()
            && self.depth_meters > 0.0
            && self.preview_fov_y_degrees.is_finite()
            && self.preview_fov_y_degrees > 0.0
            && self.preview_offset_y_meters.is_finite()
            && self.raw_overlay_overscan.is_finite()
            && self.raw_overlay_overscan > 0.0
    }
}

/// Feed placement inside a renderer-owned surface or canvas.
#[cfg_attr(feature = "serde", derive(serde::Deserialize, serde::Serialize))]
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct FeedPlacementDescriptor {
    pub surface_uv_rect: Rect2,
    pub screen_uv_rect: Rect2,
    pub opacity: f32,
}

impl FeedPlacementDescriptor {
    pub const fn new(surface_uv_rect: Rect2, screen_uv_rect: Rect2, opacity: f32) -> Self {
        Self {
            surface_uv_rect,
            screen_uv_rect,
            opacity,
        }
    }

    pub fn is_valid(self) -> bool {
        rect_is_non_empty(self.surface_uv_rect)
            && rect_is_non_empty(self.screen_uv_rect)
            && self.opacity.is_finite()
            && (0.0..=1.0).contains(&self.opacity)
    }
}

/// Fill policy for the non-feed region of a surface/canvas.
#[cfg_attr(feature = "serde", derive(serde::Deserialize, serde::Serialize))]
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub enum ProjectionBorderFillPolicy {
    #[default]
    SolidColor,
    Transparent,
    PassthroughUnderlay,
}

impl ProjectionBorderFillPolicy {
    pub const fn stable_id(self) -> &'static str {
        match self {
            Self::SolidColor => "solid-color",
            Self::Transparent => "transparent",
            Self::PassthroughUnderlay => "passthrough-underlay",
        }
    }
}

/// Border/backdrop policy independent from the video feed.
#[cfg_attr(feature = "serde", derive(serde::Deserialize, serde::Serialize))]
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct ProjectionBorderDescriptor {
    pub fill_policy: ProjectionBorderFillPolicy,
    pub color: ColorRgba,
    pub opacity: f32,
}

impl ProjectionBorderDescriptor {
    pub const fn new(
        fill_policy: ProjectionBorderFillPolicy,
        color: ColorRgba,
        opacity: f32,
    ) -> Self {
        Self {
            fill_policy,
            color,
            opacity,
        }
    }

    pub const fn transparent() -> Self {
        Self::new(
            ProjectionBorderFillPolicy::Transparent,
            ColorRgba::new(0.0, 0.0, 0.0, 0.0),
            0.0,
        )
    }

    pub fn is_valid(self) -> bool {
        self.color.is_finite() && self.opacity.is_finite() && (0.0..=1.0).contains(&self.opacity)
    }
}

impl Default for ProjectionBorderDescriptor {
    fn default() -> Self {
        Self::new(
            ProjectionBorderFillPolicy::SolidColor,
            ColorRgba::WHITE,
            1.0,
        )
    }
}

/// Four screen-space segments that make up `surface - feed`.
#[cfg_attr(feature = "serde", derive(serde::Deserialize, serde::Serialize))]
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct ProjectionBorderLayout {
    pub outer_screen_uv_rect: Rect2,
    pub feed_screen_uv_rect: Rect2,
    pub top: Rect2,
    pub right: Rect2,
    pub bottom: Rect2,
    pub left: Rect2,
    pub descriptor: ProjectionBorderDescriptor,
}

impl ProjectionBorderLayout {
    pub fn segments(self) -> [Rect2; 4] {
        [self.top, self.right, self.bottom, self.left]
    }

    pub fn is_valid(self) -> bool {
        rect_is_non_empty(self.outer_screen_uv_rect)
            && self.feed_screen_uv_rect.is_valid()
            && self.segments().into_iter().all(Rect2::is_valid)
            && self.descriptor.is_valid()
    }
}

/// Shared source-valid footprint sampled in display-eye screen UV.
#[cfg_attr(feature = "serde", derive(serde::Deserialize, serde::Serialize))]
#[derive(Clone, Debug, PartialEq)]
pub struct SourceValidScreenUvFootprint {
    pub active_fraction: f32,
    pub bbox_screen_uv_rect: Rect2,
    pub row_spans: Vec<SourceValidScreenUvRowSpan>,
}

impl SourceValidScreenUvFootprint {
    pub fn bbox_xywh(&self) -> [f32; 4] {
        rect_xywh(self.bbox_screen_uv_rect)
    }

    pub fn bbox_ltrb(&self) -> [f32; 4] {
        rect_ltrb(self.bbox_screen_uv_rect)
    }
}

/// Valid span on one display-eye screen row.
#[cfg_attr(feature = "serde", derive(serde::Deserialize, serde::Serialize))]
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct SourceValidScreenUvRowSpan {
    pub row_y: f32,
    pub active_fraction: f32,
    pub span: Option<(f32, f32)>,
}

/// Per-eye renderer-neutral projection plan.
#[cfg_attr(feature = "serde", derive(serde::Deserialize, serde::Serialize))]
#[derive(Clone, Debug, PartialEq)]
pub struct PerEyeVideoProjectionPlan {
    pub eye: Eye,
    pub mapping: VideoProjectionMapping,
    pub surface_to_screen_uv: [[f32; 3]; 3],
    pub screen_to_surface_uv: [[f32; 3]; 3],
    pub surface_to_source_uv: [[f32; 3]; 3],
    pub screen_to_source_uv: [[f32; 3]; 3],
    pub surface_coverage_screen_uv_rect: Rect2,
    pub feed_placement: FeedPlacementDescriptor,
    pub border: ProjectionBorderLayout,
    pub source_valid_uv_rect: Rect2,
    pub source_valid_screen_uv_footprint: SourceValidScreenUvFootprint,
}

impl PerEyeVideoProjectionPlan {
    #[allow(clippy::too_many_arguments)]
    pub fn from_homographies(
        eye: Eye,
        mapping: VideoProjectionMapping,
        surface_to_screen_uv: [[f32; 3]; 3],
        screen_to_surface_uv: [[f32; 3]; 3],
        surface_to_source_uv: [[f32; 3]; 3],
        screen_to_source_uv: [[f32; 3]; 3],
        feed_placement: FeedPlacementDescriptor,
        source_valid_uv_rect: Rect2,
        border_descriptor: ProjectionBorderDescriptor,
        footprint_grid: usize,
    ) -> Option<Self> {
        if !feed_placement.is_valid()
            || !rect_is_non_empty(source_valid_uv_rect)
            || !rect_is_inside_unit(source_valid_uv_rect)
            || !border_descriptor.is_valid()
        {
            return None;
        }
        let surface_coverage_screen_uv_rect =
            homography_unit_square_bounding_rect(surface_to_screen_uv).unwrap_or(Rect2::UNIT);
        let border = projection_border_layout(
            surface_coverage_screen_uv_rect,
            feed_placement.screen_uv_rect,
            border_descriptor,
        )?;
        let source_valid_screen_uv_footprint =
            if mapping == VideoProjectionMapping::FullFrameSurface {
                SourceValidScreenUvFootprint {
                    active_fraction: 1.0,
                    bbox_screen_uv_rect: Rect2::UNIT,
                    row_spans: vec![
                        SourceValidScreenUvRowSpan {
                            row_y: 0.0,
                            active_fraction: 1.0,
                            span: Some((0.0, 1.0)),
                        },
                        SourceValidScreenUvRowSpan {
                            row_y: 0.5,
                            active_fraction: 1.0,
                            span: Some((0.0, 1.0)),
                        },
                        SourceValidScreenUvRowSpan {
                            row_y: 1.0,
                            active_fraction: 1.0,
                            span: Some((0.0, 1.0)),
                        },
                    ],
                }
            } else {
                source_valid_screen_uv_footprint(
                    screen_to_source_uv,
                    source_valid_uv_rect,
                    footprint_grid,
                )
            };
        Some(Self {
            eye,
            mapping,
            surface_to_screen_uv,
            screen_to_surface_uv,
            surface_to_source_uv,
            screen_to_source_uv,
            surface_coverage_screen_uv_rect,
            feed_placement,
            border,
            source_valid_uv_rect,
            source_valid_screen_uv_footprint,
        })
    }

    pub fn marker_fields(&self, prefix: &str) -> String {
        let prefix = prefix.trim();
        let source_valid = rect_xywh(self.source_valid_uv_rect);
        let surface = rect_xywh(self.surface_coverage_screen_uv_rect);
        let feed = rect_xywh(self.feed_placement.screen_uv_rect);
        let expected = rect_xywh(self.source_valid_screen_uv_footprint.bbox_screen_uv_rect);
        let outer = rect_xywh(self.border.outer_screen_uv_rect);
        let inner = rect_xywh(self.border.feed_screen_uv_rect);
        format!(
            "{prefix}ProjectionGeometrySchema={} {prefix}ProjectionMapping={} {prefix}SurfaceCoverageScreenUvRect={} {prefix}FeedPlacementScreenUvRect={} {prefix}BorderOuterScreenUvRect={} {prefix}BorderInnerScreenUvRect={} {prefix}BorderRegionSemantics=surface_minus_feed {prefix}BorderFillPolicy={} {prefix}SourceValidUvRect={} {prefix}ExpectedSourceValidScreenUvRect={} {prefix}SourceValidActiveFraction={:.6}",
            LEGACY_RUSTY_XR_VIDEO_PROJECTION_GEOMETRY_SCHEMA,
            self.mapping.stable_id(),
            uv_rect_token(surface),
            uv_rect_token(feed),
            uv_rect_token(outer),
            uv_rect_token(inner),
            self.border.descriptor.fill_policy.stable_id(),
            uv_rect_token(source_valid),
            uv_rect_token(expected),
            self.source_valid_screen_uv_footprint.active_fraction,
        )
    }
}

/// Sample the part of display-eye screen UV that maps into a source-valid UV
/// rectangle.
pub fn source_valid_screen_uv_footprint(
    screen_to_source_uv: [[f32; 3]; 3],
    source_valid_uv_rect: Rect2,
    grid: usize,
) -> SourceValidScreenUvFootprint {
    let grid = grid.max(2);
    let mut valid_count = 0_usize;
    let mut min_x = 1.0_f32;
    let mut min_y = 1.0_f32;
    let mut max_x = 0.0_f32;
    let mut max_y = 0.0_f32;
    let step = 1.0 / grid as f32;
    for iy in 0..grid {
        for ix in 0..grid {
            let x = (ix as f32 + 0.5) * step;
            let y = (iy as f32 + 0.5) * step;
            if screen_uv_maps_to_source_uv(
                screen_to_source_uv,
                source_valid_uv_rect,
                Vec2::new(x, y),
            ) {
                valid_count += 1;
                min_x = min_x.min((x - step * 0.5).clamp(0.0, 1.0));
                min_y = min_y.min((y - step * 0.5).clamp(0.0, 1.0));
                max_x = max_x.max((x + step * 0.5).clamp(0.0, 1.0));
                max_y = max_y.max((y + step * 0.5).clamp(0.0, 1.0));
            }
        }
    }
    let bbox_screen_uv_rect = if valid_count == 0 {
        Rect2::new(Vec2::ZERO, Vec2::ZERO)
    } else {
        Rect2::new(
            Vec2::new(min_x, min_y),
            Vec2::new((max_x - min_x).max(0.0), (max_y - min_y).max(0.0)),
        )
    };
    let row_spans = [0.0_f32, 0.5, 1.0]
        .into_iter()
        .map(|row_y| {
            source_valid_screen_uv_row_span(screen_to_source_uv, source_valid_uv_rect, row_y, 256)
        })
        .collect();
    SourceValidScreenUvFootprint {
        active_fraction: valid_count as f32 / (grid * grid) as f32,
        bbox_screen_uv_rect,
        row_spans,
    }
}

/// Sample one display-eye screen row for the source-valid span.
pub fn source_valid_screen_uv_row_span(
    screen_to_source_uv: [[f32; 3]; 3],
    source_valid_uv_rect: Rect2,
    row_y: f32,
    sample_count: usize,
) -> SourceValidScreenUvRowSpan {
    let sample_count = sample_count.max(2);
    let mut min_x = 1.0_f32;
    let mut max_x = 0.0_f32;
    let mut valid_count = 0_usize;
    for index in 0..sample_count {
        let x = index as f32 / (sample_count - 1) as f32;
        if screen_uv_maps_to_source_uv(
            screen_to_source_uv,
            source_valid_uv_rect,
            Vec2::new(x, row_y),
        ) {
            valid_count += 1;
            min_x = min_x.min(x);
            max_x = max_x.max(x);
        }
    }
    SourceValidScreenUvRowSpan {
        row_y,
        active_fraction: valid_count as f32 / sample_count as f32,
        span: (valid_count > 0).then_some((min_x, max_x)),
    }
}

/// Build four border rectangles for the screen-space region outside the feed.
pub fn projection_border_layout(
    outer_screen_uv_rect: Rect2,
    feed_screen_uv_rect: Rect2,
    descriptor: ProjectionBorderDescriptor,
) -> Option<ProjectionBorderLayout> {
    if !rect_is_non_empty(outer_screen_uv_rect)
        || !feed_screen_uv_rect.is_valid()
        || !descriptor.is_valid()
    {
        return None;
    }
    let feed = rect_intersection(outer_screen_uv_rect, feed_screen_uv_rect)
        .unwrap_or_else(|| Rect2::new(outer_screen_uv_rect.center(), Vec2::ZERO));
    let outer_max = outer_screen_uv_rect.max();
    let feed_max = feed.max();
    let top = Rect2::new(
        outer_screen_uv_rect.origin,
        Vec2::new(
            outer_screen_uv_rect.size.x,
            (feed.origin.y - outer_screen_uv_rect.origin.y).max(0.0),
        ),
    );
    let bottom = Rect2::new(
        Vec2::new(outer_screen_uv_rect.origin.x, feed_max.y),
        Vec2::new(
            outer_screen_uv_rect.size.x,
            (outer_max.y - feed_max.y).max(0.0),
        ),
    );
    let middle_height = feed.size.y.max(0.0);
    let left = Rect2::new(
        Vec2::new(outer_screen_uv_rect.origin.x, feed.origin.y),
        Vec2::new(
            (feed.origin.x - outer_screen_uv_rect.origin.x).max(0.0),
            middle_height,
        ),
    );
    let right = Rect2::new(
        Vec2::new(feed_max.x, feed.origin.y),
        Vec2::new((outer_max.x - feed_max.x).max(0.0), middle_height),
    );
    Some(ProjectionBorderLayout {
        outer_screen_uv_rect,
        feed_screen_uv_rect: feed,
        top,
        right,
        bottom,
        left,
        descriptor,
    })
}

pub fn rect_xywh(rect: Rect2) -> [f32; 4] {
    [rect.origin.x, rect.origin.y, rect.size.x, rect.size.y]
}

pub fn rect_ltrb(rect: Rect2) -> [f32; 4] {
    let max = rect.max();
    [rect.origin.x, rect.origin.y, max.x, max.y]
}

pub fn uv_rect_token(rect: [f32; 4]) -> String {
    format!(
        "{:.6},{:.6},{:.6},{:.6}",
        rect[0], rect[1], rect[2], rect[3]
    )
}

/// Return the per-eye pixel domain for a delivered mono/stereo stream.
pub fn delivered_eye_stream_size(
    delivered_size: ImageSize,
    layout: StereoMediaLayout,
) -> Option<ImageSize> {
    if !delivered_size.is_non_empty() {
        return None;
    }

    let size = match layout {
        StereoMediaLayout::Mono | StereoMediaLayout::Separate => delivered_size,
        StereoMediaLayout::SideBySide { .. } => {
            ImageSize::new(delivered_size.width / 2, delivered_size.height)
        }
        StereoMediaLayout::TopBottom { .. } => {
            ImageSize::new(delivered_size.width, delivered_size.height / 2)
        }
    };

    size.is_non_empty().then_some(size)
}

/// Compute a centered crop window that fills `target_size` from `source_size`.
///
/// `overscan` values above `1.0` zoom into the source by shrinking the crop
/// window. This is useful when an app renders a full-view camera projection and
/// wants to avoid underscan or hard source edges.
pub fn centered_fill_source_window(
    source_size: ImageSize,
    target_size: ImageSize,
    overscan: f32,
) -> Option<SourcePixelWindow> {
    if !source_size.is_non_empty() || !target_size.is_non_empty() {
        return None;
    }

    let source_width = source_size.width as f32;
    let source_height = source_size.height as f32;
    let source_aspect = source_width / source_height;
    let target_aspect = target_size.width as f32 / target_size.height as f32;
    let overscan = finite_positive_or(overscan, 1.0).max(1.0);

    let (mut width, mut height) = if source_aspect > target_aspect {
        (source_height * target_aspect, source_height)
    } else {
        (source_width, source_width / target_aspect)
    };
    width /= overscan;
    height /= overscan;

    let origin = Vec2::new((source_width - width) * 0.5, (source_height - height) * 0.5);
    let window = SourcePixelWindow::new(origin, Vec2::new(width, height));
    window.is_valid().then_some(window)
}

/// Compute a simple alpha fade from normalized UV edges.
pub fn edge_fade_alpha(uv: Vec2, edge_fade: f32) -> f32 {
    let edge_fade = finite_positive_or(edge_fade, 0.0).clamp(0.0, 0.5);
    if edge_fade <= f32::EPSILON {
        return 1.0;
    }

    let edge_distance = uv.x.min(1.0 - uv.x).min(uv.y).min(1.0 - uv.y);
    (edge_distance / edge_fade).clamp(0.0, 1.0)
}

fn finite_positive_or(value: f32, fallback: f32) -> f32 {
    if value.is_finite() && value > 0.0 {
        value
    } else {
        fallback
    }
}

fn rect_is_non_empty(rect: Rect2) -> bool {
    rect.is_valid() && rect.size.x > 0.0 && rect.size.y > 0.0
}

fn rect_is_inside_unit(rect: Rect2) -> bool {
    let max = rect.max();
    rect.is_valid() && rect.origin.x >= 0.0 && rect.origin.y >= 0.0 && max.x <= 1.0 && max.y <= 1.0
}

fn rect_contains_uv(rect: Rect2, uv: Vec2) -> bool {
    let max = rect.max();
    uv.x >= rect.origin.x && uv.x <= max.x && uv.y >= rect.origin.y && uv.y <= max.y
}

fn rect_intersection(a: Rect2, b: Rect2) -> Option<Rect2> {
    if !a.is_valid() || !b.is_valid() {
        return None;
    }
    let a_max = a.max();
    let b_max = b.max();
    let min_x = a.origin.x.max(b.origin.x);
    let min_y = a.origin.y.max(b.origin.y);
    let max_x = a_max.x.min(b_max.x);
    let max_y = a_max.y.min(b_max.y);
    if max_x < min_x || max_y < min_y {
        return None;
    }
    Some(Rect2::new(
        Vec2::new(min_x, min_y),
        Vec2::new((max_x - min_x).max(0.0), (max_y - min_y).max(0.0)),
    ))
}

fn screen_uv_maps_to_source_uv(
    screen_to_source_uv: [[f32; 3]; 3],
    source_valid_uv_rect: Rect2,
    screen_uv: Vec2,
) -> bool {
    apply_homography_uv(screen_to_source_uv, screen_uv)
        .map(|source_uv| rect_contains_uv(source_valid_uv_rect, source_uv))
        .unwrap_or(false)
}
