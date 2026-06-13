//! Hostess-local framework-neutral data contracts.
//!
//! This module deliberately contains plain Rust data and small validation
//! helpers only. It does not depend on Android, OpenXR, Vulkan, Makepad, Unity,
//! Meta SDKs, LSL, or downstream application repositories.
//! Existing `rusty.xr.*` schema identifiers remain serialized compatibility
//! values until the relevant contracts are extracted into Lattice, Optics,
//! Matter, GUI, Quest, or Manifold owner crates.
//! The frozen compatibility registry lives in `legacy_rusty_xr_schemas`; new
//! default-lane contracts should not add schema IDs there.
//!
//! Enable the `serde` feature to derive serialization for stable public data
//! contracts without making serialization mandatory for plain Rust consumers.
//!
//! ```
//! use hostess_contracts::{CameraIntrinsics, ImageSize, Vec2};
//!
//! let intrinsics = CameraIntrinsics::new(
//!     Vec2::new(500.0, 510.0),
//!     Vec2::new(320.0, 240.0),
//!     ImageSize::new(640, 480),
//! );
//! assert!(intrinsics.is_valid());
//! ```

pub mod camera;
pub mod depth;
pub mod effect_stack;
pub mod hand;
pub mod home;
pub mod interaction;
pub mod layer;
pub mod legacy_rusty_xr_schemas;
pub mod math;
pub mod passthrough;
pub mod projection_matrix;
pub mod render;
pub mod room;
pub mod strobe;
pub mod time;
pub mod view;

pub use camera::{
    CameraCompositeTier, CameraExtrinsics, CameraFrameAdoptionMode, CameraFrameMetadata,
    CameraFrameMetadataFlags, CameraFrameTiming, CameraGpuBufferDescriptor, CameraImageRotation,
    CameraIntrinsics, CameraPixelDomain, CameraPixelDomainKind, CameraPoseSource,
    CameraProjectionState, CameraProjectionStatus, CameraSourceDiagnostic,
    CameraSourceDiagnosticsReport, CameraSourceId, CameraTextureColorStatus,
    CameraTextureDescriptorShape, CameraTextureLaneColor, CameraTextureLaneContract,
    CameraTextureLaneKind, CameraTextureLaneLifecycle, CameraTextureLaneProjection,
    CameraTextureLaneResource, CameraTextureLaneSource, CameraTextureLaneTiming,
    CameraTextureLaneTransform, CameraTextureResourceKind, CameraTextureSourceKind,
    CameraTextureTransform, ImageSize, ProjectionTargetState, SourceSamplerYAxis,
    SourceSamplingContract, SourceSamplingTransformStage, SourceUvRect,
    StereoCameraCalibrationProfile, StereoCameraCandidateDiagnostic, StereoCameraFrameMetadata,
    StereoCameraFramePair, StereoSourceEyeMapping, TemporalProjectionEdgeMode,
    TemporalProjectionMetrics, TemporalProjectionMode, TemporalProjectionPolicy,
    VisualProjectionState, LEGACY_RUSTY_XR_CAMERA_SOURCE_DIAGNOSTICS_SCHEMA,
    LEGACY_RUSTY_XR_CAMERA_TEXTURE_LANE_CONTRACT_SCHEMA,
    LEGACY_RUSTY_XR_SOURCE_SAMPLING_CONTRACT_SCHEMA,
};
pub use depth::{
    depth_view_position_from_uv, reference_space_point_from_depth_uv,
    render_eye_screen_uv_from_reference_point, ConfidenceFormat, DepthConfidenceSource,
    DepthFormat, DepthFrameDescriptor, DepthMetricRange, DepthPayloadDescriptor,
    DepthSampleIdentityPolicy, DepthViewDescriptor, DepthWorldSpaceContract,
    DepthWorldSpaceMetricRange, DepthWorldSpaceRenderPath, DepthWorldSpaceSourceKind,
    DepthWorldSpaceStageEvidence, DepthWorldSpaceStageKind, EnvironmentDepthState,
    LEGACY_RUSTY_XR_DEPTH_WORLD_SPACE_CONTRACT_SCHEMA,
};
pub use effect_stack::{
    EffectBufferDescriptor, EffectBufferFormat, EffectDiagnosticLayer, EffectLayerComparison,
    EffectLayerComparisonMetrics, EffectLayerMetrics, EffectPassDescriptor, EffectPassInput,
    EffectPassInputRole, EffectPassKind, EffectStackComparisonReport, EffectStackDescriptor,
    LEGACY_RUSTY_XR_EFFECT_STACK_COMPARISON_REPORT_SCHEMA,
    LEGACY_RUSTY_XR_EFFECT_STACK_DESCRIPTOR_SCHEMA,
};
pub use hand::{
    HandJointName, HandJointPose, HandJointSnapshot, HandMeshError, HandMeshSnapshot, Handedness,
    TrackingConfidence,
};
pub use home::{
    ExternalLaunchState, FocusRecoveryAction, FocusRecoveryEvent, FocusRecoveryResult,
    HomeHelperState, HomeMode, HomePanelDescriptor, HomePanelKind, HomePanelPlacement,
    HomeSessionState, HomeSupervisorPolicy, HomeSupervisorState, KioskCommandEvidence,
    KioskCommandOutcome, KioskCommandProvider, KioskCommandRunRecord, KioskControlPlanePhase,
    KioskControlPlaneStatus, KioskSurfaceIntent, LauncherEntry, LauncherEntrySource,
    SettingsShortcutCategory, SettingsShortcutDescriptor,
    LEGACY_RUSTY_XR_HOME_FOCUS_RECOVERY_EVENT_SCHEMA, LEGACY_RUSTY_XR_HOME_LAUNCHER_ENTRY_SCHEMA,
    LEGACY_RUSTY_XR_HOME_PANEL_DESCRIPTOR_SCHEMA, LEGACY_RUSTY_XR_HOME_SESSION_STATE_SCHEMA,
    LEGACY_RUSTY_XR_HOME_SETTINGS_SHORTCUT_SCHEMA, LEGACY_RUSTY_XR_KIOSK_COMMAND_EVIDENCE_SCHEMA,
    LEGACY_RUSTY_XR_KIOSK_COMMAND_RUN_RECORD_SCHEMA,
    LEGACY_RUSTY_XR_KIOSK_CONTROL_PLANE_STATUS_SCHEMA,
};
pub use interaction::{
    HandInfluencePoint, HandMenuActivation, HandMenuAnchor, InteractionRay, XrCanvasHit,
    XrCanvasSurface,
};
pub use layer::{
    FeedbackBorderTuning, PlainStereoLayer, Rect2, StereoLayerCameraPath, StereoLayerContentMode,
    StereoLayerDepthPolicy, StereoLayerPerformanceHints, StereoMediaLayout, VisualFeedbackBorder,
    VisualFeedbackBorderLayout, VisualFeedbackLayerTuning,
};
pub use legacy_rusty_xr_schemas::{LegacyRustyXrSchema, LEGACY_RUSTY_XR_SCHEMAS};
pub use math::{Pose, Quat, Vec2, Vec3};
pub use passthrough::{
    audio_reactive_mono_to_rgba_style, PassthroughColorAdjustment, PassthroughColorLutBinding,
    PassthroughColorLutChannels, PassthroughColorLutSpec, PassthroughColorReproduction,
    PassthroughExtensionRequirements, PassthroughGradientStop,
    PassthroughInterpolatedColorLutBinding, PassthroughLayerPlacement, PassthroughLayerPurpose,
    PassthroughMonoToMonoMap, PassthroughMonoToRgbaMap, PassthroughStyle, PlatformPassthroughLayer,
    PASSTHROUGH_COLOR_MAP_SIZE, XR_FB_PASSTHROUGH_EXTENSION, XR_FB_TRIANGLE_MESH_EXTENSION,
    XR_META_PASSTHROUGH_COLOR_LUT_EXTENSION,
};
pub use projection_matrix::{
    InvalidProjectionFillPolicy, MatrixStepStatus, MatrixSyntheticVideoSource,
    ProjectionFootprintRowSpan, ProjectionFootprintSummary, ProjectionGuideDomain,
    ProjectionMatrixLaneKind, ProjectionMatrixLaneReport, ProjectionPerformanceMatrixPacket,
    ProjectionPerformanceScorecard, ProjectionStageKind, ProjectionStageTokenRow,
    LEGACY_RUSTY_XR_PROJECTION_PERFORMANCE_MATRIX_SCHEMA,
};
pub use render::{
    ColorRgba, CounterSample, CounterValue, RenderCoordinateSpace, RenderPayload, RenderPoint,
    RuntimeCounters,
};
pub use room::{
    CaptureLifecycleState, CapturePermissionState, CaptureSourceKind, CaptureSourceState,
    RoomMeshCoordinateSpace, RoomMeshError, RoomMeshSemanticLabel, RoomMeshSnapshot,
    RoomMeshSourceKind, RoomMeshSourceState, RoomMeshSurface,
};
pub use strobe::{
    safety_class_for_cycle_hz, StrobeFrameFeasibility, StrobeFrequencyPlan, VisualStrobeMode,
    VisualStrobeProfile, VisualStrobeSafetyClass, FULL_FIELD_STROBE_WARNING,
    PHOTOSENSITIVE_RISK_BAND_MAX_HZ, PHOTOSENSITIVE_RISK_BAND_MIN_HZ, WCAG_GENERAL_FLASH_LIMIT_HZ,
    XR_FB_DISPLAY_REFRESH_RATE_EXTENSION,
};
pub use time::FrameTiming;
pub use view::{Eye, EyeView, FieldOfView, StereoViews};

/// Crate version exposed for lightweight smoke checks.
pub const VERSION: &str = env!("CARGO_PKG_VERSION");

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn exposes_workspace_version() {
        assert_eq!(VERSION, "0.1.0");
    }
}
