## 1. Check what the runner can do

- [ ] 1.1 Verify `rpmrebuild` is installable and works on the Linux leg's image. In an `ubuntu-22.04` container, install it from the distribution's repositories, run it against a package built the way Tauri builds one (a plain file under `/etc`), and confirm the file's flags change from `0` to `17`.

  If it isn't available there, record that and stop to re-plan: the alternatives are building the `.rpm` ourselves or running that step in a Fedora container inside the job.

## 2. The files the packages carry

- [ ] 2.1 Add the repository definitions under `packaging/`:
  - the apt source, naming the releases base URL and `signed-by=/usr/share/keyrings/transcriber-archive-keyring.gpg`;
  - the dnf `.repo`, with `baseurl` on Pages, `repo_gpgcheck=1`, `gpgcheck=0` (design.md Decision 3) and `gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-transcriber`;
  - a placeholder for the public key file, replaced in 5.1 by the real one.

  Map all of them in `src-tauri/tauri.conf.json` under `bundle.linux.deb.files` and `bundle.linux.rpm.files`. Verify a local `cargo tauri build --bundles deb,rpm` puts each file at the intended path (`dpkg-deb -c`, `rpm -qpl`).

- [ ] 2.2 Add the config-file marking to the Linux build, after the bundlers and before anything consumes the packages: `DEBIAN/conffiles` for the `.deb` (unpack, add, repack) and `rpmrebuild --change-spec-files` for the `.rpm`. Put it in a script the release workflow and a local build can both call.

  Verify with `dpkg-deb -e … && cat DEBIAN/conffiles` and `rpm -qp --qf '[%{FILENAMES} flags=%{FILEFLAGS}\n]'` that only the repository file is marked, and that the packages still install in the five distro containers the release workflow already checks.

## 3. Tests

- [ ] 3.1 Add `tests/test_package_repos.py` (or a shell equivalent run by `run_tests.py`), skipping cleanly when `podman`/`docker` is unavailable, covering with throwaway keys and dummy packages:
  - a signed flat apt repository reached through a redirect chain like GitHub's installs, and refuses a tampered index and a wrong key;
  - a dnf repository whose `xml:base` points at another host installs, and refuses metadata signed by another key;
  - a repository file marked as a conffile: an edited file survives an upgrade with a `.dpkg-dist` beside it, an untouched one is updated, and `purge` removes it;
  - the same three for `%config(noreplace)` and `.rpmnew` on the rpm side.

  The spikes from 2026-09-16 in the session scratchpad are the starting point; they already do each of these. Verify the suite fails if the conffile marking is dropped from 2.2.

## 4. Publishing the repositories

- [ ] 4.1 Add a script that builds the metadata from a release's packages: `dpkg-scanpackages` plus `apt-ftparchive release` for apt, `createrepo_c --baseurl <that release's asset base>` for dnf, then clear-sign `InRelease` and detach-sign `repomd.xml`.

  Verify by running it against the packages of a local build and pointing a container's `apt` and `dnf` at the result, as in 3.1.

- [ ] 4.2 Add `.github/workflows/publish-repos.yml`, triggered by `release: published`, which downloads that release's `.deb` and `.rpm`, runs 4.1's script with the signing subkey from the environment secret, uploads the apt files (`InRelease`, `Packages.gz`) as assets of that release, and pushes `repodata/` to the Pages branch.

  It SHALL fail with a clear message when the signing material or Pages configuration is missing, and SHALL do nothing for drafts and manual runs. Verify with a dry run on a scratch repository or a workflow run against a test release, whichever the maintainer prefers; record which was used.

## 5. Maintainer setup (by the user)

- [ ] 5.1 **Generate the keys.** Create the master key offline, plus a signing-only subkey and a revocation certificate kept off CI. Export the subkey's secret material, add it and its passphrase as secrets on the environment the publish workflow uses, and put the armored public key in `packaging/`. Record the fingerprint under this task.

- [ ] 5.2 **Enable GitHub Pages** for the repository, serving the branch the publish workflow pushes to. Verify `https://saunite.github.io/transcriber/` serves a file from that branch.

## 6. Docs and verification

- [ ] 6.1 Docs:
  - `docs/user-guide.md`: what the repository is, that installing the package registers it, the key's fingerprint and where it lands, how to disable updates (edit the file; the edit survives upgrades), and how removal cleans up;
  - `docs/building.md`: the publish step, the key's handling and rotation, and what to do if it is ever compromised;
  - `README.md`: the "There's no auto-update" line becomes conditional for `.deb` and `.rpm`.

  Verify each is described.

- [ ] 6.2 Run `.venv/bin/python run_tests.py` with `TRANSCRIBER_TEST_SPEECH` set and a network that reaches GitHub, and verify it exits 0.

- [ ] 6.3 Add a backlog item for splitting the model and the engine into their own packages, so an upgrade stops costing ~283 MB, noting that this change makes upgrades frequent enough for it to matter.

- [ ] 6.4 **At the first published release, by the user:** on a real Debian or Ubuntu machine and a real Fedora or openSUSE machine, install the downloaded package, confirm the repository registered itself, then publish a later version and confirm the package manager offers and installs it. Record both results; this is the check the container tests cannot make.
