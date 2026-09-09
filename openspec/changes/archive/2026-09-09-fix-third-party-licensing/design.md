# Design

## Goals / Non-Goals

**Goals:**
- Make the distributed artifact's licensing accurate and its obligations met, before the first release triggers any of them.
- Record the two positions this project is taking (effective license, WebView2) so they are deliberate choices rather than defaults nobody examined.
- Record why the "just remove the unused encoders" instinct does not work, with the evidence, so it is not rediscovered the hard way.

**Non-Goals:**
- Relicensing the project.
- Reducing artifact size (a separate concern; see the rejected alternative below).
- A per-crate audit of the transitive Rust dependency tree.

## Decisions

**1. The distributed binary is declared GPLv3, while the project source stays GPL-2.0-or-later.**

The build configuration is recorded verbatim inside the shipped `avutil` binary and was read directly from it:

```
--disable-static --enable-shared --disable-programs --disable-doc
--enable-mediafoundation --enable-version3 --enable-gmp
--enable-libaom --enable-libdav1d --enable-libmp3lame
--enable-libopencore-amrnb --enable-libopencore-amrwb --enable-libopus
--enable-libspeex --enable-libsvtav1 --enable-libtwolame --enable-libvorbis
--enable-libvpx --enable-libwebp --enable-libopenh264 --enable-zlib
--enable-libx264 --enable-libx265 --enable-nvenc --enable-nvdec  ...
```

`--enable-version3` is present verbatim, so the version3 components are confirmed rather than inferred.

*One unresolved anomaly, recorded rather than glossed:* the literal string `--enable-gpl` does **not** appear anywhere in that binary, yet `--enable-libx264` and `--enable-libx265` do — a combination FFmpeg's own configure normally rejects. The cause could not be determined from the shipped binary alone. **It does not change the conclusion**, because the artifact ships `libx264.dll` and `libx265.dll` as files, and x264 and x265 are GPL-2.0-or-later projects in their own right; distributing them carries GPL obligations however FFmpeg was configured. Worth raising with a reviewer, since it is the one place the evidence is internally inconsistent.

Distributing GPLv3 components alongside GPL-2.0-**or-later** source is fine — the "or later" clause permits distributing the combined work under GPLv3 — but the combined artifact cannot be offered as GPLv2-only.

*Why state it explicitly:* `README.md` currently says "GPLv2" flatly. A user who reads that and assumes GPLv2-only terms would be misled about a binary that contains GPLv3 components. The source license does not change; only the statement about what the shipped artifact is.

*Alternative considered:* stay silent and let `LICENSE`'s "or later" imply it. Rejected — the whole point of this change is that implicit and stale licensing statements are what created the problem.

**2. `WebView2Loader.dll` is distributed under the System Library exception.**

Tauri's Windows shell ships `WebView2Loader.dll`, which is proprietary Microsoft code, inside a GPL application. Strict GPL requires every component of the combined work to be GPL-compatible. The applicable carve-out is the System Library exception (GPLv3 §1; GPLv2's "major components of the operating system" language): WebView2 is a Microsoft-distributed Windows runtime component, and this DLL is a thin loader shim for it — the same basis on which GPL applications on Windows link the MSVC runtime.

*This is an argued position, not a settled one.* It is recorded here so it is a considered choice. If it is ever challenged, the alternatives are to drop the Windows GUI, to relicense away from GPL, or to add a GPL linking exception for it — all far larger changes than this one.

**3. Corresponding source is supplied by maintained directions to upstream source (GPLv3 §6(d)), not by attaching archives or a written offer.**

GPL offers several ways to satisfy the source obligation: accompany the binary with the source (GPLv2 §3(a) / GPLv3 §6), make a written offer valid at least three years (§3(b) / §6(b)), or — GPLv3 only — publish the artifact with clear directions to corresponding source hosted elsewhere, including on a third party's server (§6(d)). This project takes §6(d): the notices name each bundled GPL component, its exact version, and where its source is published upstream.

*Why this is available:* §6(d) exists only under GPLv3, so it depends on decision 1 holding. That is now verified rather than inferred — `--enable-version3` appears verbatim in the configure string embedded in the shipped `avutil` binary, and the artifact ships `libx264` and `libx265`, which are GPL-2.0-or-later projects in their own right regardless of how FFmpeg was configured.

*Why chosen over attaching archives:* the archives would otherwise be re-attached to every release, or committed to the repository — roughly 25 MB in git permanently, in every clone, unremovable without rewriting history. Directions cost nothing per release and only change when a dependency bump changes what is bundled.

*Accepted risks, deliberately taken:*

- **Upstream link rot is real, and under §6(d) it remains this project's problem.** "Regardless of what server hosts the Corresponding Source, you remain obligated to ensure that it is available." x265's original Bitbucket hosting disappeared when Bitbucket dropped Mercurial in 2020 — an actual precedent for exactly this failure. If a location stops resolving, the `licensing` capability obliges updating the directions or rehosting; that is a live duty, not a one-time step.
- **Correspondence is reconstructed rather than demonstrated.** Corresponding source includes the scripts controlling compilation, and these binaries were built by PyAV, not here. Upstream FFmpeg source alone does not convey PyAV's configure flags. This is mitigated by recording the full configure string extracted from the shipped binary, so a recipient can reproduce the build rather than guess at it.

*If either risk becomes uncomfortable,* the lighter escalation is to rehost the archives as assets on this project's own releases — still §6(d), but with no third party in the path — rather than reverting to attaching them per release.

**4. Notices ship *inside* the artifact, not only in the repo.**

A user receives `Transcriber.zip`, not the git repo. GPL and MIT obligations attach to what is distributed, so a `LICENSE` file that exists only in the repository does not discharge them. `build_portable.py` must place the notices in the extracted folder, and the model's notice must sit with the model in `resources/model/`.

## Rejected Alternative: strip the unused encoders to escape GPL

The app never encodes anything and never decodes video — it decodes audio for transcription. So bundling `libx264`, `libx265`, `libSvtAv1Enc`, `libaom`, `libvpx`, `libwebp` looks like pure waste that could simply be deleted, taking the GPL obligations with it. It cannot:

- `avcodec-62.dll`'s **PE import table** contains `libx264-165.dll` and `libx265.dll` — load-time linkage, not `dlopen`. Removing either makes `avcodec` fail to load, so `import av` throws, so `faster_whisper/audio.py:15` fails at import, so the entire application dies — including live capture, which never touches FFmpeg.
- PyAV cannot be dropped either: `av>=11` is a hard `Requires-Dist` of faster-whisper, imported at module scope.
- The only real path is building a minimal FFmpeg (`--disable-everything --disable-gpl --disable-version3` plus explicit audio demuxers/decoders) and compiling PyAV from source against it, per platform, repeated on every FFmpeg or PyAV bump.

*Cost/benefit:* removable libraries are 48 MB of the 83 MB `av.libs`, but the shipped zip is 265 MB dominated by the 145 MB model, so real savings after compression are under 10% of the download. The licensing benefit today is **zero** — the project is already GPL-compatible with what it ships. It would only pay off if the project later wanted to relicense away from GPL. Against that: a permanent cross-platform FFmpeg build pipeline, in a project that just deliberately removed CI and Docker in favour of simple local builds.

Rejected as a poor trade. Revisit only if relicensing becomes a real goal.

## Risks / Trade-offs

- [Identifying which upstream versions PyAV actually built is the real work, and getting it wrong means the published source does not correspond to the shipped binaries] → Mitigation: read PyAV's build scripts at the `16.0.1` tag to find the pinned FFmpeg/x264/x265 versions, and cross-check against the library versions the shipped binary reports (`libavcodec 62.11.100`, `libavformat 62.3.100`, `libavutil 60.8.100` — FFmpeg 8.0.x). Record both in a provenance file so a later release can repeat the check rather than redo the research.
- [Attaching source is a release-time step that can simply be forgotten, and the omission is invisible until someone asks] → Mitigation: document it as part of the release procedure rather than leaving it to memory; a release that publishes the artifact without the source is a spec violation under the `licensing` capability.
- [Component list drifts as dependencies change, recreating exactly the staleness this change fixes] → Mitigation: the `licensing` capability's requirement is written so that bundling a new component obliges updating the notices, making drift a spec violation rather than an oversight.
- [This is not legal advice, and the WebView2 position in particular is arguable] → Mitigation: positions are documented with their reasoning, so a lawyer can review the actual claims rather than reverse-engineering them.
