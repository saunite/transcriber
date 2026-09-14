## 1. Pin and guard

- [ ] 1.1 Add `av==18.1.0` to `requirements.txt`, `requirements-linux.txt` and `requirements-macos.txt` (design.md Decision 2). Verify that in a fresh venv `pip install -r requirements-linux.txt` resolves without conflict, and that `python -c "import av; print(av.__version__, av.ffmpeg_version_info)"` prints `18.1.0 8.1.2`.
- [ ] 1.2 Add the preflight guard step to `.github/workflows/release.yml`, before "Source-provenance links resolve" and with no `if:` (Decision 3). Verify:
  - PyYAML parses the workflow;
  - the step's script, run locally from the parsed YAML, **fails** at this point, naming `SOURCE-PROVENANCE.txt`'s recorded `16.0.1` against `18.1.0` (the real drift);
  - it also fails, on scratch copies, for a requirements file with no `av` line, one with `av>=18.1.0`, and two files with different pinned versions.

## 2. Re-derive the provenance

- [ ] 2.1 Collect the build facts for `pyav-ffmpeg` `8.1.2-1` (Decision 1):
  - every component's name, version, source URL and upstream licence from `scripts/pkg.py`;
  - the per-platform flags from `scripts/build-ffmpeg.py` for Linux x86-64, Windows x86-64 and macOS arm64;
  - `av.library_versions` and `av.ffmpeg_version_info` from the installed wheel;
  - the configure string, read with `strings` from the Linux wheel's bundled `libavutil`;
  - an SBOM from the `ffmpeg-manylinux-x86_64.tar.gz` release tarball, if it has one.
  Record every disagreement between these sources, and confirm that TwoLAME, Speex, libvorbis/libogg, libaom and OpenH264 are really absent from `pkg.py`, not just defined differently.
- [ ] 2.2 Rewrite `SOURCE-PROVENANCE.txt`, keeping its section structure (how the binaries got here, what ships, per-component source, maintenance):
  - `av == 18.1.0`, pinning `8.1.2-1`, with links to the recipe files at that tag;
  - the library versions and Linux configure string from 2.1;
  - a per-platform subsection whose Windows and macOS flags are stated as recipe-derived;
  - copyleft and permissive components with the new versions and URLs, removed components dropped;
  - the x265 hosting-risk note kept;
  - the maintenance section saying PyAV is pinned and the preflight guard enforces the match;
  - "Last verified" set to the date of 2.3.
  Verify with the guard script from 1.2, which must now pass, and `git diff` shows no leftover `16.0.1`, `8.0-2` or `FFmpeg 8.0` text.
- [ ] 2.3 Run the preflight link check's command locally against the new file. Verify every non-template URL resolves (`curl -fsSL -r 0-0`), and record any that don't, fixing or noting them before continuing.
- [ ] 2.4 Update `THIRD-PARTY-LICENSES.txt` (Decision 4): the "Bundled media libraries" entries (FFmpeg 8.1.2, x264, x265 4.2, the component list per 2.1) and the `PyAV 18.1.0` table line, with the `--enable-version3` statement re-checked against the new configure string. Verify that `grep -n "16.0.1\|FFmpeg 8.0\|x265 4.1\|TwoLAME"` finds nothing, unless 2.1 showed that component is still built.
- [ ] 2.5 Update README's licensing maintenance bullet to say PyAV is pinned (`av==18.1.0`), and that a bump must re-derive `SOURCE-PROVENANCE.txt`, which the preflight check enforces. Verify the bullet no longer says "If the pinned PyAV version changed".

## 3. Verification

- [ ] 3.1 Run `.venv/bin/python run_tests.py` with the recording set, in a venv matching the pinned requirements. Verify it exits 0.
- [ ] 3.2 Manual `workflow_dispatch` run on `dev` (only when the user asks for it). Verify:
  - the new guard step passes;
  - "Source-provenance links resolve" passes with the new URLs;
  - all platform jobs pass;
  - a job log's pip output shows `av-18.1.0` being installed.
