use std::{
    fs,
    path::{Component, Path, PathBuf},
    thread,
    time::{Duration, Instant},
};

use anyhow::{bail, Context, Result};
use image::{imageops, RgbaImage};
use minifb::{Key, Window, WindowOptions};
use serde::{Deserialize, Serialize};

use crate::{
    capsule::{ColorInput, ReplayCapsule},
    sha256_file, vulkan,
};

const REPLAY_WINDOW_TITLE: &str = "Rusty Hostess - camera replay";

const CAPTURE_SCHEMA: &str = "rusty.quest.camera_replay_capture.v1";
const SEQUENCE_REPORT_SCHEMA: &str = "rusty.hostess.projection_replay_sequence.v1";
const MAX_CAPTURE_FRAMES: usize = 120;

#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct QuestCaptureManifest {
    schema: String,
    status: String,
    capture_id: String,
    source: String,
    packed_stereo: bool,
    eye_order: String,
    width: u32,
    height: u32,
    pixel_format: String,
    nominal_frame_interval_ms: u32,
    requested_frame_count: u32,
    captured_frame_count: u32,
    started_unix_ms: u64,
    finished_unix_ms: Option<u64>,
    finished_reason: Option<String>,
    frames: Vec<QuestCaptureFrame>,
}

#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct QuestCaptureFrame {
    file: String,
    index: u32,
    byte_length: u64,
    left_camera_id: String,
    right_camera_id: String,
    left_frame_index: u64,
    right_frame_index: u64,
    left_timestamp_ns: i64,
    right_timestamp_ns: i64,
    pair_delta_ns: u64,
}

#[derive(Clone, Debug, Serialize)]
struct SequenceReport {
    schema: &'static str,
    status: &'static str,
    capture_schema: String,
    capture_id: String,
    capture_manifest_path: String,
    capture_manifest_sha256: String,
    capsule_path: String,
    capsule_sha256: String,
    selected_layer: String,
    camera_only: bool,
    flat_video_sequence_active: bool,
    flat_video_frame_count: usize,
    width: u32,
    height: u32,
    nominal_frame_interval_ms: u32,
    frame_count: usize,
    source: String,
    eye_order: String,
    pixel_format: String,
    replay_frames: Vec<SequenceFrameReport>,
    confidence_boundary: &'static str,
}

#[derive(Clone, Debug, Serialize)]
struct SequenceFrameReport {
    index: u32,
    source_file: String,
    source_sha256: String,
    left_input_png: String,
    right_input_png: String,
    video_input_png: Option<String>,
    rendered_png: String,
    rendered_sha256: String,
    left_camera_id: String,
    right_camera_id: String,
    left_frame_index: u64,
    right_frame_index: u64,
    left_timestamp_ns: i64,
    right_timestamp_ns: i64,
    pair_delta_ns: u64,
}

#[derive(Clone, Debug)]
pub(crate) struct PreparedFrameInputs {
    pub(crate) left: PathBuf,
    pub(crate) right: PathBuf,
    pub(crate) video: Option<PathBuf>,
}

pub(crate) struct PreparedSequence {
    pub(crate) width: u32,
    pub(crate) height: u32,
    pub(crate) frame_interval: Duration,
    pub(crate) frame_paths: Vec<PathBuf>,
    pub(crate) input_frames: Vec<PreparedFrameInputs>,
    pub(crate) report_path: PathBuf,
}

pub(crate) fn prepare(
    capture_manifest: &Path,
    capsule_path: &Path,
    output_dir: &Path,
    adapter: Option<&str>,
    selected_layer: &str,
    camera_only: bool,
) -> Result<PreparedSequence> {
    let capture_manifest = capture_manifest.canonicalize().with_context(|| {
        format!(
            "capture manifest does not exist: {}",
            capture_manifest.display()
        )
    })?;
    let capsule_path = capsule_path
        .canonicalize()
        .with_context(|| format!("capsule does not exist: {}", capsule_path.display()))?;
    let capture_bytes = fs::read(&capture_manifest)
        .with_context(|| format!("failed to read {}", capture_manifest.display()))?;
    let manifest: QuestCaptureManifest =
        serde_json::from_slice(&capture_bytes).with_context(|| {
            format!(
                "invalid Quest capture manifest {}",
                capture_manifest.display()
            )
        })?;
    validate_manifest(&manifest)?;

    let mut capsule = ReplayCapsule::read(&capsule_path)?;
    let capsule_base = capsule_path.parent().unwrap_or_else(|| Path::new("."));
    capsule.make_paths_absolute(capsule_base)?;
    let flat_video_frames = match &capsule.inputs.video {
        ColorInput::PngSequence { paths } => Some(paths.clone()),
        _ => None,
    };
    if camera_only {
        capsule.inputs.video = ColorInput::Transparent;
        capsule.projection.displacement_enabled = false;
        // ProjectionZoneUniform::zone starts after six vec4 rectangles.
        // coverage=0 selects the provider shader's legacy camera-only path;
        // debug=0 also prevents a stale synthetic diagnostic from leaking in.
        capsule.projection.zone_uniform[24] = 0.0;
        capsule.projection.zone_uniform[26] = 0.0;
    }
    if let Some(paths) = &flat_video_frames {
        if !camera_only && paths.len() != 1 && paths.len() != manifest.frames.len() {
            bail!(
                "video PNG sequence must contain one frame or exactly {} capture frames, got {}",
                manifest.frames.len(),
                paths.len()
            );
        }
    }
    if capsule.extent.width != manifest.width || capsule.extent.height != manifest.height {
        bail!(
            "capture extent {}x{} does not match capsule extent {}x{}",
            manifest.width,
            manifest.height,
            capsule.extent.width,
            capsule.extent.height
        );
    }
    let output_layer = capsule
        .outputs
        .iter()
        .find(|output| output.name == selected_layer)
        .cloned()
        .with_context(|| format!("capsule has no output layer named {selected_layer}"))?;
    capsule.outputs = vec![output_layer];

    fs::create_dir_all(output_dir)
        .with_context(|| format!("failed to create {}", output_dir.display()))?;
    let output_dir = output_dir
        .canonicalize()
        .with_context(|| format!("failed to resolve {}", output_dir.display()))?;
    let inputs_dir = output_dir.join("camera-inputs");
    let rendered_dir = output_dir.join("rendered");
    fs::create_dir_all(&inputs_dir)?;
    fs::create_dir_all(&rendered_dir)?;
    let capture_base = capture_manifest.parent().unwrap_or_else(|| Path::new("."));

    let mut replay_frames = Vec::with_capacity(manifest.frames.len());
    let mut frame_paths = Vec::with_capacity(manifest.frames.len());
    let mut input_frames = Vec::with_capacity(manifest.frames.len());
    for frame in &manifest.frames {
        let source_path = safe_child_path(capture_base, &frame.file)?;
        let source_bytes = fs::read(&source_path)
            .with_context(|| format!("failed to read capture frame {}", source_path.display()))?;
        let expected_len = manifest.width as usize * manifest.height as usize * 4;
        if frame.byte_length as usize != expected_len || source_bytes.len() != expected_len {
            bail!(
                "capture frame {} has {} bytes; expected {}",
                frame.file,
                source_bytes.len(),
                expected_len
            );
        }
        let packed = RgbaImage::from_raw(manifest.width, manifest.height, source_bytes)
            .with_context(|| format!("invalid packed RGBA frame {}", frame.file))?;
        let left_path = inputs_dir.join(format!("frame-{:04}-left.png", frame.index));
        let right_path = inputs_dir.join(format!("frame-{:04}-right.png", frame.index));
        imageops::crop_imm(&packed, 0, 0, manifest.width / 2, manifest.height)
            .to_image()
            .save(&left_path)?;
        imageops::crop_imm(
            &packed,
            manifest.width / 2,
            0,
            manifest.width / 2,
            manifest.height,
        )
        .to_image()
        .save(&right_path)?;

        capsule.inputs.camera_left = ColorInput::Png {
            path: left_path.clone(),
        };
        capsule.inputs.camera_right = ColorInput::Png {
            path: right_path.clone(),
        };
        let video_input_path = if camera_only {
            None
        } else {
            flat_video_frames.as_ref().map(|paths| {
                paths[if paths.len() == 1 {
                    0
                } else {
                    frame.index as usize
                }]
                .clone()
            })
        };
        if let Some(path) = &video_input_path {
            capsule.inputs.video = ColorInput::Png { path: path.clone() };
        }
        let frame_output_dir = rendered_dir.join(format!("frame-{:04}", frame.index));
        fs::create_dir_all(&frame_output_dir)?;
        let render = vulkan::render_capsule(&capsule, &capsule_path, &frame_output_dir, adapter)?;
        let rendered = render
            .outputs
            .iter()
            .find(|output| output.layer == selected_layer)
            .with_context(|| format!("renderer omitted selected layer {selected_layer}"))?;
        let rendered_path = PathBuf::from(&rendered.path);
        frame_paths.push(rendered_path.clone());
        input_frames.push(PreparedFrameInputs {
            left: left_path.clone(),
            right: right_path.clone(),
            video: video_input_path.clone(),
        });
        replay_frames.push(SequenceFrameReport {
            index: frame.index,
            source_file: source_path.display().to_string(),
            source_sha256: sha256_file(&source_path)?,
            left_input_png: left_path.display().to_string(),
            right_input_png: right_path.display().to_string(),
            video_input_png: video_input_path.map(|path| path.display().to_string()),
            rendered_png: rendered_path.display().to_string(),
            rendered_sha256: rendered.sha256.clone(),
            left_camera_id: frame.left_camera_id.clone(),
            right_camera_id: frame.right_camera_id.clone(),
            left_frame_index: frame.left_frame_index,
            right_frame_index: frame.right_frame_index,
            left_timestamp_ns: frame.left_timestamp_ns,
            right_timestamp_ns: frame.right_timestamp_ns,
            pair_delta_ns: frame.pair_delta_ns,
        });
    }

    let report = SequenceReport {
        schema: SEQUENCE_REPORT_SCHEMA,
        status: "pass",
        capture_schema: manifest.schema,
        capture_id: manifest.capture_id,
        capture_manifest_path: capture_manifest.display().to_string(),
        capture_manifest_sha256: sha256_file(&capture_manifest)?,
        capsule_path: capsule_path.display().to_string(),
        capsule_sha256: sha256_file(&capsule_path)?,
        selected_layer: selected_layer.to_string(),
        camera_only,
        flat_video_sequence_active: !camera_only && flat_video_frames.is_some(),
        flat_video_frame_count: if camera_only {
            0
        } else {
            flat_video_frames.as_ref().map_or(0, Vec::len)
        },
        width: manifest.width,
        height: manifest.height,
        nominal_frame_interval_ms: manifest.nominal_frame_interval_ms,
        frame_count: replay_frames.len(),
        source: manifest.source,
        eye_order: manifest.eye_order,
        pixel_format: manifest.pixel_format,
        replay_frames,
        confidence_boundary:
            "desktop-vulkan-effect-replay-only;quest-composition-performance-and-comfort-remain-device-gates",
    };
    let report_path = output_dir.join("sequence-report.json");
    fs::write(&report_path, serde_json::to_vec_pretty(&report)?)?;
    Ok(PreparedSequence {
        width: manifest.width,
        height: manifest.height,
        frame_interval: Duration::from_millis(u64::from(manifest.nominal_frame_interval_ms)),
        frame_paths,
        input_frames,
        report_path,
    })
}

pub(crate) fn play(sequence: &PreparedSequence, loops: u32, headless: bool) -> Result<()> {
    if sequence.frame_paths.is_empty() {
        bail!("prepared sequence contains no frames");
    }
    if headless {
        for path in &sequence.frame_paths {
            let image = image::open(path)
                .with_context(|| format!("failed to validate rendered frame {}", path.display()))?;
            if image.width() != sequence.width || image.height() != sequence.height {
                bail!("rendered frame {} has the wrong extent", path.display());
            }
        }
        return Ok(());
    }
    let buffers = sequence
        .frame_paths
        .iter()
        .map(|path| load_window_buffer(path, sequence.width, sequence.height))
        .collect::<Result<Vec<_>>>()?;
    let mut window = Window::new(
        REPLAY_WINDOW_TITLE,
        sequence.width as usize,
        sequence.height as usize,
        WindowOptions {
            resize: true,
            scale_mode: minifb::ScaleMode::AspectRatioStretch,
            ..WindowOptions::default()
        },
    )
    .context("failed to open camera replay window")?;
    let mut completed_loops = 0_u32;
    while window.is_open() && !window.is_key_down(Key::Escape) {
        for buffer in &buffers {
            if !window.is_open() || window.is_key_down(Key::Escape) {
                break;
            }
            let started = Instant::now();
            window.update_with_buffer(buffer, sequence.width as usize, sequence.height as usize)?;
            if let Some(remaining) = sequence.frame_interval.checked_sub(started.elapsed()) {
                thread::sleep(remaining);
            }
        }
        completed_loops = completed_loops.saturating_add(1);
        if loops != 0 && completed_loops >= loops {
            break;
        }
    }
    Ok(())
}

fn validate_manifest(manifest: &QuestCaptureManifest) -> Result<()> {
    if manifest.schema != CAPTURE_SCHEMA {
        bail!(
            "unsupported capture schema {}; expected {}",
            manifest.schema,
            CAPTURE_SCHEMA
        );
    }
    if manifest.status != "complete" {
        bail!("capture status must be complete, got {}", manifest.status);
    }
    if !manifest.packed_stereo || manifest.eye_order != "left-right" {
        bail!("capture must be packed left-right stereo");
    }
    if manifest.pixel_format != "rgba8-unorm" {
        bail!(
            "unsupported capture pixel format {}; expected rgba8-unorm",
            manifest.pixel_format
        );
    }
    if manifest.width < 2
        || !manifest.width.is_multiple_of(2)
        || manifest.height < 2
        || manifest.width > 8192
        || manifest.height > 8192
    {
        bail!("capture extent is invalid");
    }
    if !(33..=2_000).contains(&manifest.nominal_frame_interval_ms) {
        bail!("capture frame interval is outside 33..2000 ms");
    }
    if manifest.frames.is_empty() || manifest.frames.len() > MAX_CAPTURE_FRAMES {
        bail!("capture frame count is outside 1..={MAX_CAPTURE_FRAMES}");
    }
    if manifest.captured_frame_count as usize != manifest.frames.len()
        || manifest.requested_frame_count != manifest.captured_frame_count
    {
        bail!("capture frame counts are inconsistent");
    }
    if manifest.finished_unix_ms.is_none()
        || manifest.finished_reason.is_some()
        || manifest.started_unix_ms == 0
    {
        bail!("complete capture has invalid lifecycle fields");
    }
    for (expected_index, frame) in manifest.frames.iter().enumerate() {
        if frame.index as usize != expected_index {
            bail!("capture frame indices are not contiguous");
        }
        if frame.left_camera_id != "50" || frame.right_camera_id != "51" {
            bail!("capture frame {} is not camera 50/51 stereo", frame.index);
        }
    }
    Ok(())
}

fn safe_child_path(base: &Path, value: &str) -> Result<PathBuf> {
    let relative = Path::new(value);
    if relative.is_absolute()
        || relative
            .components()
            .any(|component| !matches!(component, Component::Normal(_)))
    {
        bail!("capture frame path must be one safe relative filename: {value}");
    }
    Ok(base.join(relative))
}

fn load_window_buffer(path: &Path, width: u32, height: u32) -> Result<Vec<u32>> {
    let rgba = image::open(path)
        .with_context(|| format!("failed to open rendered frame {}", path.display()))?
        .into_rgba8();
    if rgba.width() != width || rgba.height() != height {
        bail!("rendered frame {} has the wrong extent", path.display());
    }
    Ok(rgba
        .pixels()
        .map(|pixel| {
            u32::from(pixel[2])
                | (u32::from(pixel[1]) << 8)
                | (u32::from(pixel[0]) << 16)
                | (u32::from(pixel[3]) << 24)
        })
        .collect())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn capture_frame_path_rejects_traversal() {
        assert!(safe_child_path(Path::new("C:/capture"), "../frame.rgba").is_err());
        assert!(safe_child_path(Path::new("C:/capture"), "frame-0000.rgba").is_ok());
    }

    #[test]
    fn replay_window_title_remains_generic_and_hostess_owned() {
        assert_eq!(REPLAY_WINDOW_TITLE, "Rusty Hostess - camera replay");
        let lower = REPLAY_WINDOW_TITLE.to_ascii_lowercase();
        for forbidden in ["morphovision", "colorama", "private effect"] {
            assert!(!lower.contains(forbidden));
        }
    }
}
