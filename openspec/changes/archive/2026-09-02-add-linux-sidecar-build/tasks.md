## 1. Local freeze and smoke test

- [x] 1.1 Run `build_sidecar.py` inside a Linux Docker container; fix whatever it surfaces (mirroring the two real bugs the Windows freeze needed)
- [x] 1.2 Smoke-test the frozen binary standalone: `--file` on a sample clip, confirm it completes and produces a transcript with no Python interpreter on the host
- [x] 1.3 Smoke-test `--list-devices-json`: confirm it exits 0 and prints valid JSON (an empty device list is fine in a container with no audio hardware)

## 2. CI verification

- [x] 2.1 Trigger `.github/workflows/build-gui.yml` for real (`workflow_dispatch`) and confirm the `ubuntu-latest` job completes and uploads its artifact
- [x] 2.2 Remove the `UNVERIFIED` header comment from `build-gui.yml` once the run passes
