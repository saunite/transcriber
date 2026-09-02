## 1. Container-native build

- [ ] 1.1 Add `.dockerignore` (excludes `src-tauri/target`, `.git`, and other non-source directories from the Docker build context)
- [ ] 1.2 Update `docker/tauri-build.Dockerfile`: add `COPY . /app` (with `WORKDIR /app`) as the final layer, after the existing toolchain-install layers
- [ ] 1.3 Update `docker/build.ps1`: drop the `-v "${PWD}:/app"` bind mount; run the build in a named (not `--rm`) container

## 2. Output handoff

- [ ] 2.1 After a successful build, `docker cp` the container's `src-tauri/target/x86_64-pc-windows-gnu/release/bundle/` directory back to the same host-side path
- [ ] 2.2 Remove the named container (`docker rm -f`) on both the success and failure paths, so repeated runs don't leak stopped containers

## 3. Verification

- [ ] 3.1 Run `.\docker\build.ps1` end-to-end; confirm the installer lands at the same host path as before and installs/runs correctly
- [ ] 3.2 Record the new wall-clock build time against the previous ~40-50 minute baseline
