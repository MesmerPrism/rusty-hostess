use crate::bridge_command_inbox::{
    parse_bridge_command_request_value, BridgeCommandApplication, BridgeCommandInboxState,
    BridgeCommandRequest,
};
use crate::makepad_diagnostics::{emit_marker_line, marker_value};
use serde_json::{json, Value as JsonValue};
use std::{
    io::{ErrorKind, Read, Write},
    net::TcpStream,
    sync::{
        atomic::{AtomicBool, Ordering},
        Arc, Mutex,
    },
    thread,
    time::Duration,
};

pub(crate) const BRIDGE_COMMAND_STREAM_ID: &str = "stream.hostess.makepad.bridge_command";
pub(crate) const BRIDGE_COMMAND_RECEIPT_STREAM_ID: &str =
    "stream.hostess.makepad.bridge_command.receipt";
pub(crate) const BRIDGE_COMMAND_RECEIVER_ID: &str = "app.hostess_makepad.bridge_command_subscriber";
pub(crate) const MANIFOLD_COMMAND_SCHEMA: &str = "rusty.manifold.command.envelope.v1";
#[cfg(test)]
const LEGACY_RUSTY_XR_BROKER_COMMAND_SCHEMA: &str = "rusty.xr.broker.command.v1";
pub(crate) const MANIFOLD_BROKER_EVENTS_PATH: &str = "/manifold/v1/events";

#[derive(Clone, Debug, PartialEq)]
pub(crate) struct ManifoldBridgeCommandSubscriberConfig {
    pub enabled: bool,
    pub broker_host: String,
    pub broker_port: u16,
    pub stream_id: String,
    pub receipt_stream_id: String,
    pub receiver_id: String,
    pub connect_timeout_ms: u64,
}

impl Default for ManifoldBridgeCommandSubscriberConfig {
    fn default() -> Self {
        Self {
            enabled: true,
            broker_host: "127.0.0.1".to_string(),
            broker_port: 8765,
            stream_id: BRIDGE_COMMAND_STREAM_ID.to_string(),
            receipt_stream_id: BRIDGE_COMMAND_RECEIPT_STREAM_ID.to_string(),
            receiver_id: BRIDGE_COMMAND_RECEIVER_ID.to_string(),
            connect_timeout_ms: 250,
        }
    }
}

pub(crate) struct ManifoldBridgeCommandSubscriber {
    config: ManifoldBridgeCommandSubscriberConfig,
    stop: Arc<AtomicBool>,
    latest_application: Arc<Mutex<Option<BridgeCommandApplication>>>,
}

impl ManifoldBridgeCommandSubscriber {
    pub(crate) fn new(config: ManifoldBridgeCommandSubscriberConfig) -> Self {
        let stop = Arc::new(AtomicBool::new(false));
        let latest_application = Arc::new(Mutex::new(None));
        let worker_stop = stop.clone();
        let worker_latest_application = latest_application.clone();
        let worker_config = config.clone();
        thread::spawn(move || {
            run_bridge_command_worker(worker_config, worker_stop, worker_latest_application)
        });
        Self {
            config,
            stop,
            latest_application,
        }
    }

    pub(crate) fn config(&self) -> &ManifoldBridgeCommandSubscriberConfig {
        &self.config
    }

    pub(crate) fn take_latest_application(&self) -> Option<BridgeCommandApplication> {
        self.latest_application
            .lock()
            .ok()
            .and_then(|mut application| application.take())
    }
}

impl Drop for ManifoldBridgeCommandSubscriber {
    fn drop(&mut self) {
        self.stop.store(true, Ordering::Relaxed);
    }
}

pub(crate) fn build_bridge_command_subscribe_command(
    config: &ManifoldBridgeCommandSubscriberConfig,
) -> JsonValue {
    json!({
        "type": "command",
        "schema": MANIFOLD_COMMAND_SCHEMA,
        "request_id": "makepad-bridge-command-subscribe",
        "command": "subscribe",
        "params": {
            "stream": config.stream_id,
            "receiver": config.receiver_id,
        }
    })
}

pub(crate) fn parse_bridge_command_event(
    message: &JsonValue,
    expected_stream: &str,
) -> Option<BridgeCommandRequest> {
    if message.get("type").and_then(JsonValue::as_str) != Some("stream_event") {
        return None;
    }
    let payload = message.get("payload").filter(|value| value.is_object())?;
    let stream_id = first_string(
        &[
            message.get("stream"),
            message.get("stream_id"),
            payload.get("stream"),
            payload.get("stream_id"),
        ],
        expected_stream,
    );
    if stream_id != expected_stream {
        return None;
    }
    parse_bridge_command_request_value(payload).ok()
}

pub(crate) fn build_bridge_command_receipt_publish_command(
    config: &ManifoldBridgeCommandSubscriberConfig,
    application: &BridgeCommandApplication,
    receipt_sequence_id: u64,
) -> JsonValue {
    json!({
        "type": "command",
        "schema": MANIFOLD_COMMAND_SCHEMA,
        "request_id": format!("makepad-bridge-command-receipt-{}", receipt_sequence_id),
        "command": "publish_stream_event",
        "params": {
            "stream": config.receipt_stream_id,
            "receiver": config.receiver_id,
            "sequence_id": receipt_sequence_id,
            "payload": application.receipt_json.clone(),
        }
    })
}

fn run_bridge_command_worker(
    config: ManifoldBridgeCommandSubscriberConfig,
    stop: Arc<AtomicBool>,
    latest_application: Arc<Mutex<Option<BridgeCommandApplication>>>,
) {
    let mut client = BrokerWebSocketClient::new(config.clone());
    let mut inbox = BridgeCommandInboxState::default();
    let mut receipt_sequence_id = 1_u64;
    let mut last_worker_marker = String::new();
    while !stop.load(Ordering::Relaxed) {
        if let Err(error) = client.ensure_subscribed() {
            emit_bridge_command_worker_marker(
                &config,
                "connect",
                "error",
                Some(error.as_str()),
                &mut last_worker_marker,
            );
            client.reset();
            thread::sleep(Duration::from_millis(250));
            continue;
        }
        emit_bridge_command_worker_marker(
            &config,
            "connect",
            "subscribe_sent",
            None,
            &mut last_worker_marker,
        );
        match client.recv_json() {
            Ok(Some(message)) => {
                let Some(request) = parse_bridge_command_event(&message, &config.stream_id) else {
                    continue;
                };
                let Some(application) = inbox.apply_request("broker-stream", request, None) else {
                    continue;
                };
                if let Ok(mut latest) = latest_application.lock() {
                    *latest = Some(application.clone());
                }
                let receipt = build_bridge_command_receipt_publish_command(
                    &config,
                    &application,
                    receipt_sequence_id,
                );
                receipt_sequence_id = receipt_sequence_id.saturating_add(1);
                if client.send_json(&receipt, receipt_sequence_id).is_err() {
                    client.reset();
                }
            }
            Ok(None) => {}
            Err(error) => {
                emit_bridge_command_worker_marker(
                    &config,
                    "receive",
                    "error",
                    Some(error.as_str()),
                    &mut last_worker_marker,
                );
                client.reset();
                thread::sleep(Duration::from_millis(250));
            }
        }
    }
}

fn emit_bridge_command_worker_marker(
    config: &ManifoldBridgeCommandSubscriberConfig,
    phase: &str,
    status: &str,
    issue: Option<&str>,
    last_marker: &mut String,
) {
    let issue_token = issue.map(marker_value).unwrap_or_else(|| "none".to_string());
    let marker = format!(
        "RUSTY_HOSTESS_MAKEPAD_BRIDGE_COMMAND_SUBSCRIBER schema=rusty.hostess.makepad.bridge_command_subscriber.v1 phase={} status={} stream={} receiptStream={} receiver={} brokerHost={} brokerPort={} issue={} highRateJsonPayload=false",
        marker_value(phase),
        marker_value(status),
        marker_value(&config.stream_id),
        marker_value(&config.receipt_stream_id),
        marker_value(&config.receiver_id),
        marker_value(&config.broker_host),
        config.broker_port,
        issue_token,
    );
    if last_marker == &marker {
        return;
    }
    *last_marker = marker.clone();
    emit_marker_line(&marker);
}

struct BrokerWebSocketClient {
    config: ManifoldBridgeCommandSubscriberConfig,
    stream: Option<TcpStream>,
    subscribed: bool,
}

impl BrokerWebSocketClient {
    fn new(config: ManifoldBridgeCommandSubscriberConfig) -> Self {
        Self {
            config,
            stream: None,
            subscribed: false,
        }
    }

    fn reset(&mut self) {
        self.stream = None;
        self.subscribed = false;
    }

    fn ensure_subscribed(&mut self) -> Result<(), String> {
        if self.stream.is_none() {
            self.stream = Some(open_broker_websocket(&self.config)?);
            self.send_json(&build_hello_message(&self.config), 1)?;
        }
        if !self.subscribed {
            self.send_json(&build_bridge_command_subscribe_command(&self.config), 2)?;
            self.subscribed = true;
        }
        Ok(())
    }

    fn send_json(&mut self, value: &JsonValue, sequence_id: u64) -> Result<(), String> {
        let text = value.to_string();
        let frame = websocket_client_text_frame(text.as_bytes(), sequence_id);
        let stream = self
            .stream
            .as_mut()
            .ok_or_else(|| "missing_websocket_stream".to_string())?;
        stream
            .write_all(&frame)
            .map_err(|err| format!("websocket_write_failed:{err}"))?;
        stream
            .flush()
            .map_err(|err| format!("websocket_flush_failed:{err}"))?;
        Ok(())
    }

    fn recv_json(&mut self) -> Result<Option<JsonValue>, String> {
        let stream = self
            .stream
            .as_mut()
            .ok_or_else(|| "missing_websocket_stream".to_string())?;
        let payload = read_websocket_frame(stream)?;
        if payload.is_empty() {
            return Ok(None);
        }
        let text =
            String::from_utf8(payload).map_err(|err| format!("websocket_text_invalid:{err}"))?;
        let value =
            serde_json::from_str(&text).map_err(|err| format!("websocket_json_invalid:{err}"))?;
        Ok(Some(value))
    }
}

fn build_hello_message(config: &ManifoldBridgeCommandSubscriberConfig) -> JsonValue {
    json!({
        "type": "hello",
        "client_id": config.receiver_id,
        "app_package": "rusty-hostess-makepad-camera-shell",
        "role": "makepad_bridge_command_subscriber",
    })
}

fn open_broker_websocket(
    config: &ManifoldBridgeCommandSubscriberConfig,
) -> Result<TcpStream, String> {
    let address = format!("{}:{}", config.broker_host, config.broker_port);
    let mut stream =
        TcpStream::connect(address).map_err(|err| format!("broker_connect_failed:{err}"))?;
    let timeout = Duration::from_millis(config.connect_timeout_ms.clamp(50, 5_000));
    let _ = stream.set_read_timeout(Some(timeout));
    let _ = stream.set_write_timeout(Some(timeout));
    let request = format!(
        "GET {} HTTP/1.1\r\n\
         Host: {}:{}\r\n\
         Upgrade: websocket\r\n\
         Connection: Upgrade\r\n\
         Sec-WebSocket-Key: cnVzdHktaG9zdGVzcy1icmlkZ2U=\r\n\
         Sec-WebSocket-Version: 13\r\n\
         \r\n",
        MANIFOLD_BROKER_EVENTS_PATH, config.broker_host, config.broker_port
    );
    stream
        .write_all(request.as_bytes())
        .map_err(|err| format!("websocket_handshake_write_failed:{err}"))?;

    let mut response = Vec::with_capacity(512);
    let mut byte = [0_u8; 1];
    while response.len() < 4096 {
        stream
            .read_exact(&mut byte)
            .map_err(|err| format!("websocket_handshake_read_failed:{err}"))?;
        response.push(byte[0]);
        if response.ends_with(b"\r\n\r\n") {
            break;
        }
    }
    let response_text = String::from_utf8_lossy(&response);
    if !response_text.starts_with("HTTP/1.1 101") {
        return Err("websocket_handshake_rejected".to_string());
    }
    Ok(stream)
}

fn websocket_client_text_frame(payload: &[u8], sequence_id: u64) -> Vec<u8> {
    let mut frame = Vec::with_capacity(payload.len() + 16);
    frame.push(0x81);
    let mask = websocket_mask(sequence_id);
    if payload.len() <= 125 {
        frame.push(0x80 | payload.len() as u8);
    } else if payload.len() <= u16::MAX as usize {
        frame.push(0x80 | 126);
        frame.extend_from_slice(&(payload.len() as u16).to_be_bytes());
    } else {
        frame.push(0x80 | 127);
        frame.extend_from_slice(&(payload.len() as u64).to_be_bytes());
    }
    frame.extend_from_slice(&mask);
    for (index, byte) in payload.iter().enumerate() {
        frame.push(*byte ^ mask[index % 4]);
    }
    frame
}

fn websocket_mask(sequence_id: u64) -> [u8; 4] {
    let bytes = sequence_id
        .wrapping_mul(0xA6D3_1C79_F0B5_4321)
        .to_le_bytes();
    [bytes[0], bytes[3], bytes[5], bytes[7]]
}

fn read_websocket_frame(stream: &mut TcpStream) -> Result<Vec<u8>, String> {
    let mut header = [0_u8; 2];
    if let Err(err) = stream.read_exact(&mut header) {
        if matches!(err.kind(), ErrorKind::TimedOut | ErrorKind::WouldBlock) {
            return Ok(Vec::new());
        }
        return Err(format!("websocket_frame_header_read_failed:{err}"));
    }
    let masked = (header[1] & 0x80) != 0;
    let mut len = (header[1] & 0x7f) as usize;
    if len == 126 {
        let mut extended = [0_u8; 2];
        stream
            .read_exact(&mut extended)
            .map_err(|err| format!("websocket_frame_len16_read_failed:{err}"))?;
        len = u16::from_be_bytes(extended) as usize;
    } else if len == 127 {
        let mut extended = [0_u8; 8];
        stream
            .read_exact(&mut extended)
            .map_err(|err| format!("websocket_frame_len64_read_failed:{err}"))?;
        len = u64::from_be_bytes(extended).min(1024 * 1024) as usize;
    }
    let mut mask = [0_u8; 4];
    if masked {
        stream
            .read_exact(&mut mask)
            .map_err(|err| format!("websocket_frame_mask_read_failed:{err}"))?;
    }
    let mut payload = vec![0_u8; len.min(1024 * 1024)];
    stream
        .read_exact(&mut payload)
        .map_err(|err| format!("websocket_frame_payload_read_failed:{err}"))?;
    if masked {
        for (index, byte) in payload.iter_mut().enumerate() {
            *byte ^= mask[index % 4];
        }
    }
    Ok(payload)
}

fn first_string(values: &[Option<&JsonValue>], default: &str) -> String {
    values
        .iter()
        .filter_map(|value| value.and_then(JsonValue::as_str))
        .find(|value| !value.trim().is_empty())
        .unwrap_or(default)
        .trim()
        .to_string()
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::bridge_command_inbox::{
        BRIDGE_COMMAND_RECEIPT_SCHEMA, BRIDGE_PROBE_SET_MARKER_COMMAND,
    };

    #[test]
    fn builds_bridge_command_subscription_command() {
        let config = ManifoldBridgeCommandSubscriberConfig {
            enabled: true,
            ..ManifoldBridgeCommandSubscriberConfig::default()
        };
        let command = build_bridge_command_subscribe_command(&config);
        assert_eq!(command["command"], "subscribe");
        assert_eq!(command["schema"], MANIFOLD_COMMAND_SCHEMA);
        assert_ne!(command["schema"], LEGACY_RUSTY_XR_BROKER_COMMAND_SCHEMA);
        assert_eq!(command["params"]["stream"], BRIDGE_COMMAND_STREAM_ID);
        assert_eq!(command["params"]["receiver"], BRIDGE_COMMAND_RECEIVER_ID);
    }

    #[test]
    fn parses_bridge_command_stream_event_and_builds_receipt_publish() {
        let config = ManifoldBridgeCommandSubscriberConfig::default();
        let event = json!({
            "type": "stream_event",
            "stream": BRIDGE_COMMAND_STREAM_ID,
            "sequence_id": 7,
            "payload": {
                "$schema": "rusty.hostess.bridge_command.request.v1",
                "request_id": "request.safe-probe",
                "command": BRIDGE_PROBE_SET_MARKER_COMMAND,
                "params": {
                    "probe_token": "probe-from-broker",
                    "source": "manifold-broker-stream"
                }
            }
        });
        let request =
            parse_bridge_command_event(&event, BRIDGE_COMMAND_STREAM_ID).expect("request parses");
        assert_eq!(request.request_id, "request.safe-probe");
        assert_eq!(request.probe_token, "probe-from-broker");
        assert_eq!(request.source, "manifold-broker-stream");

        let application = BridgeCommandApplication {
            request_id: request.request_id,
            command: request.command,
            probe_token: request.probe_token,
            receipt_json: json!({
                "$schema": BRIDGE_COMMAND_RECEIPT_SCHEMA,
                "request_id": "request.safe-probe",
                "command": BRIDGE_PROBE_SET_MARKER_COMMAND,
                "runtime_accepted": true,
                "applied": true
            }),
            receipt_path: None,
        };
        let publish = build_bridge_command_receipt_publish_command(&config, &application, 3);
        assert_eq!(publish["command"], "publish_stream_event");
        assert_eq!(publish["schema"], MANIFOLD_COMMAND_SCHEMA);
        assert_ne!(publish["schema"], LEGACY_RUSTY_XR_BROKER_COMMAND_SCHEMA);
        assert_eq!(
            publish["params"]["stream"],
            BRIDGE_COMMAND_RECEIPT_STREAM_ID
        );
        assert_eq!(
            publish["params"]["payload"]["$schema"],
            BRIDGE_COMMAND_RECEIPT_SCHEMA
        );
        assert_eq!(publish["params"]["payload"]["applied"], true);
    }

    #[test]
    fn ignores_unmatched_bridge_command_stream() {
        let event = json!({
            "type": "stream_event",
            "stream": "stream.hostess.makepad.other",
            "payload": {
                "$schema": "rusty.hostess.bridge_command.request.v1",
                "request_id": "request.other",
                "command": BRIDGE_PROBE_SET_MARKER_COMMAND
            }
        });
        assert!(parse_bridge_command_event(&event, BRIDGE_COMMAND_STREAM_ID).is_none());
    }

    #[test]
    fn idle_websocket_read_timeout_is_nonfatal() {
        let listener = std::net::TcpListener::bind("127.0.0.1:0").expect("bind listener");
        let address = listener.local_addr().expect("listener address");
        let server = std::thread::spawn(move || {
            let (_socket, _) = listener.accept().expect("accept client");
            std::thread::sleep(std::time::Duration::from_millis(100));
        });
        let mut client = TcpStream::connect(address).expect("connect client");
        client
            .set_read_timeout(Some(std::time::Duration::from_millis(10)))
            .expect("set read timeout");

        let payload = read_websocket_frame(&mut client).expect("idle timeout is not fatal");

        assert!(payload.is_empty());
        server.join().expect("server joined");
    }
}
