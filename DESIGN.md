---
name: Transcriber
description: A chart recorder, not a chat log.
colors:
  stock: "#e9f0ea"
  stock-edge: "#dde6de"
  stock-raised: "#f4f8f4"
  grid-major: "#cbb4ac"
  grid-minor: "rgb(203 180 172 / 0.35)"
  gutter: "#e3ebe4"
  pen-sys: "#16233a"
  pen-mic: "#b4231d"
  ink: "#17231b"
  ink-soft: "#4e6152"
  ink-faint: "#7c8f80"
  panel: "#d5ddd4"
  panel-edge: "#bcc7bb"
  panel-deep: "#c6cfc5"
typography:
  body:
    fontFamily: "ui-sans-serif, system-ui, -apple-system, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif"
    fontSize: "15px"
    fontWeight: 400
    lineHeight: 1.5
  label:
    fontFamily: "ui-sans-serif, system-ui, -apple-system, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif"
    fontSize: "0.6875rem"
    fontWeight: 700
    letterSpacing: "0.1em"
  mono:
    fontFamily: "ui-monospace, 'Cascadia Code', 'SF Mono', 'Segoe UI Mono', Consolas, monospace"
    fontSize: "0.6875rem"
rounded:
  sm: "1px"
  md: "2px"
  lg: "3px"
spacing:
  sm: "0.5rem"
  md: "0.9rem"
  lg: "1.5rem"
components:
  button-record:
    backgroundColor: "{colors.pen-sys}"
    textColor: "{colors.stock}"
    rounded: "{rounded.lg}"
    padding: "0.7rem 1rem"
  button-quiet:
    backgroundColor: "{colors.stock-raised}"
    textColor: "{colors.ink-soft}"
    rounded: "{rounded.md}"
    padding: "0.35rem 0.6rem"
  note:
    backgroundColor: "{colors.pen-sys}"
    textColor: "{colors.stock}"
    rounded: "{rounded.md}"
---

# Design System: Transcriber

## Overview

**Creative North Star: "The Chart Recorder"**

Transcriber reads as an instrument, not an app: a paper chart mounted on a physical body, two ink pens marking a calibrated time axis, a gridded roll advancing underneath. The window is minimized during the meeting it records — nobody watches text arrive line by line — so the entire visual system is built for the moment *after*: glancing back at a chart and reading what happened, including the silences, at their true scale.

This replaced an earlier "verbatim transcript" direction (courtroom-stenographer paper, a single stamp-red accent) that spent its hero moment on a screen no one is looking at during capture. The chart-recorder world keeps the instinct toward a calm, non-chat metaphor but relocates the drama: two pens (`SYS` and `MIC`), each with its own ink color, draw directly onto ruled stock, and a "pen lift" state exists specifically so a stalled engine is never visually indistinguishable from a quiet room — a real bug class the old chat-log metaphor could not represent.

The ruling lives in the time gutter, not across the reading column, so the chart's calibration is always visible without ever competing with the transcript text for the same pixels — a rule this build states directly in its own CSS.

**Key Characteristics:**
- Two pen inks, not one accent: navy `SYS` and red `MIC`, distinguished by hue because they are simultaneous, independent traces on one axis, not competing meanings.
- Silence is legible, not hidden: chart speed rescales the time axis continuously so a session's true rhythm (dense stretches, six-minute silences) survives being glanced at.
- The instrument's own state (pen up / pen down / pen lifted mid-run) is drawn as a visibly distinct pen position and color, never a text badge layered on top.
- Grid confined to the gutter: the ruled scale never crosses into the reading column.
- No waveform, no chat bubbles: the transcribed text itself is the trace.

## Colors

A muted chart-stock green-white field with a warm-red printed grid, mounted in a cooler green instrument body, carrying two independent pen inks.

### Primary
- **SYS Ink** (`#16233a`, deep navy-black): the system-audio pen. Used for its trace text, its swatch, the record button fill, the focus ring, and the "pens down" states. The dominant, default-active color of the instrument.
- **MIC Ink** (`#b4231d`, warm red): the microphone pen. Used for its trace text and swatch, and reused — deliberately, as the instrument's one fault color — for the pen-lift (stalled) state and error/detail text.

### Neutral
- **Stock** (`#e9f0ea`): the chart paper itself — background of the chart area and the "reading" ground.
- **Stock, Raised** (`#f4f8f4`): inputs and the drop zone, one step lighter than the stock they sit on.
- **Stock, Edge** (`#dde6de`): the chart area's own border, distinct from the panel edges around it.
- **Gutter** (`#e3ebe4`): the fill behind the time-ruling column.
- **Grid, Major** (`#cbb4ac`): the heavier ruling line (every 60px) in the time gutter — a warm red-brown, cool-stock's complement.
- **Grid, Minor** (`rgb(203 180 172 / 0.35)`): the finer ruling (every 12px), built as grid-major's own RGB at 0.35 alpha rather than a second hex — the two weights share one hue by construction, not by matching two independently-picked colors.
- **Panel** (`#d5ddd4`): the instrument body — title block, rail, debug panel — a step cooler and darker than the chart stock it frames.
- **Panel, Edge** (`#bcc7bb`): borders and dividers throughout the instrument body.
- **Panel, Deep** (`#c6cfc5`): the mode-switch track background, recessed relative to the panel.
- **Ink** (`#17231b`): primary text on stock, tinted from the chart's green hue rather than flat gray.
- **Ink, Soft** (`#4e6152`): labels, hints, secondary text, and inactive states.
- **Ink, Faint** (`#7c8f80`): the least prominent marginalia (disabled affordances, unarmed pen states).

### Named Rules
**The Gutter-Only Grid Rule.** The ruled scale lives exclusively in the time gutter. A grid printed across the reading column is true to physical chart paper but hostile to the moment this app exists for — reading the transcript afterward — so the calibration and the prose never share pixels.

**The Two-Pen Rule.** SYS and MIC each own one ink color, used consistently for their swatch, trace text, and pen mark. No third pen color is introduced for any other state; the pen-lift fault state reuses MIC's red rather than adding a color, because a lifted pen is drawn as a state of the mechanism, not a new signal.

## Typography

**Body Font:** ui-sans-serif / system-ui stack (Segoe UI, Roboto, Helvetica, Arial fallbacks)
**Label/Mono Font:** ui-monospace stack (Cascadia Code, SF Mono, Segoe UI Mono, Consolas)

**Character:** Workhorse system stacks throughout — no imported or bundled typeface. This is a hard product constraint (no build step, no network dependency at first launch), not a stylistic default; the direction contract's call for "condensed caps on labels" is carried instead by uppercase + wide tracking on the system sans, a cited adaptation recorded directly in `style.css` above `.tb-label, .rail-label`.

### Hierarchy
- **Label** (700, 0.6875rem, tracked +0.1em, uppercase): title-block field labels, rail field labels, tab names, pen state text.
- **Wordmark** (700, 0.8125rem, tracked +0.16em, uppercase): the single instance of the app name.
- **Body/Trace** (400, 15px base / trace text at inherited size, line-height 1.5): transcript line text, colored per-pen.
- **Mono/Data** (400, 0.625–0.75rem, tabular numerals): timestamps in the trace's time column, pen names, chart-speed readout, debug log.

### Named Rules
**The No Display Face Rule.** Nothing on this screen is large, bold display type. The wordmark is small and quiet; the trace text is the only content ever meant to hold attention.

## Layout

A two-region instrument under a title block. The title block (record-to path, model, language) spans the full width as one row. Below it, `.instrument` is a CSS grid: a fixed-width rail (`16.5rem`, narrowing to `13.5rem` under `52rem`) carrying transport, pen arming, chart speed, and filters, beside a flexible chart area that fills the remainder. A collapsible engine-log panel (`<details>`) sits full-width at the bottom, closed by default, capped at `40vh` (`30vh` under short windows).

The chart itself is a scrolling roll (`<ol class="roll">`) with a fixed gutter width (`6.75rem`, `5.75rem` narrow) holding the time ruling; each transcript line's vertical position is set inline by `main.js` from elapsed time × chart scale, not by document flow order alone — literalizing the "advancing roll" metaphor. Minimum window is 640×480; the single breakpoint at `52rem` narrows the rail and gutter rather than reflowing the structure.

## Elevation & Depth

Soft, ambient lift only — the record button and notes sit slightly proud of the instrument via a diffuse, heavily-blurred shadow tinted from ink (`--shadow: rgba(23, 35, 27, 0.22)`), never a hard offset block shadow. Most of the surface (panel, chart, rail) is flat; elevation is reserved for the two elements that need to read as "sitting above" the instrument: the primary record action and toast notes.

### Shadow Vocabulary
- **Record lift** (`0 5px 14px -8px var(--shadow)`, deepens to `0 8px 18px -8px` on hover): the primary record button.
- **Note lift** (`0 10px 24px -12px var(--shadow)`): toast notes sliding in from the right edge.

### Named Rules
**The Diffuse-Only Rule.** Every authored shadow is soft-blurred with a real offset; a hard zero-blur shadow never appears here — it belongs to a different, neobrutalist world.

## Shapes

Small, near-uniform radii (1–3px) throughout, closer to a physical instrument's machined edges than to a soft app UI. Pen swatches and the record/stop/checkbox marks share a single small clip-path "nib" shape (a flattened pentagon, drawn in CSS, not a glyph) reused for the record button's pen icon and the run-state dot — the same mark stands for "this pen" wherever it appears.

## Components

### Buttons
- **Primary (Start recording):** SYS-ink filled, stock-colored text, `3px` radius, `0.7rem 1rem` padding, lifts 1px on hover with a deepening shadow. Carries the drawn pen-nib icon. The only filled, high-contrast control per screen.
- **Quiet (Stop, Browse):** `stock-raised` background, `ink-soft` text, `1px` bordered, `2px` radius — the default secondary treatment; border and text darken to `ink` on hover.
- **Mode tab:** unfilled, uppercase, tracked; the selected tab gets a `stock` background and an inset bottom border in `pen-sys` rather than a filled pill.

### Inputs / Fields
- **Style:** `stock-raised` background, `1px solid panel-edge` border, `2px` radius, `0.8125rem` text. Uniform across text, number, search, and select inputs.
- **Focus:** border shifts to `--focus` (`pen-sys`); no glow or ring on inputs, though `:focus-visible` elsewhere uses a `2px` outline.

### Transport / Pens
- **Run state:** a drawn pen-nib dot that changes color and vertical position per state — soft ink-soft raised for idle/loaded, SYS-navy lowered-flat for listening, MIC-red lowered for advancing, MIC-red raised for pen-lift (the fault). The instrument's mechanism changes; nothing is layered on top as a badge.
- **Pen row (SYS/MIC):** a `3px`-wide color swatch, mono pen name, description, and state text; unarmed pens desaturate to `panel-edge`/`ink-soft`.

### Chart / Trace
- **Roll:** the scrolling chart surface; grid ruling confined to the gutter (see Named Rules, Colors).
- **Trace line:** two-column grid (time column + text), a `1px` left rule with a small drawn pen-mark tick colored per source, text colored per pen. New lines animate in with `mark-lands` (260ms, slide + fade — "a mark landing on the paper"), the system's one authored line-arrival motion.
- **Marks scale mode:** at compressed chart speeds, trace text and source labels hide and each line collapses to a colored mark only — the session's shape becomes readable at a glance, per the signature "chart speed" interaction.
- **Gap note:** a small mono label naming a silence's duration, placed inline on the axis where the silence occurred.

### Notes (toast)
- SYS-ink filled, stock text, `2px` radius, slides in from the right, dismissible by click.

### Drop Zone
- Dashed `1px` border in `panel-edge`, `stock-raised` background; on drag-over the border solidifies and shifts to `pen-sys` (not `pen-mic`) with text darkening to `ink` — the drop affordance references the SYS pen, not the live-fault red.

## Do's and Don'ts

### Do:
- **Do** keep the two pen inks (`pen-sys` navy, `pen-mic` red) exclusive to their own source — trace text, swatches, and marks always match their pen.
- **Do** confine ruled grid lines to the time gutter; never print a grid across the text-reading column.
- **Do** represent instrument state (idle / listening / advancing / pen-lift) as a change to the pen mark itself (color + position), never as a text badge stacked on top of unchanged chrome.
- **Do** use the diffuse ambient shadow family for anything that needs to read as "lifted off the instrument"; never a hard offset shadow.

### Don't:
- **Don't** add a third accent color; every new state maps onto SYS, MIC, or a neutral ink step.
- **Don't** reintroduce a chat-log or chat-bubble treatment for speaker turns — the direction explicitly refuses that pattern.
- **Don't** bundle or fetch a display/condensed webfont for labels; the system-sans + uppercase + tracking treatment is the resolved substitute, not a placeholder.
- **Don't** drive any meter or pen position from audio amplitude — the event contract carries no audio levels; pen motion is chunk-arrival cadence only, and a true level meter is a named future backend cost, not something to fake visually.
