#!/usr/bin/env python3
"""Build the apt and dnf repository metadata for one published release.

The packages stay where they are, as that release's assets; only the index is
built here, and only the index is signed. Both package managers carry each
package's checksum inside the signed index, so that single signature covers the
downloads too (openspec/changes/add-linux-package-repos, design.md Decision 3).

    apt   flat repository: Packages.gz, Release, InRelease, uploaded as assets
          of the same release, so `Filename:` resolves next to them.
    dnf   repodata/ for GitHub Pages, with the payload URL written as an
          absolute xml:base pointing at the release's own asset.

Needs dpkg-scanpackages, apt-ftparchive, createrepo_c and gpg (Ubuntu:
dpkg-dev, apt-utils, createrepo-c, gnupg).

Usage:
  build_repo_metadata.py --packages DIR --asset-base URL --apt-out DIR --rpm-out DIR
                         [--sign-with KEYID]

--asset-base is where that release's assets are downloadable, ending in a
slash, e.g. https://github.com/<owner>/<repo>/releases/download/v0.2.0/
The passphrase for the signing key is read from GPG_PASSPHRASE when set.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


def need(*tools: str) -> None:
    missing = [t for t in tools if not shutil.which(t)]
    if missing:
        raise SystemExit(f"missing tool(s): {', '.join(missing)} (see this script's docstring)")


def run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=True, **kwargs)


def gpg_sign(args: list[str]) -> None:
    """gpg, non-interactive, using GPG_PASSPHRASE when the key needs one."""
    base = ["gpg", "--batch", "--yes"]
    if os.environ.get("GPG_PASSPHRASE"):
        base += ["--pinentry-mode", "loopback", "--passphrase", os.environ["GPG_PASSPHRASE"]]
    run(base + args)


def build_apt(packages: Path, out: Path, sign_with: str | None) -> list[Path]:
    need("dpkg-scanpackages", "apt-ftparchive", "gpg")
    out.mkdir(parents=True, exist_ok=True)
    for deb in packages.glob("*.deb"):                    # scanpackages reads the directory it indexes
        shutil.copy(deb, out / deb.name)
    listing = run(["dpkg-scanpackages", "--multiversion", "."], cwd=out,
                  capture_output=True, text=True).stdout
    if not listing.strip():
        raise SystemExit(f"no .deb found in {packages}")
    (out / "Packages").write_text(listing)
    run(["gzip", "-kf", "Packages"], cwd=out)
    release = run(["apt-ftparchive", "release", "."], cwd=out, capture_output=True, text=True).stdout
    (out / "Release").write_text(release)
    signer = ["--local-user", sign_with] if sign_with else []
    gpg_sign(signer + ["--clearsign", "-o", str(out / "InRelease"), str(out / "Release")])
    for deb in out.glob("*.deb"):                          # the packages are already release assets
        deb.unlink()
    return sorted(p for p in out.iterdir() if p.is_file())


def build_rpm(packages: Path, out: Path, asset_base: str, sign_with: str | None) -> list[Path]:
    need("createrepo_c", "gpg")
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    rpms = list(packages.glob("*.rpm"))
    if not rpms:
        raise SystemExit(f"no .rpm found in {packages}")
    for rpm in rpms:                                       # createrepo_c reads each package's headers
        shutil.copy(rpm, out / rpm.name)
    run(["createrepo_c", "--baseurl", asset_base, str(out)], stdout=subprocess.DEVNULL)
    for rpm in out.glob("*.rpm"):                          # keep only the metadata for Pages
        rpm.unlink()
    signer = ["--local-user", sign_with] if sign_with else []
    gpg_sign(signer + ["--detach-sign", "--armor", str(out / "repodata" / "repomd.xml")])
    return sorted(p for p in (out / "repodata").iterdir() if p.is_file())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--packages", type=Path, required=True, help="directory holding the release's .deb and .rpm")
    parser.add_argument("--asset-base", required=True, help="URL the release's assets are downloadable from (trailing slash)")
    parser.add_argument("--apt-out", type=Path, required=True, help="where to write the apt index")
    parser.add_argument("--rpm-out", type=Path, required=True, help="where to write repodata/ for Pages")
    parser.add_argument("--sign-with", help="key to sign with (default: gpg's default key)")
    args = parser.parse_args()

    if not args.asset_base.endswith("/"):
        raise SystemExit("--asset-base must end with a slash")

    for path in build_apt(args.packages, args.apt_out, args.sign_with):
        print(f"apt  {path}")
    for path in build_rpm(args.packages, args.rpm_out, args.asset_base, args.sign_with):
        print(f"dnf  {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
