use std::{
    collections::BTreeMap,
    fs,
    path::{Path, PathBuf},
};

use anyhow::{bail, Context, Result};
use image::GenericImageView;
use serde::{Deserialize, Serialize};

use crate::{
    capsule::{COMPARISON_SCHEMA, REPORT_SCHEMA},
    sha256_file,
};

#[derive(Clone, Copy, Debug)]
pub struct ComparisonThresholds {
    pub max_channel_error: u8,
    pub outlier_channel_error: u8,
    pub max_mean_absolute_error: f64,
    pub max_outlier_pixel_ratio: f64,
}

#[derive(Debug, Deserialize)]
struct ComparableReport {
    schema: String,
    adapter: ComparableAdapter,
    outputs: Vec<ComparableOutput>,
}

#[derive(Debug, Deserialize, Serialize)]
struct ComparableAdapter {
    name: String,
}

#[derive(Debug, Deserialize)]
struct ComparableOutput {
    layer: String,
    path: PathBuf,
    sha256: String,
}

#[derive(Debug, Serialize)]
struct ComparisonReport {
    schema: &'static str,
    status: &'static str,
    baseline_report: ReportReference,
    candidate_report: ReportReference,
    thresholds: ThresholdReport,
    layers: Vec<LayerComparison>,
}

#[derive(Debug, Serialize)]
struct ReportReference {
    path: String,
    sha256: String,
    adapter: String,
}

#[derive(Debug, Serialize)]
struct ThresholdReport {
    max_channel_error: u8,
    outlier_channel_error: u8,
    max_mean_absolute_error: f64,
    max_outlier_pixel_ratio: f64,
}

#[derive(Debug, Serialize)]
struct LayerComparison {
    layer: String,
    baseline_path: String,
    candidate_path: String,
    exact_sha256: bool,
    width: u32,
    height: u32,
    max_absolute_channel_error: u8,
    mean_absolute_channel_error: f64,
    outlier_pixel_count: u64,
    outlier_pixel_ratio: f64,
    status: &'static str,
}

pub fn compare_reports(
    baseline_path: &Path,
    candidate_path: &Path,
    output_path: &Path,
    thresholds: ComparisonThresholds,
) -> Result<bool> {
    validate_thresholds(thresholds)?;
    let baseline = read_report(baseline_path)?;
    let candidate = read_report(candidate_path)?;
    let candidate_outputs = candidate
        .outputs
        .iter()
        .map(|output| (output.layer.as_str(), output))
        .collect::<BTreeMap<_, _>>();
    let baseline_names = baseline
        .outputs
        .iter()
        .map(|output| output.layer.as_str())
        .collect::<Vec<_>>();
    if baseline_names.len() != candidate_outputs.len()
        || baseline_names
            .iter()
            .any(|name| !candidate_outputs.contains_key(name))
    {
        bail!("baseline and candidate reports do not contain the same output layers");
    }

    let mut layers = Vec::with_capacity(baseline.outputs.len());
    let mut passed = true;
    for baseline_output in &baseline.outputs {
        let candidate_output = candidate_outputs[baseline_output.layer.as_str()];
        let baseline_image = image::open(&baseline_output.path).with_context(|| {
            format!(
                "failed to load baseline layer {}",
                baseline_output.path.display()
            )
        })?;
        let candidate_image = image::open(&candidate_output.path).with_context(|| {
            format!(
                "failed to load candidate layer {}",
                candidate_output.path.display()
            )
        })?;
        if baseline_image.dimensions() != candidate_image.dimensions() {
            bail!(
                "layer {} dimensions differ: {:?} vs {:?}",
                baseline_output.layer,
                baseline_image.dimensions(),
                candidate_image.dimensions()
            );
        }
        let baseline_rgba = baseline_image.to_rgba8();
        let candidate_rgba = candidate_image.to_rgba8();
        let mut maximum = 0_u8;
        let mut total = 0_u64;
        let mut outlier_pixels = 0_u64;
        for (baseline_pixel, candidate_pixel) in baseline_rgba
            .as_raw()
            .chunks_exact(4)
            .zip(candidate_rgba.as_raw().chunks_exact(4))
        {
            let mut pixel_maximum = 0_u8;
            for channel in 0..4 {
                let difference = baseline_pixel[channel].abs_diff(candidate_pixel[channel]);
                maximum = maximum.max(difference);
                pixel_maximum = pixel_maximum.max(difference);
                total += difference as u64;
            }
            if pixel_maximum > thresholds.outlier_channel_error {
                outlier_pixels += 1;
            }
        }
        let channel_count = baseline_rgba.as_raw().len() as f64;
        let pixel_count = (baseline_rgba.width() as u64) * (baseline_rgba.height() as u64);
        let mean = total as f64 / channel_count;
        let outlier_ratio = outlier_pixels as f64 / pixel_count as f64;
        let layer_passed = maximum <= thresholds.max_channel_error
            && mean <= thresholds.max_mean_absolute_error
            && outlier_ratio <= thresholds.max_outlier_pixel_ratio;
        passed &= layer_passed;
        layers.push(LayerComparison {
            layer: baseline_output.layer.clone(),
            baseline_path: baseline_output.path.display().to_string(),
            candidate_path: candidate_output.path.display().to_string(),
            exact_sha256: baseline_output.sha256 == candidate_output.sha256,
            width: baseline_rgba.width(),
            height: baseline_rgba.height(),
            max_absolute_channel_error: maximum,
            mean_absolute_channel_error: mean,
            outlier_pixel_count: outlier_pixels,
            outlier_pixel_ratio: outlier_ratio,
            status: if layer_passed { "pass" } else { "fail" },
        });
    }

    let report = ComparisonReport {
        schema: COMPARISON_SCHEMA,
        status: if passed { "pass" } else { "fail" },
        baseline_report: ReportReference {
            path: baseline_path.display().to_string(),
            sha256: sha256_file(baseline_path)?,
            adapter: baseline.adapter.name,
        },
        candidate_report: ReportReference {
            path: candidate_path.display().to_string(),
            sha256: sha256_file(candidate_path)?,
            adapter: candidate.adapter.name,
        },
        thresholds: ThresholdReport {
            max_channel_error: thresholds.max_channel_error,
            outlier_channel_error: thresholds.outlier_channel_error,
            max_mean_absolute_error: thresholds.max_mean_absolute_error,
            max_outlier_pixel_ratio: thresholds.max_outlier_pixel_ratio,
        },
        layers,
    };
    if let Some(parent) = output_path.parent() {
        fs::create_dir_all(parent)
            .with_context(|| format!("failed to create {}", parent.display()))?;
    }
    fs::write(output_path, serde_json::to_vec_pretty(&report)?)
        .with_context(|| format!("failed to write {}", output_path.display()))?;
    Ok(passed)
}

fn read_report(path: &Path) -> Result<ComparableReport> {
    let report: ComparableReport = serde_json::from_slice(
        &fs::read(path).with_context(|| format!("failed to read {}", path.display()))?,
    )
    .with_context(|| format!("invalid replay report {}", path.display()))?;
    if report.schema != REPORT_SCHEMA {
        bail!(
            "{} has schema {}, expected {}",
            path.display(),
            report.schema,
            REPORT_SCHEMA
        );
    }
    Ok(report)
}

fn validate_thresholds(thresholds: ComparisonThresholds) -> Result<()> {
    if !thresholds.max_mean_absolute_error.is_finite()
        || thresholds.max_mean_absolute_error < 0.0
        || thresholds.max_mean_absolute_error > 255.0
    {
        bail!("max_mean_absolute_error must be in 0..255");
    }
    if !thresholds.max_outlier_pixel_ratio.is_finite()
        || !(0.0..=1.0).contains(&thresholds.max_outlier_pixel_ratio)
    {
        bail!("max_outlier_pixel_ratio must be in 0..1");
    }
    Ok(())
}
