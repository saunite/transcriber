## Context

See proposal.md - Why. What was checked while exploring:

- **The user's icons.** `resources/transcriber-icon-light-blue-bg.png` is 64×64 RGBA and fully opaque, with a rgb(186,244,255) background. `resources/transcriber-icon.png` is the same mark on a transparent background.
- **The full-size source.** `resources/src/transcriber-icon-full-size.xcf` is 805×802 with five layers: `Background` (transparent), two stroke layers, `a`, and a `transcriber` text layer that extends off the canvas and isn't visible in the flattened image. Flattening it with ImageMagick (`magick … -background none -flatten`) gives a crisp 805×802 render of the same mark.
- **The generator.** `cargo tauri icon <png>` produces, for desktop:
  - `32x32.png`, `64x64.png`, `128x128.png`, `128x128@2x.png` (256), and `icon.png` (512)
  - `icon.ico` with 16, 24, 32, 48, 64 and 256 px
  - `icon.icns`

  It also writes `android/`, `ios/`, and ten `Square*Logo.png`/`StoreLogo.png` Windows Store tiles.
- **Upscaling.** Run on the 64 px file, the generator's 512 px output is visibly soft.
- **Today.** `bundle.icon` lists only `icons/icon.png` (32×32) and `icons/icon.ico` (32×32). The `.rpm` installs a single `hicolor/32x32` icon, and the `.desktop` file references it as `Icon=transcriber-gui`.

## Goals / Non-Goals

**Goals:**
- One committed master at 1024×1024, and every platform icon derived from it.
- The icon on every surface Tauri and PyInstaller can set, with no extra tooling in the build.

**Non-Goals:**
- A simplified variant for 16–32 px (see Risks).
- An in-app logo in the UI. The UI follows `DESIGN.md`, so adding a brand mark there is a separate design decision.
- A macOS-specific rounded-rectangle ("squircle") shape with inset padding.
- GitHub's repository social preview, which is set by hand in the repo settings, not from files.

## Decisions

### 1. Export a 1024×1024 master from the `.xcf`, framed tight, on the light-blue background

```
magick resources/src/transcriber-icon-full-size.xcf -background none -flatten -trim +repage \
  -compose over -gravity center -extent '%[fx:max(w,h)*1.24]x%[fx:max(w,h)*1.24]' \
  -background 'rgb(186,244,255)' -flatten -resize 1024x1024 resources/transcriber-icon-1024.png
```

**`-compose over` is required.** Found during implementation: ImageMagick's XCF reader leaves the flattened image with `Compose: None`, and `-extent` uses that method to place the image on the padded canvas. Without the option, the result is a solid light-blue square with no mark (1 colour, 497 bytes), and it still passes a size/opacity/corner-colour check. With it, the output is pixel-identical (`compare -metric AE` = 0) to the same pipeline run through an intermediate PNG, which re-reads with the normal `Compose: Over`.

The command flattens the layers to the canvas, crops to the mark, adds about 12% margin on each side, squares it, puts it on the user's light-blue, and scales it to 1024. The output is committed, so the build never has to read GIMP files.

- **Tight framing vs. the 64 px file's framing.** Compared at 64, 32 and 16 px, the two framings are nearly identical: the mark is about 2.8:1 wide, so its width sets the scale either way. The tight crop comes out slightly larger, so it's used.
- **Light-blue, not transparent.** This was the user's choice of file, and it's the right one. The strokes are black and dark blue, so on a transparent background they would disappear against dark panels, taskbars and docks.
- **Rejected: generating from the 64 px PNG.** Every size above 64 px would be upscaled, which is visibly soft at 512 and also violates the "no upscaled sizes" requirement.

### 2. Regenerate `src-tauri/icons/` with `cargo tauri icon`, keep only the desktop set

Run `cargo tauri icon resources/transcriber-icon-1024.png`, then delete `android/`, `ios/`, `Square*Logo.png` and `StoreLogo.png`, since this app ships to none of those. Point `bundle.icon` at the desktop set:

```json
"icon": ["icons/32x32.png", "icons/128x128.png", "icons/128x128@2x.png", "icons/icon.png", "icons/icon.icns", "icons/icon.ico"]
```

That's Tauri's default list plus `icon.png` (512 px), so Linux packages also install a 512 px icon for HiDPI launchers. Tauri installs each listed PNG into `hicolor/<size>/apps/transcriber-gui.png` for AppImage, `.deb` and `.rpm`; embeds the `.ico` in the Windows executable and the NSIS installer and uninstaller; puts the `.icns` in the `.app` (and so the `.dmg`); and uses these files for the runtime window icon. The existing `.desktop` line, `Icon=transcriber-gui`, stays as it is.

**Rejected: a script that runs the generator and cleans up.** It's two commands run whenever the icon changes, so the README documents them instead (task 4.1).

### 3. The standalone CLI binary gets the icon on Windows and macOS

`build_sidecar.py` passes `--icon src-tauri/icons/icon.ico` on Windows and `--icon src-tauri/icons/icon.icns` on macOS. PyInstaller embeds either format directly, with no Pillow conversion needed. On Linux it passes nothing, because ELF binaries carry no icon. The same frozen binary is both the GUI's sidecar and the CLI archive's `transcriber(.exe)`, so Explorer shows the mark for the CLI too. The icon files come from Decision 2, so the build step order doesn't change: `src-tauri/icons/` is committed.

### 4. README header image

The README's first line becomes a centered `<img src="resources/transcriber-icon-1024.png" width="96" alt="Transcriber icon">` above the title. It uses the master at display width, which stays crisp on HiDPI screens, and the image is in the repo, so it renders on GitHub with no external host.

## Risks / Trade-offs

- **[Trade-off]** At 16 px and 32 px (title bars, the Windows taskbar's small mode, file-manager list views), the wide mark blurs: the superscript "a" and the thinnest sound wave disappear. That's inherent to a 2.8:1 mark in a square, not to the export. → A simplified small-size variant (for example the "v" check alone) would fix it; that's a design task for the user, deferred.
- **[Risk]** macOS. Recent macOS versions expect icons shaped as rounded rectangles with inset padding, and may show a full-bleed square icon inside a grey rounded plate. → No Mac is available to check; this goes on the macOS testers' list in `03`'s README note. A rounded variant for the `.icns` can follow if testers report it.
- **[Trade-off]** The committed master is a generated file. If the `.xcf` changes, the master must be re-exported with Decision 1's command, which the README note records.
