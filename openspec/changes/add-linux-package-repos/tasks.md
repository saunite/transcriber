## 1. Check what the runner can do

- [x] 1.1 Decide where the rpm config marking runs.

  **Done 2026-09-16.** `rpmrebuild` is **not available on Ubuntu**: `apt-cache search rpmrebuild` on `ubuntu:22.04` returns nothing, while `rpm` 4.17 is in jammy/universe. It works on Fedora, where it took a Tauri-style plain file from `flags=0` to `flags=17`.

  Moving the whole leg to Fedora is out: GitHub hosts no Fedora runner, and a Fedora container would raise the glibc floor from 2.35 to 2.41 and break the Debian and Ubuntu installs the specs require. So that one step runs in a `fedora:42` container inside the Ubuntu job (design.md Decision 5), which already uses `docker` for its install checks.

## 2. The files the packages carry

- [x] 2.1 Add the repository definitions under `packaging/`:
  - the apt source, naming the releases base URL and `signed-by=/usr/share/keyrings/transcriber-archive-keyring.gpg`;
  - the dnf `.repo`, with `baseurl` on Pages, `repo_gpgcheck=1`, `gpgcheck=0` (design.md Decision 3) and `gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-transcriber`;
  - a placeholder for the public key file, replaced in 5.1 by the real one.

  Map all of them in `src-tauri/tauri.conf.json` under `bundle.linux.deb.files` and `bundle.linux.rpm.files`. Verify a local `cargo tauri build --bundles deb,rpm` puts each file at the intended path (`dpkg-deb -c`, `rpm -qpl`).

  **Done 2026-09-16.** `packaging/` holds `transcriber.list`, `transcriber.repo` and `transcriber-repo-key.asc` (the real public key, 819 bytes, exported from the key made in 5.1; `pub` + signing `sub`, no private material). Each file opens with a comment telling the user their edits survive upgrades and how to turn updates off.

  **Deviation from design.md Decision 4:** one armored key file serves both, at `/usr/share/keyrings/transcriber-archive-keyring.asc` for apt (which accepts armored keys in `signed-by`) and `/etc/pki/rpm-gpg/RPM-GPG-KEY-transcriber` for dnf, instead of shipping a dearmored copy as well. It keeps a binary blob out of the repository.

  **Verified** with a local `cargo tauri build --bundles deb,rpm`: `dpkg-deb -c` shows `etc/apt/sources.list.d/transcriber.list` and `usr/share/keyrings/transcriber-archive-keyring.asc`; `rpm -qp` shows `/etc/yum.repos.d/transcriber.repo` and `/etc/pki/rpm-gpg/RPM-GPG-KEY-transcriber`.

- [x] 2.2 Add the config-file marking to the Linux build, after the bundlers and before anything consumes the packages: `DEBIAN/conffiles` for the `.deb` (unpack, add, repack) and `rpmrebuild --change-spec-files` for the `.rpm`. Put it in a script the release workflow and a local build can both call.

  Verify with `dpkg-deb -e … && cat DEBIAN/conffiles` and `rpm -qp --qf '[%{FILENAMES} flags=%{FILEFLAGS}\n]'` that only the repository file is marked, and that the packages still install in the five distro containers the release workflow already checks.

  **Done 2026-09-16.** `mark_package_configs.py` at the repo root does both halves and is called by a new "Mark the repository file as configuration" step in the release workflow's Linux job, between the bundlers and the install checks. It picks `docker` or `podman`, whichever exists.

  **Added scope, agreed with the user:** `rpmbuild` refuses a package whose `Summary` is empty, and Tauri built both packages with no description at all (`apt show` and `dnf info` showed "(none)"). `bundle.shortDescription` and `bundle.longDescription` are now set in `tauri.conf.json`, which unblocks the rebuild and fills a field both package managers display.

  **Found while testing:** the container writes its output as a user the caller may not be able to delete, which left a 250 MB temporary directory behind. The container now hands ownership back (`chown -R "$(stat -c '%u:%g' /work)" /work`) before it exits; a rerun leaves nothing.

  **Verified:** the `.deb` carries a one-line `conffiles` naming only the repository file; the `.rpm` shows `flags=17` on `/etc/yum.repos.d/transcriber.repo` while the key and the binaries stay `flags=0`. All five distro images install the packages (Debian stable, Ubuntu 24.04, Fedora, openSUSE Leap, openSUSE Tumbleweed), and on Fedora the installed `transcriber.repo` reads `enabled=1`, `repo_gpgcheck=1`, is owned by the package, and the key is at its path.

## 3. Tests

- [x] 3.1 Add `tests/test_package_repos.py` (or a shell equivalent run by `run_tests.py`), skipping cleanly when `podman`/`docker` is unavailable, covering with throwaway keys and dummy packages:
  - a signed flat apt repository reached through a redirect chain like GitHub's installs, and refuses a tampered index and a wrong key;
  - a dnf repository whose `xml:base` points at another host installs, and refuses metadata signed by another key;
  - a repository file marked as a conffile: an edited file survives an upgrade with a `.dpkg-dist` beside it, an untouched one is updated, and `purge` removes it;
  - the same three for `%config(noreplace)` and `.rpmnew` on the rpm side.

  The spikes from 2026-09-16 in the session scratchpad are the starting point; they already do each of these. Verify the suite fails if the conffile marking is dropped from 2.2.

  **Done 2026-09-16.** `tests/test_package_repos.py` has three checks, all passing: the apt repository (installs through the redirect shape, refuses a tampered index and a wrong key), the dnf repository (installs with the package on a second host, refuses a wrong key), and the config marking (an edited file survives an upgrade with `.dpkg-dist`/`.rpmnew` beside it, an untouched one is updated, removal cleans up). It skips with a message when no container runtime exists.

  **Mutation check:** with `DEB_CONFFILES` and `RPM_CONFIG_FILES` emptied in `mark_package_configs.py`, the third check fails with "the .deb was not marked"; the file was restored afterwards (no diff).

  **Cost:** the suite takes about 2 minutes 50 seconds, which roughly triples `run_tests.py`. Flagged for the user; gating it behind an environment variable is a one-line change if that is too slow.

## 4. Publishing the repositories

- [x] 4.1 Add a script that builds the metadata from a release's packages: `dpkg-scanpackages` plus `apt-ftparchive release` for apt, `createrepo_c --baseurl <that release's asset base>` for dnf, then clear-sign `InRelease` and detach-sign `repomd.xml`.

  Verify by running it against the packages of a local build and pointing a container's `apt` and `dnf` at the result, as in 3.1.

  **Done 2026-09-16.** `build_repo_metadata.py` builds both indexes and signs only those, taking `--packages`, `--asset-base`, `--apt-out`, `--rpm-out` and optional `--sign-with`, with the passphrase from `GPG_PASSPHRASE`. It copies packages in only so the tools can read their headers, and deletes those copies afterwards, so neither output holds a package.

  **Verified** against the real 250 MB `.deb` and `.rpm` in an `ubuntu:24.04` container: it writes `Packages`, `Packages.gz`, `Release` and a clear-signed `InRelease`, plus `repodata/` with `repomd.xml.asc`, and the metadata carries `<location xml:base="https://github.com/saunite/transcriber/releases/download/v0.1.0/" href="Transcriber-0.1.0-1.x86_64.rpm"/>`. `Filename: ./Transcriber_0.1.0_amd64.deb` resolves against the flat repository's base, and no package copies are left behind.

- [x] 4.2 Add `.github/workflows/publish-repos.yml`, triggered by `release: published`, which downloads that release's `.deb` and `.rpm`, runs 4.1's script with the signing subkey from the environment secret, uploads the apt files (`InRelease`, `Packages.gz`) as assets of that release, and pushes `repodata/` to the Pages branch.

  It SHALL fail with a clear message when the signing material or Pages configuration is missing, and SHALL do nothing for drafts and manual runs. Verify with a dry run on a scratch repository or a workflow run against a test release, whichever the maintainer prefers; record which was used.

  **Done 2026-09-16.** The workflow runs on `release: published` (plus a manual trigger taking a tag), on the `release-signing` environment. It refuses to start when `GPG_SIGNING_SUBKEY` is unset or Pages is not enabled, then imports the subkey, downloads that release's `.deb` and `.rpm`, builds and signs the indexes, uploads the apt files as assets of the same release, and pushes `repodata/` to `gh-pages` under `rpm/`. Nothing triggers it for a draft or a tag build.

  **Verified locally, not yet on GitHub:** the same commands were run in containers against the real packages. `apt` read the signed index through a redirect and offered `Candidate: 0.1.0`; `dnf` accepted the signed metadata and listed `transcriber.x86_64 0.1.0-1`. The live run is still open, and 6.4 already covers the first real release; the user's preference for a scratch-repository dry run is the open question below.

## 5. Maintainer setup (by the user)

- [x] 5.1 **Generate the keys** (by the user).

  **Done 2026-09-16.** Keyring at `~/Nextcloud/Pessoal/keys/transcriber-signing` (self-hosted Nextcloud, `0700`):
  - **master** `612A3A5D8538DCF38F43BE232DADC8BDB40BC439`, ed25519 `[SC]`, no expiry;
  - **signing subkey** `468AB93232044ED3EA7EA3D8ED41E8274CE3715A`, ed25519 `[S]`;
  - revocation certificate present as `612A…C439.rev`.

  GitHub environment `release-signing` holds `GPG_SIGNING_SUBKEY` and `GPG_PASSPHRASE`, and no secret export was left on disk.

  **The fingerprint for the docs (task 6.1) is the master's:** `612A 3A5D 8538 DCF3 8F43 BE23 2DAD C8BD B40B C439`.

  Three corrections to the steps as first written, found while running them:
  - `!` must be quoted separately in zsh (`"$SUB"'!'`), or history expansion eats it, and it is needed **only** on `--export-secret-subkeys`. Signing uses `--local-user "$FPR"`, and gpg picks the signing subkey itself.
  - `grep -c "PRIVATE KEY BLOCK"` returns 2 for one key, since `BEGIN` and `END` both match. Count `"BEGIN PGP PRIVATE KEY BLOCK"` instead.
  - `sec#` does not show when reading the exported file; import it into a throwaway `GNUPGHOME` and run `gpg --list-secret-keys` there, where `sec#` proves the master stayed behind.

- [x] 5.2 **Enable GitHub Pages.**

  **Done 2026-09-16.** An orphan `gh-pages` branch was created with a placeholder page saying what the site is for, and pushed. Pushing that branch enabled Pages by itself, so the API call reported it was already on. `https://saunite.github.io/transcriber/` returns HTTP 200 and serves the placeholder, from branch `gh-pages`, path `/`.

## 6. Docs and verification

- [x] 6.1 Docs:
  - `docs/user-guide.md`: what the repository is, that installing the package registers it, the key's fingerprint and where it lands, how to disable updates (edit the file; the edit survives upgrades), and how removal cleans up;
  - `docs/building.md`: the publish step, the key's handling and rotation, and what to do if it is ever compromised;
  - `README.md`: the "There's no auto-update" line becomes conditional for `.deb` and `.rpm`.

  Verify each is described.

  **Done 2026-09-16.**
  - **`docs/user-guide.md`** gains "Updates for the .deb and .rpm": what the repository is, a table of the four installed files, the key's fingerprint, the one-time trust prompt on Fedora and openSUSE (and why apt has none), how to turn updates off with the edit surviving upgrades, and that removal cleans up (`apt purge`, `dnf remove`).
  - **`docs/building.md`** gains "Package repositories" under Releasing: what the publish workflow does in four steps, where the signing key lives, what to do if the subkey leaks or the master is lost, why the key has no expiry, and why the config marking runs in a Fedora container.
  - **`README.md`**: the no-auto-update line now names the `.deb` and `.rpm` exception and links to the guide; the Linux table says `apt purge` removes the repository while `remove` keeps it.
  - **Checked:** every relative link and anchor in the four documents still resolves.

- [x] 6.2 Run `.venv/bin/python run_tests.py` with `TRANSCRIBER_TEST_SPEECH` set and a network that reaches GitHub, and verify it exits 0.

  **Done 2026-09-16.** With `TRANSCRIBER_TEST_SPEECH` set and GitHub reachable: 17/17 suites passed, exit 0, nothing skipped. `tests/test_package_repos.py` takes 192 s of the 306 s total, so the suite went from about 100 s to about 5 minutes. Whether to gate it behind an environment variable is still the user's call.

- [x] 6.3 Add a backlog item for splitting the model and the engine into their own packages, so an upgrade stops costing ~283 MB, noting that this change makes upgrades frequent enough for it to matter.

  **Done 2026-09-16.** Added to "Parked changes" above the release item, with the 142 MB model and 153 MB engine measured from this build and the note that this change is what makes it matter.

- [ ] 6.4 **At the first published release, by the user:** on a real Debian or Ubuntu machine and a real Fedora or openSUSE machine, install the downloaded package, confirm the repository registered itself, then publish a later version and confirm the package manager offers and installs it. Record both results; this is the check the container tests cannot make.
