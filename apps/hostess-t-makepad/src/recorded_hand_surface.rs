use std::path::{Path, PathBuf};

use rusty_quest_makepad_camera_shell::{
    MeshReplayRuntime, QuestMakepadMatterSurfaceError, QuestMakepadMatterSurfaceSourceFrame,
    QuestMakepadRecordedHandSourceFrameBuilder, RecordedCompactHandJointFrame, RecordedHandRig,
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
    builder: QuestMakepadRecordedHandSourceFrameBuilder,
    frames: Vec<RecordedCompactHandJointFrame>,
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

        let builder = QuestMakepadRecordedHandSourceFrameBuilder::new(source_id, rig)
            .map_err(|error| format!("build {source_id} source-frame builder failed: {error}"))?;

        Ok(Some(Self {
            source_id: source_id.to_owned(),
            builder,
            frames,
        }))
    }

    pub(crate) fn source_frame_for_replay(
        &self,
        replay_runtime: &MeshReplayRuntime,
    ) -> Result<QuestMakepadMatterSurfaceSourceFrame, QuestMakepadMatterSurfaceError> {
        let frame_index = replay_runtime.current_frame_index() % self.frames.len();
        self.builder.source_frame(&self.frames[frame_index])
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
