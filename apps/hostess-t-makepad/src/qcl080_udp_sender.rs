use std::{
    net::UdpSocket,
    sync::atomic::{AtomicBool, Ordering},
    thread,
    time::{Duration, Instant},
};

use crate::{
    makepad_diagnostics::emit_marker_line,
    runtime_settings::{hotload_bool, hotload_text, hotload_u16, hotload_u32, marker_token},
};

pub(crate) const KEY_QCL080_UDP_ENABLED: &str = "qcl080_udp_enabled";
pub(crate) const KEY_QCL080_UDP_HOST: &str = "qcl080_udp_host";
pub(crate) const KEY_QCL080_UDP_PORT: &str = "qcl080_udp_port";
pub(crate) const KEY_QCL080_UDP_MARKER: &str = "qcl080_udp_marker";
pub(crate) const KEY_QCL080_UDP_PACKET_COUNT: &str = "qcl080_udp_packet_count";
pub(crate) const KEY_QCL080_UDP_INTERVAL_MS: &str = "qcl080_udp_interval_ms";
pub(crate) const KEY_QCL080_UDP_RUN_ID: &str = "qcl080_udp_run_id";

pub(crate) const DEFAULT_QCL080_UDP_PORT: u16 = 18_767;
pub(crate) const DEFAULT_QCL080_UDP_MARKER: &str = "rusty-qcl-udp";
const DEFAULT_QCL080_UDP_PACKET_COUNT: u32 = 12;
const DEFAULT_QCL080_UDP_INTERVAL_MS: u32 = 50;

static QCL080_UDP_SENDER_STARTED: AtomicBool = AtomicBool::new(false);

#[derive(Clone, Debug, PartialEq)]
pub(crate) struct Qcl080UdpSenderConfig {
    pub(crate) enabled: bool,
    pub(crate) host: String,
    pub(crate) port: u16,
    pub(crate) marker: String,
    pub(crate) packet_count: u32,
    pub(crate) interval_ms: u32,
    pub(crate) run_id: String,
}

impl Qcl080UdpSenderConfig {
    pub(crate) fn from_runtime_properties() -> Self {
        Self {
            enabled: hotload_bool(KEY_QCL080_UDP_ENABLED, false),
            host: hotload_text(KEY_QCL080_UDP_HOST, ""),
            port: hotload_u16(
                KEY_QCL080_UDP_PORT,
                DEFAULT_QCL080_UDP_PORT,
                1,
                u16::MAX,
            ),
            marker: hotload_text(KEY_QCL080_UDP_MARKER, DEFAULT_QCL080_UDP_MARKER),
            packet_count: hotload_u32(
                KEY_QCL080_UDP_PACKET_COUNT,
                DEFAULT_QCL080_UDP_PACKET_COUNT,
                1,
                10_000,
            ),
            interval_ms: hotload_u32(
                KEY_QCL080_UDP_INTERVAL_MS,
                DEFAULT_QCL080_UDP_INTERVAL_MS,
                0,
                60_000,
            ),
            run_id: hotload_text(KEY_QCL080_UDP_RUN_ID, ""),
        }
    }

    fn target(&self) -> String {
        format!("{}:{}", self.host, self.port)
    }
}

#[derive(Clone, Debug, PartialEq)]
pub(crate) struct Qcl080UdpSenderResult {
    pub(crate) status: &'static str,
    pub(crate) packets_sent: u32,
    pub(crate) elapsed_ms: u128,
    pub(crate) issue: String,
}

pub(crate) fn spawn_runtime_probe_once(phase: &str) {
    if QCL080_UDP_SENDER_STARTED
        .compare_exchange(false, true, Ordering::AcqRel, Ordering::Acquire)
        .is_err()
    {
        return;
    }

    let config = Qcl080UdpSenderConfig::from_runtime_properties();
    if !config.enabled {
        return;
    }

    let phase = phase.to_string();
    thread::spawn(move || {
        let result = send_udp_freshness_packets(&config);
        emit_marker_line(&marker_line(&phase, &config, &result));
    });
}

pub(crate) fn send_udp_freshness_packets(config: &Qcl080UdpSenderConfig) -> Qcl080UdpSenderResult {
    let started = Instant::now();
    if config.host.trim().is_empty() {
        return Qcl080UdpSenderResult {
            status: "error",
            packets_sent: 0,
            elapsed_ms: started.elapsed().as_millis(),
            issue: "missing_host".to_string(),
        };
    }

    let socket = match UdpSocket::bind("0.0.0.0:0") {
        Ok(socket) => socket,
        Err(error) => {
            return Qcl080UdpSenderResult {
                status: "error",
                packets_sent: 0,
                elapsed_ms: started.elapsed().as_millis(),
                issue: format!("udp_bind_failed:{error}"),
            }
        }
    };
    let target = config.target();
    let mut packets_sent = 0;
    let interval = Duration::from_millis(config.interval_ms as u64);
    for sequence in 0..config.packet_count {
        let payload = format!("{}|{:04}\n", config.marker, sequence);
        match socket.send_to(payload.as_bytes(), &target) {
            Ok(_) => {
                packets_sent += 1;
            }
            Err(error) => {
                return Qcl080UdpSenderResult {
                    status: if packets_sent > 0 { "partial" } else { "error" },
                    packets_sent,
                    elapsed_ms: started.elapsed().as_millis(),
                    issue: format!("udp_send_failed:{error}"),
                };
            }
        }
        if sequence + 1 < config.packet_count && !interval.is_zero() {
            thread::sleep(interval);
        }
    }

    Qcl080UdpSenderResult {
        status: "sent",
        packets_sent,
        elapsed_ms: started.elapsed().as_millis(),
        issue: "none".to_string(),
    }
}

pub(crate) fn marker_line(
    phase: &str,
    config: &Qcl080UdpSenderConfig,
    result: &Qcl080UdpSenderResult,
) -> String {
    format!(
        "RUSTY_HOSTESS_MAKEPAD_QCL080_UDP_SENDER schema=rusty.hostess.makepad.qcl080_udp_sender.v1 phase={} status={} enabled={} host={} port={} marker={} packetsRequested={} packetsSent={} intervalMs={} elapsedMs={} runId={} issue={} senderSource=makepad-runtime socketOwner=app-owned highRateJsonPayload=false settingsControlPayload=false",
        marker_token(phase),
        result.status,
        config.enabled,
        marker_token(&config.host),
        config.port,
        marker_token(&config.marker),
        config.packet_count,
        result.packets_sent,
        config.interval_ms,
        result.elapsed_ms,
        marker_token(&config.run_id),
        marker_token(&result.issue),
    )
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn marker_line_reports_app_owned_udp_sender_contract() {
        let config = Qcl080UdpSenderConfig {
            enabled: true,
            host: "192.0.2.10".to_string(),
            port: 18_767,
            marker: DEFAULT_QCL080_UDP_MARKER.to_string(),
            packet_count: 24,
            interval_ms: 20,
            run_id: "run-1".to_string(),
        };
        let result = Qcl080UdpSenderResult {
            status: "sent",
            packets_sent: 24,
            elapsed_ms: 480,
            issue: "none".to_string(),
        };

        let line = marker_line("startup", &config, &result);

        assert!(line.contains("RUSTY_HOSTESS_MAKEPAD_QCL080_UDP_SENDER"));
        assert!(line.contains("schema=rusty.hostess.makepad.qcl080_udp_sender.v1"));
        assert!(line.contains("senderSource=makepad-runtime"));
        assert!(line.contains("socketOwner=app-owned"));
        assert!(line.contains("packetsSent=24"));
        assert!(line.contains("runId=run-1"));
        assert!(line.contains("highRateJsonPayload=false"));
    }

    #[test]
    fn qcl080_properties_are_read_from_makepad_debug_namespace() {
        let names = crate::runtime_settings::runtime_property_names(KEY_QCL080_UDP_ENABLED);

        assert!(names.contains(&"debug.rustyquest.makepad.qcl080.udp.enabled".to_string()));
        assert!(names.contains(&"debug.rusty.qcl080.udp.enabled".to_string()));
    }
}
