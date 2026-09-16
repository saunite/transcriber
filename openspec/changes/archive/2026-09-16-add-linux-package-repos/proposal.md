## Why

Someone who installs the `.deb` or `.rpm` today has no way to learn that a new version exists, short of opening the app and pressing **Check for updates**, which only tells them and links to the download page. Every upgrade is a manual download and reinstall. Meanwhile their machine already has software built to do this: `apt` and `dnf` check registered repositories on their own schedule and offer upgrades through the system's software centre.

GitHub has no apt or yum registry (GitHub Packages covers npm, Maven, NuGet, RubyGems and containers only), so the repository has to be assembled from static files. That's cheap: both formats are a handful of small files produced by two command-line tools.

Decided with the user on 2026-09-16, after the options were compared and the mechanics verified in containers.

## What Changes

- **Every published release doubles as an apt and a dnf repository**, so installed `.deb` and `.rpm` users get upgrades through their package manager.
  - **apt:** a flat repository whose files (`InRelease`, `Packages.gz` and the `.deb` itself) are all release assets, reached through `https://github.com/saunite/transcriber/releases/latest/download/`. **Verified:** apt follows GitHub's two redirects, including the cross-host hop to the asset CDN, and verifies the signature.
  - **dnf:** `repodata/` on GitHub Pages (a few kilobytes), with `xml:base` in the metadata pointing at the release asset for the `.rpm`. **Verified:** dnf fetches metadata from one host and the package from the other, with `repo_gpgcheck=1`.
  - **Why they differ:** apt resolves `Filename:` relative to the repository's base URL, which can be the releases path; dnf always fetches `repodata/repomd.xml`, a path release assets cannot have, since asset names hold no slashes.
- **The packages register the repository themselves**, so updates begin with nothing for the user to do. Each ships the repository file and the public key.
- **A user who edits or disables that file keeps their version.** The repository file is a dpkg *conffile* and an rpm `%config(noreplace)` file, so an edited file survives upgrades and the new one lands beside it as `.dpkg-dist` or `.rpmnew`, while an untouched one is updated silently. **This needs post-processing:** Tauri's bundlers mark nothing as a config file, so a plain packaged file would be overwritten on every upgrade. Verified fixes: adding the path to `DEBIAN/conffiles`, and `rpmrebuild --change-spec-files` for the rpm, which took the file from `flags=0` to `flags=17`.
- **Signing follows option B:** a master key kept offline by the maintainer, with only a signing subkey in CI. Only the repository index is signed, which is a complete chain in both ecosystems because the index carries each package's checksum, and it keeps the packages themselves unsigned exactly as they are today.
- **Repository metadata is produced when a release is published**, not when the draft is built: a draft's assets are not publicly downloadable, and `releases/latest/download/` only resolves once a release is public.
- **Not in this change:**
  - splitting the model or the engine into their own packages, so an upgrade still downloads about 283 MB (parked in the backlog by the user's decision);
  - Windows, macOS, the AppImage and the portable builds, which keep the manual **Check for updates** button;
  - publishing the first real release, which this change's live verification waits on.

## Capabilities

### New Capabilities

- `linux-package-repos`: what the published repositories are, how the packages register them, how an edited repository file is treated, and how the signing key is handled and can be checked by a user.

### Modified Capabilities

- `release-build`: added "Publishing a release publishes its package repositories" — the metadata is generated and signed when a release is published, and neither a draft nor a manual build changes the repositories.

## Impact

- **`.github/workflows/`:** a new workflow triggered by `release: published` that builds and signs the apt and dnf metadata, uploads the apt files as release assets, and pushes `repodata/` to the Pages branch. The existing release workflow gains the two post-processing steps so the packages carry conffile and `%config(noreplace)` markings.
- **New packaged files:** the apt source file, the dnf `.repo` file, and the public key, plus their mapping in `src-tauri/tauri.conf.json` under `deb.files` and `rpm.files`.
- **Repository setup, by the maintainer:** GitHub Pages enabled for the repository, and the signing subkey plus its passphrase stored as environment secrets the release workflow can read.
- **Tests:** container checks like the spikes already run — a signed flat apt repository behind redirects, a dnf repository whose payload is on another host, rejection of a tampered index and of a wrong key, and the upgrade behaviour of the repository file when edited and when untouched.
- **Docs:** the user guide (what the repository is, the key's fingerprint, how to disable updates or remove the repository), `docs/building.md` (the publish step and key handling), and the README's "no auto-update" line, which becomes conditional for `.deb` and `.rpm` users.
- **No engine, GUI or shell (Rust) changes.**
