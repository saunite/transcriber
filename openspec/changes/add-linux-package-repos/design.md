## Context

See proposal.md for why. What follows was verified in throwaway containers on 2026-09-16 before any of it was written down; the results are quoted where they matter.

Today's release flow: a pushed `v*` tag runs preflight, each platform leg builds and uploads to a **draft** release, and a maintainer publishes it by hand. The Linux leg builds the AppImage, `.deb`, `.rpm` and CLI archive with Tauri 2.9.3's bundlers on `ubuntu-22.04`, renames them lowercase, install-tests them in five distro containers, then `gh release upload`s them.

## Goals / Non-Goals

**Goals:**
- Upgrades arrive through `apt` and `dnf` for people who installed those packages.
- What a user can verify does not get weaker: a signature covers the index, and the index covers the packages.
- No second copy of a 280 MB package anywhere.

**Non-Goals:**
- Making updates smaller. Splitting the model and engine into their own packages is parked.
- Any change for AppImage, portable, Windows or macOS users.
- Signing the packages themselves. They stay unsigned, as today, and openSUSE keeps needing `--allow-unsigned-rpm` for a hand-downloaded `.rpm`.

## Decisions

### 1. apt lives entirely in Releases; dnf needs a few kilobytes on Pages

```
 apt                                        dnf
 deb [signed-by=...] https://github.com/    baseurl=https://saunite.github.io/transcriber/rpm/
   saunite/transcriber/releases/latest/       |
   download/ ./                               +-- repodata/repomd.xml(+.asc), primary.xml.zst
    |                                              |
    +-- InRelease, Packages.gz, the .deb           +-- <location xml:base=".../releases/download/v0.2.0/"
        all as release assets                                    href="transcriber_0.2.0_amd64.deb-equivalent.rpm"/>
```

apt resolves `Filename:` against the base URL in `sources.list`, so putting the base at the releases path makes the index and the package siblings. dnf always requests `<baseurl>/repodata/repomd.xml`, and release asset names cannot contain a slash, so its metadata needs a real directory: GitHub Pages, well under its 1 GB guidance at a few kilobytes per release, while `xml:base` sends the payload fetch to the release asset.

**Verified:** apt installed through GitHub's redirect shape (`/releases/latest/download/X` → tagged path → `release-assets.githubusercontent.com`, cross-host, signed URL) and refused both a tampered `Packages` ("File has unexpected size (275 != 274)") and an index signed by another key ("NO_PUBKEY … is not signed"). dnf fetched `repodata/*` from one host and the `.rpm` from the other, and refused a `repomd.xml` re-signed with a different key ("Signing key not found").

- **Alternative, rejected:** hosting the packages on Pages. Two releases of the `.deb` alone exceed the 1 GB guidance.
- **Alternative, rejected:** a hosted repository service (Cloudsmith, packagecloud). It removes key custody, but adds a third party, a quota against 283 MB per version, and someone else's key in the trust path. Worth revisiting if key handling becomes a burden.

### 2. Metadata is published by a `release: published` workflow

A draft's assets are not publicly downloadable and `releases/latest/download/` does not resolve until a release is public, so metadata generated during the tag build would describe something users cannot fetch. A separate workflow, triggered when the release is published, downloads that release's `.deb` and `.rpm`, builds the index, signs it, uploads the apt files as assets of that same release, and pushes `repodata/` to the Pages branch.

This also keeps the existing promise that publishing is a human action: until someone clicks publish, no repository changes.

### 3. Only the index is signed

`apt-ftparchive` writes a `Release` carrying each package's checksum, and `InRelease` is that file clear-signed. `createrepo_c` writes checksums into `primary.xml`, and `repomd.xml.asc` signs the metadata. So one signature per release covers everything, and `gpgcheck=0` with `repo_gpgcheck=1` on the dnf side is a complete chain rather than a weakening.

The benefit is practical: one signing step, no `rpmsign`, and the packages stay byte-identical to what the tag build produced and install-tested.

### 4. Key handling: offline master, signing subkey in CI (option B)

- The maintainer generates a master key offline, keeps it and a revocation certificate off CI, and creates a signing-only subkey.
- Only the subkey's secret material and its passphrase live in GitHub, as secrets on an environment the publish workflow uses.
- The public key ships inside both packages: dearmored at `/usr/share/keyrings/transcriber-archive-keyring.gpg` for apt's `signed-by`, and armored at `/etc/pki/rpm-gpg/RPM-GPG-KEY-transcriber` for dnf's `gpgkey`.
- **No expiry**, with the revocation certificate as the escape hatch. An expired key breaks `apt update` for everyone until they manually install a package carrying a new one.
- **Rotation**, if ever needed: ship both keys in the packages for a release or two, then sign with the new one, then drop the old.

**What this does and does not protect.** It stops a tampered or intercepted download, and a corrupted CDN. It does not stop someone who takes over the repository, because they would hold both the assets and the CI secret. That is why the master key stays out of CI: it is what makes revoking and re-issuing possible.

### 5. The rpm marking runs in a Fedora container, on the same Ubuntu runner

The Linux leg stays on `ubuntu-22.04`. It cannot move to Fedora: GitHub hosts no Fedora runner, and building inside a Fedora container would raise the glibc floor from 2.35 to 2.41, so the packages would refuse to start on Debian stable and Ubuntu LTS, which `release-build` requires them to support.

`rpmrebuild` is **not packaged for Ubuntu** (`rpm` 4.17 is in jammy/universe, `rpmrebuild` is absent), so that step runs in a `fedora:42` container inside the job, which already runs `docker` for its five install checks. It rewrites package metadata only and touches no binary, so it has no bearing on glibc.

### 6. Config-file marking has to be added after Tauri builds

Tauri's bundlers call `FileOptions::new(dest)` with no config flag and never write a `conffiles` control file, so a packaged file in `/etc` is silently replaced on every upgrade. **Verified** on a deb built that way: a user's commented-out repository line was overwritten without a word.

Both are fixed in the Linux leg, after the bundlers run and before the install checks:
- **deb:** `dpkg-deb -R`, add the path to `DEBIAN/conffiles`, `dpkg-deb -b`.
- **rpm:** `rpmrebuild --change-spec-files`, prefixing the file's line with `%config(noreplace)`. **Verified:** the file went from `flags=0` to `flags=17` (config + noreplace).

With that, the behaviour is the package managers' own, and no install script of ours is involved:

| | user edited it | untouched | removed |
|---|---|---|---|
| deb conffile | kept, new one as `.dpkg-dist` | updated silently | kept on `remove`, deleted on `purge` |
| rpm `%config(noreplace)` | kept, new one as `.rpmnew` | updated silently | deleted on erase |

- **Alternative, rejected:** installing `rpmrebuild` from its upstream tarball on the runner. It adds a download outside any distribution's packaging to a job that signs releases.
- **Alternative, rejected:** a postinstall script comparing checksums. It reimplements what both package managers already do, and gets the "user disabled it" case wrong easily.

## Risks / Trade-offs

- **[`rpmrebuild` runs in a container]** → Verified working on Fedora 42 and confirmed absent from Ubuntu's repositories, hence Decision 5. If the Fedora image's tooling ever changes, the alternative is building the `.rpm` ourselves.
- **[Every upgrade is ~283 MB]** → Unchanged by this work, but users meet it more often once upgrades are automatic. The split is parked; this is the reason it is worth doing.
- **[`releases/latest/download/` follows the newest published release]** → A release published out of order, or an older one re-published, would move what users are offered. Publishing order is already a manual step.
- **[Self-registration is contentious]** → Debian policy dislikes a package adding a third-party source; Chrome and VS Code do it anyway. The user chose it, and Decision 5 makes opting out survive upgrades.
- **[Pages must be enabled by hand]** → A repository setting, not something a workflow can turn on. It is a task, and the publish workflow should fail loudly rather than silently push to a branch nobody serves.
