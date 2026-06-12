use crate::makepad_widgets::makepad_platform::event::{XrHand, XrHandMeshBindData, XrUpdateEvent};
use crate::makepad_widgets::*;
use rusty_quest_makepad_camera_shell::{
    QuestMakepadMatterSurfaceError, QuestMakepadMatterSurfaceSourceFrame,
    QuestMakepadMatterSurfaceWorker, QuestMakepadRecordedHandSourceFrameBuilder,
    QuestMakepadRecordedHandSourceFrameOptions, RecordedCompactHandJointFrame, RecordedHandRig,
};
use std::sync::Arc;

const LIVE_LEFT_SOURCE_ID: &str = "live-meta-quest-hand-left";
const LIVE_RIGHT_SOURCE_ID: &str = "live-meta-quest-hand-right";

#[derive(Clone, Debug, Default)]
pub(crate) struct LiveHandSurfaceSource {
    left: Option<LiveHandSurfaceHandState>,
    right: Option<LiveHandSurfaceHandState>,
    left_rig: Option<LiveHandSurfaceRigCache>,
    right_rig: Option<LiveHandSurfaceRigCache>,
    last_observe_time_seconds: Option<f64>,
    left_ready_marker_emitted: bool,
    right_ready_marker_emitted: bool,
    error_marker_emitted: bool,
}

impl LiveHandSurfaceSource {
    pub(crate) fn reset_markers(&mut self) {
        self.left_ready_marker_emitted = false;
        self.right_ready_marker_emitted = false;
        self.error_marker_emitted = false;
        self.last_observe_time_seconds = None;
    }

    pub(crate) fn observe_update(
        &mut self,
        cx: &mut Cx,
        update: &XrUpdateEvent,
        frame_index: u64,
        phase: &str,
        min_interval_seconds: Option<f64>,
    ) -> Option<String> {
        if !self.should_observe(update.state.time, min_interval_seconds) {
            return None;
        }
        let timestamp_ns = timestamp_ns(update.state.time);
        let left_bind = cx.xr_hand_mesh_bind_data(true);
        if let Some(marker) = self.observe_hand(
            true,
            &update.state.left_hand,
            left_bind.as_ref(),
            frame_index,
            timestamp_ns,
            phase,
        ) {
            return Some(marker);
        }

        let right_bind = cx.xr_hand_mesh_bind_data(false);
        self.observe_hand(
            false,
            &update.state.right_hand,
            right_bind.as_ref(),
            frame_index,
            timestamp_ns,
            phase,
        )
    }

    #[cfg(test)]
    pub(crate) fn source_frame_for_latest(
        &self,
    ) -> Result<Option<QuestMakepadMatterSurfaceSourceFrame>, QuestMakepadMatterSurfaceError> {
        self.source_frame_for_latest_matching(None)
    }

    #[cfg(test)]
    pub(crate) fn source_frame_for_latest_matching(
        &self,
        is_left: Option<bool>,
    ) -> Result<Option<QuestMakepadMatterSurfaceSourceFrame>, QuestMakepadMatterSurfaceError> {
        if matches!(is_left, None | Some(true)) {
            if let Some(left) = self.left.as_ref() {
                return left.source_frame().map(Some);
            }
        }
        if matches!(is_left, None | Some(false)) {
            return self
                .right
                .as_ref()
                .map(LiveHandSurfaceHandState::source_frame)
                .transpose();
        }
        Ok(None)
    }

    pub(crate) fn submit_worker_frame_for_latest_matching(
        &self,
        worker: &QuestMakepadMatterSurfaceWorker,
        phase: &str,
        is_left: Option<bool>,
        delta_seconds: f32,
        include_gpu_oracle_payloads: bool,
    ) -> Option<LiveHandSurfaceWorkerSourceSummary> {
        let state = self.latest_matching(is_left)?;
        let options = if include_gpu_oracle_payloads {
            QuestMakepadRecordedHandSourceFrameOptions::gpu_oracle_probes()
        } else {
            QuestMakepadRecordedHandSourceFrameOptions::matter_only()
        };
        worker.submit_recorded_hand_frame(
            phase,
            Arc::clone(&state.builder),
            state.compact_frame.clone(),
            delta_seconds,
            options,
            "hostess.live_openxr_hand.center_probe",
        );
        Some(LiveHandSurfaceWorkerSourceSummary::from_state(
            state,
            include_gpu_oracle_payloads,
        ))
    }

    #[cfg(test)]
    pub(crate) fn has_latest_matching(&self, is_left: Option<bool>) -> bool {
        match is_left {
            Some(true) => self.left.is_some(),
            Some(false) => self.right.is_some(),
            None => self.left.is_some() || self.right.is_some(),
        }
    }

    fn latest_matching(&self, is_left: Option<bool>) -> Option<&LiveHandSurfaceHandState> {
        if matches!(is_left, None | Some(true)) {
            if let Some(left) = self.left.as_ref() {
                return Some(left);
            }
        }
        if matches!(is_left, None | Some(false)) {
            return self.right.as_ref();
        }
        None
    }

    fn observe_hand(
        &mut self,
        is_left: bool,
        hand: &XrHand,
        bind: Option<&XrHandMeshBindData>,
        frame_index: u64,
        timestamp_ns: u64,
        phase: &str,
    ) -> Option<String> {
        let bind = bind?;
        if !hand.in_view() {
            return None;
        }
        let rig_cache = if is_left {
            &mut self.left_rig
        } else {
            &mut self.right_rig
        };
        if rig_cache
            .as_ref()
            .is_none_or(|cache| !cache.matches_bind(is_left, bind))
        {
            match LiveHandSurfaceRigCache::from_bind(is_left, bind) {
                Ok(cache) => *rig_cache = Some(cache),
                Err(issue) => return self.live_hand_error_marker(phase, issue),
            }
        }
        let Some(rig_cache) = rig_cache.as_ref() else {
            return self.live_hand_error_marker(phase, "live_hand_bind_cache_missing".to_string());
        };

        match LiveHandSurfaceHandState::from_makepad_hand(
            is_left,
            hand,
            frame_index,
            timestamp_ns,
            rig_cache,
        ) {
            Ok(state) => {
                let emit_ready = if is_left {
                    let emit = !self.left_ready_marker_emitted;
                    self.left = Some(state.clone());
                    self.left_ready_marker_emitted = true;
                    emit
                } else {
                    let emit = !self.right_ready_marker_emitted;
                    self.right = Some(state.clone());
                    self.right_ready_marker_emitted = true;
                    emit
                };
                emit_ready.then(|| state.marker_line(phase))
            }
            Err(issue) => self.live_hand_error_marker(phase, issue),
        }
    }

    fn should_observe(&mut self, time_seconds: f64, min_interval_seconds: Option<f64>) -> bool {
        if self.left.is_none() && self.right.is_none() {
            self.last_observe_time_seconds = time_seconds.is_finite().then_some(time_seconds);
            return true;
        }
        let Some(min_interval_seconds) = min_interval_seconds else {
            self.last_observe_time_seconds = time_seconds.is_finite().then_some(time_seconds);
            return true;
        };
        if !time_seconds.is_finite()
            || !min_interval_seconds.is_finite()
            || min_interval_seconds <= 0.0
        {
            self.last_observe_time_seconds = time_seconds.is_finite().then_some(time_seconds);
            return true;
        }
        if self
            .last_observe_time_seconds
            .is_none_or(|last| time_seconds - last >= min_interval_seconds)
        {
            self.last_observe_time_seconds = Some(time_seconds);
            return true;
        }
        false
    }

    fn live_hand_error_marker(&mut self, phase: &str, issue: String) -> Option<String> {
        if self.error_marker_emitted {
            return None;
        }
        self.error_marker_emitted = true;
        Some(format!(
            "RUSTY_HOSTESS_MAKEPAD_LIVE_HAND_SURFACE_SOURCE schema=rusty.hostess.makepad.live_hand_surface_source.v1 phase={} status=error issue={} providerShape=bind-mesh-plus-compact-joint-frame liveOpenXrHandProvider=true highRateJsonPayload=false",
            crate::runtime_settings::marker_token(phase),
            crate::runtime_settings::marker_token(&issue),
        ))
    }
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub(crate) struct LiveHandSurfaceWorkerSourceSummary {
    pub(crate) source_id: &'static str,
    pub(crate) frame_index: usize,
    pub(crate) vertex_count: usize,
    pub(crate) triangle_count: usize,
    pub(crate) gpu_oracle_payloads_requested: bool,
}

impl LiveHandSurfaceWorkerSourceSummary {
    fn from_state(state: &LiveHandSurfaceHandState, gpu_oracle_payloads_requested: bool) -> Self {
        Self {
            source_id: state.source_id,
            frame_index: state.compact_frame.frame_index,
            vertex_count: state.vertex_count,
            triangle_count: state.index_count / 3,
            gpu_oracle_payloads_requested,
        }
    }
}

#[derive(Clone, Debug)]
struct LiveHandSurfaceRigCache {
    builder: Arc<QuestMakepadRecordedHandSourceFrameBuilder>,
    is_left: bool,
    bind_version: u32,
    joint_count: usize,
    vertex_count: usize,
    normal_count: usize,
    index_count: usize,
}

impl LiveHandSurfaceRigCache {
    fn from_bind(is_left: bool, bind: &XrHandMeshBindData) -> Result<Self, String> {
        let joint_bind_poses = bind
            .joint_bind_poses
            .iter()
            .copied()
            .map(pose_arrays)
            .collect::<Vec<_>>();
        let vertex_positions = bind
            .vertex_positions
            .iter()
            .copied()
            .map(vec3_array)
            .collect::<Vec<_>>();
        let vertex_normals = bind
            .vertex_normals
            .iter()
            .copied()
            .map(vec3_array)
            .collect::<Vec<_>>();
        let rig = RecordedHandRig::from_makepad_openxr_bind_data(
            is_left,
            bind.bind_version,
            &joint_bind_poses,
            &bind.joint_radii,
            &bind.joint_parent_indices,
            &vertex_positions,
            &vertex_normals,
            &bind.vertex_blend_indices,
            &bind.vertex_blend_weights,
            &bind.indices,
        )
        .map_err(|error| format!("live_hand_bind_data:{error}"))?;
        let source_id = if is_left {
            LIVE_LEFT_SOURCE_ID
        } else {
            LIVE_RIGHT_SOURCE_ID
        };
        let builder = QuestMakepadRecordedHandSourceFrameBuilder::new(source_id, rig)
            .map_err(|error| format!("live_hand_source_builder:{error}"))?;

        Ok(Self {
            builder: Arc::new(builder),
            is_left,
            bind_version: bind.bind_version,
            joint_count: bind.joint_bind_poses.len(),
            vertex_count: bind.vertex_positions.len(),
            normal_count: bind.vertex_normals.len(),
            index_count: bind.indices.len(),
        })
    }

    fn matches_bind(&self, is_left: bool, bind: &XrHandMeshBindData) -> bool {
        self.is_left == is_left
            && self.bind_version == bind.bind_version
            && self.joint_count == bind.joint_bind_poses.len()
            && self.vertex_count == bind.vertex_positions.len()
            && self.normal_count == bind.vertex_normals.len()
            && self.index_count == bind.indices.len()
    }
}

#[derive(Clone, Debug)]
struct LiveHandSurfaceHandState {
    source_id: &'static str,
    is_left: bool,
    builder: Arc<QuestMakepadRecordedHandSourceFrameBuilder>,
    compact_frame: RecordedCompactHandJointFrame,
    bind_version: u32,
    joint_count: usize,
    vertex_count: usize,
    index_count: usize,
}

impl LiveHandSurfaceHandState {
    fn from_makepad_hand(
        is_left: bool,
        hand: &XrHand,
        frame_index: u64,
        timestamp_ns: u64,
        rig_cache: &LiveHandSurfaceRigCache,
    ) -> Result<Self, String> {
        let joint_poses = hand
            .joints
            .iter()
            .copied()
            .map(pose_arrays)
            .collect::<Vec<_>>();
        let compact_frame = RecordedCompactHandJointFrame::from_makepad_openxr_compact_frame(
            is_left,
            usize::try_from(frame_index).unwrap_or(usize::MAX),
            timestamp_ns,
            &joint_poses,
            hand.tips,
            [
                hand.pinch_strength_index(),
                hand.pinch_strength_middle(),
                hand.pinch_strength_ring(),
                hand.pinch_strength_pinky(),
            ],
        )
        .map_err(|error| format!("live_hand_compact_frame:{error}"))?;

        Ok(Self {
            source_id: if is_left {
                LIVE_LEFT_SOURCE_ID
            } else {
                LIVE_RIGHT_SOURCE_ID
            },
            is_left,
            builder: Arc::clone(&rig_cache.builder),
            compact_frame,
            bind_version: rig_cache.bind_version,
            joint_count: rig_cache.joint_count,
            vertex_count: rig_cache.vertex_count,
            index_count: rig_cache.index_count,
        })
    }

    #[allow(dead_code)]
    fn source_frame(
        &self,
    ) -> Result<QuestMakepadMatterSurfaceSourceFrame, QuestMakepadMatterSurfaceError> {
        self.builder.source_frame(&self.compact_frame)
    }

    fn marker_line(&self, phase: &str) -> String {
        format!(
            "RUSTY_HOSTESS_MAKEPAD_LIVE_HAND_SURFACE_SOURCE schema=rusty.hostess.makepad.live_hand_surface_source.v1 phase={} status=ready sourceId={} handedness={} frameIndex={} bindVersion={} jointCount={} vertexCount={} indexCount={} providerShape=bind-mesh-plus-compact-joint-frame liveOpenXrHandProvider=true recordedInputEquivalent=true gpuAdapterBoundaryUnchanged=true highRateJsonPayload=false",
            crate::runtime_settings::marker_token(phase),
            crate::runtime_settings::marker_token(self.source_id),
            if self.is_left { "left" } else { "right" },
            self.compact_frame.frame_index,
            self.bind_version,
            self.joint_count,
            self.vertex_count,
            self.index_count,
        )
    }
}

fn pose_arrays(
    pose: crate::makepad_widgets::makepad_platform::makepad_math::Pose,
) -> ([f32; 3], [f32; 4]) {
    (
        vec3_array(pose.position),
        [
            pose.orientation.x,
            pose.orientation.y,
            pose.orientation.z,
            pose.orientation.w,
        ],
    )
}

fn vec3_array(value: crate::makepad_widgets::makepad_platform::makepad_math::Vec3) -> [f32; 3] {
    [value.x, value.y, value.z]
}

fn timestamp_ns(time_seconds: f64) -> u64 {
    if !time_seconds.is_finite() || time_seconds <= 0.0 {
        return 0;
    }
    (time_seconds * 1_000_000_000.0)
        .round()
        .clamp(0.0, u64::MAX as f64) as u64
}

#[cfg(test)]
mod tests {
    use super::*;
    use makepad_widgets::makepad_platform::makepad_math::{vec2f, vec3f, Pose, Quat};

    #[test]
    fn live_makepad_hand_builds_recorded_equivalent_source_frame() {
        let mut source = LiveHandSurfaceSource::default();
        let hand = synthetic_hand();
        let bind = synthetic_bind();

        let marker = source
            .observe_hand(true, &hand, Some(&bind), 7, 2_000_000_000, "unit-test")
            .expect("ready marker emitted");
        assert!(marker.contains("sourceId=live-meta-quest-hand-left"));
        assert!(marker.contains("providerShape=bind-mesh-plus-compact-joint-frame"));
        assert!(marker.contains("recordedInputEquivalent=true"));

        let source_frame = source
            .source_frame_for_latest()
            .expect("source frame result")
            .expect("source frame present");
        assert_eq!(source_frame.source_id, LIVE_LEFT_SOURCE_ID);
        assert_eq!(source_frame.frame.frame_index, 7);
        assert_eq!(source_frame.frame.surface.vertex_count(), 3);
        assert_eq!(source_frame.frame.surface.triangle_count(), 1);
        assert!(source_frame.gpu_skinning_probe.is_some());
        assert!(source_frame.gpu_skinning_mesh_probe.is_some());
        assert!(source_frame.gpu_mesh_sdf_probe.is_some());
        let position = source_frame.frame.surface.positions[2];
        assert_eq!([position.x, position.y, position.z], [1.0, 1.0, -0.25]);
        assert!(source.has_latest_matching(Some(true)));
        assert!(!source.has_latest_matching(Some(false)));
        let summary = LiveHandSurfaceWorkerSourceSummary::from_state(
            source.latest_matching(Some(true)).unwrap(),
            false,
        );
        assert_eq!(summary.source_id, LIVE_LEFT_SOURCE_ID);
        assert_eq!(summary.frame_index, 7);
        assert_eq!(summary.vertex_count, 3);
        assert_eq!(summary.triangle_count, 1);
        assert!(!summary.gpu_oracle_payloads_requested);
        assert_eq!(
            source
                .source_frame_for_latest_matching(Some(false))
                .expect("right frame result"),
            None
        );
    }

    #[test]
    fn live_observe_interval_keeps_first_frame_and_bounds_followups() {
        let mut source = LiveHandSurfaceSource::default();

        assert!(source.should_observe(1.0, Some(0.25)));
        source
            .observe_hand(
                true,
                &synthetic_hand(),
                Some(&synthetic_bind()),
                0,
                0,
                "unit-test",
            )
            .expect("ready marker emitted");

        assert!(!source.should_observe(1.1, Some(0.25)));
        assert!(source.should_observe(1.25, Some(0.25)));
        assert!(source.should_observe(1.26, None));
    }

    fn synthetic_hand() -> XrHand {
        let mut hand = XrHand::default();
        hand.flags = XrHand::IN_VIEW;
        hand.tips[XrHand::INDEX_TIP] = 0.25;
        hand.tips_active = 1 << XrHand::INDEX_TIP;
        hand.joints[XrHand::CENTER] = pose(0.0, 0.0, 0.0);
        hand.joints[XrHand::WRIST] = pose(0.0, -0.1, 0.0);
        hand.joints[XrHand::INDEX_KNUCKLE3] = pose(1.0, 0.0, 0.0);
        hand
    }

    fn synthetic_bind() -> XrHandMeshBindData {
        let mut bind = XrHandMeshBindData {
            is_left: true,
            bind_version: 1,
            joint_bind_poses: vec![pose(0.0, 0.0, 0.0); 26],
            joint_radii: vec![0.01; 26],
            joint_parent_indices: vec![-1; 26],
            vertex_positions: vec![
                vec3f(0.0, 0.0, 0.0),
                vec3f(1.0, 0.0, -0.5),
                vec3f(1.0, 1.0, -0.5),
            ],
            vertex_normals: vec![
                vec3f(0.0, 1.0, 0.0),
                vec3f(0.0, 1.0, 0.0),
                vec3f(0.0, 1.0, 0.0),
            ],
            vertex_uvs: vec![vec2f(0.0, 0.0), vec2f(1.0, 0.0), vec2f(1.0, 1.0)],
            vertex_blend_indices: vec![[0, 0, 0, 0], [9, 0, 0, 0], [10, 0, 0, 0]],
            vertex_blend_weights: vec![
                [1.0, 0.0, 0.0, 0.0],
                [1.0, 0.0, 0.0, 0.0],
                [1.0, 0.0, 0.0, 0.0],
            ],
            indices: vec![0, 1, 2],
        };
        bind.joint_bind_poses[9] = pose(1.0, 0.0, -0.5);
        bind.joint_bind_poses[10] = pose(1.0, 0.0, -0.5);
        bind.joint_parent_indices[10] = 9;
        bind
    }

    fn pose(x: f32, y: f32, z: f32) -> Pose {
        Pose::new(Quat::default(), vec3f(x, y, z))
    }
}
