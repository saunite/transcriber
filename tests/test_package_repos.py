#!/usr/bin/env python3
"""The apt and dnf repositories published with each release, and the way the
installed repository file survives upgrades (openspec/changes/add-linux-package-repos).

Everything runs in throwaway containers with throwaway keys and dummy packages;
nothing here touches this machine's package manager, keyring or the project's
real signing key. Skips with a message when no container runtime is available.

Checks:
- a signed flat apt repository reached through GitHub's redirect shape installs,
  and is refused when its index is tampered with or signed by another key;
- a dnf repository whose metadata points at a second host installs from there,
  and is refused when the metadata is signed by another key;
- mark_package_configs.py makes the repository file a dpkg conffile and an rpm
  %config(noreplace) file, so an edited file survives an upgrade and an
  untouched one is updated.

Run: python tests/test_package_repos.py
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEB_CONFFILE = "/etc/apt/sources.list.d/transcriber.list"
RPM_CONFIG = "/etc/yum.repos.d/transcriber.repo"
DEBIAN = "debian:12"
FEDORA = "fedora:42"


class Skip(Exception):
    pass


def runtime() -> str:
    for name in ("podman", "docker"):
        if shutil.which(name):
            return name
    raise Skip("no podman or docker; install one to run the repository checks")


def run_in(image: str, script: str, mount: Path | None = None) -> str:
    """Run a script in a container, returning its combined output."""
    args = [runtime(), "run", "--rm"]
    if mount:
        args += ["-v", f"{mount}:/p:z"]
    args += [image, "bash", "-c", script]
    done = subprocess.run(args, capture_output=True, text=True, timeout=1800)
    return done.stdout + done.stderr


APT_REPO = r"""
set -e
export DEBIAN_FRONTEND=noninteractive
apt-get -qq update >/dev/null && apt-get -qq install -y dpkg-dev apt-utils gnupg python3 >/dev/null
echo "127.0.0.1 ghlike cdnlike" >> /etc/hosts
mkdir -p /w/pkg/DEBIAN /w/assets /w/keys && cd /w
printf 'Package: spike\nVersion: 1.0\nArchitecture: amd64\nMaintainer: s <s@e.com>\nDescription: d\n' > pkg/DEBIAN/control
dpkg-deb -b pkg assets/spike_1.0_amd64.deb >/dev/null
export GNUPGHOME=/w/keys && chmod 700 /w/keys
gpg --batch --quiet --passphrase '' --quick-gen-key 'Spike <s@e.com>' default default never
gpg --armor --export > assets/key.asc
sign() { cd /w/assets && dpkg-scanpackages --multiversion . > Packages 2>/dev/null && gzip -kf Packages \
         && apt-ftparchive release . > Release && gpg --batch --yes --clearsign ${1:+--local-user "$1"} -o InRelease Release; }
sign
cat > /w/serve.py <<'PY'
import http.server, threading, os
class GH(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        n = os.path.basename(self.path)
        loc = (f"http://ghlike:8080/releases/download/v1.0/{n}"
               if self.path.startswith("/releases/latest/download/") else f"http://cdnlike:8081/blob/{n}?sig=x")
        self.send_response(302); self.send_header("Location", loc); self.end_headers()
    do_HEAD = do_GET
    def log_message(self, *a): pass
class CDN(http.server.SimpleHTTPRequestHandler):
    def translate_path(self, p): return os.path.join("/w/assets", os.path.basename(p.split("?")[0]))
    def log_message(self, *a): pass
threading.Thread(target=lambda: http.server.HTTPServer(("0.0.0.0", 8080), GH).serve_forever(), daemon=True).start()
http.server.HTTPServer(("0.0.0.0", 8081), CDN).serve_forever()
PY
python3 /w/serve.py & sleep 1
mkdir -p /etc/apt/keyrings && gpg --dearmor < /w/assets/key.asc > /etc/apt/keyrings/spike.gpg
echo "deb [signed-by=/etc/apt/keyrings/spike.gpg] http://ghlike:8080/releases/latest/download/ ./" > /etc/apt/sources.list.d/spike.list
only() { apt-get update -o Dir::Etc::sourcelist=/etc/apt/sources.list.d/spike.list -o Dir::Etc::sourceparts=- "$@"; }
only >/dev/null 2>&1 && apt-get install -y spike >/dev/null 2>&1 && dpkg -s spike >/dev/null 2>&1 && echo "MARK-INSTALLED"
sed -i 's/Version: 1.0/Version: 9.9/' /w/assets/Packages && gzip -kf /w/assets/Packages
rm -rf /var/lib/apt/lists/*
only 2>&1 | grep -qiE "hash sum|unexpected size|not signed" && echo "MARK-REFUSED-TAMPER"
cd /w/assets && gpg --batch --quiet --passphrase '' --quick-gen-key 'Evil <e@e.com>' default default never
sign e@e.com
rm -rf /var/lib/apt/lists/*
only 2>&1 | grep -qiE "no_pubkey|not signed" && echo "MARK-REFUSED-WRONGKEY"
"""

DNF_REPO = r"""
set -e
dnf -q -y install createrepo_c rpm-build rpm-sign gnupg2 python3 >/dev/null 2>&1
echo "127.0.0.1 pageslike cdnlike" >> /etc/hosts
mkdir -p /w/{pages,assets,keys,rb/SPECS} && cd /w
cat > rb/SPECS/s.spec <<'EOF'
Name: spike
Version: 1.0
Release: 1
Summary: s
License: MIT
BuildArch: noarch
%description
d
%install
mkdir -p %{buildroot}/usr/share/spike && echo hi > %{buildroot}/usr/share/spike/f
%files
/usr/share/spike/f
EOF
rpmbuild -bb --define "_topdir /w/rb" rb/SPECS/s.spec >/dev/null 2>&1
cp rb/RPMS/noarch/*.rpm assets/ && cp assets/*.rpm pages/
export GNUPGHOME=/w/keys && chmod 700 /w/keys
gpg --batch --quiet --passphrase '' --quick-gen-key 'Spike <s@e.com>' default default never
gpg --armor --export > pages/key.asc
createrepo_c --baseurl "http://cdnlike:8081/blob/" /w/pages >/dev/null && rm -f /w/pages/*.rpm
gpg --batch --yes --detach-sign --armor /w/pages/repodata/repomd.xml
cat > /w/serve.py <<'PY'
import http.server, threading, os
class Pages(http.server.SimpleHTTPRequestHandler):
    def translate_path(self, p): return os.path.join("/w/pages", p.lstrip("/").split("?")[0])
    def log_message(self, *a): pass
class CDN(Pages):
    def translate_path(self, p): return os.path.join("/w/assets", os.path.basename(p.split("?")[0]))
threading.Thread(target=lambda: http.server.HTTPServer(("0.0.0.0", 8080), Pages).serve_forever(), daemon=True).start()
http.server.HTTPServer(("0.0.0.0", 8081), CDN).serve_forever()
PY
python3 /w/serve.py & sleep 1
rpm --import /w/pages/key.asc
printf '[spike]\nname=s\nbaseurl=http://pageslike:8080/\nenabled=1\nrepo_gpgcheck=1\ngpgcheck=0\ngpgkey=http://pageslike:8080/key.asc\n' > /etc/yum.repos.d/spike.repo
dnf -y install spike >/dev/null 2>&1 && rpm -q spike >/dev/null && echo "MARK-INSTALLED"
grep -o 'xml:base="http://cdnlike:8081/blob/"' <(for f in /w/pages/repodata/*primary.xml*; do case "$f" in *.zst) zstd -dc "$f" 2>/dev/null;; *.gz) zcat "$f";; *) cat "$f";; esac; done) >/dev/null && echo "MARK-PAYLOAD-ELSEWHERE"
dnf -y remove spike >/dev/null 2>&1
gpg --batch --quiet --passphrase '' --quick-gen-key 'Evil <e@e.com>' default default never
gpg --batch --yes --detach-sign --armor --local-user e@e.com -o /w/pages/repodata/repomd.xml.asc /w/pages/repodata/repomd.xml
dnf clean all >/dev/null 2>&1
dnf -y install spike 2>&1 | grep -qiE "signature|gpg|not verif" && echo "MARK-REFUSED-WRONGKEY"
"""

DEB_UPGRADE = rf"""
set -e
export DEBIAN_FRONTEND=noninteractive
dpkg -i /p/spike_1.0_amd64.deb >/dev/null
sed -i 's/^deb /# deb /' {DEB_CONFFILE}
dpkg -i --force-confdef /p/spike_2.0_amd64.deb >/dev/null 2>&1
grep -q '^# deb ' {DEB_CONFFILE} && echo "MARK-EDIT-KEPT"
ls {DEB_CONFFILE}.dpkg-dist >/dev/null 2>&1 && echo "MARK-NEW-BESIDE"
dpkg -P spike >/dev/null 2>&1
dpkg -i /p/spike_1.0_amd64.deb >/dev/null && dpkg -i /p/spike_2.0_amd64.deb >/dev/null 2>&1
grep -q 'v2' {DEB_CONFFILE} && echo "MARK-UNTOUCHED-UPDATED"
dpkg -P spike >/dev/null 2>&1
[ -e {DEB_CONFFILE} ] || echo "MARK-PURGED"
"""

RPM_UPGRADE = rf"""
set -e
rpm -i /p/spike-1.0-1.noarch.rpm
sed -i 's/^enabled=1/enabled=0/' {RPM_CONFIG}
rpm -U /p/spike-2.0-1.noarch.rpm 2>/dev/null
grep -q '^enabled=0' {RPM_CONFIG} && echo "MARK-EDIT-KEPT"
ls {RPM_CONFIG}.rpmnew >/dev/null 2>&1 && echo "MARK-NEW-BESIDE"
rpm -e spike && rm -f {RPM_CONFIG}*
rpm -i /p/spike-1.0-1.noarch.rpm && rpm -U /p/spike-2.0-1.noarch.rpm 2>/dev/null
grep -q 'v2' {RPM_CONFIG} && echo "MARK-UNTOUCHED-UPDATED"
rpm -e spike
[ -e {RPM_CONFIG} ] || echo "MARK-ERASED"
"""


def expect(output: str, *marks: str) -> None:
    missing = [m for m in marks if f"MARK-{m}" not in output]
    if missing:
        raise AssertionError(f"missing {', '.join(missing)}; last output:\n" + output[-1200:])


def check_apt_repository() -> str:
    expect(run_in(DEBIAN, APT_REPO), "INSTALLED", "REFUSED-TAMPER", "REFUSED-WRONGKEY")
    return "installs through the redirects; refuses a tampered index and a wrong key"


def check_dnf_repository() -> str:
    expect(run_in(FEDORA, DNF_REPO), "INSTALLED", "PAYLOAD-ELSEWHERE", "REFUSED-WRONGKEY")
    return "installs with the package on another host; refuses a wrong key"


def _dummy_packages(out: Path) -> None:
    """Two versions of a dummy .deb and .rpm carrying the repository file paths."""
    for version, body in (("1.0", "deb http://example/ ./ # v1"), ("2.0", "deb http://example/ ./ # v2")):
        tree = out / f"deb{version}"
        (tree / "DEBIAN").mkdir(parents=True)
        (tree / DEB_CONFFILE.lstrip("/")).parent.mkdir(parents=True)
        (tree / DEB_CONFFILE.lstrip("/")).write_text(body + "\n")
        (tree / "DEBIAN" / "control").write_text(
            f"Package: spike\nVersion: {version}\nArchitecture: amd64\nMaintainer: s <s@e.com>\nDescription: d\n")
        subprocess.run(["dpkg-deb", "-b", str(tree), str(out / f"spike_{version}_amd64.deb")],
                       check=True, stdout=subprocess.DEVNULL)
    for version, body in (("1.0", "[spike]\nenabled=1\nbaseurl=v1"), ("2.0", "[spike]\nenabled=1\nbaseurl=v2")):
        spec = out / f"s{version}.spec"
        spec.write_text(f"""Name: spike
Version: {version}
Release: 1
Summary: s
License: MIT
BuildArch: noarch
%description
d
%install
mkdir -p %{{buildroot}}{Path(RPM_CONFIG).parent}
printf '{body}\\n' > %{{buildroot}}{RPM_CONFIG}
%files
{RPM_CONFIG}
""")
        subprocess.run(["rpmbuild", "-bb", "--define", f"_topdir {out}/rb", str(spec)],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for built in (out / "rb" / "RPMS" / "noarch").glob("*.rpm"):
        shutil.move(str(built), str(out / built.name))


def check_config_marking() -> str:
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp)
        _dummy_packages(out)
        subprocess.run([sys.executable, str(ROOT / "mark_package_configs.py"), str(out)],
                       check=True, stdout=subprocess.DEVNULL, timeout=1800)

        conffiles = subprocess.run(["dpkg-deb", "-I", str(out / "spike_1.0_amd64.deb"), "conffiles"],
                                   capture_output=True, text=True).stdout
        assert DEB_CONFFILE in conffiles, f"the .deb was not marked: {conffiles!r}"
        flags = subprocess.run(["rpm", "-qp", "--qf", "[%{FILENAMES} %{FILEFLAGS}\n]",
                                str(out / "spike-1.0-1.noarch.rpm")], capture_output=True, text=True).stdout
        assert f"{RPM_CONFIG} 17" in flags, f"the .rpm was not marked %config(noreplace): {flags!r}"

        expect(run_in(DEBIAN, DEB_UPGRADE, mount=out),
               "EDIT-KEPT", "NEW-BESIDE", "UNTOUCHED-UPDATED", "PURGED")
        expect(run_in(FEDORA, RPM_UPGRADE, mount=out),
               "EDIT-KEPT", "NEW-BESIDE", "UNTOUCHED-UPDATED", "ERASED")
    return "an edited repository file survives an upgrade; an untouched one is updated; removal cleans up"


def main() -> int:
    checks = [
        ("apt repository", check_apt_repository),
        ("dnf repository", check_dnf_repository),
        ("repository file is a config file", check_config_marking),
    ]
    failures = 0
    for name, check in checks:
        try:
            print(f"PASS  {name}: {check()}", flush=True)
        except Skip as exc:
            print(f"SKIP  {name}: {exc}", flush=True)
        except (AssertionError, subprocess.SubprocessError) as exc:
            failures += 1
            print(f"FAIL  {name}: " + "\n      ".join(str(exc).splitlines()[:6]), flush=True)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
