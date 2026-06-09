use crate::camera_texture_path::MakepadCameraTexturePath;
use makepad_widgets::makepad_platform::event::video_playback::{
    VideoTextureUpdateMetadata, VideoYuvMetadata,
};
use makepad_widgets::makepad_platform::event::XrUpdateEvent;
use makepad_widgets::*;

const CAMERA_PAIR_CLOSE_TIMESTAMP_NS: u64 = 25_000_000;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum StereoEye {
    Left,
    Right,
}

impl StereoEye {
    pub(crate) fn label(self) -> &'static str {
        match self {
            Self::Left => "left",
            Self::Right => "right",
        }
    }

    pub(crate) fn video_id(self) -> LiveId {
        match self {
            Self::Left => live_id!(rusty_makepad_left_camera_import_probe),
            Self::Right => live_id!(rusty_makepad_right_camera_import_probe),
        }
    }

    pub(crate) fn from_video_id(video_id: LiveId) -> Option<Self> {
        if video_id == Self::Left.video_id() {
            Some(Self::Left)
        } else if video_id == Self::Right.video_id() {
            Some(Self::Right)
        } else {
            None
        }
    }
}

#[derive(Clone)]
pub(crate) struct CameraTextureFrameSample {
    pub(crate) side: StereoEye,
    pub(crate) yuv: VideoYuvMetadata,
    pub(crate) metadata: VideoTextureUpdateMetadata,
    pub(crate) texture_path: MakepadCameraTexturePath,
    pub(crate) rotation_steps: f32,
    pub(crate) position_ms: u128,
    pub(crate) texture_update_count: u64,
}

impl CameraTextureFrameSample {
    pub(crate) fn new(
        side: StereoEye,
        yuv: VideoYuvMetadata,
        metadata: VideoTextureUpdateMetadata,
        position_ms: u128,
        texture_update_count: u64,
        texture_path: MakepadCameraTexturePath,
    ) -> Self {
        Self {
            side,
            yuv,
            metadata,
            texture_path,
            rotation_steps: yuv.rotation_steps,
            position_ms,
            texture_update_count,
        }
    }
}

#[derive(Clone)]
pub(crate) struct AdoptedStereoCameraFrame {
    pub(crate) adoption_id: u64,
    pub(crate) left: CameraTextureFrameSample,
    pub(crate) right: CameraTextureFrameSample,
    pub(crate) pairing: StereoFramePairing,
    pub(crate) pose: Option<XrPoseSnapshot>,
}

impl AdoptedStereoCameraFrame {
    pub(crate) fn new(
        adoption_id: u64,
        left: CameraTextureFrameSample,
        right: CameraTextureFrameSample,
        pose: Option<XrPoseSnapshot>,
    ) -> Self {
        let pairing = StereoFramePairing::from_samples(&left, &right);
        Self {
            adoption_id,
            left,
            right,
            pairing,
            pose,
        }
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) struct StereoFramePairing {
    pub(crate) status: &'static str,
    pub(crate) sequence_delta: Option<i64>,
    pub(crate) timestamp_delta_ns: Option<u64>,
    pub(crate) close_timestamp_match: bool,
}

impl StereoFramePairing {
    pub(crate) fn from_samples(
        left: &CameraTextureFrameSample,
        right: &CameraTextureFrameSample,
    ) -> Self {
        let sequence_delta = left
            .metadata
            .camera_frame_sequence
            .zip(right.metadata.camera_frame_sequence)
            .map(|(left, right)| left as i64 - right as i64);
        let timestamp_delta_ns = left
            .metadata
            .camera_timestamp_ns
            .zip(right.metadata.camera_timestamp_ns)
            .map(|(left, right)| left.abs_diff(right));
        let close_timestamp_match = timestamp_delta_ns
            .map(|delta| delta <= CAMERA_PAIR_CLOSE_TIMESTAMP_NS)
            .unwrap_or(false);
        let status = if sequence_delta == Some(0) {
            "sequence-match"
        } else if close_timestamp_match {
            "timestamp-close"
        } else if sequence_delta.is_some() || timestamp_delta_ns.is_some() {
            "latest-complete-with-timing-gap"
        } else {
            "latest-complete-no-frame-timing"
        };
        Self {
            status,
            sequence_delta,
            timestamp_delta_ns,
            close_timestamp_match,
        }
    }
}

#[derive(Clone, Copy, Debug)]
pub(crate) struct XrPoseSnapshot {
    pub(crate) update_count: u64,
    pub(crate) predicted_display_time_ns: i64,
    pub(crate) left_valid: bool,
    pub(crate) right_valid: bool,
    pub(crate) left_position: [f32; 3],
    pub(crate) right_position: [f32; 3],
    pub(crate) left_orientation: [f32; 4],
    pub(crate) right_orientation: [f32; 4],
}

impl XrPoseSnapshot {
    pub(crate) fn from_update(update: &XrUpdateEvent, update_count: u64) -> Self {
        let state = update.state.as_ref();
        let left = state.left_eye_view;
        let right = state.right_eye_view;
        Self {
            update_count,
            predicted_display_time_ns: (state.time * 1_000_000_000.0).round() as i64,
            left_valid: left.valid,
            right_valid: right.valid,
            left_position: [
                left.pose.position.x,
                left.pose.position.y,
                left.pose.position.z,
            ],
            right_position: [
                right.pose.position.x,
                right.pose.position.y,
                right.pose.position.z,
            ],
            left_orientation: [
                left.pose.orientation.x,
                left.pose.orientation.y,
                left.pose.orientation.z,
                left.pose.orientation.w,
            ],
            right_orientation: [
                right.pose.orientation.x,
                right.pose.orientation.y,
                right.pose.orientation.z,
                right.pose.orientation.w,
            ],
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn frame_sample(
        side: StereoEye,
        camera_frame_sequence: Option<u64>,
        camera_timestamp_ns: Option<u64>,
        texture_update_count: u64,
    ) -> CameraTextureFrameSample {
        let mut metadata = VideoTextureUpdateMetadata::default();
        metadata.camera_frame_sequence = camera_frame_sequence;
        metadata.camera_timestamp_ns = camera_timestamp_ns;
        CameraTextureFrameSample::new(
            side,
            VideoYuvMetadata::disabled(),
            metadata,
            texture_update_count as u128,
            texture_update_count,
            MakepadCameraTexturePath::DirectHardwareBufferExternal,
        )
    }

    #[test]
    fn stereo_frame_pairing_prefers_matching_camera_sequence() {
        let left = frame_sample(StereoEye::Left, Some(42), Some(1_000_000), 7);
        let right = frame_sample(StereoEye::Right, Some(42), Some(8_000_000), 8);

        let pairing = StereoFramePairing::from_samples(&left, &right);

        assert_eq!(pairing.status, "sequence-match");
        assert_eq!(pairing.sequence_delta, Some(0));
        assert_eq!(pairing.timestamp_delta_ns, Some(7_000_000));
    }

    #[test]
    fn stereo_frame_pairing_accepts_close_timestamps_when_sequences_differ() {
        let left = frame_sample(StereoEye::Left, Some(101), Some(20_000_000), 3);
        let right = frame_sample(StereoEye::Right, Some(102), Some(30_000_000), 4);

        let pairing = StereoFramePairing::from_samples(&left, &right);

        assert_eq!(pairing.status, "timestamp-close");
        assert_eq!(pairing.sequence_delta, Some(-1));
        assert!(pairing.close_timestamp_match);
    }

    #[test]
    fn stereo_frame_pairing_reports_timing_gap_for_distant_frames() {
        let left = frame_sample(StereoEye::Left, Some(101), Some(20_000_000), 3);
        let right = frame_sample(StereoEye::Right, Some(105), Some(80_000_000), 4);

        let pairing = StereoFramePairing::from_samples(&left, &right);

        assert_eq!(pairing.status, "latest-complete-with-timing-gap");
        assert_eq!(pairing.sequence_delta, Some(-4));
        assert_eq!(pairing.timestamp_delta_ns, Some(60_000_000));
        assert!(!pairing.close_timestamp_match);
    }
}
