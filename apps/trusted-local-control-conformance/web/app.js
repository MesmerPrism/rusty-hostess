"use strict";

const commandRegistry = new Set([
  "describe",
  "get_state",
  "list_videos",
  "select_video",
  "play",
  "pause",
]);

let authorityRevision = 0;
let playerRevision = 0;
let requestSequence = 0;
let eventSocket = null;

const byId = (id) => document.getElementById(id);

function appendEvent(event) {
  const row = document.createElement("li");
  row.textContent = `${event.type}: ${event.command || event.reason || "state"}`;
  byId("events").prepend(row);
}

function setControlsEnabled(enabled) {
  for (const id of ["video-select", "select-video", "play", "pause"]) {
    byId(id).disabled = !enabled;
  }
}

function renderState(state) {
  playerRevision = state.revision;
  byId("active-state").textContent =
    `Selected: ${state.selected_video_id}; playing: ${state.playing}; revision: ${playerRevision}`;
}

function nextRequestId(command) {
  requestSequence += 1;
  return `browser-${command.replaceAll("_", "-")}-${String(requestSequence).padStart(8, "0")}`;
}

function sendCommand(command, payload = {}) {
  if (!commandRegistry.has(command)) {
    throw new Error("command is outside the packaged registry");
  }
  eventSocket.send(JSON.stringify({
    command,
    expected_authority_revision: authorityRevision,
    expected_player_revision: playerRevision,
    payload,
    request_id: nextRequestId(command),
  }));
}

function loadVideos(videos) {
  const select = byId("video-select");
  select.replaceChildren();
  for (const video of videos) {
    const option = document.createElement("option");
    option.value = video.video_id;
    option.textContent = video.title;
    select.append(option);
  }
}

function connectEvents() {
  const scheme = window.location.protocol === "https:" ? "wss:" : "ws:";
  eventSocket = new WebSocket(`${scheme}//${window.location.host}/v1/events`);
  eventSocket.addEventListener("message", (message) => {
    const event = JSON.parse(message.data);
    appendEvent({type: event.event, command: event.command, reason: event.reason});
    if (Number.isInteger(event.authority_revision)) {
      authorityRevision = event.authority_revision;
    }
    if (event.event === "command_applied") {
      renderState(event.state);
    }
    if (event.event === "command_result" && event.command === "get_state") {
      renderState(event.state);
      sendCommand("list_videos");
    }
    if (event.event === "command_result" && event.command === "list_videos") {
      loadVideos(event.videos);
    }
  });
  eventSocket.addEventListener("open", () => sendCommand("get_state"));
}

byId("pair-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const response = await fetch("/v1/pair", {
    method: "POST",
    credentials: "same-origin",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({
      pairing_code: byId("pairing-code").value,
      request_id: nextRequestId("pair"),
    }),
  });
  const reply = await response.json();
  if (!response.ok) {
    byId("connection-status").textContent = `Pairing rejected: ${reply.reason}`;
    return;
  }
  authorityRevision = reply.authority_revision;
  byId("connection-status").textContent = `Paired: ${reply.controller_label}`;
  setControlsEnabled(true);
  connectEvents();
});

byId("select-video").addEventListener("click", () => {
  sendCommand("select_video", {video_id: byId("video-select").value});
});
byId("play").addEventListener("click", () => sendCommand("play"));
byId("pause").addEventListener("click", () => sendCommand("pause"));
