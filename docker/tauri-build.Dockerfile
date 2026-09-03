# Cross-build environment for the Tauri desktop GUI
# (openspec/changes/add-tauri-gui). Produces the Windows NSIS installer via
# GNU/mingw-w64 cross-compilation (no MSVC/Visual Studio/Wine needed) and
# the Linux AppImage/deb natively, from one Linux-based image -- built to
# work around this machine's execution-policy block on Rust toolchain
# binaries (see openspec/changes/add-tauri-gui/tasks.md).
#
# UNVERIFIED until this image actually builds and successfully produces
# both installers -- first real test happens when this is built and run.

FROM rust:1-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    pkg-config \
    curl \
    wget \
    file \
    libssl-dev \
    libwebkit2gtk-4.1-dev \
    libxdo-dev \
    libayatana-appindicator3-dev \
    librsvg2-dev \
    nsis \
    gcc-mingw-w64-x86-64 \
    binutils-mingw-w64-x86-64 \
    && rm -rf /var/lib/apt/lists/*

RUN rustup target add x86_64-pc-windows-gnu \
    && cargo install --locked tauri-cli --version "^2"

# Copied into the image's own (native, Linux) filesystem rather than
# bind-mounted from the Windows host -- see
# openspec/changes/fix-docker-build-filesystem/design.md. cargo/makensis
# I/O against a bind-mounted NTFS checkout was the dominant cost of a
# Windows build, not actual compilation/packaging work.
WORKDIR /app
COPY . /app
