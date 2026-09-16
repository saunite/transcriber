<p align="center"><img src="resources/transcriber-icon-1024.png" width="96" alt="Transcriber icon"></p>

# Audio Transcriber

Transcribe meetings, calls and recordings on your own machine. A desktop app
for Windows, Linux and macOS, and the same engine as a command-line tool.
Nothing is uploaded. The model ships with the download, so the first
transcription works with the network off, and the app's only network request
is the **Check for updates** button, when you click it.

- Transcribe video and audio files (MP4, MKV, MP3, WAV and the rest) to TXT, SRT or VTT
- Transcribe live, from system audio and your microphone at once, tagged `[SYS]` and `[MIC]`
- Built on [faster-whisper](https://github.com/SYSTRAN/faster-whisper); no ffmpeg to install

The app captures live audio on Windows and Linux. On macOS it transcribes
files, and live capture is CLI-only, on macOS 14.4 or later.

## Install

Every [release](https://github.com/saunite/transcriber/releases) offers each platform in up to three forms. They're all the same version and all include the `base` Whisper model, so the first transcription works offline. There's no auto-update. The app's **Check for updates** button (at the bottom of the settings rail) asks GitHub for the latest release when you click it; it only reports what it finds and can open the releases page, and nothing is downloaded or installed for you. To upgrade, download the new version.

- **Portable**: nothing to install, no admin rights. Deleting it is the uninstall.
- **Installer or package**: installs like any other app, with a menu entry and an uninstaller.
- **CLI**: the command-line transcriber on its own, with no GUI and no Python needed, plus the meeting launcher script.

### Linux

The packages are install-tested on current Debian, Ubuntu LTS, Fedora, openSUSE Leap, and openSUSE Tumbleweed.

| File | What it is |
|---|---|
| `transcriber_<version>_amd64.AppImage` | Portable GUI. Run `chmod +x` on it, then run it. AppImages need FUSE (`libfuse2`); without it, run it with `--appimage-extract-and-run`. |
| `transcriber_<version>_amd64.deb` | Debian/Ubuntu package: `sudo apt install ./transcriber_<version>_amd64.deb`. Remove with `sudo apt remove transcriber`. |
| `transcriber-<version>-1.x86_64.rpm` | Fedora: `sudo dnf install ./transcriber-<version>-1.x86_64.rpm`. openSUSE: `sudo zypper install --allow-unsigned-rpm ./transcriber-<version>-1.x86_64.rpm`. Remove with `sudo dnf remove transcriber` or `sudo zypper remove transcriber`. |
| `transcriber-cli_<version>_linux-x64.tar.gz` | CLI (see below). |

The `.deb` and `.rpm` also put the command-line transcriber on your `PATH` as `transcriber-sidecar`. Run that way, it downloads models on first use instead of using the bundled one.

### Windows

| File | What it is |
|---|---|
| `Transcriber_<version>_x64-setup.exe` | Installer. It installs for your user only, under `%LOCALAPPDATA%`, so it never asks for admin rights. Uninstall it from Settings → Apps → Installed apps. |
| `Transcriber_<version>_windows-x64.zip` | Portable GUI. Extract it anywhere and run `transcriber-gui.exe` from inside the extracted folder. Deleting the folder is the uninstall. |
| `transcriber-cli_<version>_windows-x64.zip` | CLI (see below): `transcriber.exe`, the `win-start-transcription.bat` and `transcribe_file.bat` launchers, and the bundled model. |

All three are unsigned, so Windows SmartScreen warns the first time you run one ("Windows protected your PC"). Choose **More info**, then **Run anyway**.

### macOS

**Built automatically on Apple Silicon GitHub runners, but not yet tested on a real Mac. Testers welcome.** If you try them, please [open an issue](https://github.com/saunite/transcriber/issues) saying what worked, especially:

- Does the `.dmg` or the zipped `.app` open after you allow it in Privacy & Security (below)?
- Does file transcription work in the app?
- Does the CLI's `--coreaudio-tap` live capture work?
- Does a *downloaded* copy behave as described below the first time you open it?

| File | What it is |
|---|---|
| `Transcriber_<version>_aarch64.dmg` | Disk image. Open it and drag `Transcriber.app` to Applications. |
| `Transcriber_<version>_macos-arm64.zip` | Portable app. Unzip it and open `Transcriber.app`. Deleting it is the uninstall. |
| `transcriber-cli_<version>_macos-arm64.tar.gz` | CLI (see below). |

Apple Silicon (arm64) only; Intel Macs are not supported.

The app is ad-hoc signed but not notarized, so the first time you open it macOS says it can't verify the developer. Go to **System Settings → Privacy & Security**, scroll to the message about Transcriber, and choose **Open Anyway**.

Live capture isn't available in the macOS app yet; the CLI does it on macOS 14.4 or later, and [the user guide](docs/user-guide.md#macos) has the setup. File transcription works in the app.

### CLI archive

Extract it, then run it from the extracted folder:

```bash
./transcriber --file meeting.mp4                  # bundled base model, works offline
./transcriber --file meeting.mp4 --model small    # other sizes download on first use
./linux-start-transcription.sh sprint-review      # Teams-meeting launcher (system audio + mic)
```

On Windows the binary is `transcriber.exe` and the launchers are `win-start-transcription.bat` and `transcribe_file.bat`; the options are the same.

On macOS, clear the download quarantine first with `xattr -d com.apple.quarantine ./transcriber`. The launcher is `./mac-start-transcription.sh`, and system-audio capture (`--coreaudio-tap`) needs macOS 14.4 or later.

The launcher scripts use the `transcriber` binary next to them when it's there, and `python transcriber.py` otherwise, so the same scripts work from a source checkout.

## Run it

**The app.** Open it, then either drop a recording on the **File** tab, or go to
the **Live** tab and press **Start transcribing** before your meeting. The
transcript builds on a time axis as it goes, and is saved to your Documents
folder.

**The CLI.**

```bash
transcriber --file meeting.mp4                    # a recording -> meeting_transcript_<time>.txt
transcriber --live --include-mic                  # a live meeting: system audio + microphone
transcriber --file talk.mp4 --format srt          # subtitles instead
```

From a source checkout, that's `python transcriber.py` with the same options.

## Where next

- **[User guide](docs/user-guide.md)**: every option, per-platform setup for live capture, troubleshooting.
- **[Contributing](CONTRIBUTING.md)**: how changes are made here, and how to run the tests.
- **[Building](docs/building.md)**: building the app and the CLI from source, and making a release.

## License

- **Source in this repository:** GPL-2.0-or-later
- **Distributed binary artifacts:** GPL-3.0-or-later

The binaries bundle FFmpeg (via PyAV) built with GPL codecs — x264 and x265 —
and `--enable-version3` components, which are stricter than the source license.
The "or later" clause covers the combination, but a released artifact cannot be
offered under GPLv2-only terms.

`LICENSE` has the full text and the reasoning. `THIRD-PARTY-LICENSES.txt` lists
every bundled component with its license and copyright, and
`SOURCE-PROVENANCE.txt` records exact versions and where to obtain corresponding
source. All three ship inside every artifact.
