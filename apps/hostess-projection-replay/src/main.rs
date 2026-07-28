mod capsule;
mod compare;
mod control_panel;
mod control_profile;
mod control_transport;
mod execution_plan;
mod sequence;
mod v1_compat;
mod vulkan;

use std::{
    fs,
    path::{Path, PathBuf},
};

use anyhow::{Context, Result};
use capsule::{ArtifactHash, ReplayCapsule, ReplayReport, ValidationReport, REPORT_SCHEMA};
use clap::{Parser, Subcommand};
use sha2::{Digest, Sha256};

#[derive(Debug, Parser)]
#[command(
    name = "hostess-projection-replay",
    about = "Replay an offline projection capsule through its original Vulkan SPIR-V shaders."
)]
struct Args {
    #[command(subcommand)]
    command: Command,
}

#[derive(Debug, Subcommand)]
enum Command {
    /// Render one projection replay capsule.
    Render {
        /// Replay capsule JSON.
        #[arg(long)]
        capsule: PathBuf,

        /// Output directory for guide images, layer images, and the replay report.
        #[arg(long)]
        out: PathBuf,

        /// Optional case-insensitive substring used to select a Vulkan adapter.
        #[arg(long)]
        adapter: Option<String>,
    },
    /// Compare two replay reports with explicit cross-driver tolerances.
    Compare {
        #[arg(long)]
        baseline: PathBuf,
        #[arg(long)]
        candidate: PathBuf,
        #[arg(long)]
        out: PathBuf,
        #[arg(long, default_value_t = 8)]
        max_channel_error: u8,
        #[arg(long, default_value_t = 2)]
        outlier_channel_error: u8,
        #[arg(long, default_value_t = 0.05)]
        max_mean_absolute_error: f64,
        #[arg(long, default_value_t = 0.01)]
        max_outlier_pixel_ratio: f64,
    },
    /// Render and loop a Quest-owned packed stereo camera capture.
    PlayCapture {
        /// Quest capture.manifest.json.
        #[arg(long)]
        capture: PathBuf,
        /// Provider-owned replay capsule used as the effect template.
        #[arg(long)]
        capsule: PathBuf,
        /// Local cache for eye inputs, rendered frames, and the sequence report.
        #[arg(long)]
        out: PathBuf,
        /// Capsule output layer to display.
        #[arg(long, default_value = "final")]
        layer: String,
        /// Optional case-insensitive substring used to select a Vulkan adapter.
        #[arg(long)]
        adapter: Option<String>,
        /// Number of loops; zero loops until the window closes.
        #[arg(long, default_value_t = 0)]
        loops: u32,
        /// Prepare and validate the full sequence without opening a window.
        #[arg(long, default_value_t = false)]
        headless: bool,
        /// Use only the recorded camera pair, disabling video, zone diagnostics, and displacement.
        #[arg(long, default_value_t = false)]
        camera_only: bool,
    },
    /// Open an interactive control panel over a Quest camera replay.
    ControlCapture {
        /// Quest capture.manifest.json.
        #[arg(long)]
        capture: PathBuf,
        /// Provider-owned replay capsule used as the effect template.
        #[arg(long)]
        capsule: PathBuf,
        /// Local cache for eye inputs, rendered frames, and control receipts.
        #[arg(long)]
        out: PathBuf,
        /// Capsule output layer shown when the window opens.
        #[arg(long, default_value = "final")]
        layer: String,
        /// Optional case-insensitive substring used to select a Vulkan adapter.
        #[arg(long)]
        adapter: Option<String>,
        /// Use only the recorded camera pair, disabling video and displacement.
        #[arg(long, default_value_t = false)]
        camera_only: bool,
        /// Directory used for portable control-profile save/load.
        #[arg(long)]
        profile_dir: Option<PathBuf>,
        /// Optional provider-owned, hash-bound replay control transport sidecar.
        #[arg(long)]
        control_transport: Option<PathBuf>,
    },
    /// Validate a v1 or v2 capsule and write its deterministic Hostess execution plan.
    NormalizePlan {
        /// Replay capsule JSON.
        #[arg(long)]
        capsule: PathBuf,
        /// Destination for the normalized plan JSON.
        #[arg(long)]
        out: PathBuf,
    },
    /// Validate and apply a provider control transport, then save a v2 state.
    ControlTransportConformance {
        #[arg(long)]
        capsule: PathBuf,
        #[arg(long)]
        control_transport: PathBuf,
        #[arg(long)]
        out: PathBuf,
        #[arg(long, default_value = "conformance-state")]
        state_id: String,
        #[arg(long, default_value_t = 0.0)]
        elapsed_seconds: f32,
    },
}

fn main() -> Result<()> {
    let args = Args::parse();
    match args.command {
        Command::Render {
            capsule,
            out,
            adapter,
        } => render(capsule, out, adapter),
        Command::Compare {
            baseline,
            candidate,
            out,
            max_channel_error,
            outlier_channel_error,
            max_mean_absolute_error,
            max_outlier_pixel_ratio,
        } => {
            let passed = compare::compare_reports(
                &baseline,
                &candidate,
                &out,
                compare::ComparisonThresholds {
                    max_channel_error,
                    outlier_channel_error,
                    max_mean_absolute_error,
                    max_outlier_pixel_ratio,
                },
            )?;
            println!("{}", out.display());
            if !passed {
                anyhow::bail!("projection replay comparison failed");
            }
            Ok(())
        }
        Command::PlayCapture {
            capture,
            capsule,
            out,
            layer,
            adapter,
            loops,
            headless,
            camera_only,
        } => {
            let sequence = sequence::prepare(
                &capture,
                &capsule,
                &out,
                adapter.as_deref(),
                &layer,
                camera_only,
            )?;
            println!("{}", sequence.report_path.display());
            sequence::play(&sequence, loops, headless)
        }
        Command::ControlCapture {
            capture,
            capsule,
            out,
            layer,
            adapter,
            camera_only,
            profile_dir,
            control_transport,
        } => {
            let sequence = sequence::prepare(
                &capture,
                &capsule,
                &out,
                adapter.as_deref(),
                &layer,
                camera_only,
            )?;
            println!("{}", sequence.report_path.display());
            control_panel::run(
                sequence,
                &capsule,
                &out,
                adapter,
                &layer,
                camera_only,
                profile_dir.as_deref(),
                control_transport.as_deref(),
            )
        }
        Command::NormalizePlan { capsule, out } => normalize_plan(&capsule, &out),
        Command::ControlTransportConformance {
            capsule,
            control_transport,
            out,
            state_id,
            elapsed_seconds,
        } => control_transport_conformance(
            &capsule,
            &control_transport,
            &out,
            state_id,
            elapsed_seconds,
        ),
    }
}

fn control_transport_conformance(
    capsule_path: &Path,
    transport_path: &Path,
    out: &Path,
    state_id: String,
    elapsed_seconds: f32,
) -> Result<()> {
    let loaded = ReplayCapsule::read_bound(capsule_path)?;
    let transport =
        control_transport::ControlTransport::read(transport_path, &loaded.capsule, &loaded.sha256)?;
    let selected = transport
        .phase_controls
        .iter()
        .map(|control| control.default_phase)
        .collect::<Vec<_>>();
    let mut effective = loaded.capsule;
    transport.apply(&mut effective, elapsed_seconds, &selected)?;
    let layer = effective
        .outputs
        .first()
        .context("capsule must declare an output layer")?;
    let values = transport
        .phase_controls
        .iter()
        .zip(selected)
        .map(|(control, value)| (control.control_id.clone(), value))
        .collect();
    let state = control_profile::ReplayControlState {
        schema: control_profile::REPLAY_CONTROL_STATE_SCHEMA.to_string(),
        state_id,
        revision: 0,
        created_unix_ms: 0,
        replay_layer: control_profile::ReplayLayerState {
            layer_token: layer.name.clone(),
            override_value: layer.override_value,
        },
        projection: control_profile::ProjectionControlState {
            scale: 1.0,
            rgb_uniform_f32: effective.projection.rgb_uniform,
            displacement_uniform_f32: effective.projection.displacement_uniform,
            displacement_enabled: effective.projection.displacement_enabled,
            zone_uniform_f32: effective.projection.zone_uniform,
        },
        control_transport: Some(control_profile::ControlTransportState {
            transport_id: transport.transport_id,
            capsule_sha256: loaded.sha256,
            values,
        }),
        preview: None,
    };
    let path = state.write(out)?;
    println!("{}", path.display());
    Ok(())
}

fn normalize_plan(capsule_path: &Path, out: &Path) -> Result<()> {
    let bytes = fs::read(capsule_path)
        .with_context(|| format!("failed to read replay capsule {}", capsule_path.display()))?;
    let schema = serde_json::from_slice::<serde_json::Value>(&bytes)
        .context("invalid replay capsule JSON")?
        .get("schema")
        .and_then(serde_json::Value::as_str)
        .context("replay capsule schema must be a string")?
        .to_string();
    let plan = match schema.as_str() {
        capsule::CAPSULE_SCHEMA => {
            let capsule = ReplayCapsule::read(capsule_path)?;
            v1_compat::normalize(&capsule)
        }
        execution_plan::CAPSULE_V2_SCHEMA => {
            execution_plan::ReplayCapsuleV2::read(capsule_path)?.normalize(capsule_path)?
        }
        _ => anyhow::bail!("unsupported replay capsule schema {schema}"),
    };
    if let Some(parent) = out.parent() {
        fs::create_dir_all(parent)
            .with_context(|| format!("failed to create {}", parent.display()))?;
    }
    fs::write(out, serde_json::to_vec_pretty(&plan)?)
        .with_context(|| format!("failed to write {}", out.display()))?;
    println!("{}", out.display());
    Ok(())
}

fn render(args_capsule: PathBuf, args_out: PathBuf, adapter: Option<String>) -> Result<()> {
    let capsule_path = args_capsule
        .canonicalize()
        .with_context(|| format!("capsule does not exist: {}", args_capsule.display()))?;
    let capsule = ReplayCapsule::read(&capsule_path)?;
    fs::create_dir_all(&args_out)
        .with_context(|| format!("failed to create output directory {}", args_out.display()))?;
    let output_dir = args_out
        .canonicalize()
        .with_context(|| format!("failed to resolve output directory {}", args_out.display()))?;
    let base = capsule_path.parent().unwrap_or_else(|| Path::new("."));

    let shader_hashes = capsule
        .shader_paths()
        .into_iter()
        .map(|(role, path)| {
            let path = capsule::resolve_path(base, path)
                .canonicalize()
                .with_context(|| format!("failed to resolve shader {}", path.display()))?;
            Ok(ArtifactHash {
                role: role.to_string(),
                path: path.display().to_string(),
                sha256: sha256_file(&path)?,
            })
        })
        .collect::<Result<Vec<_>>>()?;

    let render = vulkan::render_capsule(&capsule, &capsule_path, &output_dir, adapter.as_deref())?;
    let report = ReplayReport {
        schema: REPORT_SCHEMA,
        capsule_schema: capsule.schema.clone(),
        capsule_name: capsule.name.clone(),
        capsule_path: capsule_path.display().to_string(),
        capsule_sha256: sha256_file(&capsule_path)?,
        extent: capsule.extent,
        adapter: render.adapter,
        shaders: shader_hashes,
        outputs: render.outputs,
        validation: ValidationReport {
            exact_spirv_loaded: true,
            descriptor_contract: "combined-image-sampler-sets0,1,2,4;uniform-buffer-sets3,5"
                .to_string(),
            guide_push_bytes: capsule.guide.push_left.len() * 4,
            projection_push_bytes: capsule.projection.push_left.len() * 4,
            rgb_uniform_bytes: capsule.projection.rgb_uniform.len() * 4,
            displacement_uniform_bytes: capsule.projection.displacement_uniform.len() * 4,
            zone_uniform_bytes: capsule.projection.zone_uniform.len() * 4,
        },
    };
    let report_path = output_dir.join("replay-report.json");
    fs::write(&report_path, serde_json::to_vec_pretty(&report)?)
        .with_context(|| format!("failed to write {}", report_path.display()))?;
    println!("{}", report_path.display());
    Ok(())
}

pub(crate) fn sha256_file(path: &Path) -> Result<String> {
    let bytes = fs::read(path)
        .with_context(|| format!("failed to read artifact for hashing: {}", path.display()))?;
    let mut hasher = Sha256::new();
    hasher.update(bytes);
    Ok(format!("{:x}", hasher.finalize()))
}
