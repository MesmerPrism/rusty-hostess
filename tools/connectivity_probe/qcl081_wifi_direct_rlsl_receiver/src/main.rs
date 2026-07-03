use rlsl::prelude::{local_clock, StreamInlet};
use rlsl::resolver;
use serde_json::{json, Value};
use std::env;
use std::fs;
use std::path::Path;
use std::time::{Duration, Instant};

const REPORT_SCHEMA: &str = "rusty.hostess.qcl081_wifi_direct_lsl_receiver.v1";
const RECEIVER_BACKEND: &str = "rlsl";
const LIBRARY_VERSION: &str = "rlsl 0.0.5";

#[derive(Debug)]
struct Args {
    run_id: String,
    out: String,
    stream_name: String,
    stream_type: String,
    source_id: String,
    sample_count: usize,
    timeout_seconds: f64,
    topology_report: String,
}

fn main() {
    let args = match parse_args() {
        Ok(args) => args,
        Err(message) => {
            eprintln!("{message}");
            std::process::exit(64);
        }
    };

    let report = run_receiver(&args);
    if let Some(parent) = Path::new(&args.out).parent() {
        if let Err(error) = fs::create_dir_all(parent) {
            eprintln!(
                "failed to create output directory {}: {error}",
                parent.display()
            );
            std::process::exit(1);
        }
    }
    let pretty = match serde_json::to_string_pretty(&report) {
        Ok(text) => text,
        Err(error) => {
            eprintln!("failed to serialize report: {error}");
            std::process::exit(1);
        }
    };
    if let Err(error) = fs::write(&args.out, format!("{pretty}\n")) {
        eprintln!("failed to write report {}: {error}", args.out);
        std::process::exit(1);
    }
    println!(
        "{}",
        serde_json::to_string(&report).unwrap_or_else(|_| "{}".to_string())
    );
    std::process::exit(
        if report.get("status").and_then(Value::as_str) == Some("pass") {
            0
        } else {
            2
        },
    );
}

fn parse_args() -> Result<Args, String> {
    let mut args = Args {
        run_id: String::new(),
        out: String::new(),
        stream_name: "RustyQCL081WifiDirect".to_string(),
        stream_type: "rusty.quest.qcl081.wifi_direct".to_string(),
        source_id: String::new(),
        sample_count: 16,
        timeout_seconds: 20.0,
        topology_report: String::new(),
    };

    let mut iter = env::args().skip(1);
    while let Some(arg) = iter.next() {
        match arg.as_str() {
            "--run-id" => args.run_id = take_value(&mut iter, &arg)?,
            "--out" => args.out = take_value(&mut iter, &arg)?,
            "--stream-name" => args.stream_name = take_value(&mut iter, &arg)?,
            "--stream-type" => args.stream_type = take_value(&mut iter, &arg)?,
            "--source-id" => args.source_id = take_value(&mut iter, &arg)?,
            "--sample-count" => {
                let value = take_value(&mut iter, &arg)?;
                args.sample_count = value
                    .parse::<usize>()
                    .map_err(|_| format!("--sample-count must be an integer: {value}"))?
                    .max(1);
            }
            "--timeout-seconds" => {
                let value = take_value(&mut iter, &arg)?;
                args.timeout_seconds = value
                    .parse::<f64>()
                    .map_err(|_| format!("--timeout-seconds must be a number: {value}"))?
                    .max(1.0);
            }
            "--topology-report" => args.topology_report = take_value(&mut iter, &arg)?,
            "--help" | "-h" => {
                return Err(
                    "usage: qcl081-wifi-direct-rlsl-receiver --run-id ID --out PATH --source-id ID [--sample-count N] [--timeout-seconds N]".to_string(),
                );
            }
            unknown => return Err(format!("unknown argument: {unknown}")),
        }
    }

    if args.run_id.trim().is_empty() {
        return Err("--run-id is required".to_string());
    }
    if args.out.trim().is_empty() {
        return Err("--out is required".to_string());
    }
    if args.source_id.trim().is_empty() {
        return Err("--source-id is required".to_string());
    }
    Ok(args)
}

fn take_value(iter: &mut impl Iterator<Item = String>, name: &str) -> Result<String, String> {
    iter.next()
        .ok_or_else(|| format!("{name} requires a value"))
}

fn run_receiver(args: &Args) -> Value {
    let topology = read_json(&args.topology_report);
    let discovery_started = Instant::now();
    let streams =
        resolver::resolve_by_property("source_id", &args.source_id, 1, args.timeout_seconds);
    let discovery_ms = discovery_started.elapsed().as_millis() as u64;
    if streams.is_empty() {
        return base_report(
            args,
            "fail",
            0,
            100.0,
            Some(discovery_ms),
            false,
            vec!["hostess.issue.connectivity_probe.lsl_discovery_failed".to_string()],
            "No Quest QCL-081 pure-Rust rlsl outlet was discovered by source_id.",
            &topology,
        );
    }

    let info = &streams[0];
    let inlet = StreamInlet::new(info, 360, 1, true);
    if let Err(error) = inlet.open_stream(args.timeout_seconds) {
        let mut report = base_report(
            args,
            "fail",
            0,
            100.0,
            Some(discovery_ms),
            false,
            vec!["hostess.issue.connectivity_probe.lsl_open_stream_failed".to_string()],
            &format!(
                "Windows pure-Rust rlsl inlet discovered the stream but could not open it: {error}"
            ),
            &topology,
        );
        attach_stream_info(&mut report, info);
        return report;
    }

    let time_correction_before = inlet.time_correction(1.0);
    let mut received_sequences: Vec<i64> = Vec::new();
    let mut lsl_timestamps: Vec<f64> = Vec::new();
    let mut host_pull_clock: Vec<f64> = Vec::new();
    let mut errors: Vec<String> = Vec::new();
    let channel_count = (info.channel_count() as usize).max(1);
    let mut buffer = vec![0.0_f32; channel_count];
    let deadline = Instant::now() + Duration::from_secs_f64(args.timeout_seconds);
    while received_sequences.len() < args.sample_count && Instant::now() < deadline {
        match inlet.pull_sample_f(&mut buffer, 0.25) {
            Ok(timestamp) if timestamp > 0.0 => {
                received_sequences.push(buffer[0].round() as i64);
                lsl_timestamps.push(timestamp);
                host_pull_clock.push(local_clock());
            }
            Ok(_) => {}
            Err(error) => {
                errors.push(error);
                if errors.len() >= 3 {
                    break;
                }
            }
        }
    }
    let time_correction_after = inlet.time_correction(1.0);

    let received_count = received_sequences.len();
    let loss_percent =
        (((args.sample_count - received_count) as f64 / args.sample_count as f64) * 100.0 * 100.0)
            .round()
            / 100.0;
    let monotonic_sequences = received_sequences
        .iter()
        .enumerate()
        .all(|(index, value)| *value == index as i64);
    let monotonic_timestamps = lsl_timestamps.windows(2).all(|pair| pair[1] > pair[0]);
    let (status, issue_codes) =
        if received_count == args.sample_count && monotonic_sequences && monotonic_timestamps {
            ("pass", Vec::new())
        } else if received_count > 0 {
            (
                "warn",
                vec!["hostess.issue.connectivity_probe.lsl_sample_continuity_degraded".to_string()],
            )
        } else {
            (
                "fail",
                vec!["hostess.issue.connectivity_probe.lsl_sample_continuity_failed".to_string()],
            )
        };

    let mut report = base_report(
        args,
        status,
        received_count,
        loss_percent,
        Some(discovery_ms),
        monotonic_sequences && monotonic_timestamps,
        issue_codes,
        "Windows pure-Rust rlsl inlet received Quest-owned source-timestamped LSL samples over Wi-Fi Direct.",
        &topology,
    );
    attach_stream_info(&mut report, info);
    insert(&mut report, "received_sequences", json!(received_sequences));
    insert(&mut report, "lsl_timestamps_seconds", json!(lsl_timestamps));
    insert(
        &mut report,
        "source_timestamp_domain",
        json!("rlsl_local_clock"),
    );
    insert(
        &mut report,
        "source_timestamps_monotonic",
        json!(monotonic_timestamps),
    );
    insert(
        &mut report,
        "host_pull_clock_seconds",
        json!(host_pull_clock),
    );
    insert(
        &mut report,
        "time_correction_seconds_before",
        json!(time_correction_before),
    );
    insert(
        &mut report,
        "time_correction_seconds_after",
        json!(time_correction_after),
    );
    insert(
        &mut report,
        "inter_sample_ms_median",
        json!(median_delta_ms(&lsl_timestamps)),
    );
    if !errors.is_empty() {
        insert(&mut report, "receiver_errors", json!(errors));
    }
    report
}

fn base_report(
    args: &Args,
    status: &str,
    samples_received: usize,
    loss_percent: f64,
    discovery_ms: Option<u64>,
    monotonic: bool,
    issue_codes: Vec<String>,
    notes: &str,
    topology: &Value,
) -> Value {
    json!({
        "schema": REPORT_SCHEMA,
        "status": status,
        "run_id": args.run_id,
        "source": "quest-runtime",
        "evidence_tier": "quest_runtime",
        "receiver_backend": RECEIVER_BACKEND,
        "stream_name": args.stream_name,
        "stream_type": args.stream_type,
        "source_id": args.source_id,
        "samples_requested": args.sample_count,
        "samples_received": samples_received,
        "loss_percent": loss_percent,
        "discovery_ms": discovery_ms,
        "monotonic_sequences": monotonic,
        "library_version": LIBRARY_VERSION,
        "topology": {
            "owner": "wifi_direct",
            "network_provider": "wifi_direct",
            "endpoint_direction": "lsl_multicast_discovery_plus_tcp_samples",
            "topology_report_path": args.topology_report,
            "paired_topology_status": topology.get("status").cloned().unwrap_or(Value::Null),
            "paired_topology_promotion_allowed": topology
                .get("promotion")
                .and_then(|promotion| promotion.get("allowed"))
                .cloned()
                .unwrap_or(Value::Null),
        },
        "issue_codes": issue_codes,
        "notes": notes,
    })
}

fn attach_stream_info(report: &mut Value, info: &rlsl::stream_info::StreamInfo) {
    insert(report, "discovered_stream_name", json!(info.name()));
    insert(report, "discovered_stream_type", json!(info.type_()));
    insert(report, "discovered_source_id", json!(info.source_id()));
    insert(
        report,
        "discovered_channel_count",
        json!(info.channel_count()),
    );
    insert(
        report,
        "discovered_nominal_srate",
        json!(info.nominal_srate()),
    );
    insert(report, "discovered_v4address", json!(info.v4address()));
    insert(report, "discovered_v4data_port", json!(info.v4data_port()));
    insert(
        report,
        "discovered_v4service_port",
        json!(info.v4service_port()),
    );
}

fn insert(report: &mut Value, name: &str, value: Value) {
    if let Some(object) = report.as_object_mut() {
        object.insert(name.to_string(), value);
    }
}

fn read_json(path: &str) -> Value {
    if path.trim().is_empty() {
        return json!({});
    }
    match fs::read_to_string(path) {
        Ok(text) => serde_json::from_str(&text).unwrap_or_else(|_| json!({})),
        Err(_) => json!({}),
    }
}

fn median_delta_ms(values: &[f64]) -> Option<f64> {
    if values.len() < 2 {
        return None;
    }
    let mut deltas: Vec<f64> = values
        .windows(2)
        .map(|pair| (pair[1] - pair[0]) * 1000.0)
        .collect();
    deltas.sort_by(|left, right| left.partial_cmp(right).unwrap_or(std::cmp::Ordering::Equal));
    let mid = deltas.len() / 2;
    let median = if deltas.len() % 2 == 0 {
        (deltas[mid - 1] + deltas[mid]) / 2.0
    } else {
        deltas[mid]
    };
    Some((median * 1000.0).round() / 1000.0)
}
