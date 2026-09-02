// UNVERIFIED against a running Tauri app (see index.html header comment).
// Uses the global window.__TAURI__ (app.withGlobalTauri in
// tauri.conf.json) -- no npm/bundler step.

const { invoke } = window.__TAURI__.core;
const { listen } = window.__TAURI__.event;

const els = {
  toast: document.getElementById("toast"),
  startLiveBtn: document.getElementById("start-live-btn"),
  stopLiveBtn: document.getElementById("stop-live-btn"),
  macosNotice: document.getElementById("macos-live-notice"),
  liveControls: document.getElementById("live-controls"),
  deviceSelect: document.getElementById("device-select"),
  modelSelect: document.getElementById("model-select"),
  languageInput: document.getElementById("language-input"),
  includeMicCheckbox: document.getElementById("include-mic-checkbox"),
  micDeviceLabel: document.getElementById("mic-device-label"),
  micDeviceSelect: document.getElementById("mic-device-select"),
  transcriptView: document.getElementById("transcript-view"),
  debugLog: document.getElementById("debug-log"),
  dropZone: document.getElementById("drop-zone"),
  formatSelect: document.getElementById("format-select"),
  taskSelect: document.getElementById("task-select"),
  fileProgress: document.getElementById("file-progress"),
};

function showToast(message) {
  els.toast.textContent = message;
  els.toast.classList.remove("hidden");
  setTimeout(() => els.toast.classList.add("hidden"), 8000);
}

function appendTranscriptLine({ ts, tag, text }) {
  const line = document.createElement("div");
  line.className = "line";
  const tagHtml = tag ? `<span class="tag-${tag}">[${tag}]</span> ` : "";
  line.innerHTML = `<span class="ts">${ts}</span> ${tagHtml}<span class="text"></span>`;
  line.querySelector(".text").textContent = text; // avoid HTML-injecting transcript text
  els.transcriptView.appendChild(line);
  els.transcriptView.scrollTop = els.transcriptView.scrollHeight;
}

function appendDebugLine(line) {
  els.debugLog.textContent += line + "\n";
  els.debugLog.scrollTop = els.debugLog.scrollHeight;
}

async function populateDevices() {
  try {
    const devices = await invoke("list_devices");
    const inputDevices = devices.filter((d) => d.max_input_channels > 0);
    for (const select of [els.deviceSelect, els.micDeviceSelect]) {
      select.innerHTML = "";
      for (const device of inputDevices) {
        const opt = document.createElement("option");
        opt.value = device.index;
        opt.textContent = `[${device.index}] ${device.name}`;
        select.appendChild(opt);
      }
    }
  } catch (err) {
    showToast(`Could not list audio devices: ${err}`);
  }
}

let liveSessionActive = false;

function setLiveSessionActive(active) {
  liveSessionActive = active;
  els.startLiveBtn.classList.toggle("hidden", active);
  els.stopLiveBtn.classList.toggle("hidden", !active);
}

async function startLiveSession() {
  els.transcriptView.innerHTML = "";
  try {
    await invoke("start_live_session", {
      model: els.modelSelect.value,
      language: els.languageInput.value.trim() || null,
      includeMic: els.includeMicCheckbox.checked,
      micDevice: els.includeMicCheckbox.checked
        ? Number(els.micDeviceSelect.value)
        : null,
    });
    setLiveSessionActive(true);
  } catch (err) {
    showToast(`Could not start live capture: ${err}`);
  }
}

async function stopLiveSession() {
  try {
    await invoke("stop_live_session");
  } catch (err) {
    showToast(`Could not stop live capture: ${err}`);
  } finally {
    setLiveSessionActive(false);
  }
}

// Mirrors transcriber.py's video_extensions | audio_extensions -- checked
// client-side so an unsupported drop never spawns the sidecar
// (specs/desktop-gui "Drop an unsupported file").
const SUPPORTED_EXTENSIONS = new Set([
  "mp4", "avi", "mkv", "mov", "wmv", "flv", "webm", "m4v",
  "mp3", "wav", "flac", "m4a", "ogg", "opus", "wma",
]);

function hasSupportedExtension(filePath) {
  const ext = filePath.split(".").pop()?.toLowerCase();
  return !!ext && SUPPORTED_EXTENSIONS.has(ext);
}

async function transcribeFile(filePath) {
  if (!hasSupportedExtension(filePath)) {
    showToast(`Unsupported file type: ${filePath}`);
    return;
  }
  els.fileProgress.classList.remove("hidden");
  try {
    await invoke("start_file_transcription", {
      filePath,
      format: els.formatSelect.value,
      task: els.taskSelect.value,
      model: els.modelSelect.value,
      language: els.languageInput.value.trim() || null,
    });
  } catch (err) {
    showToast(`Could not transcribe file: ${err}`);
    els.fileProgress.classList.add("hidden");
  }
}

function setupDropZone() {
  // dragDropEnabled (tauri.conf.json) routes file drops through the
  // tauri://drag-drop window event rather than the browser's native drop
  // event.
  listen("tauri://drag-drop", (event) => {
    const paths = event.payload?.paths ?? [];
    if (paths.length > 0) {
      transcribeFile(paths[0]);
    }
  });
  listen("tauri://drag-enter", () => els.dropZone.classList.add("drag-over"));
  listen("tauri://drag-leave", () => els.dropZone.classList.remove("drag-over"));
}

async function applyPlatformGate() {
  // specs/desktop-gui "Graceful macOS degradation": live capture stays
  // disabled on macOS regardless of whether the sidecar supports
  // --coreaudio-tap, until add-macos-capture's hardware verification
  // (tasks.md section 5) is complete -- see tasks.md 5.8.
  const platform = await invoke("get_platform");
  if (platform === "macos") {
    els.liveControls.classList.add("hidden");
    els.macosNotice.classList.remove("hidden");
  }
}

els.startLiveBtn.addEventListener("click", startLiveSession);
els.stopLiveBtn.addEventListener("click", stopLiveSession);
els.includeMicCheckbox.addEventListener("change", () => {
  els.micDeviceLabel.classList.toggle("hidden", !els.includeMicCheckbox.checked);
});
els.dropZone.addEventListener("click", () => {
  // Click-to-browse needs @tauri-apps/plugin-dialog, not yet added --
  // drag-and-drop is the supported path for now.
  showToast("Click-to-browse isn't wired up yet -- drag a file onto this area instead.");
});

listen("transcript-line", (event) => appendTranscriptLine(event.payload));
listen("sidecar-log", (event) => appendDebugLine(event.payload.line));
listen("sidecar-crashed", (event) => {
  setLiveSessionActive(false);
  showToast(event.payload.message);
});
listen("file-transcription-complete", (event) => {
  els.fileProgress.classList.add("hidden");
  if (!event.payload) {
    showToast("File transcription failed -- see debug log for details.");
  }
});

setupDropZone();
applyPlatformGate();
populateDevices();
