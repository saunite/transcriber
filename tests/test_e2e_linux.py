#!/usr/bin/env python3
"""End-to-end tests of the built desktop app on Linux (openspec/changes/add-e2e-gui-tests-linux).

Builds the debug app and drives its real window through tauri-driver and
WebKitWebDriver, so the page, the Tauri commands and plugins, and the network
are all real:

- update check online: a real verdict, never "Couldn't check" (skipped when
  GitHub is unreachable);
- download page: the OS URL opener gets exactly the releases URL (a recording
  xdg-open stands in for the browser);
- no request at startup: strace sees no IPv4/IPv6 connect from any process;
- model folder (openspec/changes/choose-model-folder): a stored choice survives
  a restart, a folder without model.bin is refused before any live engine
  starts, and a chosen folder is what the engine loads (the folder dialog
  itself can't be driven, so the choice is stored the way the page stores it);
- offline (re-run inside `unshare -rn`): the update check says it couldn't
  check, the download page still opens, and the engine transcribes the speech
  sample with the staged sidecar.

Needs a graphical session, `cargo install tauri-driver --locked`, the
distribution's WebKitWebDriver, strace, unshare and ip. Skips, naming what is
missing, when any of them are absent. Windows open while it runs.

Run:  python tests/test_e2e_linux.py
"""
from __future__ import annotations

import json
import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC_TAURI = ROOT / "src-tauri"
APP = SRC_TAURI / "target" / "debug" / "transcriber-gui"
SIDECAR = SRC_TAURI / "binaries" / "transcriber-sidecar-x86_64-unknown-linux-gnu"
RELEASES_URL = "https://github.com/saunite/transcriber/releases/latest"
UP_TO_DATE, AVAILABLE, NO_RELEASE = "You're up to date", "is available", "No releases published yet"
COULD_NOT_CHECK = "Couldn't check for updates"
PORT = 4444
TIMEOUT = 60
SCENARIOS = ["update check online", "download page", "no request at startup",
             "model folder remembered", "model folder refused", "model folder used",
             "update check offline", "download page offline", "engine offline"]


class Skip(Exception):
    pass


def tool(name):
    # cargo installs into ~/.cargo/bin, which is not always on PATH.
    return shutil.which(name) or shutil.which(name, path=str(Path.home() / ".cargo" / "bin"))


def missing_piece():
    """The first thing this machine lacks to run the suite, with how to fix it."""
    if not sys.platform.startswith("linux"):
        return "not Linux (tauri-driver's Linux backend is WebKitWebDriver)"
    if not (os.environ.get("WAYLAND_DISPLAY") or os.environ.get("DISPLAY")):
        return "no graphical display: run from a desktop session (WAYLAND_DISPLAY or DISPLAY)"
    hints = {
        "tauri-driver": "cargo install tauri-driver --locked",
        "WebKitWebDriver": "install the distribution's WebKitGTK WebDriver package (Fedora: webkitgtk6.0, Debian/Ubuntu: webkit2gtk-driver)",
        "strace": "install strace",
        "unshare": "install util-linux",
        "ip": "install iproute2",
    }
    for name, hint in hints.items():
        if not tool(name):
            return f"{name} not found: {hint}"
    if not SIDECAR.is_file():
        return f"no staged sidecar at {SIDECAR}: build it with build_portable.py or the README's sidecar steps"
    return None


# ---- A minimal W3C WebDriver client ------------------------------------------

class App:
    """One tauri-driver + app process tree and its WebDriver session."""

    def __init__(self, env):
        self.proc = subprocess.Popen([tool("tauri-driver"), "--port", str(PORT)], env=env,
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                     start_new_session=True)
        try:
            self._wait(lambda: self._call("GET", "/status"), "tauri-driver to start")
            caps = {"capabilities": {"alwaysMatch": {"tauri:options": {"application": str(APP)}}}}
            self.session = self._call("POST", "/session", caps)["sessionId"]
        except BaseException:
            self.close()
            raise

    def _call(self, method, path, body=None):
        data = None if body is None else json.dumps(body).encode()
        req = urllib.request.Request(f"http://127.0.0.1:{PORT}{path}", data=data, method=method,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=TIMEOUT) as response:
            return json.load(response)["value"]

    @staticmethod
    def _wait(probe, what):
        deadline = time.monotonic() + TIMEOUT
        while True:
            try:
                result = probe()
                if result:
                    return result
            except OSError:
                pass
            if time.monotonic() > deadline:
                raise AssertionError(f"timed out waiting for {what}")
            time.sleep(0.2)

    def _element(self, css):
        found = self._call("POST", f"/session/{self.session}/element", {"using": "css selector", "value": css})
        return next(iter(found.values()))

    def click(self, css):
        # WebKitWebDriver answers every native input command (element click,
        # send keys, actions) with "unsupported operation" here
        # (tauri-apps/tauri#6541), so the real button is clicked from script:
        # its handler, the Tauri command and plugins still run for real.
        self._element(css)  # fail with WebDriver's "no such element" if absent
        outcome = self.run_async(f"const el = document.querySelector({json.dumps(css)}); el.click(); done('ok');")
        assert outcome == "ok", f"clicking {css} failed: {outcome}"

    def text(self, css):
        return self._call("GET", f"/session/{self.session}/element/{self._element(css)}/text")

    def displayed(self, css):
        return self._call("GET", f"/session/{self.session}/element/{self._element(css)}/displayed")

    def wait_text(self, css):
        return self._wait(lambda: self.text(css), f"text in {css}")

    def run_async(self, script):
        """Runs script in the page; it calls done(value) when finished."""
        body = {"script": f"const done = arguments[arguments.length - 1]; {script}", "args": []}
        try:
            return self._call("POST", f"/session/{self.session}/execute/async", body)
        except TimeoutError:
            raise AssertionError(f"page script never finished within {TIMEOUT}s (a command that never answers?): {script}")

    def close(self):
        try:
            if getattr(self, "session", None):
                self._call("DELETE", f"/session/{self.session}")
        except OSError:
            pass
        finally:
            kill_group(self.proc)


def kill_group(proc):
    try:
        os.killpg(proc.pid, signal.SIGTERM)
        proc.wait(timeout=10)
    except ProcessLookupError:
        pass
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGKILL)
        proc.wait()


# ---- Environment for the app ---------------------------------------------------

def app_env(workdir):
    """PATH starts with a recording xdg-open, so opening a URL writes it to a
    file instead of launching a browser (the opener tries xdg-open first)."""
    shim_dir = workdir / "bin"
    shim_dir.mkdir(exist_ok=True)
    log = workdir / "xdg-open.log"
    shim = shim_dir / "xdg-open"
    shim.write_text(f'#!/bin/sh\nprintf "%s\\n" "$*" >> "{log}"\n', encoding="utf-8")
    shim.chmod(0o755)
    # Its own data directory too, so the app's WebKit storage (the theme, the
    # chosen model folder) never touches the user's real app data
    # (openspec/changes/choose-model-folder).
    env = {**os.environ, "PATH": f"{shim_dir}{os.pathsep}{os.environ.get('PATH', '')}",
           "XDG_DATA_HOME": str(workdir / "data")}
    return env, log


def assert_opened_releases(log):
    App._wait(lambda: log.is_file() and log.read_text(encoding="utf-8").strip(), "the URL opener to be called")
    opened = log.read_text(encoding="utf-8").splitlines()
    assert opened == [RELEASES_URL], f"URL opener got {opened}, expected [{RELEASES_URL!r}]"


# ---- Scenarios -------------------------------------------------------------------

def github_reachable():
    try:
        socket.create_connection(("api.github.com", 443), timeout=5).close()
        return True
    except OSError:
        return False


def check_for_updates(app):
    app.click("#update-check-btn")
    return app.wait_text("#update-result")


def test_update_check_online(workdir):
    if not github_reachable():
        raise Skip("no route to api.github.com:443")
    env, log = app_env(workdir)
    app = App(env)
    try:
        result = check_for_updates(app)
        assert COULD_NOT_CHECK not in result, f"the real check failed online: {result!r}"
        assert any(verdict in result for verdict in (UP_TO_DATE, AVAILABLE, NO_RELEASE)), f"unexpected result {result!r}"
        if app.displayed("#update-open-btn"):
            app.click("#update-open-btn")
            assert_opened_releases(log)
        return result
    finally:
        app.close()


def test_update_check_offline(workdir):
    app = App(app_env(workdir)[0])
    try:
        result = check_for_updates(app)
        assert COULD_NOT_CHECK in result, f"expected {COULD_NOT_CHECK!r} with no network, got {result!r}"
        return result
    finally:
        app.close()


def test_download_page(workdir):
    """The real command, plugin and opener, called the way the page calls them."""
    env, log = app_env(workdir)
    app = App(env)
    try:
        outcome = app.run_async("window.__TAURI__.core.invoke('open_releases_page').then(() => done('ok'), (e) => done('error: ' + e));")
        assert outcome == "ok", f"open_releases_page failed: {outcome}"
        assert_opened_releases(log)
    finally:
        app.close()


def test_no_request_at_startup(workdir):
    """The app is up once its page has asked for the device list, which spawns
    the sidecar. WebDriver is not used here: it opens loopback connections."""
    trace = workdir / "startup.strace"
    proc = subprocess.Popen([tool("strace"), "-f", "-qq", "-e", "trace=connect,execve", "-o", str(trace), str(APP)],
                            env=app_env(workdir)[0], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                            start_new_session=True)
    try:
        App._wait(lambda: trace.is_file() and "--list-devices-json" in trace.read_text(errors="replace"),
                  "the page to load and list audio devices")
        time.sleep(3)
    finally:
        kill_group(proc)
    connects = [line for line in trace.read_text(errors="replace").splitlines()
                if re.search(r"connect\(.*sa_family=AF_INET6?\b", line)]
    assert not connects, "network connection attempted at startup:\n" + "\n".join(connects[:5])


# The chosen model folder (openspec/changes/choose-model-folder). The native
# folder dialog can't be driven, so the choice is stored the way the page
# stores it, then the page re-renders from it.
MODEL_DIR_KEY = "transcriber-model-dir"
BUNDLED_MODEL = SRC_TAURI / "resources" / "model"


def store_model_dir(app, folder):
    value = json.dumps(str(folder)) if folder else "null"
    app.run_async(f"if ({value}) localStorage.setItem('{MODEL_DIR_KEY}', {value}); "
                  f"else localStorage.removeItem('{MODEL_DIR_KEY}'); renderModelSelect(); done('ok');")


def shown_model(app):
    return app.run_async("const s = document.getElementById('model-select'); done([s.value, s.selectedOptions[0]?.textContent ?? '']);")


def model_folder(workdir, name, with_model):
    """A model folder: symlinks to the bundled model's files, or empty."""
    folder = workdir / name
    folder.mkdir()
    if with_model:
        for file in BUNDLED_MODEL.iterdir():
            (folder / file.name).symlink_to(file)
    return folder


def silent_wav(path):
    import wave
    with wave.open(str(path), "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(16000)
        out.writeframes(b"\0\0" * 16000)
    return path


def debug_log(app):
    return app.run_async("done(document.getElementById('debug-log').textContent);")


def test_model_folder_remembered(workdir):
    env = app_env(workdir)[0]
    folder = model_folder(workdir, "faster-whisper-e2e", with_model=True)
    app = App(env)
    try:
        store_model_dir(app, folder)
        # WebKit writes localStorage to disk about half a second later; closing
        # the process group before that would lose it, which is the test's doing,
        # not the app's.
        needle = str(folder).encode("utf-16-le")
        App._wait(lambda: any(needle in f.read_bytes() or str(folder).encode() in f.read_bytes()
                              for f in (workdir / "data").rglob("*.localstorage*") if f.is_file()),
                  "the choice to reach the app's storage on disk")
    finally:
        app.close()
    app = App(env)  # same data directory, fresh process
    try:
        value, label = App._wait(lambda: (lambda v: v if v[0] else None)(shown_model(app)), "the Model field to load")
        assert [value, label] == [str(folder), "faster-whisper-e2e"], f"after a restart the Model field shows {label!r} ({value!r})"
    finally:
        app.close()


def test_model_folder_refused(workdir):
    folder = model_folder(workdir, "not-a-model", with_model=False)
    live = ["pgrep", "-f", "transcriber-sidecar.*--live"]
    app = App(app_env(workdir)[0])
    try:
        assert subprocess.run(live, capture_output=True).returncode == 1, "a live engine was already running"
        store_model_dir(app, folder)
        app.click("#start-live-btn")
        note = App._wait(lambda: (lambda t: t if "model.bin" in t else None)(app.text("#note-root")), "the refusal note")
        assert str(folder) in note and "has no model.bin" in note, f"unexpected note: {note!r}"
        time.sleep(1)
        started = subprocess.run(live, capture_output=True, text=True)
        assert started.returncode == 1, f"a live engine started despite the refusal: {started.stdout.strip()}"
    finally:
        app.close()


def test_model_folder_used(workdir):
    folder = model_folder(workdir, "faster-whisper-e2e", with_model=True)
    app = App(app_env(workdir)[0])
    try:
        # Matched on the folder, not the label: the label comes from the staged
        # sidecar binary, which may predate transcriber.py's label change.
        bundled = SRC_TAURI / "target" / "debug" / "resources" / "model"
        for i, (chosen, expected) in enumerate([(folder, f" model from {folder} on "),
                                                (None, f" model from {bundled} on ")]):
            store_model_dir(app, chosen)
            wav = silent_wav(workdir / f"silence-{i}.wav")
            app.run_async(f"window.__TAURI__.event.emit('tauri://drag-drop', {{paths: [{json.dumps(str(wav))}]}}).then(() => done('ok'));")
            App._wait(lambda: expected in debug_log(app), f"the engine log to show{expected!r}")
            App._wait(lambda: app.run_async(f"done(document.getElementById('file-queue').textContent.includes('silence-{i}.wav') && !document.getElementById('file-queue').textContent.includes('transcribing'))"),
                      f"silence-{i}.wav to finish")
    finally:
        app.close()


def test_engine_offline():
    result = subprocess.run([sys.executable, str(ROOT / "tests" / "test_engine.py"), "--engine", str(SIDECAR)],
                            capture_output=True, text=True, encoding="utf-8", errors="replace")
    output = result.stdout + result.stderr
    assert result.returncode == 0, "engine tests failed with no network:\n" + output.strip()
    return "; ".join(line.strip() for line in output.splitlines() if re.match(r"(PASS|SKIP|FAIL)\s", line))


# ---- Runner -----------------------------------------------------------------------

def run(scenarios):
    failures = 0
    for name, fn, *args in scenarios:
        try:
            detail = fn(*args)
            print(f"PASS  {name}" + (f": {detail}" if detail else ""), flush=True)
        except Skip as exc:
            print(f"SKIP  {name}: {exc}", flush=True)
        except Exception as exc:  # report every scenario, not just the first failure
            failures += 1
            print(f"FAIL  {name}: " + "\n      ".join(str(exc).splitlines()[:8]), flush=True)
    return failures


def main() -> int:
    inside_netns = "--inside-netns" in sys.argv
    if not inside_netns:
        piece = missing_piece()
        if piece:
            for name in SCENARIOS:
                print(f"SKIP  {name}: {piece}")
            return 0
        build = subprocess.run(["cargo", "build"], cwd=SRC_TAURI, capture_output=True, text=True)
        if build.returncode != 0:
            print("FAIL  cargo build of the debug app:\n" + build.stderr[-2000:])
            return 1

    with tempfile.TemporaryDirectory(prefix="transcriber-e2e-") as tmp:
        dirs = [Path(tmp) / str(i) for i in range(6)]
        for d in dirs:
            d.mkdir()
        if inside_netns:
            return run([
                ("update check offline", test_update_check_offline, dirs[0]),
                ("download page offline", test_download_page, dirs[1]),
                ("engine offline", test_engine_offline),
            ])
        failures = run([
            ("update check online", test_update_check_online, dirs[0]),
            ("download page", test_download_page, dirs[1]),
            ("no request at startup", test_no_request_at_startup, dirs[2]),
            ("model folder remembered", test_model_folder_remembered, dirs[3]),
            ("model folder refused", test_model_folder_refused, dirs[4]),
            ("model folder used", test_model_folder_used, dirs[5]),
        ])

    # No network at all, by construction: a fresh network namespace with only
    # loopback up, so the test client can still reach tauri-driver.
    inner = subprocess.run([tool("unshare"), "-rn", "sh", "-c", 'ip link set lo up && exec "$@"', "sh",
                            sys.executable, str(Path(__file__).resolve()), "--inside-netns"])
    return 1 if failures or inner.returncode else 0


if __name__ == "__main__":
    sys.exit(main())
