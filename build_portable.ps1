# Assembles a self-contained, no-installer portable build from the raw
# `cargo tauri build` output: the GUI exe, the sidecar exe, WebView2Loader.dll,
# and the bundled model resources, copied into one extract-and-run folder.
# See openspec/changes/add-portable-build/design.md Decision 2 -- this is
# purely an assembly step after the existing build pipeline (build_sidecar.py,
# fetch_sidecar_resources.py, cargo tauri build), not a new build path.
#
# Usage: .\build_portable.ps1 [-Target x86_64-pc-windows-gnu] [-OutputDir dist\portable\Transcriber] [-Zip]
param(
    [string]$Target = "x86_64-pc-windows-gnu",
    [string]$OutputDir = "dist\portable\Transcriber",
    [switch]$Zip
)
$ErrorActionPreference = "Stop"
$repoRoot = $PSScriptRoot
$releaseDir = Join-Path $repoRoot "src-tauri\target\$Target\release"

$requiredFiles = @("transcriber-gui.exe", "transcriber-sidecar.exe", "WebView2Loader.dll")
foreach ($file in $requiredFiles) {
    if (-not (Test-Path (Join-Path $releaseDir $file))) {
        throw "Missing $file in $releaseDir -- run the build first (see docker\build.ps1 or 'cargo tauri build --target $Target')."
    }
}
$modelDir = Join-Path $repoRoot "src-tauri\resources\model"
if (-not (Test-Path (Join-Path $modelDir "model.bin"))) {
    throw "Missing model.bin under $modelDir -- run fetch_sidecar_resources.py first."
}

$outputPath = Join-Path $repoRoot $OutputDir
if (Test-Path $outputPath) { Remove-Item $outputPath -Recurse -Force }
New-Item -ItemType Directory -Force -Path $outputPath | Out-Null

foreach ($file in $requiredFiles) {
    Copy-Item (Join-Path $releaseDir $file) -Destination $outputPath
}

# Same "resources/model" relative layout tauri.conf.json's bundle.resources
# declares, since sidecar.rs's resolve_model_dir() resolves resource_dir()
# (the exe's own directory, for an unbundled/portable executable) joined
# with "resources/model" -- see src-tauri/src/sidecar.rs.
$outputModelDir = Join-Path $outputPath "resources\model"
New-Item -ItemType Directory -Force -Path $outputModelDir | Out-Null
Copy-Item (Join-Path $modelDir "*") -Destination $outputModelDir -Recurse -Force

Write-Output "Portable build assembled at $outputPath"

if ($Zip) {
    $zipPath = "$outputPath.zip"
    if (Test-Path $zipPath) { Remove-Item $zipPath -Force }
    Compress-Archive -Path $outputPath -DestinationPath $zipPath
    Write-Output "Zipped to $zipPath"
}
