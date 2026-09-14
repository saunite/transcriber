#!/usr/bin/env python3
"""GUI behaviour tests (openspec/changes/add-automated-local-tests).

Loads the real src/index.html in headless Chromium with a fake
window.__TAURI__ (tests/fake_tauri.js), so no app build, audio or engine is
needed. Checks what the page sends (recorded invoke calls) and what it shows.

Setup: pip install -r requirements-dev.txt && python -m playwright install chromium
Run:   python tests/test_gui.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parent.parent
FAKE_BRIDGE = (Path(__file__).resolve().parent / "fake_tauri.js").read_text(encoding="utf-8")
REFUSAL = "A live session is still running. Stop it before transcribing a file."


def missing_commands(main_js: Path, main_rs: Path) -> list[str]:
    """Commands main.js invokes that generate_handler![...] does not register."""
    used = set(re.findall(r'invoke\(\s*"([A-Za-z0-9_]+)"', main_js.read_text(encoding="utf-8")))
    handler = re.search(r"generate_handler!\[(.*?)\]", main_rs.read_text(encoding="utf-8"), re.S)
    registered = {name.strip().split("::")[-1] for name in handler.group(1).split(",") if name.strip()}
    return sorted(used - registered)


def calls(page, cmd):
    return page.evaluate("cmd => __fake.calls.filter(c => c.cmd === cmd)", cmd)


def wait_for_calls(page, cmd, count):
    page.wait_for_function(
        "([cmd, n]) => __fake.calls.filter(c => c.cmd === cmd).length >= n", arg=[cmd, count]
    )


def open_page(browser, responses=None):
    page = browser.new_page()
    errors = []
    page.on("pageerror", lambda exc: errors.append(str(exc)))
    page.add_init_script(FAKE_BRIDGE)
    if responses:
        page.add_init_script(f"Object.assign(window.__fake.responses, {json.dumps(responses)});")
    page.goto((ROOT / "src" / "index.html").as_uri())
    wait_for_calls(page, "list_devices", 1)
    return page, errors


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


def test_live_start_stop(browser):
    page, errors = open_page(browser)
    sys_pen, mic_pen = page.locator(".pen-sys .pen-state"), page.locator(".pen-mic .pen-state")
    page.click("#start-live-btn")
    wait_for_calls(page, "start_live_session", 1)
    args = calls(page, "start_live_session")[0]["args"]
    assert args["micDevice"] is None, f"expected the system-default mic, got micDevice={args['micDevice']!r}"
    expect(sys_pen).to_have_text("Capturing")
    expect(mic_pen).to_have_text("Capturing")

    page.click("#stop-btn")
    wait_for_calls(page, "stop_live_session", 1)
    expect(sys_pen).to_have_text("Idle")
    expect(mic_pen).to_have_text("Idle")
    # The session controls once said "Start Recording". ("Drop recordings" on
    # the File tab is about audio files, not the action, so it is not checked.)
    labels = page.eval_on_selector_all("#start-live-btn, #stop-btn", "els => els.map(e => e.textContent)")
    assert not any(re.search(r"record", label, re.I) for label in labels), f"a control says 'Record': {labels}"
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


def test_refusal_shown(browser):
    page, errors = open_page(browser, {"start_file_transcription": {"reject": REFUSAL}})
    drop(page, "/media/one.mp4")
    wait_for_calls(page, "start_file_transcription", 1)
    expect(page.locator("#note-root")).to_contain_text(REFUSAL)
    return page, errors


def main() -> int:
    failures = 0

    def report(name, fn, *args):
        nonlocal failures
        try:
            result = fn(*args)
            if result:
                page, errors = result
                page.close()
                assert not errors, f"script error on the page: {errors}"
            print(f"PASS  {name}")
        except Exception as exc:  # report every scenario, not just the first failure
            failures += 1
            print(f"FAIL  {name}: " + "\n      ".join(str(exc).splitlines()[:4]))

    report("command drift", test_command_drift)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        report("page loads", test_page_loads, browser)
        report("live start/stop", test_live_start_stop, browser)
        report("file queue", test_file_queue, browser)
        report("unsupported file", test_unsupported_file, browser)
        report("refusal shown", test_refusal_shown, browser)
        browser.close()
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
