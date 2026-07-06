use lsl::{ExPushable, Pullable};
use serde_json::{json, Value};
use std::collections::{HashMap, HashSet};
use std::env;
use std::fs;
use std::path::Path;
use std::thread;
use std::time::{Duration, Instant};

const RECEIVER_SCHEMA: &str = "rusty.hostess.qcl081_wifi_direct_lsl_receiver.v1";
const ECHO_SCHEMA: &str = "rusty.hostess.qcl081_wifi_direct_lsl_echo_roundtrip.v1";
const BACKEND: &str = "rust-lsl";
const LIBRARY_VERSION: &str = "lsl 0.1.1";

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum Mode {
    Receiver,
    EchoRoundtrip,
}

#[derive(Debug)]
struct Args {
    mode: Mode,
    run_id: String,
    out: String,
    stream_name: String,
    stream_type: String,
    source_id: String,
    command_stream_name: String,
    command_stream_type: String,
    command_source_id: String,
    echo_stream_name: String,
    echo_stream_type: String,
    echo_source_id: String,
    sample_count: usize,
    interval_ms: f64,
    timeout_seconds: f64,
    pre_send_delay_ms: f64,
    analysis_warmup_seconds: f64,
    analysis_warmup_samples: usize,
    topology_report: String,
}

#[derive(Debug)]
struct EchoRow {
    sequence: i64,
    host_send_lsl_clock_seconds: f64,
    quest_receive_lsl_clock_seconds: f64,
    quest_echo_send_lsl_clock_seconds: f64,
    command_capture_timestamp_seconds: Option<f64>,
    host_receive_lsl_clock_seconds: f64,
    echo_lsl_timestamp_seconds: f64,
    host_send_monotonic_seconds: Option<f64>,
}

fn main() {
    let args = match parse_args() {
        Ok(args) => args,
        Err(message) => {
            eprintln!("{message}");
            std::process::exit(64);
        }
    };

    let report = match args.mode {
        Mode::Receiver => run_receiver(&args),
        Mode::EchoRoundtrip => run_echo_roundtrip(&args),
    };
    if let Some(parent) = Path::new(&args.out).parent() {
        if let Err(error) = fs::create_dir_all(parent) {
            eprintln!(
                "failed to create output directory {}: {error}",
                parent.display()
            );
            std::process::exit(1);
        }
    }
    let pretty = serde_json::to_string_pretty(&report).unwrap_or_else(|_| "{}".to_string());
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
        mode: Mode::EchoRoundtrip,
        run_id: String::new(),
        out: String::new(),
        stream_name: "RustyQCL081WifiDirect".to_string(),
        stream_type: "rusty.quest.qcl081.wifi_direct".to_string(),
        source_id: String::new(),
        command_stream_name: "RustyQCL081WifiDirectCommand".to_string(),
        command_stream_type: "rusty.quest.qcl081.wifi_direct.command".to_string(),
        command_source_id: String::new(),
        echo_stream_name: "RustyQCL081WifiDirectEcho".to_string(),
        echo_stream_type: "rusty.quest.qcl081.wifi_direct.echo".to_string(),
        echo_source_id: String::new(),
        sample_count: 300,
        interval_ms: 100.0,
        timeout_seconds: 60.0,
        pre_send_delay_ms: 3000.0,
        analysis_warmup_seconds: 5.0,
        analysis_warmup_samples: 0,
        topology_report: String::new(),
    };

    let mut iter = env::args().skip(1).peekable();
    if let Some(first) = iter.peek().cloned() {
        if !first.starts_with("--") {
            args.mode = match first.as_str() {
                "receiver" => Mode::Receiver,
                "echo-roundtrip" => Mode::EchoRoundtrip,
                "echo" => Mode::EchoRoundtrip,
                _ => return Err(format!("unknown subcommand: {first}")),
            };
            iter.next();
        }
    }

    while let Some(arg) = iter.next() {
        match arg.as_str() {
            "--run-id" => args.run_id = take_value(&mut iter, &arg)?,
            "--out" => args.out = take_value(&mut iter, &arg)?,
            "--stream-name" => args.stream_name = take_value(&mut iter, &arg)?,
            "--stream-type" => args.stream_type = take_value(&mut iter, &arg)?,
            "--source-id" => args.source_id = take_value(&mut iter, &arg)?,
            "--command-stream-name" => args.command_stream_name = take_value(&mut iter, &arg)?,
            "--command-stream-type" => args.command_stream_type = take_value(&mut iter, &arg)?,
            "--command-source-id" => args.command_source_id = take_value(&mut iter, &arg)?,
            "--echo-stream-name" => args.echo_stream_name = take_value(&mut iter, &arg)?,
            "--echo-stream-type" => args.echo_stream_type = take_value(&mut iter, &arg)?,
            "--echo-source-id" => args.echo_source_id = take_value(&mut iter, &arg)?,
            "--sample-count" => args.sample_count = parse_usize(&mut iter, &arg)?.max(1),
            "--interval-ms" => args.interval_ms = parse_f64(&mut iter, &arg)?.max(1.0),
            "--timeout-seconds" => args.timeout_seconds = parse_f64(&mut iter, &arg)?.max(1.0),
            "--pre-send-delay-ms" => args.pre_send_delay_ms = parse_f64(&mut iter, &arg)?.max(0.0),
            "--analysis-warmup-seconds" => {
                args.analysis_warmup_seconds = parse_f64(&mut iter, &arg)?.max(0.0)
            }
            "--analysis-warmup-samples" => {
                args.analysis_warmup_samples = parse_usize(&mut iter, &arg)?
            }
            "--topology-report" => args.topology_report = take_value(&mut iter, &arg)?,
            "--help" | "-h" => return Err(help_text()),
            unknown => return Err(format!("unknown argument: {unknown}")),
        }
    }

    if args.run_id.trim().is_empty() {
        return Err("--run-id is required".to_string());
    }
    if args.out.trim().is_empty() {
        return Err("--out is required".to_string());
    }
    if args.mode == Mode::Receiver && args.source_id.trim().is_empty() {
        return Err("--source-id is required for receiver".to_string());
    }
    if args.mode == Mode::EchoRoundtrip && args.command_source_id.trim().is_empty() {
        return Err("--command-source-id is required for echo-roundtrip".to_string());
    }
    if args.mode == Mode::EchoRoundtrip && args.echo_source_id.trim().is_empty() {
        return Err("--echo-source-id is required for echo-roundtrip".to_string());
    }
    Ok(args)
}

fn help_text() -> String {
    "usage: qcl081-wifi-direct-lsl-rust <receiver|echo-roundtrip> --run-id ID --out PATH [LSL options]".to_string()
}

fn take_value(iter: &mut impl Iterator<Item = String>, name: &str) -> Result<String, String> {
    iter.next()
        .ok_or_else(|| format!("{name} requires a value"))
}

fn parse_usize(iter: &mut impl Iterator<Item = String>, name: &str) -> Result<usize, String> {
    let value = take_value(iter, name)?;
    value
        .parse::<usize>()
        .map_err(|_| format!("{name} must be an integer: {value}"))
}

fn parse_f64(iter: &mut impl Iterator<Item = String>, name: &str) -> Result<f64, String> {
    let value = take_value(iter, name)?;
    value
        .parse::<f64>()
        .map_err(|_| format!("{name} must be a number: {value}"))
}

fn run_receiver(args: &Args) -> Value {
    let topology = read_json(&args.topology_report);
    let discovery_started = Instant::now();
    let streams = match lsl::resolve_byprop("source_id", &args.source_id, 1, args.timeout_seconds) {
        Ok(streams) => streams,
        Err(error) => {
            return receiver_base_report(
                args,
                "fail",
                0,
                100.0,
                None,
                false,
                vec!["hostess.issue.connectivity_probe.lsl_discovery_error".to_string()],
                &format!("Rust lsl receiver failed during stream discovery: {error}"),
                &topology,
            )
        }
    };
    let discovery_ms = discovery_started.elapsed().as_millis() as u64;
    if streams.is_empty() {
        return receiver_base_report(
            args,
            "fail",
            0,
            100.0,
            Some(discovery_ms),
            false,
            vec!["hostess.issue.connectivity_probe.lsl_discovery_failed".to_string()],
            "No Quest QCL-081 LSL outlet was discovered by source_id.",
            &topology,
        );
    }

    let inlet = match lsl::StreamInlet::new(&streams[0], 60, 1, true) {
        Ok(inlet) => inlet,
        Err(error) => {
            let mut report = receiver_base_report(
                args,
                "fail",
                0,
                100.0,
                Some(discovery_ms),
                false,
                vec!["hostess.issue.connectivity_probe.lsl_inlet_create_failed".to_string()],
                &format!("Rust lsl inlet creation failed: {error}"),
                &topology,
            );
            attach_stream_info(&mut report, &streams[0]);
            return report;
        }
    };
    let _ = inlet.open_stream(args.timeout_seconds.min(5.0));
    let time_correction_before = inlet.time_correction(1.0).ok();
    let mut received_sequences: Vec<i64> = Vec::new();
    let mut lsl_timestamps: Vec<f64> = Vec::new();
    let mut host_pull_clock: Vec<f64> = Vec::new();
    let deadline = Instant::now() + Duration::from_secs_f64(args.timeout_seconds);
    while received_sequences.len() < args.sample_count && Instant::now() < deadline {
        let (sample, timestamp): (Vec<f32>, f64) = match inlet.pull_sample(0.25) {
            Ok(value) => value,
            Err(_) => continue,
        };
        if sample.is_empty() || timestamp == 0.0 {
            continue;
        }
        received_sequences.push(sample[0].round() as i64);
        lsl_timestamps.push(timestamp);
        host_pull_clock.push(lsl::local_clock());
    }
    let time_correction_after = inlet.time_correction(1.0).ok();

    let received_count = received_sequences.len();
    let loss_percent =
        round3(((args.sample_count - received_count) as f64 / args.sample_count as f64) * 100.0);
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

    let mut report = receiver_base_report(
        args,
        status,
        received_count,
        loss_percent,
        Some(discovery_ms),
        monotonic_sequences && monotonic_timestamps,
        issue_codes,
        "Windows Rust lsl inlet received Quest-owned source-timestamped LSL samples over Wi-Fi Direct.",
        &topology,
    );
    attach_stream_info(&mut report, &streams[0]);
    insert(&mut report, "received_sequences", json!(received_sequences));
    insert(&mut report, "lsl_timestamps_seconds", json!(lsl_timestamps));
    insert(
        &mut report,
        "source_timestamp_domain",
        json!("quest_lsl_local_clock"),
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
    report
}

fn run_echo_roundtrip(args: &Args) -> Value {
    let topology = read_json(&args.topology_report);
    let sample_count = args.sample_count.max(1);
    let interval = Duration::from_secs_f64((args.interval_ms / 1000.0).max(0.001));
    let timeout = Duration::from_secs_f64(args.timeout_seconds.max(1.0));
    let command_info = match lsl::StreamInfo::new(
        &args.command_stream_name,
        &args.command_stream_type,
        2,
        lsl::IRREGULAR_RATE,
        lsl::ChannelFormat::Double64,
        &args.command_source_id,
    ) {
        Ok(info) => info,
        Err(error) => {
            return echo_base_report(
                args,
                "fail",
                vec![
                    "hostess.issue.connectivity_probe.lsl_command_streaminfo_create_failed"
                        .to_string(),
                ],
                &format!("Rust lsl command streaminfo creation failed: {error}"),
                &topology,
                0,
                0,
            )
        }
    };
    let command_outlet = match lsl::StreamOutlet::new(&command_info, 1, 60) {
        Ok(outlet) => outlet,
        Err(error) => {
            return echo_base_report(
                args,
                "fail",
                vec![
                    "hostess.issue.connectivity_probe.lsl_command_outlet_create_failed".to_string(),
                ],
                &format!("Rust lsl command outlet creation failed: {error}"),
                &topology,
                0,
                0,
            )
        }
    };

    let mut sent_by_sequence: HashMap<i64, f64> = HashMap::new();
    let mut sent_monotonic_by_sequence: HashMap<i64, f64> = HashMap::new();
    let mut sent_count = 0usize;
    let mut first_send_lsl: Option<f64> = None;
    let mut last_send_lsl: Option<f64> = None;
    let started = Instant::now();
    let deadline = started + timeout;

    let discovery_started = Instant::now();
    let resolver = lsl::ContinuousResolver::new_with_prop("source_id", &args.echo_source_id, 5.0);
    let mut streams = Vec::new();
    let mut discovery_method = String::new();
    let mut resolve_probe_count = 0usize;
    let mut visible_streams_tail: Vec<Value> = Vec::new();
    while Instant::now() < deadline && streams.is_empty() {
        resolve_probe_count += 1;
        if let Ok(resolver) = resolver.as_ref() {
            streams = resolver.results().unwrap_or_default();
            if !streams.is_empty() {
                discovery_method = "continuous_resolver_by_source_id".to_string();
                break;
            }
        }
        streams =
            lsl::resolve_byprop("source_id", &args.echo_source_id, 1, 0.5).unwrap_or_default();
        if !streams.is_empty() {
            discovery_method = "resolve_byprop_source_id".to_string();
            break;
        }
        if resolve_probe_count % 10 == 0 {
            visible_streams_tail = lsl::resolve_streams(0.05)
                .unwrap_or_default()
                .iter()
                .map(stream_summary)
                .collect();
        }
    }
    let discovery_ms = discovery_started.elapsed().as_millis() as u64;
    if streams.is_empty() {
        let mut report = echo_base_report(
            args,
            "fail",
            vec!["hostess.issue.connectivity_probe.lsl_echo_discovery_failed".to_string()],
            "No Quest QCL-081 LSL echo outlet was discovered by source_id.",
            &topology,
            sent_count,
            0,
        );
        insert(&mut report, "discovery_ms", json!(discovery_ms));
        insert(
            &mut report,
            "discovery_method",
            json!(if resolver.is_ok() {
                "continuous_resolver_by_source_id_plus_resolve_byprop"
            } else {
                "resolve_byprop_source_id"
            }),
        );
        insert(
            &mut report,
            "continuous_resolver_create_status",
            json!(if resolver.is_ok() { "pass" } else { "failed" }),
        );
        insert(
            &mut report,
            "resolve_probe_count",
            json!(resolve_probe_count),
        );
        insert(
            &mut report,
            "visible_streams_tail",
            json!(visible_streams_tail),
        );
        insert(
            &mut report,
            "lsl_api_config",
            json!(current_lsl_api_config()),
        );
        return report;
    }

    let echo_inlet = match lsl::StreamInlet::new(&streams[0], 60, 1, true) {
        Ok(inlet) => inlet,
        Err(error) => {
            let mut report = echo_base_report(
                args,
                "fail",
                vec!["hostess.issue.connectivity_probe.lsl_echo_inlet_create_failed".to_string()],
                &format!("Rust lsl echo inlet creation failed: {error}"),
                &topology,
                sent_count,
                0,
            );
            attach_stream_info(&mut report, &streams[0]);
            insert(&mut report, "discovery_ms", json!(discovery_ms));
            return report;
        }
    };
    let _ = echo_inlet.open_stream(args.timeout_seconds.min(5.0));
    let time_correction_before = echo_inlet.time_correction(2.0).ok();
    let send_started = Instant::now();
    let mut next_send =
        send_started + Duration::from_secs_f64((args.pre_send_delay_ms / 1000.0).max(0.0));
    let max_send_count = sample_count;
    let mut rows = Vec::new();
    let mut seen_sequences: HashSet<i64> = HashSet::new();
    let receive_loop_started = Instant::now();
    let mut first_receive_offset_ms: Option<f64> = None;
    let mut last_receive_offset_ms: Option<f64> = None;
    let mut pull_timeout_count = 0usize;
    let mut pull_timeouts_after_first_echo = 0usize;
    let mut consecutive_pull_timeouts_after_last_echo = 0usize;
    let mut max_consecutive_pull_timeouts_after_last_echo = 0usize;

    while Instant::now() < deadline && seen_sequences.len() < sample_count {
        send_due_command_samples(
            &command_outlet,
            &mut sent_count,
            max_send_count,
            &mut next_send,
            interval,
            send_started,
            &mut first_send_lsl,
            &mut last_send_lsl,
            &mut sent_by_sequence,
            &mut sent_monotonic_by_sequence,
        );
        let (sample, timestamp): (Vec<f64>, f64) = match echo_inlet.pull_sample(0.025) {
            Ok(value) => value,
            Err(_) => {
                pull_timeout_count += 1;
                continue;
            }
        };
        if sample.is_empty() || timestamp == 0.0 {
            pull_timeout_count += 1;
            if first_receive_offset_ms.is_some() {
                pull_timeouts_after_first_echo += 1;
                consecutive_pull_timeouts_after_last_echo += 1;
                max_consecutive_pull_timeouts_after_last_echo =
                    max_consecutive_pull_timeouts_after_last_echo
                        .max(consecutive_pull_timeouts_after_last_echo);
            }
            continue;
        }
        let receive_offset = receive_loop_started.elapsed().as_secs_f64() * 1000.0;
        if first_receive_offset_ms.is_none() {
            first_receive_offset_ms = Some(receive_offset);
        }
        last_receive_offset_ms = Some(receive_offset);
        consecutive_pull_timeouts_after_last_echo = 0;
        if sample.len() < 4 {
            continue;
        }
        let sequence = sample[0].round() as i64;
        let host_send = sent_by_sequence
            .get(&sequence)
            .copied()
            .unwrap_or(sample[1]);
        rows.push(EchoRow {
            sequence,
            host_send_lsl_clock_seconds: host_send,
            quest_receive_lsl_clock_seconds: sample[2],
            quest_echo_send_lsl_clock_seconds: sample[3],
            command_capture_timestamp_seconds: sample.get(4).copied(),
            host_receive_lsl_clock_seconds: lsl::local_clock(),
            echo_lsl_timestamp_seconds: timestamp,
            host_send_monotonic_seconds: sent_monotonic_by_sequence.get(&sequence).copied(),
        });
        seen_sequences.insert(sequence);
    }
    let time_correction_after = echo_inlet.time_correction(1.0).ok();
    let receive_loop_elapsed_ms = receive_loop_started.elapsed().as_secs_f64() * 1000.0;
    let clock_correction = median_available(&[time_correction_before, time_correction_after]);
    let timing_samples = aligned_rows(&rows, clock_correction);
    let unique_sequences = sorted_unique_sequences(&timing_samples);
    let sequence_gaps = sequence_gap_ranges(&unique_sequences);
    let matched_count = unique_sequences.len();
    let duplicate_count = timing_samples.len().saturating_sub(matched_count);
    let loss_percent =
        round3(((sample_count - matched_count) as f64 / sample_count as f64) * 100.0);
    let warmup_seconds = args
        .analysis_warmup_seconds
        .max(args.analysis_warmup_samples as f64 * args.interval_ms / 1000.0);
    let first_send = first_send_lsl.unwrap_or(0.0);
    let analysis_rows: Vec<Value> = timing_samples
        .iter()
        .filter(|row| {
            row.get("host_send_lsl_clock_seconds")
                .and_then(Value::as_f64)
                .map(|value| value - first_send >= warmup_seconds)
                .unwrap_or(false)
        })
        .cloned()
        .collect();

    let mut issue_codes = Vec::new();
    if matched_count != sample_count {
        issue_codes.push("hostess.issue.connectivity_probe.lsl_echo_sample_loss".to_string());
    }
    if duplicate_count > 0 {
        issue_codes
            .push("hostess.issue.connectivity_probe.lsl_echo_duplicate_sequences".to_string());
    }
    if clock_correction.is_none() {
        issue_codes.push(
            "hostess.issue.connectivity_probe.lsl_echo_clock_alignment_unavailable".to_string(),
        );
    } else if has_large_negative_segment(&timing_samples) {
        issue_codes.push(
            "hostess.issue.connectivity_probe.lsl_echo_clock_alignment_segment_negative"
                .to_string(),
        );
    }
    let status =
        if matched_count == sample_count && clock_correction.is_some() && issue_codes.is_empty() {
            "pass"
        } else if matched_count > 0 {
            "warn"
        } else {
            "fail"
        };

    let mut report = echo_base_report(
        args,
        status,
        issue_codes,
        "Windows Rust lsl command outlet and inlet measured Quest LSL echo timing with LSL clock correction applied to Quest receive/send timestamps.",
        &topology,
        sent_count,
        timing_samples.len(),
    );
    attach_stream_info(&mut report, &streams[0]);
    let send_duration = match (first_send_lsl, last_send_lsl) {
        (Some(first), Some(last)) => Some(round6(last - first)),
        _ => None,
    };
    insert(&mut report, "discovery_ms", json!(discovery_ms));
    insert(&mut report, "discovery_method", json!(discovery_method));
    insert(
        &mut report,
        "continuous_resolver_create_status",
        json!(if resolver.is_ok() { "pass" } else { "failed" }),
    );
    insert(
        &mut report,
        "resolve_probe_count",
        json!(resolve_probe_count),
    );
    insert(
        &mut report,
        "visible_streams_tail",
        json!(visible_streams_tail),
    );
    insert(
        &mut report,
        "lsl_api_config",
        json!(current_lsl_api_config()),
    );
    insert(&mut report, "samples_requested", json!(sample_count));
    insert(&mut report, "samples_matched", json!(matched_count));
    insert(
        &mut report,
        "duplicate_echo_samples",
        json!(duplicate_count),
    );
    insert(&mut report, "loss_percent", json!(loss_percent));
    insert(
        &mut report,
        "send_interval_ms",
        json!(round3(args.interval_ms)),
    );
    insert(&mut report, "send_duration_seconds", json!(send_duration));
    insert(
        &mut report,
        "streaming_target_seconds",
        json!(round6(
            (sample_count - 1) as f64 * args.interval_ms / 1000.0
        )),
    );
    insert(
        &mut report,
        "receive_loop_elapsed_ms",
        json!(round3(receive_loop_elapsed_ms)),
    );
    insert(
        &mut report,
        "first_echo_receive_offset_ms",
        json!(first_receive_offset_ms.map(round3)),
    );
    insert(
        &mut report,
        "last_echo_receive_offset_ms",
        json!(last_receive_offset_ms.map(round3)),
    );
    insert(&mut report, "pull_timeout_count", json!(pull_timeout_count));
    insert(
        &mut report,
        "pull_timeouts_after_first_echo",
        json!(pull_timeouts_after_first_echo),
    );
    insert(
        &mut report,
        "max_consecutive_pull_timeouts_after_last_echo",
        json!(max_consecutive_pull_timeouts_after_last_echo),
    );
    insert(
        &mut report,
        "clock_alignment",
        json!({
            "status": if clock_correction.is_some() { "pass" } else { "unavailable" },
            "method": "lsl.StreamInlet.time_correction",
            "formula": "windows_clock_seconds = quest_lsl_local_clock_seconds + correction_seconds",
            "time_correction_seconds_before": time_correction_before,
            "time_correction_seconds_after": time_correction_after,
            "time_correction_seconds_used": clock_correction,
        }),
    );
    insert(
        &mut report,
        "latency_ms_summary",
        latency_summary(&timing_samples),
    );
    insert(
        &mut report,
        "analysis_window",
        analysis_window_json(&timing_samples, &analysis_rows, warmup_seconds),
    );
    insert(
        &mut report,
        "latency_ms_summary_after_warmup",
        latency_summary(&analysis_rows),
    );
    insert(
        &mut report,
        "stability_after_warmup",
        stability_summary(&analysis_rows),
    );
    insert(
        &mut report,
        "sequence_first",
        json!(unique_sequences.first().copied()),
    );
    insert(
        &mut report,
        "sequence_last",
        json!(unique_sequences.last().copied()),
    );
    insert(
        &mut report,
        "sequence_gap_count",
        json!(sequence_gaps.len()),
    );
    insert(
        &mut report,
        "sequence_missing_between_first_last",
        json!(sequence_missing_count(&sequence_gaps)),
    );
    insert(
        &mut report,
        "sequence_gap_ranges",
        json!(sequence_gaps.into_iter().take(20).collect::<Vec<_>>()),
    );
    insert(&mut report, "timing_samples", json!(timing_samples));
    let tail: Vec<Value> = report
        .get("timing_samples")
        .and_then(Value::as_array)
        .map(|rows| {
            rows.iter()
                .rev()
                .take(10)
                .cloned()
                .collect::<Vec<_>>()
                .into_iter()
                .rev()
                .collect()
        })
        .unwrap_or_default();
    insert(&mut report, "timing_samples_tail", json!(tail));
    report
}

#[allow(clippy::too_many_arguments)]
fn send_due_command_samples(
    outlet: &lsl::StreamOutlet,
    sent_count: &mut usize,
    max_send_count: usize,
    next_send: &mut Instant,
    interval: Duration,
    started: Instant,
    first_send_lsl: &mut Option<f64>,
    last_send_lsl: &mut Option<f64>,
    sent_by_sequence: &mut HashMap<i64, f64>,
    sent_monotonic_by_sequence: &mut HashMap<i64, f64>,
) {
    while *sent_count < max_send_count && Instant::now() >= *next_send {
        let sequence = *sent_count as i64;
        let host_send_lsl = lsl::local_clock();
        let sample = vec![sequence as f64, host_send_lsl];
        if outlet.push_sample_ex(&sample, host_send_lsl, true).is_err() {
            return;
        }
        sent_by_sequence.insert(sequence, host_send_lsl);
        sent_monotonic_by_sequence.insert(sequence, started.elapsed().as_secs_f64());
        if first_send_lsl.is_none() {
            *first_send_lsl = Some(host_send_lsl);
        }
        *last_send_lsl = Some(host_send_lsl);
        *sent_count += 1;
        *next_send += interval;
        if Instant::now() < *next_send {
            let sleep_for = (*next_send - Instant::now()).min(Duration::from_millis(1));
            thread::sleep(sleep_for);
        }
    }
}

fn receiver_base_report(
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
        "schema": RECEIVER_SCHEMA,
        "status": status,
        "run_id": args.run_id,
        "source": "quest-runtime",
        "evidence_tier": "quest_runtime",
        "receiver_backend": BACKEND,
        "stream_name": args.stream_name,
        "stream_type": args.stream_type,
        "source_id": args.source_id,
        "samples_requested": args.sample_count,
        "samples_received": samples_received,
        "loss_percent": loss_percent,
        "discovery_ms": discovery_ms,
        "monotonic_sequences": monotonic,
        "library_version": LIBRARY_VERSION,
        "liblsl_protocol_version": lsl::protocol_version(),
        "liblsl_library_version": lsl::library_version(),
        "liblsl_library_info": lsl::library_info(),
        "lsl_api_config": current_lsl_api_config(),
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

fn echo_base_report(
    args: &Args,
    status: &str,
    issue_codes: Vec<String>,
    notes: &str,
    topology: &Value,
    samples_sent: usize,
    samples_received: usize,
) -> Value {
    json!({
        "schema": ECHO_SCHEMA,
        "status": status,
        "run_id": args.run_id,
        "source": "windows-host-plus-quest-runtime",
        "evidence_tier": "quest_runtime",
        "command_producer_backend": BACKEND,
        "echo_receiver_backend": BACKEND,
        "command_stream_name": args.command_stream_name,
        "command_stream_type": args.command_stream_type,
        "command_source_id": args.command_source_id,
        "echo_stream_name": args.echo_stream_name,
        "echo_stream_type": args.echo_stream_type,
        "echo_source_id": args.echo_source_id,
        "samples_requested": args.sample_count,
        "samples_sent": samples_sent,
        "samples_received": samples_received,
        "library_version": LIBRARY_VERSION,
        "liblsl_protocol_version": lsl::protocol_version(),
        "liblsl_library_version": lsl::library_version(),
        "liblsl_library_info": lsl::library_info(),
        "topology": {
            "owner": "wifi_direct",
            "network_provider": "wifi_direct",
            "endpoint_direction": "lsl_multicast_discovery_plus_bidirectional_lsl_samples",
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

fn aligned_rows(rows: &[EchoRow], correction_seconds: Option<f64>) -> Vec<Value> {
    let mut seen = HashSet::new();
    rows.iter()
        .map(|row| {
            let duplicate = !seen.insert(row.sequence);
            let mut value = json!({
                "sequence": row.sequence,
                "host_send_lsl_clock_seconds": round9(row.host_send_lsl_clock_seconds),
                "quest_receive_lsl_clock_seconds": round9(row.quest_receive_lsl_clock_seconds),
                "quest_echo_send_lsl_clock_seconds": round9(row.quest_echo_send_lsl_clock_seconds),
                "command_capture_timestamp_seconds": row.command_capture_timestamp_seconds.map(round9),
                "host_receive_lsl_clock_seconds": round9(row.host_receive_lsl_clock_seconds),
                "echo_lsl_timestamp_seconds": round9(row.echo_lsl_timestamp_seconds),
                "host_send_monotonic_seconds": row.host_send_monotonic_seconds.map(round9),
                "duplicate_sequence": duplicate,
            });
            if let Some(correction) = correction_seconds {
                let quest_receive_host = row.quest_receive_lsl_clock_seconds + correction;
                let quest_echo_send_host = row.quest_echo_send_lsl_clock_seconds + correction;
                let host_to_quest = (quest_receive_host - row.host_send_lsl_clock_seconds) * 1000.0;
                let quest_processing = (row.quest_echo_send_lsl_clock_seconds - row.quest_receive_lsl_clock_seconds) * 1000.0;
                let quest_to_host = (row.host_receive_lsl_clock_seconds - quest_echo_send_host) * 1000.0;
                let round_trip = (row.host_receive_lsl_clock_seconds - row.host_send_lsl_clock_seconds) * 1000.0;
                let accounted = host_to_quest + quest_processing + quest_to_host;
                insert(&mut value, "quest_receive_windows_clock_seconds", json!(round9(quest_receive_host)));
                insert(&mut value, "quest_echo_send_windows_clock_seconds", json!(round9(quest_echo_send_host)));
                insert(&mut value, "windows_send_to_quest_receive_ms", json!(round9(host_to_quest)));
                insert(&mut value, "quest_processing_ms", json!(round9(quest_processing)));
                insert(&mut value, "quest_send_to_windows_receive_ms", json!(round9(quest_to_host)));
                insert(&mut value, "round_trip_ms", json!(round9(round_trip)));
                insert(&mut value, "accounting_error_ms", json!(round9(round_trip - accounted)));
            } else {
                let quest_processing = (row.quest_echo_send_lsl_clock_seconds - row.quest_receive_lsl_clock_seconds) * 1000.0;
                let round_trip = (row.host_receive_lsl_clock_seconds - row.host_send_lsl_clock_seconds) * 1000.0;
                insert(&mut value, "quest_receive_windows_clock_seconds", Value::Null);
                insert(&mut value, "quest_echo_send_windows_clock_seconds", Value::Null);
                insert(&mut value, "windows_send_to_quest_receive_ms", Value::Null);
                insert(&mut value, "quest_processing_ms", json!(round9(quest_processing)));
                insert(&mut value, "quest_send_to_windows_receive_ms", Value::Null);
                insert(&mut value, "round_trip_ms", json!(round9(round_trip)));
                insert(&mut value, "accounting_error_ms", Value::Null);
            }
            value
        })
        .collect()
}

fn latency_summary(rows: &[Value]) -> Value {
    json!({
        "windows_send_to_quest_receive": summarize_ms(&values(rows, "windows_send_to_quest_receive_ms")),
        "quest_processing": summarize_ms(&values(rows, "quest_processing_ms")),
        "quest_send_to_windows_receive": summarize_ms(&values(rows, "quest_send_to_windows_receive_ms")),
        "round_trip": summarize_ms(&values(rows, "round_trip_ms")),
        "accounting_error": summarize_ms(&values(rows, "accounting_error_ms")),
    })
}

fn analysis_window_json(all_rows: &[Value], analysis_rows: &[Value], warmup_seconds: f64) -> Value {
    let first = analysis_rows
        .first()
        .and_then(|row| row.get("host_send_lsl_clock_seconds"))
        .and_then(Value::as_f64);
    let last = analysis_rows
        .last()
        .and_then(|row| row.get("host_send_lsl_clock_seconds"))
        .and_then(Value::as_f64);
    json!({
        "warmup_excluded_seconds": round3(warmup_seconds),
        "samples_total": all_rows.len(),
        "samples_excluded": all_rows.len().saturating_sub(analysis_rows.len()),
        "samples_analyzed": analysis_rows.len(),
        "analyzed_send_duration_seconds": match (first, last) {
            (Some(first), Some(last)) => Value::from(round6(last - first)),
            _ => Value::Null,
        },
    })
}

fn stability_summary(rows: &[Value]) -> Value {
    let receive_times = values(rows, "host_receive_lsl_clock_seconds");
    let round_trips = values(rows, "round_trip_ms");
    let inter_arrival_ms: Vec<f64> = receive_times
        .windows(2)
        .map(|pair| (pair[1] - pair[0]) * 1000.0)
        .collect();
    let rtt_jitter_ms: Vec<f64> = round_trips
        .windows(2)
        .map(|pair| (pair[1] - pair[0]).abs())
        .collect();
    let sequences = sorted_unique_sequences(rows);
    let gaps = sequence_gap_ranges(&sequences);
    json!({
        "samples_analyzed": rows.len(),
        "sequence_gap_count": gaps.len(),
        "sequence_missing_between_first_last": sequence_missing_count(&gaps),
        "inter_echo_arrival_ms": summarize_ms(&inter_arrival_ms),
        "round_trip_jitter_ms": summarize_ms(&rtt_jitter_ms),
        "round_trip_ms": summarize_ms(&round_trips),
    })
}

fn values(rows: &[Value], key: &str) -> Vec<f64> {
    rows.iter()
        .filter_map(|row| row.get(key).and_then(Value::as_f64))
        .filter(|value| value.is_finite())
        .collect()
}

fn summarize_ms(items: &[f64]) -> Value {
    if items.is_empty() {
        return Value::Null;
    }
    let mut ordered = items.to_vec();
    ordered.sort_by(|left, right| left.partial_cmp(right).unwrap_or(std::cmp::Ordering::Equal));
    json!({
        "count": ordered.len(),
        "min": round3(ordered[0]),
        "median": round3(median_sorted(&ordered)),
        "p95": round3(percentile_sorted(&ordered, 95.0)),
        "max": round3(*ordered.last().unwrap_or(&ordered[0])),
    })
}

fn sorted_unique_sequences(rows: &[Value]) -> Vec<i64> {
    let mut sequences: Vec<i64> = rows
        .iter()
        .filter_map(|row| row.get("sequence").and_then(Value::as_i64))
        .collect::<HashSet<_>>()
        .into_iter()
        .collect();
    sequences.sort_unstable();
    sequences
}

fn sequence_gap_ranges(sequences: &[i64]) -> Vec<Value> {
    let mut gaps = Vec::new();
    for pair in sequences.windows(2) {
        if pair[1] > pair[0] + 1 {
            gaps.push(json!({"start": pair[0] + 1, "end": pair[1] - 1}));
        }
    }
    gaps
}

fn sequence_missing_count(gaps: &[Value]) -> i64 {
    gaps.iter()
        .map(|gap| {
            let start = gap.get("start").and_then(Value::as_i64).unwrap_or(0);
            let end = gap.get("end").and_then(Value::as_i64).unwrap_or(-1);
            (end - start + 1).max(0)
        })
        .sum()
}

fn median_delta_ms(items: &[f64]) -> Option<f64> {
    if items.len() < 2 {
        return None;
    }
    let mut deltas: Vec<f64> = items
        .windows(2)
        .map(|pair| (pair[1] - pair[0]) * 1000.0)
        .collect();
    deltas.sort_by(|left, right| left.partial_cmp(right).unwrap_or(std::cmp::Ordering::Equal));
    Some(round3(median_sorted(&deltas)))
}

fn median_available(items: &[Option<f64>]) -> Option<f64> {
    let mut values: Vec<f64> = items
        .iter()
        .filter_map(|value| *value)
        .filter(|value| value.is_finite())
        .collect();
    if values.is_empty() {
        return None;
    }
    values.sort_by(|left, right| left.partial_cmp(right).unwrap_or(std::cmp::Ordering::Equal));
    Some(median_sorted(&values))
}

fn median_sorted(ordered: &[f64]) -> f64 {
    let mid = ordered.len() / 2;
    if ordered.len() % 2 == 0 {
        (ordered[mid - 1] + ordered[mid]) / 2.0
    } else {
        ordered[mid]
    }
}

fn percentile_sorted(ordered: &[f64], percentile: f64) -> f64 {
    if ordered.len() == 1 {
        return ordered[0];
    }
    let position = (percentile.clamp(0.0, 100.0) / 100.0) * ((ordered.len() - 1) as f64);
    let lower = position.floor() as usize;
    let upper = position.ceil() as usize;
    if lower == upper {
        ordered[lower]
    } else {
        let fraction = position - lower as f64;
        ordered[lower] + (ordered[upper] - ordered[lower]) * fraction
    }
}

fn has_large_negative_segment(rows: &[Value]) -> bool {
    rows.iter().any(|row| {
        [
            "windows_send_to_quest_receive_ms",
            "quest_send_to_windows_receive_ms",
        ]
        .iter()
        .any(|key| {
            row.get(*key)
                .and_then(Value::as_f64)
                .map(|value| value < -25.0)
                .unwrap_or(false)
        })
    })
}

fn attach_stream_info(report: &mut Value, info: &lsl::StreamInfo) {
    insert(report, "discovered_stream_name", json!(info.stream_name()));
    insert(report, "discovered_stream_type", json!(info.stream_type()));
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
    insert(report, "discovered_hostname", json!(info.hostname()));
    insert(report, "discovered_uid", json!(info.uid()));
    insert(report, "discovered_session_id", json!(info.session_id()));
    insert(report, "discovered_created_at", json!(info.created_at()));
    if let Ok(xml) = info.to_xml() {
        insert(
            report,
            "discovered_v4address",
            json!(xml_text(&xml, "v4address")),
        );
        insert(
            report,
            "discovered_v4data_port",
            json!(xml_text(&xml, "v4data_port")),
        );
        insert(
            report,
            "discovered_v4service_port",
            json!(xml_text(&xml, "v4service_port")),
        );
    }
}

fn stream_summary(info: &lsl::StreamInfo) -> Value {
    let mut summary = json!({
        "name": info.stream_name(),
        "type": info.stream_type(),
        "source_id": info.source_id(),
        "hostname": info.hostname(),
        "uid": info.uid(),
        "session_id": info.session_id(),
        "channel_count": info.channel_count(),
        "nominal_srate": info.nominal_srate(),
    });
    if let Ok(xml) = info.to_xml() {
        insert(
            &mut summary,
            "v4address",
            json!(xml_text(&xml, "v4address")),
        );
        insert(
            &mut summary,
            "v4data_port",
            json!(xml_text(&xml, "v4data_port")),
        );
        insert(
            &mut summary,
            "v4service_port",
            json!(xml_text(&xml, "v4service_port")),
        );
    }
    summary
}

fn xml_text(xml: &str, tag: &str) -> String {
    roxmltree::Document::parse(xml)
        .ok()
        .and_then(|document| {
            document
                .descendants()
                .find(|node| node.has_tag_name(tag))
                .and_then(|node| node.text())
                .map(str::to_string)
        })
        .unwrap_or_default()
}

fn current_lsl_api_config() -> Value {
    let path = env::var("LSLAPICFG").unwrap_or_default();
    if path.trim().is_empty() {
        return json!({"path": "", "content": ""});
    }
    json!({
        "path": path,
        "content": fs::read_to_string(env::var("LSLAPICFG").unwrap_or_default()).unwrap_or_default(),
    })
}

fn read_json(path: &str) -> Value {
    if path.trim().is_empty() {
        return json!({});
    }
    fs::read_to_string(path)
        .ok()
        .and_then(|text| serde_json::from_str(&text).ok())
        .unwrap_or_else(|| json!({}))
}

fn insert(report: &mut Value, name: &str, value: Value) {
    if let Some(object) = report.as_object_mut() {
        object.insert(name.to_string(), value);
    }
}

fn round3(value: f64) -> f64 {
    (value * 1000.0).round() / 1000.0
}

fn round6(value: f64) -> f64 {
    (value * 1_000_000.0).round() / 1_000_000.0
}

fn round9(value: f64) -> f64 {
    (value * 1_000_000_000.0).round() / 1_000_000_000.0
}
