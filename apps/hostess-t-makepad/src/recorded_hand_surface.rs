use std::{
    path::{Path, PathBuf},
    sync::Arc,
};

use rusty_quest_makepad_camera_shell::{
    MeshReplayRuntime, QuestMakepadMatterSurfaceWorker, QuestMakepadRecordedHandSourceFrameBuilder,
    QuestMakepadRecordedHandSourceFrameOptions, RecordedCompactHandJointFrame, RecordedHandRig,
    MESH_REPLAY_SOURCE_RECORDED_META_QUEST_HAND_LEFT,
    MESH_REPLAY_SOURCE_RECORDED_META_QUEST_HAND_RIGHT,
};

const LEFT_RIG_FILE: &str = "left.rig.json";
const LEFT_CLIP_FILE: &str = "left.clip.jsonl";
const RIGHT_RIG_FILE: &str = "right.rig.json";
const RIGHT_CLIP_FILE: &str = "right.clip.jsonl";

#[derive(Clone, Debug)]
pub(crate) struct RecordedHandSurfaceSource {
    source_id: String,
    builder: Arc<QuestMakepadRecordedHandSourceFrameBuilder>,
    frames: Vec<RecordedCompactHandJointFrame>,
    vertex_count: usize,
    triangle_count: usize,
    worker_source_markers_emitted: usize,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub(crate) struct RecordedHandSurfaceWorkerSourceSummary {
    source_id: String,
    frame_index: usize,
    vertex_count: usize,
    triangle_count: usize,
    gpu_oracle_payloads_requested: bool,
}

impl RecordedHandSurfaceWorkerSourceSummary {
    fn marker_line(&self, phase: &str, selected_mode: &str) -> String {
        format!(
            "RUSTY_HOSTESS_MAKEPAD_RECORDED_HAND_SURFACE_WORKER_SOURCE schema=rusty.hostess.makepad.recorded_hand_surface_worker_source.v1 phase={} status=ready selectedMode={} sourceId={} providerShape=bind-mesh-plus-compact-joint-frame frameIndex={} vertexCount={} triangleCount={} issue=none recordedHandProvider=true workerSourceSelected=true compactFrameWorkerSubmit=true sourceFrameExpansionThread=matter-worker gpuOraclePayloadsRequested={} recordedInputEquivalent=true gpuAdapterBoundaryUnchanged=true highRateJsonPayload=false",
            crate::runtime_settings::marker_token(phase),
            crate::runtime_settings::marker_token(selected_mode),
            crate::runtime_settings::marker_token(&self.source_id),
            self.frame_index,
            self.vertex_count,
            self.triangle_count,
            self.gpu_oracle_payloads_requested,
        )
    }
}

impl RecordedHandSurfaceSource {
    pub(crate) fn from_replay_runtime(
        effective_settings_path: Option<&str>,
        replay_runtime: &MeshReplayRuntime,
    ) -> Result<Option<Self>, String> {
        let Some((source_id, rig_file, clip_file)) =
            recorded_capture_files(replay_runtime.config().source.as_str())
        else {
            return Ok(None);
        };
        let Some(root) = effective_settings_path
            .and_then(|path| Path::new(path).parent())
            .map(Path::to_path_buf)
        else {
            return Ok(None);
        };

        let Some(rig_path) = resolve_capture_file(&root, rig_file) else {
            return Ok(None);
        };
        let Some(clip_path) = resolve_capture_file(&root, clip_file) else {
            return Ok(None);
        };

        let rig_json = std::fs::read_to_string(&rig_path)
            .map_err(|error| format!("read {} failed: {error}", rig_path.display()))?;
        let rig = RecordedHandRig::from_json_str(&rig_json)
            .map_err(|error| format!("parse {} failed: {error}", rig_path.display()))?;
        let clip_text = std::fs::read_to_string(&clip_path)
            .map_err(|error| format!("read {} failed: {error}", clip_path.display()))?;
        let mut frames = Vec::new();
        for (index, line) in clip_text.lines().enumerate() {
            if line.trim().is_empty() {
                continue;
            }
            let frame = RecordedCompactHandJointFrame::from_json_line(line).map_err(|error| {
                format!(
                    "parse {} line {} failed: {error}",
                    clip_path.display(),
                    index + 1
                )
            })?;
            frames.push(frame);
        }
        if frames.is_empty() {
            return Ok(None);
        }

        let vertex_count = rig.bind_surface.vertex_count();
        let triangle_count = rig.bind_surface.triangle_count();
        let builder = QuestMakepadRecordedHandSourceFrameBuilder::new(source_id, rig)
            .map_err(|error| format!("build {source_id} source-frame builder failed: {error}"))?;

        Ok(Some(Self {
            source_id: source_id.to_owned(),
            builder: Arc::new(builder),
            frames,
            vertex_count,
            triangle_count,
            worker_source_markers_emitted: 0,
        }))
    }

    pub(crate) fn submit_worker_frame_for_replay(
        &self,
        worker: &QuestMakepadMatterSurfaceWorker,
        phase: &str,
        replay_runtime: &MeshReplayRuntime,
        delta_seconds: f32,
        include_gpu_oracle_payloads: bool,
    ) -> RecordedHandSurfaceWorkerSourceSummary {
        let frame_index = replay_runtime.current_frame_index() % self.frames.len();
        let frame = &self.frames[frame_index];
        let options = if include_gpu_oracle_payloads {
            QuestMakepadRecordedHandSourceFrameOptions::gpu_oracle_probes()
        } else {
            QuestMakepadRecordedHandSourceFrameOptions::matter_only()
        };
        worker.submit_recorded_hand_frame(
            phase,
            Arc::clone(&self.builder),
            frame.clone(),
            delta_seconds,
            options,
            "hostess.recorded_hand.center_probe",
        );
        RecordedHandSurfaceWorkerSourceSummary {
            source_id: self.source_id.clone(),
            frame_index: frame.frame_index,
            vertex_count: self.vertex_count,
            triangle_count: self.triangle_count,
            gpu_oracle_payloads_requested: include_gpu_oracle_payloads,
        }
    }

    pub(crate) fn worker_marker_line_if_due(
        &mut self,
        phase: &str,
        selected_mode: &str,
        summary: &RecordedHandSurfaceWorkerSourceSummary,
        marker_limit: usize,
    ) -> Option<String> {
        if self.worker_source_markers_emitted >= marker_limit {
            return None;
        }
        self.worker_source_markers_emitted += 1;
        Some(summary.marker_line(phase, selected_mode))
    }

    pub(crate) fn marker_line(&self, phase: &str) -> String {
        format!(
            "RUSTY_HOSTESS_MAKEPAD_RECORDED_HAND_SURFACE_SOURCE schema=rusty.hostess.makepad.recorded_hand_surface_source.v1 phase={} status=ready sourceId={} frameCount={} providerShape=bind-mesh-plus-compact-joint-frame highRateJsonPayload=false",
            crate::runtime_settings::marker_token(phase),
            crate::runtime_settings::marker_token(&self.source_id),
            self.frames.len(),
        )
    }
}

fn recorded_capture_files(source: &str) -> Option<(&'static str, &'static str, &'static str)> {
    match source {
        MESH_REPLAY_SOURCE_RECORDED_META_QUEST_HAND_LEFT => Some((
            "recorded-meta-quest-hand-left-capture",
            LEFT_RIG_FILE,
            LEFT_CLIP_FILE,
        )),
        MESH_REPLAY_SOURCE_RECORDED_META_QUEST_HAND_RIGHT => Some((
            "recorded-meta-quest-hand-right-capture",
            RIGHT_RIG_FILE,
            RIGHT_CLIP_FILE,
        )),
        _ => None,
    }
}

fn resolve_capture_file(root: &Path, file_name: &str) -> Option<PathBuf> {
    [
        root.join(file_name),
        root.join("hand-recordings").join(file_name),
        root.join("recorded-hand").join(file_name),
        root.join("recorded-hand-capture").join(file_name),
    ]
    .into_iter()
    .find(|path| path.is_file())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn worker_marker_reports_recorded_live_equivalent_shape() {
        let summary = RecordedHandSurfaceWorkerSourceSummary {
            source_id: "recorded-meta-quest-hand-left-capture".to_string(),
            frame_index: 42,
            vertex_count: 1360,
            triangle_count: 2314,
            gpu_oracle_payloads_requested: true,
        };

        let marker = summary.marker_line("unit-test", "recorded-hand-replay");

        assert!(marker.contains("RUSTY_HOSTESS_MAKEPAD_RECORDED_HAND_SURFACE_WORKER_SOURCE"));
        assert!(marker.contains("selectedMode=recorded-hand-replay"));
        assert!(marker.contains("providerShape=bind-mesh-plus-compact-joint-frame"));
        assert!(marker.contains("frameIndex=42"));
        assert!(marker.contains("vertexCount=1360"));
        assert!(marker.contains("triangleCount=2314"));
        assert!(marker.contains("compactFrameWorkerSubmit=true"));
        assert!(marker.contains("sourceFrameExpansionThread=matter-worker"));
        assert!(marker.contains("gpuOraclePayloadsRequested=true"));
        assert!(marker.contains("recordedInputEquivalent=true"));
        assert!(marker.contains("gpuAdapterBoundaryUnchanged=true"));
        assert!(marker.contains("highRateJsonPayload=false"));
    }
}
