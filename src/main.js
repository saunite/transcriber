// Transcriber -- "Verbatim" direction (.impeccable/surfaces/src-index-html.md).
// Uses the global window.__TAURI__ (app.withGlobalTauri in tauri.conf.json)
// -- no npm/bundler step. IPC contract (commands/events) is fixed by
// src-tauri/src/{main,sidecar}.rs; this file only owns presentation.

const { invoke } = window.__TAURI__.core;
const { listen } = window.__TAURI__.event;
// tauri-plugin-dialog registered in main.rs; withGlobalTauri exposes its
// JS API at window.__TAURI__.dialog with no npm package needed (UNVERIFIED
// against a real build -- see src-tauri/Cargo.toml).
const { open: openFileDialog } = window.__TAURI__.dialog;

const els = {
  noteRoot: document.getElementById("note-root"),
  settingsToggle: document.getElementById("settings-toggle"),
  settingsDrawer: document.getElementById("settings-drawer"),
  modelSelect: document.getElementById("model-select"),
  languageInput: document.getElementById("language-input"),
  includeMicCheckbox: document.getElementById("include-mic-checkbox"),
  micDeviceField: document.getElementById("mic-device-field"),
  micDeviceSelect: document.getElementById("mic-device-select"),
  tabLive: document.getElementById("tab-live"),
  tabFile: document.getElementById("tab-file"),
  panelLive: document.getElementById("panel-live"),
  panelFile: document.getElementById("panel-file"),
  liveStamp: document.getElementById("live-stamp"),
  startingStamp: document.getElementById("starting-stamp"),
  busyStamp: document.getElementById("busy-stamp"),
  stopBtn: document.getElementById("stop-btn"),
  liveEmpty: document.getElementById("live-empty"),
  startLiveBtn: document.getElementById("start-live-btn"),
  macosNotice: document.getElementById("macos-live-notice"),
  transcriptLive: document.getElementById("transcript-live"),
  dropZone: document.getElementById("drop-zone"),
  formatSelect: document.getElementById("format-select"),
  taskSelect: document.getElementById("task-select"),
  transcriptFile: document.getElementById("transcript-file"),
  debugLog: document.getElementById("debug-log"),
};

// ---- Notes (error/status toasts) --------------------------------------

function showNote(message) {
  const note = document.createElement("div");
  note.className = "note";
  note.textContent = message;
  note.addEventListener("click", () => note.remove());
  els.noteRoot.appendChild(note);
  setTimeout(() => note.remove(), 8000);
}

// ---- Tabs ---------------------------------------------------------------

function selectTab(name) {
  const liveActive = name === "live";
  els.tabLive.setAttribute("aria-selected", String(liveActive));
  els.tabFile.setAttribute("aria-selected", String(!liveActive));
  els.panelLive.hidden = !liveActive;
  els.panelFile.hidden = liveActive;
  updateTopline();
}

els.tabLive.addEventListener("click", () => {
  if (!els.tabLive.disabled) selectTab("live");
});
els.tabFile.addEventListener("click", () => selectTab("file"));

function activeTab() {
  return els.tabLive.getAttribute("aria-selected") === "true" ? "live" : "file";
}

// ---- Settings drawer ------------------------------------------------------

els.settingsToggle.addEventListener("click", () => {
  const expanded = els.settingsToggle.getAttribute("aria-expanded") === "true";
  els.settingsToggle.setAttribute("aria-expanded", String(!expanded));
  els.settingsDrawer.hidden = expanded;
});

els.includeMicCheckbox.addEventListener("change", () => {
  els.micDeviceField.hidden = !els.includeMicCheckbox.checked;
});

async function populateMicDevices() {
  try {
    const devices = await invoke("list_devices");
    els.micDeviceSelect.innerHTML = "";
    for (const device of devices.filter((d) => d.max_input_channels > 0)) {
      const opt = document.createElement("option");
      opt.value = device.index;
      opt.textContent = `[${device.index}] ${device.name}`;
      els.micDeviceSelect.appendChild(opt);
    }
  } catch (err) {
    showNote(`Could not list audio devices: ${err}`);
  }
}

// ---- Transcript lines -----------------------------------------------------

// Only one sidecar session runs at a time; incoming transcript-line /
// sidecar-log events belong to whichever flow most recently started.
let currentFlow = null; // "live" | "file" | null

function appendTranscriptLine(list, { ts, tag, text }) {
  const item = document.createElement("li");
  item.className = "transcript-line";
  const tagHtml = tag ? `<span class="line-tag line-tag-${tag}">${tag}</span>` : "";
  item.innerHTML = `
    <span class="line-meta">
      <span class="line-ts mono">${ts}</span>
      ${tagHtml}
    </span>
    <span class="line-text"></span>
  `;
  item.querySelector(".line-text").textContent = text; // avoid HTML-injecting transcript text
  list.appendChild(item);
  list.hidden = false;
  list.scrollTop = list.scrollHeight;
}

function appendDebugLine(line) {
  els.debugLog.textContent += line + "\n";
  els.debugLog.scrollTop = els.debugLog.scrollHeight;
}

// ---- Live session state ----------------------------------------------------

// idle -> starting (invoke resolved, no output yet) -> active (first output
// arrived) -> idle. Mirrors specs/desktop-gui "Start live capture" (shows a
// starting state until output begins).
let liveState = "idle";

function setLiveState(next) {
  liveState = next;
  els.liveEmpty.hidden = next !== "idle";
  els.startingStamp.hidden = next !== "starting";
  els.liveStamp.hidden = next !== "active";
  els.stopBtn.hidden = next === "idle";
  els.stopBtn.disabled = next === "stopping";
  updateTopline();
}

function updateTopline() {
  const onLiveTab = activeTab() === "live";
  els.liveStamp.hidden = !(onLiveTab && liveState === "active");
  els.startingStamp.hidden = !(onLiveTab && liveState === "starting");
  els.stopBtn.hidden = !(onLiveTab && liveState !== "idle");
  els.busyStamp.hidden = !(activeTab() === "file" && fileBusy);
}

async function startLiveSession() {
  els.transcriptLive.innerHTML = "";
  els.transcriptLive.hidden = true;
  els.startLiveBtn.disabled = true;
  currentFlow = "live";
  try {
    await invoke("start_live_session", {
      model: els.modelSelect.value,
      language: els.languageInput.value.trim() || null,
      includeMic: els.includeMicCheckbox.checked,
      micDevice: els.includeMicCheckbox.checked ? Number(els.micDeviceSelect.value) : null,
    });
    setLiveState("starting");
  } catch (err) {
    showNote(`Could not start live capture: ${err}`);
    setLiveState("idle");
  } finally {
    els.startLiveBtn.disabled = false;
  }
}

async function stopLiveSession() {
  setLiveState("stopping");
  try {
    await invoke("stop_live_session");
  } catch (err) {
    showNote(`Could not stop live capture: ${err}`);
  } finally {
    setLiveState("idle");
  }
}

els.startLiveBtn.addEventListener("click", startLiveSession);
els.stopBtn.addEventListener("click", stopLiveSession);

// ---- File transcription -----------------------------------------------------

// Mirrors transcriber.py's video_extensions | audio_extensions -- checked
// client-side so an unsupported drop never spawns the sidecar
// (specs/desktop-gui "Drop an unsupported file").
const VIDEO_EXTENSIONS = ["mp4", "avi", "mkv", "mov", "wmv", "flv", "webm", "m4v"];
const AUDIO_EXTENSIONS = ["mp3", "wav", "flac", "m4a", "ogg", "opus", "wma"];
const SUPPORTED_EXTENSIONS = new Set([...VIDEO_EXTENSIONS, ...AUDIO_EXTENSIONS]);

function hasSupportedExtension(filePath) {
  const ext = filePath.split(".").pop()?.toLowerCase();
  return !!ext && SUPPORTED_EXTENSIONS.has(ext);
}

let fileBusy = false;

function setFileBusy(busy) {
  fileBusy = busy;
  updateTopline();
}

async function transcribeFile(filePath) {
  if (!hasSupportedExtension(filePath)) {
    showNote(`Unsupported file type: ${filePath}`);
    return;
  }
  selectTab("file");
  els.transcriptFile.innerHTML = "";
  els.transcriptFile.hidden = true;
  currentFlow = "file";
  setFileBusy(true);
  try {
    await invoke("start_file_transcription", {
      filePath,
      format: els.formatSelect.value,
      task: els.taskSelect.value,
      model: els.modelSelect.value,
      language: els.languageInput.value.trim() || null,
    });
  } catch (err) {
    showNote(`Could not transcribe file: ${err}`);
    setFileBusy(false);
  }
}

els.dropZone.addEventListener("click", async () => {
  const path = await openFileDialog({
    multiple: false,
    filters: [
      { name: "Video", extensions: VIDEO_EXTENSIONS },
      { name: "Audio", extensions: AUDIO_EXTENSIONS },
    ],
  });
  if (typeof path === "string") transcribeFile(path);
});

function setupDropZone() {
  // dragDropEnabled (tauri.conf.json) routes file drops through the
  // tauri://drag-drop window event rather than the browser's native drop
  // event.
  listen("tauri://drag-drop", (event) => {
    els.dropZone.classList.remove("drag-over");
    const paths = event.payload?.paths ?? [];
    if (paths.length > 0) transcribeFile(paths[0]);
  });
  listen("tauri://drag-enter", () => {
    selectTab("file");
    els.dropZone.classList.add("drag-over");
  });
  listen("tauri://drag-leave", () => els.dropZone.classList.remove("drag-over"));
}

// ---- Platform gate -----------------------------------------------------

async function applyPlatformGate() {
  // specs/desktop-gui "Graceful macOS degradation": live capture stays
  // disabled on macOS regardless of whether the sidecar supports
  // --coreaudio-tap, until add-macos-capture's hardware verification
  // (tasks.md section 5) is complete -- see tasks.md 5.8.
  const platform = await invoke("get_platform");
  if (platform === "macos") {
    els.tabLive.disabled = true;
    els.macosNotice.hidden = false;
    els.liveEmpty.hidden = true;
    selectTab("file");
  }
}

// ---- Event wiring -----------------------------------------------------

listen("transcript-line", (event) => {
  if (currentFlow === "live" && liveState === "starting") setLiveState("active");
  const list = currentFlow === "file" ? els.transcriptFile : els.transcriptLive;
  appendTranscriptLine(list, event.payload);
});

listen("sidecar-log", (event) => {
  if (currentFlow === "live" && liveState === "starting") setLiveState("active");
  appendDebugLine(event.payload.line);
});

listen("sidecar-crashed", (event) => {
  setLiveState("idle");
  showNote(event.payload.message);
});

listen("file-transcription-complete", (event) => {
  setFileBusy(false);
  showNote(event.payload ? "Transcript saved." : "File transcription failed — see the engine log for details.");
});

setupDropZone();
applyPlatformGate();
populateMicDevices();
updateTopline();
