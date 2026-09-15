#!/usr/bin/env python3
"""GUI behaviour tests (openspec/changes/add-automated-local-tests).

Loads the real src/index.html in headless Chromium with a fake
window.__TAURI__ (tests/fake_tauri.js), so no app build, audio or engine is
needed. Checks what the page sends (recorded invoke calls) and what it shows.

Setup: pip install -r requirements-dev.txt && python -m playwright install chromium
Run:   python tests/test_gui.py
"""
from __future__ import annotations

import base64
import hashlib
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parent.parent
FAKE_BRIDGE = (Path(__file__).resolve().parent / "fake_tauri.js").read_text(encoding="utf-8")
SRC_DIR = ROOT / "src"
APP_ORIGIN = "http://tauri.localhost"  # the origin Tauri serves the app from on Windows
CONTENT_TYPES = {".html": "text/html", ".js": "application/javascript", ".css": "text/css"}
# Record every policy violation so a scenario can fail on it like a script error.
RECORD_CSP_VIOLATIONS = """
window.__cspViolations = [];
document.addEventListener('securitypolicyviolation', (e) =>
  window.__cspViolations.push(`${e.violatedDirective} ${e.blockedURI}`));
"""
REFUSAL = "A live session is still running. Stop it before transcribing a file."
LIVE_FUNCTIONS = ("transcribe_live_simple", "_run_dual_capture")
MODEL_LOADING = ("Loading base model from /m on cpu with int8...", "✓ Model loaded successfully")


def missing_commands(main_js: Path, main_rs: Path) -> list[str]:
    """Commands main.js invokes that generate_handler![...] does not register."""
    used = set(re.findall(r'invoke\(\s*"([A-Za-z0-9_]+)"', main_js.read_text(encoding="utf-8")))
    handler = re.search(r"generate_handler!\[(.*?)\]", main_rs.read_text(encoding="utf-8"), re.S)
    registered = {name.strip().split("::")[-1] for name in handler.group(1).split(",") if name.strip()}
    return sorted(used - registered)


def functions_missing_listening(transcriber_py: Path) -> list[str]:
    """Live capture functions whose body never prints the "Listening..." line
    the GUI waits for (openspec/changes/fix-capturing-shown-before-listening)."""
    src = transcriber_py.read_text(encoding="utf-8")
    missing = []
    for name in LIVE_FUNCTIONS:
        body = re.search(rf"(?ms)^def {name}\(.*?(?=^def |\Z)", src)
        code = "\n".join(l for l in body.group(0).splitlines() if not l.strip().startswith("#")) if body else ""
        if "Listening..." not in code:  # comments don't count: only a real print keeps the GUI moving
            missing.append(name)
    return missing


def csp_problems(tauri_conf: Path) -> list[str]:
    """What is wrong with the app window's Content Security Policy
    (openspec/changes/harden-webview-csp-and-tls). Chromium here runs without
    Tauri, so this pins the configured policy rather than proving enforcement."""
    csp = json.loads(tauri_conf.read_text(encoding="utf-8")).get("app", {}).get("security", {}).get("csp")
    if not isinstance(csp, str) or not csp.strip():
        return [f"no CSP is set (csp = {csp!r})"]
    problems = []
    if "default-src 'self'" not in csp:
        problems.append("missing default-src 'self'")
    problems += [f"allows {bad}" for bad in ("'unsafe-inline'", "'unsafe-eval'") if bad in csp]
    return problems


class _InlineScripts(HTMLParser):
    """Collects the text of every inline <script> element."""

    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.scripts, self._current = [], None

    def handle_starttag(self, tag, attrs):
        if tag == "script":
            self._current = []

    def handle_data(self, data):
        if self._current is not None:
            self._current.append(data)

    def handle_endtag(self, tag):
        if tag == "script" and self._current is not None:
            self.scripts.append("".join(self._current))
            self._current = None


def effective_csp(tauri_conf: Path, html: Path) -> str:
    """The policy the app window actually enforces for `html`, built the way
    Tauri 2 builds it (openspec/changes/test-gui-under-app-csp):
    tauri-codegen 2.6.3 inject_script_hashes hashes each non-empty inline
    <script> after normalize_script_for_csp (CR/CRLF -> LF), and tauri 2.11.5
    replace_csp_nonce adds 'self' plus those hashes to script-src."""
    csp = json.loads(tauri_conf.read_text(encoding="utf-8"))["app"]["security"]["csp"]
    parser = _InlineScripts()
    parser.feed(html.read_text(encoding="utf-8"))
    hashes = []
    for script in parser.scripts:
        if script:  # `script:not(:empty)`
            normalized = script.replace("\r\n", "\n").replace("\r", "\n")
            digest = hashlib.sha256(normalized.encode("utf-8")).digest()
            hashes.append(f"'sha256-{base64.b64encode(digest).decode()}'")
    if not hashes:
        return csp
    directives = [d.strip() for d in csp.split(";") if d.strip()]
    for i, directive in enumerate(directives):
        if directive.split()[0] == "script-src":
            sources = directive.split()[1:]
            sources = ["'self'"] * ("'self'" not in sources) + sources
            directives[i] = " ".join(["script-src", *sources, *hashes])
            break
    else:
        directives.append(" ".join(["script-src", "'self'", *hashes]))
    return "; ".join(directives)


def calls(page, cmd):
    return page.evaluate("cmd => __fake.calls.filter(c => c.cmd === cmd)", cmd)


def wait_for_calls(page, cmd, count):
    page.wait_for_function(
        "([cmd, n]) => __fake.calls.filter(c => c.cmd === cmd).length >= n", arg=[cmd, count]
    )


def serve_app(route):
    """Serve src/ as the app window sees it: from its own origin, under the
    policy Tauri enforces (openspec/changes/test-gui-under-app-csp)."""
    path = route.request.url.split("?", 1)[0][len(APP_ORIGIN):].lstrip("/") or "index.html"
    file = (SRC_DIR / path).resolve()
    if not file.is_relative_to(SRC_DIR.resolve()) or not file.is_file() or file.suffix not in CONTENT_TYPES:
        route.fulfill(status=404, body="")
        return
    headers = {"Content-Type": CONTENT_TYPES[file.suffix]}
    if file.suffix == ".html":
        headers["Content-Security-Policy"] = effective_csp(ROOT / "src-tauri" / "tauri.conf.json", file)
    route.fulfill(status=200, body=file.read_bytes(), headers=headers)


def open_page(browser, responses=None):
    page = browser.new_page()
    errors = []
    page.on("pageerror", lambda exc: errors.append(str(exc)))
    page.add_init_script(RECORD_CSP_VIOLATIONS)
    page.add_init_script(FAKE_BRIDGE)
    if responses:
        page.add_init_script(f"Object.assign(window.__fake.responses, {json.dumps(responses)});")
    page.route(f"{APP_ORIGIN}/**", serve_app)
    page.goto(f"{APP_ORIGIN}/index.html")
    wait_for_calls(page, "list_devices", 1)
    return page, errors


def log(page, line):
    page.evaluate("line => __fake.emit('sidecar-log', {line})", line)


def drop(page, *paths):
    page.evaluate("paths => __fake.emit('tauri://drag-drop', {paths})", list(paths))


def queue_states(page):
    return page.eval_on_selector_all("#file-queue .file-queue-item", "els => els.map(e => e.dataset.state)")


def test_page_loads(browser):
    page, errors = open_page(browser)
    assert calls(page, "get_platform"), "get_platform was not requested"
    assert calls(page, "list_devices"), "list_devices was not requested"
    return page, errors


def test_command_drift():
    missing = missing_commands(ROOT / "src" / "main.js", ROOT / "src-tauri" / "src" / "main.rs")
    assert not missing, f"main.js invokes commands the app does not register: {', '.join(missing)}"


def test_listening_wording():
    missing = functions_missing_listening(ROOT / "transcriber.py")
    assert not missing, f"live capture functions no longer print 'Listening...': {', '.join(missing)}"


def test_csp():
    problems = csp_problems(ROOT / "src-tauri" / "tauri.conf.json")
    assert not problems, "tauri.conf.json CSP: " + "; ".join(problems)


def test_live_start_stop(browser):
    page, errors = open_page(browser)
    pens = page.locator(".pen-sys .pen-state, .pen-mic .pen-state")
    status = page.locator("#run-state-label")
    page.click("#start-live-btn")
    wait_for_calls(page, "start_live_session", 1)
    args = calls(page, "start_live_session")[0]["args"]
    assert args["micDevice"] is None, f"expected the system-default mic, got micDevice={args['micDevice']!r}"
    expect(status).to_have_text("Starting — waiting for the engine")
    expect(pens).to_have_text(["Idle", "Idle"])

    # Model loading is engine output, but nothing is being captured yet.
    for line in MODEL_LOADING:
        log(page, line)
    page.wait_for_timeout(100)
    expect(status).to_have_text("Starting — waiting for the engine")
    expect(pens).to_have_text(["Idle", "Idle"])

    log(page, "Listening... (Ctrl+C to stop)")
    expect(pens).to_have_text(["Capturing", "Capturing"])
    expect(status).to_have_text("Listening — no speech yet")

    page.click("#stop-btn")
    wait_for_calls(page, "stop_live_session", 1)
    expect(pens).to_have_text(["Idle", "Idle"])
    # The session controls once said "Start Recording". ("Drop recordings" on
    # the File tab is about audio files, not the action, so it is not checked.)
    labels = page.eval_on_selector_all("#start-live-btn, #stop-btn", "els => els.map(e => e.textContent)")
    assert not any(re.search(r"record", label, re.I) for label in labels), f"a control says 'Record': {labels}"
    return page, errors


def test_exit_before_listening(browser):
    page, errors = open_page(browser)
    # Record every text the pens ever show, so a brief "Capturing" can't slip by.
    page.evaluate("""() => {
        window.__penTexts = [];
        const record = () => document.querySelectorAll('.pen-state').forEach(e => __penTexts.push(e.textContent));
        new MutationObserver(record).observe(document.body, {subtree: true, childList: true, characterData: true});
    }""")
    page.click("#start-live-btn")
    wait_for_calls(page, "start_live_session", 1)
    for line in MODEL_LOADING:
        log(page, line)
    page.evaluate("__fake.emit('sidecar-crashed', {message: 'No microphone found.'})")
    expect(page.locator("#note-root")).to_contain_text("No microphone found.")
    expect(page.locator(".pen-sys .pen-state, .pen-mic .pen-state")).to_have_text(["Idle", "Idle"])
    seen = page.evaluate("window.__penTexts")
    assert "Capturing" not in seen, f"a pen showed Capturing before the engine was listening: {seen}"
    return page, errors


def test_file_queue(browser):
    page, errors = open_page(browser)
    drop(page, "/media/one.mp4", "/media/two.wav", "/media/three.ogg")
    wait_for_calls(page, "start_file_transcription", 1)
    page.wait_for_timeout(200)  # give a wrongly parallel queue time to show itself
    started = calls(page, "start_file_transcription")
    assert len(started) == 1, f"expected one file transcription at a time, got {len(started)}"
    assert started[0]["args"]["filePath"] == "/media/one.mp4"
    assert queue_states(page) == ["transcribing", "waiting", "waiting"], queue_states(page)

    page.evaluate("__fake.emit('file-transcription-complete', true)")
    wait_for_calls(page, "start_file_transcription", 2)
    assert calls(page, "start_file_transcription")[1]["args"]["filePath"] == "/media/two.wav"

    page.evaluate("__fake.emit('file-transcription-complete', false)")
    wait_for_calls(page, "start_file_transcription", 3)
    assert calls(page, "start_file_transcription")[2]["args"]["filePath"] == "/media/three.ogg"
    assert queue_states(page) == ["done", "failed", "transcribing"], queue_states(page)
    return page, errors


def test_unsupported_file(browser):
    page, errors = open_page(browser)
    drop(page, "/media/notes.docx")
    expect(page.locator("#note-root")).to_contain_text("Unsupported file type")
    assert calls(page, "start_file_transcription") == [], "an unsupported file reached the engine"
    return page, errors


def test_injected_script_refused(browser):
    """Script that isn't the app's own must not run in the window: an inline
    handler added after load, and a string handed to setTimeout. Checked through
    page state, because without the policy both do run
    (openspec/changes/test-gui-under-app-csp)."""
    page, errors = open_page(browser)
    page.evaluate("""() => {
        window.__probe = 0;
        document.body.insertAdjacentHTML('beforeend', '<img id="csp-probe" src="/no-such-file" onerror="window.__probe = 1">');
        window.__evalran = 0;
        setTimeout("window.__evalran = 1", 0);
    }""")
    page.wait_for_timeout(300)
    state = page.evaluate("({probe: window.__probe, evalran: window.__evalran, violations: window.__cspViolations})")
    assert state["probe"] == 0, "an injected inline event handler ran"
    assert state["evalran"] == 0, "string-evaluated code ran"
    violations = " | ".join(state["violations"])
    assert "script-src-attr" in violations and "eval" in violations, f"expected inline-handler and eval violations, got {state['violations']}"
    page.evaluate("window.__cspViolations = []; document.getElementById('csp-probe').remove()")  # expected, not a failure
    return page, errors


def test_refusal_shown(browser):
    page, errors = open_page(browser, {"start_file_transcription": {"reject": REFUSAL}})
    drop(page, "/media/one.mp4")
    wait_for_calls(page, "start_file_transcription", 1)
    expect(page.locator("#note-root")).to_contain_text(REFUSAL)
    return page, errors


def test_chart_search_count(browser):
    """The count is the matching lines the user can see: the shown chart, after
    the Show filter (openspec/changes/fix-chart-search-count)."""
    page, errors = open_page(browser)
    line = "(line) => __fake.emit('transcript-line', line)"
    count = page.locator("#search-count")
    page.evaluate(line, {"ts": "2026-09-03 14:22:07", "tag": "SYS", "text": "the budget is fine"})
    page.evaluate(line, {"ts": "2026-09-03 14:22:09", "tag": "MIC", "text": "which budget?"})

    page.select_option("#pen-filter", "SYS")
    page.fill("#chart-search", "budget")
    expect(count).to_have_text("1 line")
    expect(page.locator("#transcript-live .trace-hit")).to_have_count(1)

    # A file run's line lands on the file chart, which is then shown.
    page.select_option("#pen-filter", "all")
    drop(page, "/media/one.mp4")
    wait_for_calls(page, "start_file_transcription", 1)
    page.evaluate(line, {"ts": "00:01.000 -> 00:03.000", "tag": None, "text": "quarterly budget review"})
    expect(page.locator("#chart-file")).to_be_visible()
    expect(count).to_have_text("1 line")

    page.fill("#chart-search", "quarterly")
    page.click("#tab-live")
    expect(count).to_have_text("0 lines")
    page.click("#tab-file")
    expect(count).to_have_text("1 line")

    page.fill("#chart-search", "")
    expect(count).to_be_hidden()
    return page, errors


def test_model_folder(browser):
    """The Model field: bundled by default, a chosen folder sent to both
    commands and remembered, reset, cancel, and the shell's refusal shown
    (openspec/changes/choose-model-folder)."""
    refusal = "the model folder /models/gone has no model.bin. Choose a faster-whisper model folder under Model, or pick Bundled (base)."
    page, errors = open_page(browser)
    select = page.locator("#model-select")
    shown = lambda: page.eval_on_selector("#model-select", "s => s.selectedOptions[0].textContent")

    def start_live(n):
        page.click("#start-live-btn")
        wait_for_calls(page, "start_live_session", n)
        model_dir = calls(page, "start_live_session")[n - 1]["args"]["modelDir"]
        page.click("#stop-btn")
        wait_for_calls(page, "stop_live_session", n)
        return model_dir

    # Default: the bundled model, sent as no folder.
    expect(select).to_have_value("")
    assert shown() == "Bundled (base)", shown()
    assert start_live(1) is None

    # Pick: the folder picker's answer is shown and sent to both commands.
    page.evaluate("__fake.dialogOpen = '/models/small'")
    select.select_option("choose-folder")
    expect(select).to_have_value("/models/small")
    assert shown() == "small", shown()
    assert start_live(2) == "/models/small"
    drop(page, "/media/one.mp4")
    wait_for_calls(page, "start_file_transcription", 1)
    assert calls(page, "start_file_transcription")[0]["args"]["modelDir"] == "/models/small"
    page.evaluate("__fake.emit('file-transcription-complete', true)")

    # Cancel: a dismissed picker keeps the current choice.
    page.evaluate("__fake.dialogOpen = null")
    select.select_option("choose-folder")
    expect(select).to_have_value("/models/small")

    # Remember: a reload still shows and sends the folder.
    page.reload()
    wait_for_calls(page, "list_devices", 1)
    expect(select).to_have_value("/models/small")
    assert start_live(1) == "/models/small"

    # Keyboard: stepping onto "Choose folder…" with arrows never opens the picker.
    page.evaluate("__fake.dialogOpen = '/should/not/open'; __fake.dialogOpens = 0")
    select.focus()
    page.keyboard.press("End")
    page.keyboard.press("ArrowDown")
    page.wait_for_timeout(200)
    assert page.evaluate("__fake.dialogOpens") == 0, "arrow keys opened the folder picker"
    expect(select).not_to_have_value("choose-folder")

    # A Hugging Face cache snapshot is named after its model, not its hash.
    page.evaluate("__fake.dialogOpen = '/home/me/.cache/huggingface/hub/models--Systran--faster-whisper-small/snapshots/536b0662742c02347bc0e980a01041f333bce120'")
    select.select_option("choose-folder")
    expect(select).to_have_value(re.compile("snapshots"))
    assert shown() == "Systran--faster-whisper-small", shown()

    # Reset: back to the bundled model, sent as no folder.
    select.select_option("")
    assert start_live(2) is None
    page.close()
    assert not errors, f"script error on the page: {errors}"

    # Refusal: the shell's message reaches the user.
    page, errors = open_page(browser, {"start_live_session": {"reject": refusal}})
    page.click("#start-live-btn")
    expect(page.locator("#note-root")).to_contain_text(refusal)
    return page, errors


def test_update_check(browser):
    """Each answer of check_for_update shows its result next to the button, and
    nothing checks by itself (openspec/changes/add-manual-update-check)."""
    cases = [
        ({"state": "available", "version": "0.2.0"}, "0.2.0 is available"),
        ({"state": "up_to_date", "version": "0.1.0"}, "You're up to date (0.1.0)"),
        ({"state": "no_release"}, "No releases published yet"),
        ({"state": "unavailable"}, "Couldn't check for updates"),
        ({"reject": "boom"}, "Couldn't check for updates"),
    ]
    for response, text in cases:
        page, errors = open_page(browser, {"check_for_update": response})
        page.wait_for_timeout(200)
        assert calls(page, "check_for_update") == [], "the page checked for updates without a click"
        page.focus("#update-check-btn")
        page.keyboard.press("Enter")
        expect(page.locator("#update-result")).to_contain_text(text)
        open_btn = page.locator("#update-open-btn")
        if response.get("state") == "available":
            # The download page becomes the one action, and keeps keyboard focus.
            expect(page.locator("#update-check-btn")).to_be_hidden()
            expect(open_btn).to_be_focused()
            page.keyboard.press("Enter")
            wait_for_calls(page, "open_releases_page", 1)
        else:
            expect(page.locator("#update-check-btn")).to_be_enabled()
            expect(page.locator("#update-check-btn")).to_be_focused()
            expect(open_btn).to_be_hidden()
        if response is not cases[-1][0]:  # the last page goes back to report()
            violations = page.evaluate("window.__cspViolations")
            page.close()
            assert not errors and not violations, f"{response}: errors {errors}, CSP {violations}"
    return page, errors


def main() -> int:
    failures = 0

    def report(name, fn, *args):
        nonlocal failures
        try:
            result = fn(*args)
            if result:
                page, errors = result
                violations = page.evaluate("window.__cspViolations")
                page.close()
                assert not errors, f"script error on the page: {errors}"
                assert not violations, f"content security policy violation: {violations}"
            print(f"PASS  {name}")
        except Exception as exc:  # report every scenario, not just the first failure
            failures += 1
            print(f"FAIL  {name}: " + "\n      ".join(str(exc).splitlines()[:4]))

    report("command drift", test_command_drift)
    report("listening wording", test_listening_wording)
    report("content security policy", test_csp)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        report("page loads", test_page_loads, browser)
        report("live start/stop", test_live_start_stop, browser)
        report("exit before listening", test_exit_before_listening, browser)
        report("file queue", test_file_queue, browser)
        report("unsupported file", test_unsupported_file, browser)
        report("refusal shown", test_refusal_shown, browser)
        report("injected script refused", test_injected_script_refused, browser)
        report("update check", test_update_check, browser)
        report("chart search count", test_chart_search_count, browser)
        report("model folder", test_model_folder, browser)
        browser.close()
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
