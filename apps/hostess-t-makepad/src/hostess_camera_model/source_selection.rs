//! Camera-source selection scoring helpers.

use super::ImageSize;

/// Public Quest camera-source preference used by the example shell.
pub const QUEST_CAMERA_PREFERRED_SQUARE_SIZE: u32 = 1280;

/// Public Quest camera-source cap used before preferring larger formats.
pub const QUEST_CAMERA_MAX_DIMENSION: u32 = 1920;

/// Source-size and source-kind policy for camera adapters.
///
/// The policy is intentionally metadata-only: platform adapters still own the
/// actual API calls, permission prompts, and camera-source handles.
#[cfg_attr(feature = "serde", derive(serde::Deserialize, serde::Serialize))]
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct CameraSourceSelectionPolicy {
    pub preferred_square_size: u32,
    pub max_dimension: u32,
    pub prefer_square: bool,
}

impl CameraSourceSelectionPolicy {
    pub const QUEST_RAW_CAMERA: Self = Self {
        preferred_square_size: QUEST_CAMERA_PREFERRED_SQUARE_SIZE,
        max_dimension: QUEST_CAMERA_MAX_DIMENSION,
        prefer_square: true,
    };
}

impl Default for CameraSourceSelectionPolicy {
    fn default() -> Self {
        Self::QUEST_RAW_CAMERA
    }
}

/// Public input used to rank candidate camera streams.
#[cfg_attr(feature = "serde", derive(serde::Deserialize, serde::Serialize))]
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct CameraSourceCandidate {
    pub size: ImageSize,
    pub is_stereo: bool,
    pub preferred_device_rank: u8,
    pub frame_rate_millihz: Option<u32>,
}

impl CameraSourceCandidate {
    pub const fn new(size: ImageSize) -> Self {
        Self {
            size,
            is_stereo: false,
            preferred_device_rank: 0,
            frame_rate_millihz: None,
        }
    }

    pub const fn with_stereo(mut self, is_stereo: bool) -> Self {
        self.is_stereo = is_stereo;
        self
    }

    pub const fn with_preferred_device_rank(mut self, rank: u8) -> Self {
        self.preferred_device_rank = rank;
        self
    }

    pub const fn with_frame_rate_millihz(mut self, frame_rate_millihz: u32) -> Self {
        self.frame_rate_millihz = Some(frame_rate_millihz);
        self
    }
}

/// Score a camera stream candidate. Higher scores are preferred.
///
/// Ordering priorities are stereo source, preferred device rank, exact
/// preferred square size, formats within the cap, square formats, pixel count,
/// and frame rate. Adapters can use this score directly or mirror it in
/// platform-native code.
pub fn score_camera_source_candidate(
    candidate: CameraSourceCandidate,
    policy: CameraSourceSelectionPolicy,
) -> Option<i64> {
    if !candidate.size.is_non_empty() {
        return None;
    }

    let preferred = policy.preferred_square_size.max(1);
    let cap = policy.max_dimension.max(preferred);
    let width = candidate.size.width;
    let height = candidate.size.height;
    let pixels = width as i64 * height as i64;
    let cap_pixels = cap as i64 * cap as i64;
    let exact_preferred_square = width == preferred && height == preferred;
    let within_cap = width <= cap && height <= cap;

    let mut score = 0_i64;
    if candidate.is_stereo {
        score += 10_000_000_000_000;
    }
    score += candidate.preferred_device_rank as i64 * 1_000_000_000_000;
    if exact_preferred_square {
        score += 100_000_000_000;
    }
    if within_cap {
        score += 10_000_000_000;
    } else {
        score -= 10_000_000_000;
    }
    if policy.prefer_square && width == height {
        score += 1_000_000_000;
    }

    score += pixels.min(cap_pixels) / 16;
    score -= width.abs_diff(preferred) as i64 * 5_000;
    score -= height.abs_diff(preferred) as i64 * 5_000;
    score += candidate.frame_rate_millihz.unwrap_or_default() as i64;
    Some(score)
}
