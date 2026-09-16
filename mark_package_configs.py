#!/usr/bin/env python3
"""Mark the repository definition as a configuration file in the built packages.

Tauri's bundlers ship every packaged file as an ordinary one, so the repository
file we install under /etc would be silently overwritten on each upgrade, taking
a user's "I disabled this" edit with it. dpkg and rpm both have the behaviour we
want -- keep the user's file, leave ours beside it as .dpkg-dist/.rpmnew -- but
only for files marked as configuration, and that marking has to be added after
the bundler runs (openspec/changes/add-linux-package-repos, design.md).

`rpmrebuild` is not packaged for Ubuntu, where the release builds run, so the
rpm half runs in a Fedora container. It rewrites package metadata only, never a
binary, so it has no bearing on which glibc the packages need.

Usage: mark_package_configs.py <dir-or-file> [...]      (defaults to src-tauri/target/release/bundle)
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DEFAULT_BUNDLE = ROOT / "src-tauri" / "target" / "release" / "bundle"
DEB_CONFFILES = ["/etc/apt/sources.list.d/transcriber.list"]
RPM_CONFIG_FILES = ["/etc/yum.repos.d/transcriber.repo"]
FEDORA_IMAGE = "fedora:42"

# The signing key is deliberately not marked: it is ours to replace, and a user
# editing it would only break the repository they are being served from.


def container_runtime() -> str:
    for name in ("docker", "podman"):
        if shutil.which(name):
            return name
    raise SystemExit("no docker or podman found; one is needed to mark the .rpm (see this script's docstring)")


def mark_deb(deb: Path) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tree = Path(tmp) / "tree"
        subprocess.run(["dpkg-deb", "-R", str(deb), str(tree)], check=True)
        conffiles = tree / "DEBIAN" / "conffiles"
        existing = conffiles.read_text().splitlines() if conffiles.exists() else []
        wanted = [p for p in DEB_CONFFILES if p not in existing]
        if not wanted:
            print(f"{deb.name}: already marked")
            return
        conffiles.write_text("\n".join(existing + wanted) + "\n")
        rebuilt = Path(tmp) / deb.name
        subprocess.run(["dpkg-deb", "-b", str(tree), str(rebuilt)], check=True,
                       stdout=subprocess.DEVNULL)
        shutil.move(str(rebuilt), str(deb))
    print(f"{deb.name}: conffiles -> {', '.join(DEB_CONFFILES)}")


def mark_rpm(rpm: Path) -> None:
    runtime = container_runtime()
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        shutil.copy(rpm, work / rpm.name)
        # rpmrebuild hands the generated spec to this script on stdin; it
        # prefixes our file's %files line, which carries an %attr(...) prefix
        # and quotes the path.
        pattern = "|".join(p.replace("/", r"\/") for p in RPM_CONFIG_FILES)
        (work / "addconfig.sh").write_text(
            "#!/bin/sh\n"
            f"sed 's|^\\(%attr([^)]*)\\) \\(\"\\({pattern}\\)\"\\)|%config(noreplace) \\1 \\2|'\n".replace(
                "{pattern}", pattern)
        )
        (work / "addconfig.sh").chmod(0o755)
        subprocess.run([
            runtime, "run", "--rm", "-v", f"{work}:/work:z", FEDORA_IMAGE, "sh", "-c",
            "dnf -q -y install rpmrebuild >/dev/null 2>&1 && "
            "RPMREBUILD_TMPDIR=/work/tmp rpmrebuild --batch "
            "--change-spec-files=/work/addconfig.sh --directory=/work/out "
            f"-p /work/{rpm.name} >/dev/null && "
            # Everything the container wrote is owned by whoever root maps to
            # outside it, which the caller may not be able to delete; hand it
            # back before the temporary directory is cleaned up.
            "chown -R \"$(stat -c '%u:%g' /work)\" /work",
        ], check=True)
        rebuilt = next(iter((work / "out").rglob("*.rpm")), None)
        if rebuilt is None:
            raise SystemExit(f"rpmrebuild produced no package for {rpm.name}")
        shutil.move(str(rebuilt), str(rpm))
    print(f"{rpm.name}: %config(noreplace) -> {', '.join(RPM_CONFIG_FILES)}")


def main(argv: list[str]) -> int:
    targets = [Path(a) for a in argv[1:]] or [DEFAULT_BUNDLE]
    packages = []
    for target in targets:
        if target.is_dir():
            packages += sorted(target.rglob("*.deb")) + sorted(target.rglob("*.rpm"))
        elif target.is_file():
            packages.append(target)
        else:
            raise SystemExit(f"not found: {target}")
    if not packages:
        raise SystemExit(f"no .deb or .rpm found in {', '.join(str(t) for t in targets)}")
    for package in packages:
        (mark_deb if package.suffix == ".deb" else mark_rpm)(package)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
