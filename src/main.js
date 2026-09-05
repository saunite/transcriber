// Transcriber — chart-recorder direction (.impeccable/surfaces/src-index-html.md).
// Uses the global window.__TAURI__ (app.withGlobalTauri in tauri.conf.json)
// -- no npm/bundler step. IPC contract (commands/events) is fixed by
// src-tauri/src/{main,sidecar}.rs; this file only owns presentation.

const { invoke } = window.__TAURI__.core;
const { listen } = window.__TAURI__.event;
const { open: openFileDialog, save: saveFileDialog } = window.__TAURI__.dialog;
const { getCurrentWindow } = window.__TAURI__.window;

const els = {
  noteRoot: document.getElementById("note-root"),
  modelSelect: document.getElementById("model-select"),
  languageSelect: document.getElementById("language-select"),
  includeMicCheckbox: document.getElementById("include-mic-checkbox"),
  micDeviceField: document.getElementById("mic-device-field"),
  micDeviceSelect: document.getElementById("mic-device-select"),
  outputPathInput: document.getElementById("output-path-input"),
  outputBrowseBtn: document.getElementById("output-browse-btn"),
  audioDeviceInput: document.getElementById("audio-device-input"),
  tabLive: document.getElementById("tab-live"),
  tabFile: document.getElementById("tab-file"),
  panelLive: document.getElementById("panel-live"),
  panelFile: document.getElementById("panel-file"),
  chartLive: document.getElementById("chart-live"),
  chartFile: document.getElementById("chart-file"),
  runState: document.getElementById("run-state"),
  runStateLabel: document.getElementById("run-state-label"),
  runElapsed: document.getElementById("run-elapsed"),
  runDetail: document.getElementById("run-detail"),
  fileState: document.getElementById("file-state"),
  stopBtn: document.getElementById("stop-btn"),
  liveEmpty: document.getElementById("live-empty"),
  fileEmpty: document.getElementById("file-empty"),
  startLiveBtn: document.getElementById("start-live-btn"),
  macosNotice: document.getElementById("macos-live-notice"),
  transcriptLive: document.getElementById("transcript-live"),
  transcriptFile: document.getElementById("transcript-file"),
  dropZone: document.getElementById("drop-zone"),
  formatSelect: document.getElementById("format-select"),
  taskSelect: document.getElementById("task-select"),
  debugLog: document.getElementById("debug-log"),
  chartSpeed: document.getElementById("chart-speed"),
  chartSpeedReadout: document.getElementById("chart-speed-readout"),
  penFilter: document.getElementById("pen-filter"),
  timeMode: document.getElementById("time-mode"),
  timeModeHint: document.getElementById("time-mode-hint"),
  chartSearch: document.getElementById("chart-search"),
  searchCount: document.getElementById("search-count"),
  penSys: document.querySelector(".pen-sys"),
  penMic: document.querySelector(".pen-mic"),
  themeSelect: document.getElementById("theme-select"),
};

// The GUI always passes --chunk-duration 10, so "output is overdue" is a
// known constant here rather than a new backend signal.
const CHUNK_SECONDS = 10;
const STALL_MS = CHUNK_SECONDS * 2 * 1000;

// ---- Theme ------------------------------------------------------------

const THEME_KEY = "transcriber-theme";
const osDarkQuery = window.matchMedia("(prefers-color-scheme: dark)");

function getStoredThemePreference() {
  try {
    const stored = localStorage.getItem(THEME_KEY);
    return stored === "light" || stored === "dark" ? stored : "system";
  } catch (e) {
    return "system";
  }
}

// Syncs the native window chrome (title bar) to the resolved theme. Passing
// null tells Tauri "follow the OS" for the chrome directly -- whether that
// stays live on its own or needs re-asserting isn't documented either way,
// so the matchMedia listener below re-calls this on every OS change while
// preference is "system" as a harmless, idempotent safety net.
function syncWindowChrome(preference) {
  getCurrentWindow()
    .setTheme(preference === "system" ? null : preference)
    .catch((e) => console.error("setTheme failed:", e));
}

// Applying the preference to the DOM only ever needs a `data-theme`
// attribute for an explicit choice -- "system" removes it entirely and the
// CSS media query alone renders correctly, including on first paint before
// this script ever runs (see index.html's inline head script).
function applyThemePreference(preference) {
  if (preference === "system") {
    delete document.documentElement.dataset.theme;
  } else {
    document.documentElement.dataset.theme = preference;
  }
  syncWindowChrome(preference);
}

function setThemePreference(preference) {
  try {
    localStorage.setItem(THEME_KEY, preference);
  } catch (e) {}
  applyThemePreference(preference);
}

function initTheme() {
  const preference = getStoredThemePreference();
  els.themeSelect.value = preference;
  applyThemePreference(preference);

  els.themeSelect.addEventListener("change", () => {
    setThemePreference(els.themeSelect.value);
  });

  osDarkQuery.addEventListener("change", () => {
    if (getStoredThemePreference() === "system") syncWindowChrome("system");
  });
}

// ---- Notes (error/status) -------------------------------------------------

function showNote(message) {
  const note = document.createElement("div");
  note.className = "note";
  note.textContent = message;
  note.addEventListener("click", () => note.remove());
  els.noteRoot.appendChild(note);
  setTimeout(() => note.remove(), 8000);
}

// ---- Timestamps -----------------------------------------------------------

// Three shapes reach us as `ts` (the Rust regex has already stripped the
// brackets):
//   live  --actual-time : "2026-09-03 14:22:07"
//   file                : "78:12.500 -> 78:15.250"   (MM may exceed 59)
//   file  --actual-time : "2026-09-03 14:22:07.500 -> ..."
// A range yields its start. Returns seconds on a per-kind axis, or null.
function parseStamp(ts) {
  if (typeof ts !== "string") return null;
  const start = ts.split("->")[0].trim();

  const abs = start.match(/^(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2}):(\d{2})(?:\.(\d+))?$/);
  if (abs) {
    const [, y, mo, d, h, mi, s, frac] = abs;
    const ms = Date.UTC(+y, +mo - 1, +d, +h, +mi, +s, frac ? +frac.padEnd(3, "0").slice(0, 3) : 0);
    return { kind: "abs", seconds: ms / 1000 };
  }

  const rel = start.match(/^(\d+):(\d{1,2}(?:\.\d+)?)$/);
  if (rel) return { kind: "rel", seconds: +rel[1] * 60 + parseFloat(rel[2]) };

  return null;
}

function formatClock(seconds) {
  const total = Math.max(0, Math.round(seconds));
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  const mm = String(m).padStart(h > 0 ? 2 : 1, "0");
  return h > 0 ? `${h}:${mm}:${String(s).padStart(2, "0")}` : `${mm}:${String(s).padStart(2, "0")}`;
}

function formatDuration(seconds) {
  if (seconds >= 3600) {
    const h = Math.floor(seconds / 3600);
    const m = Math.round((seconds % 3600) / 60);
    return m ? `${h} h ${m} min` : `${h} h`;
  }
  if (seconds >= 60) {
    const m = Math.floor(seconds / 60);
    const s = Math.round(seconds % 60);
    return s ? `${m} min ${s} s` : `${m} min`;
  }
  return `${Math.round(seconds)} s`;
}

// ---- Chart scale (the signature control) ----------------------------------

// Pixels per second of elapsed time. One control drives the whole axis.
let pxPerSecond = 6;

function scaleFromSlider(value) {
  return 0.2 * Math.pow(150, value / 100); // 0.2 px/s → 30 px/s
}

function applyChartScale() {
  pxPerSecond = scaleFromSlider(Number(els.chartSpeed.value));

  let mode = "reading";
  let label = "reading";
  if (pxPerSecond < 1.2) {
    mode = "marks";
    label = "overview";
  } else if (pxPerSecond < 5) {
    mode = "compact";
    label = "compact";
  }

  for (const chart of [els.chartLive, els.chartFile]) {
    chart.dataset.scaleMode = mode;
    chart.style.setProperty("--chart-scale", String(pxPerSecond));
  }
  els.chartSpeedReadout.textContent = label;

  relayout(els.transcriptLive);
  relayout(els.transcriptFile);
}

els.chartSpeed.addEventListener("input", applyChartScale);

// ---- The trace ------------------------------------------------------------

// Nominal height a row occupies, subtracted from a gap so the axis measures
// the space *between* marks rather than double-counting the marks themselves.
function rowNominalPx(chart) {
  return chart.dataset.scaleMode === "marks" ? 6 : 26;
}

function relayout(list) {
  const chart = list.closest(".chart");
  const nominal = rowNominalPx(chart);
  let previous = null;

  for (const item of list.children) {
    const offset = Number(item.dataset.offset);
    if (!Number.isFinite(offset) || previous === null) {
      item.style.marginTop = "";
    } else {
      const gapSeconds = Math.min(Math.max(offset - previous, 0), 86400);
      const gapPx = Math.max(0, gapSeconds * pxPerSecond - nominal);
      item.style.marginTop = gapPx > 0.5 ? `${gapPx}px` : "";

      const note = item.querySelector(".gap-note");
      // A gap only worth naming once it reads as silence rather than a pause.
      if (gapSeconds >= 45 && gapPx >= 26) {
        if (note) {
          note.textContent = formatDuration(gapSeconds);
        } else {
          const el = document.createElement("span");
          el.className = "gap-note";
          el.textContent = formatDuration(gapSeconds);
          item.appendChild(el);
        }
      } else if (note) {
        note.remove();
      }
    }
    if (Number.isFinite(offset)) previous = offset;
  }
}

// Which reading the time gutter shows. Positions on the axis are always
// elapsed-proportional; this only changes the label.
function renderTimestamps() {
  const mode = els.timeMode.value;
  let sawClockless = false;

  for (const list of [els.transcriptLive, els.transcriptFile]) {
    for (const item of list.children) {
      const cell = item.querySelector(".trace-time");
      if (!cell) continue;
      const clock = item.dataset.clock;
      const offset = Number(item.dataset.offset);

      if (mode === "clock" && clock) {
        cell.textContent = clock;
      } else if (Number.isFinite(offset)) {
        cell.textContent = formatClock(offset);
        if (mode === "clock") sawClockless = true;
      } else {
        cell.textContent = item.dataset.rawTs || "";
      }
    }
  }

  // Only explain the fallback when it is actually happening.
  els.timeModeHint.hidden = !(mode === "clock" && sawClockless);
}

els.timeMode.addEventListener("change", renderTimestamps);

const sessionOrigin = { live: null, file: null };

// Single source of truth: an empty state is shown when the roll is actually
// empty, never tracked imperatively. It sits over the chart, so any drift
// between a flag and the DOM would hide real transcript lines behind it —
// which is exactly what happened when it was set from three call sites.
function refreshEmptyStates() {
  els.liveEmpty.hidden = els.transcriptLive.children.length > 0;
  els.fileEmpty.hidden = els.transcriptFile.children.length > 0;
}

function appendTranscriptLine(list, { ts, tag, text }) {
  const flow = list === els.transcriptFile ? "file" : "live";
  const parsed = parseStamp(ts);

  let offset = null;
  if (parsed) {
    const origin = sessionOrigin[flow];
    if (origin === null || origin.kind !== parsed.kind) {
      sessionOrigin[flow] = parsed;
      offset = 0;
    } else {
      offset = parsed.seconds - origin.seconds;
    }
  }

  const item = document.createElement("li");
  item.className = `trace trace-new ${tag === "MIC" ? "trace-mic" : "trace-sys"}`;
  if (offset !== null) item.dataset.offset = String(offset);
  if (tag) item.dataset.pen = tag;

  // Keep both readings on the element. The engine always runs with
  // --actual-time for live capture, so wall-clock is real data we hold rather
  // than derive -- discarding it in favour of an elapsed offset was a
  // regression against what the old UI showed. A transcribed file has no
  // clock time to offer, so those lines simply have no clock reading.
  if (parsed && parsed.kind === "abs") {
    item.dataset.clock = new Date(parsed.seconds * 1000).toISOString().slice(11, 19);
  }
  item.dataset.rawTs = ts ?? "";

  const time = document.createElement("span");
  time.className = "trace-time";

  const body = document.createElement("span");
  body.className = "trace-body";
  if (tag) {
    const source = document.createElement("span");
    source.className = "trace-source";
    source.textContent = tag;
    body.appendChild(source);
  }
  const textEl = document.createElement("span");
  textEl.className = "trace-text";
  textEl.textContent = text; // never innerHTML: transcript text is untrusted
  body.appendChild(textEl);

  item.append(time, body);
  list.appendChild(item);

  const chart = list.closest(".chart");
  refreshEmptyStates();
  renderTimestamps();
  relayout(list);
  applyFilters();
  chart.scrollTop = chart.scrollHeight;
}

function clearTranscript(list) {
  const flow = list === els.transcriptFile ? "file" : "live";
  list.innerHTML = "";
  sessionOrigin[flow] = null;
  refreshEmptyStates();
}

function appendDebugLine(line) {
  const el = document.createElement("div");
  el.textContent = line;
  els.debugLog.appendChild(el);
  els.debugLog.scrollTop = els.debugLog.scrollHeight;
}

// The engine log is append-only across sessions, so old scrollback ("Listening
// ...", "Capturing audio ...") keeps reading as live long after a session
// ended -- which is what makes the log look out of sync with the status.
// A boundary line, visibly the app speaking rather than the engine, says
// which run the lines above belong to.
function appendLogMarker(text) {
  const el = document.createElement("div");
  el.className = "debug-marker";
  const now = new Date().toTimeString().slice(0, 8);
  el.textContent = `── ${text} · ${now} ──`;
  els.debugLog.appendChild(el);
  els.debugLog.scrollTop = els.debugLog.scrollHeight;
}

// ---- Filtering and search -------------------------------------------------

function applyFilters() {
  const pen = els.penFilter.value;
  const query = els.chartSearch.value.trim().toLowerCase();
  let hits = 0;

  for (const list of [els.transcriptLive, els.transcriptFile]) {
    for (const item of list.children) {
      const penOk = pen === "all" || item.dataset.pen === pen;
      const textEl = item.querySelector(".trace-text");
      const matches = query !== "" && textEl.textContent.toLowerCase().includes(query);
      if (query !== "" && matches) hits += 1;

      item.hidden = !penOk || (query !== "" && !matches);
      item.classList.toggle("trace-hit", query !== "" && matches && penOk);
    }
    relayout(list);
  }

  if (query === "") {
    els.searchCount.hidden = true;
  } else {
    els.searchCount.hidden = false;
    els.searchCount.textContent = hits === 1 ? "1 line" : `${hits} lines`;
  }
}

els.penFilter.addEventListener("change", applyFilters);
els.chartSearch.addEventListener("input", applyFilters);

// ---- Mode switch ----------------------------------------------------------

function selectTab(name) {
  const liveActive = name === "live";
  els.tabLive.setAttribute("aria-selected", String(liveActive));
  els.tabFile.setAttribute("aria-selected", String(!liveActive));
  els.panelLive.hidden = !liveActive;
  els.panelFile.hidden = liveActive;
  els.chartLive.hidden = !liveActive;
  els.chartFile.hidden = liveActive;
}

els.tabLive.addEventListener("click", () => {
  if (!els.tabLive.disabled) selectTab("live");
});
els.tabFile.addEventListener("click", () => selectTab("file"));

// ---- Settings -------------------------------------------------------------

function syncMicPen() {
  const on = els.includeMicCheckbox.checked;
  els.micDeviceField.hidden = !on;
  els.penMic.dataset.armed = String(on);
  const state = els.penMic.querySelector(".pen-state");
  state.textContent = on ? state.dataset.on : state.dataset.off;
}

els.includeMicCheckbox.addEventListener("change", syncMicPen);

// Mirrors start_teams_transcription.bat's meeting_<timestamp>.txt naming --
// a bare filename (no directory) so the sidecar saves it next to wherever
// it's running from, same as the .bat's relative "%output_file%".
function timestampSuffix() {
  return new Date().toISOString().replace(/[-:]/g, "").replace("T", "_").slice(0, 15);
}
function defaultOutputFilename() {
  return `transcript_${timestampSuffix()}.txt`;
}
els.outputPathInput.value = defaultOutputFilename();

// Re-stamped on every session start (not just page load), so recording
// twice without touching the field -- or reusing a browsed path -- can
// never silently truncate the previous run's transcript. Strips a prior
// auto-stamp first so repeated starts append one fresh stamp, not several.
function withFreshTimestamp(pathStr) {
  const dot = pathStr.lastIndexOf(".");
  const base = dot === -1 ? pathStr : pathStr.slice(0, dot);
  const ext = dot === -1 ? "" : pathStr.slice(dot);
  return `${base.replace(/_\d{8}_\d{6}$/, "")}_${timestampSuffix()}${ext}`;
}

els.outputBrowseBtn.addEventListener("click", async () => {
  const path = await saveFileDialog({
    defaultPath: els.outputPathInput.value || defaultOutputFilename(),
    filters: [{ name: "Text", extensions: ["txt"] }],
  });
  if (typeof path === "string") els.outputPathInput.value = path;
});

// faster-whisper's supported language codes (openai/whisper's tokenizer
// LANGUAGES table) -- fixed by the model, not app config, so listed here
// rather than fetched from the sidecar.
const WHISPER_LANGUAGES = {
  en: "english", zh: "chinese", de: "german", es: "spanish", ru: "russian",
  ko: "korean", fr: "french", ja: "japanese", pt: "portuguese", tr: "turkish",
  pl: "polish", ca: "catalan", nl: "dutch", ar: "arabic", sv: "swedish",
  it: "italian", id: "indonesian", hi: "hindi", fi: "finnish", vi: "vietnamese",
  he: "hebrew", uk: "ukrainian", el: "greek", ms: "malay", cs: "czech",
  ro: "romanian", da: "danish", hu: "hungarian", ta: "tamil", no: "norwegian",
  th: "thai", ur: "urdu", hr: "croatian", bg: "bulgarian", lt: "lithuanian",
  la: "latin", mi: "maori", ml: "malayalam", cy: "welsh", sk: "slovak",
  te: "telugu", fa: "persian", lv: "latvian", bn: "bengali", sr: "serbian",
  az: "azerbaijani", sl: "slovenian", kn: "kannada", et: "estonian", mk: "macedonian",
  br: "breton", eu: "basque", is: "icelandic", hy: "armenian", ne: "nepali",
  mn: "mongolian", bs: "bosnian", kk: "kazakh", sq: "albanian", sw: "swahili",
  gl: "galician", mr: "marathi", pa: "punjabi", si: "sinhala", km: "khmer",
  sn: "shona", yo: "yoruba", so: "somali", af: "afrikaans", oc: "occitan",
  ka: "georgian", be: "belarusian", tg: "tajik", sd: "sindhi", gu: "gujarati",
  am: "amharic", yi: "yiddish", lo: "lao", uz: "uzbek", fo: "faroese",
  ht: "haitian creole", ps: "pashto", tk: "turkmen", nn: "nynorsk", mt: "maltese",
  sa: "sanskrit", lb: "luxembourgish", my: "myanmar", bo: "tibetan", tl: "tagalog",
  mg: "malagasy", as: "assamese", tt: "tatar", haw: "hawaiian", ln: "lingala",
  ha: "hausa", ba: "bashkir", jw: "javanese", su: "sundanese", yue: "cantonese",
};

function populateLanguageSelect() {
  els.languageSelect.innerHTML = "";
  const autoOpt = document.createElement("option");
  autoOpt.value = "";
  autoOpt.textContent = "Auto-detect";
  els.languageSelect.appendChild(autoOpt);
  const codes = Object.keys(WHISPER_LANGUAGES).sort((a, b) =>
    WHISPER_LANGUAGES[a].localeCompare(WHISPER_LANGUAGES[b])
  );
  for (const code of codes) {
    const opt = document.createElement("option");
    opt.value = code;
    opt.textContent = WHISPER_LANGUAGES[code][0].toUpperCase() + WHISPER_LANGUAGES[code].slice(1);
    els.languageSelect.appendChild(opt);
  }
}
populateLanguageSelect();

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

// ---- Live session state ---------------------------------------------------

// idle → loaded (invoke resolved, no output yet) → advancing (output arriving)
// → penlift (advancing expected, nothing arriving) → stopping → idle.
let liveState = "idle";
let currentFlow = null; // "live" | "file" | null
let sessionStartedAt = null;
let lastLineAt = null;
let sawFirstLine = false;
let stallTimer = null;
// Whether a live session is *supposed* to be running right now. Distinct from
// liveState, which is what the panel is displaying.
let sessionRunning = false;

// Plain product language: a control or status names what is happening, never
// the metaphor. The chart world lives in the visual system, not in vocabulary
// the user has to decode to press a button.
const STATE_LABEL = {
  idle: "Not recording",
  loaded: "Starting — waiting for the engine",
  listening: "Listening — no speech yet",
  advancing: "Recording",
  penlift: "Recording stalled — no output",
  stopping: "Stopping",
};

function renderRunState() {
  const shown = liveState === "penlift" ? "penlift" : liveState;
  els.runState.dataset.state = shown;
  els.runStateLabel.textContent = STATE_LABEL[shown] ?? shown;

  els.stopBtn.hidden = liveState === "idle";
  els.stopBtn.disabled = liveState === "stopping";
  els.startLiveBtn.hidden = liveState !== "idle";

  if (liveState === "penlift") {
    const silent = lastLineAt ? Math.round((Date.now() - lastLineAt) / 1000) : 0;
    els.runDetail.hidden = false;
    els.runDetail.textContent =
      `No transcript output for ${silent}s — the engine should produce a chunk every ${CHUNK_SECONDS}s. ` +
      `Check the engine log below; raising and lowering the pens restarts capture.`;
  } else {
    els.runDetail.hidden = true;
    els.runDetail.textContent = "";
  }

  const running = liveState !== "idle";
  els.runElapsed.hidden = !running;
  if (running && sessionStartedAt) {
    els.runElapsed.textContent = formatClock((Date.now() - sessionStartedAt) / 1000);
  }
}

function setLiveState(next) {
  liveState = next;
  if (next === "idle") {
    sessionStartedAt = null;
    lastLineAt = null;
    sawFirstLine = false;
  }
  renderRunState();
}

// The stall check: a frontend timer against the known chunk duration, not a
// new backend signal. Only meaningful once at least one chunk has arrived —
// before that the engine is still loading its model, which is not a stall.
function tickInstrument() {
  if (liveState === "idle") return;

  if (sawFirstLine && (liveState === "advancing" || liveState === "penlift")) {
    const overdue = Date.now() - lastLineAt > STALL_MS;
    const next = overdue ? "penlift" : "advancing";
    if (next !== liveState) {
      liveState = next;
    }
  }
  renderRunState();
}

stallTimer = setInterval(tickInstrument, 1000);

function markLineArrived() {
  lastLineAt = Date.now();
  sawFirstLine = true;
  // A chunk arriving while a session is supposed to be running is proof it is
  // alive, and outranks a stale display state. Gated on sessionRunning so
  // that buffered lines arriving *after* a deliberate stop cannot resurrect
  // the status to "Recording" -- the resync exists to correct display drift,
  // never to contradict the user's own stop.
  if (sessionRunning && liveState !== "advancing" && liveState !== "stopping") {
    if (sessionStartedAt === null) sessionStartedAt = Date.now();
    setLiveState("advancing");
  }
}

async function startLiveSession() {
  clearTranscript(els.transcriptLive);
  els.startLiveBtn.disabled = true;
  currentFlow = "live";
  sessionStartedAt = Date.now();
  lastLineAt = Date.now();
  sawFirstLine = false;
  const outputPath = withFreshTimestamp(els.outputPathInput.value.trim() || "transcript.txt");
  els.outputPathInput.value = outputPath;
  try {
    await invoke("start_live_session", {
      model: els.modelSelect.value,
      language: els.languageSelect.value || null,
      includeMic: els.includeMicCheckbox.checked,
      micDevice: els.includeMicCheckbox.checked ? Number(els.micDeviceSelect.value) : null,
      outputPath,
      audioDevice: els.audioDeviceInput.value.trim() !== "" ? Number(els.audioDeviceInput.value) : null,
    });
    sessionRunning = true;
    appendLogMarker("recording started");
    setLiveState("loaded");
  } catch (err) {
    sessionRunning = false;
    showNote(`Could not start live capture: ${err}`);
    setLiveState("idle");
  } finally {
    els.startLiveBtn.disabled = false;
  }
}

async function stopLiveSession() {
  sessionRunning = false;
  setLiveState("stopping");
  // "requested", not "stopped": whether the process actually died is what
  // openspec/changes/confirm-live-session-stop reports, and this marker must
  // not claim knowledge it does not have.
  appendLogMarker("stop requested");
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

// ---- File transcription ---------------------------------------------------

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
  els.fileState.hidden = !busy;
  els.fileState.dataset.state = busy ? "advancing" : "idle";
}

async function transcribeFile(filePath) {
  if (!hasSupportedExtension(filePath)) {
    showNote(`Unsupported file type: ${filePath}`);
    return;
  }
  selectTab("file");
  clearTranscript(els.transcriptFile);
  currentFlow = "file";
  setFileBusy(true);
  try {
    await invoke("start_file_transcription", {
      filePath,
      format: els.formatSelect.value,
      task: els.taskSelect.value,
      model: els.modelSelect.value,
      language: els.languageSelect.value || null,
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

// ---- Platform gate --------------------------------------------------------

async function applyPlatformGate() {
  // specs/desktop-gui "Graceful macOS degradation": live capture stays
  // disabled on macOS regardless of whether the sidecar supports
  // --coreaudio-tap, until add-macos-capture's hardware verification
  // (tasks.md section 5) is complete -- see tasks.md 5.8.
  const platform = await invoke("get_platform");
  if (platform === "macos") {
    els.tabLive.disabled = true;
    els.macosNotice.hidden = false;
    selectTab("file");
  }
}

// ---- Event wiring ---------------------------------------------------------

listen("transcript-line", (event) => {
  // Anything not explicitly a file run is a live run, for both the routing
  // and the state update -- they must agree, or a line can land on the live
  // chart without the panel ever leaving its idle state.
  const isFile = currentFlow === "file";
  if (!isFile) markLineArrived();
  appendTranscriptLine(isFile ? els.transcriptFile : els.transcriptLive, event.payload);
});

listen("sidecar-log", (event) => {
  // Engine chatter proves the process came up, so it advances the initial
  // "starting" state -- the engine reaches "Listening..." up to a full chunk
  // before the first transcript line, and leaving the status on "Starting"
  // that whole time reads as hung. It deliberately does NOT clear a stall:
  // once chunks have been flowing, only a real chunk proves recovery.
  if (currentFlow !== "file" && liveState === "loaded") setLiveState("listening");
  appendDebugLine(event.payload.line);
});

listen("sidecar-crashed", (event) => {
  sessionRunning = false;
  appendLogMarker("engine exited unexpectedly");
  setLiveState("idle");
  showNote(event.payload.message);
});

listen("file-transcription-complete", (event) => {
  setFileBusy(false);
  showNote(event.payload ? "Transcript saved." : "File transcription failed — see the engine log for details.");
});

initTheme();
setupDropZone();
applyPlatformGate();
populateMicDevices();
syncMicPen();
applyChartScale();
renderRunState();
