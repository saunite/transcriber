---
name: Transcriber
description: A verbatim record, not a chat app.
colors:
  paper: "#fbfaf6"
  paper-raised: "#ffffff"
  ink: "#1c1a16"
  ink-soft: "#6b6355"
  ink-faint: "#a49c8c"
  rule: "#ddd6c7"
  rule-strong: "#c7bfab"
  live: "#a3271d"
  live-ink: "#fdf4f2"
  manila: "#ecdfb8"
  manila-ink: "#453a1e"
typography:
  body:
    fontFamily: "ui-sans-serif, system-ui, -apple-system, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif"
    fontSize: "15px"
    fontWeight: 400
    lineHeight: 1.5
  label:
    fontFamily: "ui-sans-serif, system-ui, -apple-system, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif"
    fontSize: "0.8125rem"
    fontWeight: 700
    letterSpacing: "0.14em"
  mono:
    fontFamily: "ui-monospace, 'Cascadia Code', 'SF Mono', 'Segoe UI Mono', Consolas, monospace"
    fontSize: "0.75rem"
rounded:
  sm: "3px"
  md: "4px"
  lg: "6px"
spacing:
  sm: "0.5rem"
  md: "1rem"
  lg: "1.75rem"
components:
  button-primary:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.paper}"
    rounded: "{rounded.lg}"
    padding: "0.85rem 1.9rem"
  stamp-live:
    backgroundColor: "{colors.live-ink}"
    textColor: "{colors.live}"
    rounded: "{rounded.sm}"
  note:
    backgroundColor: "{colors.manila}"
    textColor: "{colors.manila-ink}"
---

# Design System: Transcriber

## Overview

**Creative North Star: "The Verbatim Record"**

Transcriber is a courtroom stenographer's transcript, not a chat log. Every screen reads as paper: an off-white page holding ink-black text, ruled hairlines standing in for the folder tabs and rules of a physical document, and exactly one color — a stamp red — reserved for a single meaning: capture is live, right now. Nothing else on the page competes for that red.

The system was chosen over its own runner-up (a calmer, more familiar "digital ship's log" direction) specifically because a verbatim transcript is the most literal, instantly legible object for what this product does: it turns spoken words into a written record. A first-time user should recognize the metaphor before reading a single label.

Speaker source (`SYS` vs `MIC`) is carried by type style, not color — small-caps upright for the system channel, small-caps italic for the microphone — so the one-accent rule never gets diluted into a chat-bubble palette. Errors and status messages are a second, distinct material rather than a second hue: a manila "note" tag, as if a correction slip had been clipped to the page, keeping red's meaning uncontested.

**Key Characteristics:**
- One accent color, one meaning: red is reserved for "recording is live" and appears nowhere else.
- Speaker/source distinction lives in type style (upright vs. italic small caps), never in color.
- Errors and transient status render as a manila note, a second material rather than a second accent.
- Calm by default: no big display type, no marketing hero — this is a working tool, not a pitch.

## Colors

Restrained: a paper-and-ink neutral field carrying almost the entire surface, with one committed accent held to a single, non-negotiable meaning.

### Primary
- **Report Red** (`#a3271d`, dark: `#e0645a`): reserved exclusively for the "LIVE" capture stamp and its focus ring. Never used for anything else — not errors, not hover states, not links — so its appearance always means the same thing: audio is being captured right now.

### Neutral
- **Paper** (`#fbfaf6`, dark: `#17140f`): the page ground.
- **Paper, Raised** (`#ffffff`, dark: `#1f1b14`): panels and the settings drawer, one step lifted off the page ground.
- **Ink** (`#1c1a16`, dark: `#ece5d6`): primary text, and the fill of the primary action button (inverted).
- **Ink, Soft** (`#6b6355`, dark: `#b3a891`): secondary text — hints, labels, inactive tab text. Tinted from ink, never a flat gray.
- **Ink, Faint** (`#a49c8c`, dark: `#746b58`): timestamps and the least important marginalia.
- **Rule** (`#ddd6c7`, dark: `#38321f`): hairline dividers between transcript lines.
- **Rule, Strong** (`#c7bfab`, dark: `#4a4227`): borders on panels, controls, and the drop zone.

### Named Rules
**The One Red Rule.** Report Red means exactly one thing: capture is live. It never appears as a link color, a hover color, or an error color. If a new state seems to need red, it isn't actually the live-capture state, and it doesn't get the color.

**The Note, Not a Badge, Rule.** Status and errors are a manila note (a second material), not a second accent hue. A colored toast would compete with the live-red signal; a note doesn't.

## Typography

**Body Font:** ui-sans-serif / system-ui stack (with Segoe UI, Roboto, Helvetica, Arial fallbacks)
**Label/Mono Font:** ui-monospace stack (Cascadia Code, SF Mono, Segoe UI Mono, Consolas)

**Character:** Workhorse system stacks, deliberately — this is an Operate surface (a tool used while running a meeting), and per this project's own design guidance, system faces serve that register better than an imported display face would. Discipline comes from restraint and scale steps, not a custom typeface.

### Hierarchy
- **Label** (700, 0.8125rem, tracked +0.14em, uppercase): the wordmark and tab names.
- **Stamp** (700, 0.75rem, tracked +0.08em, uppercase): LIVE / STARTING / TRANSCRIBING.
- **Title/Action** (700, 1.0625rem): the primary "Start Live Session" button — the only large, bold text on the page.
- **Body** (400, 0.9375rem, line-height 1.55): transcript line text.
- **Mono/Data** (400, 0.75–0.8125rem, tabular numerals): timestamps and the engine log.

### Named Rules
**The No Display Face Rule.** This system has no headline voice — the wordmark is small and quiet. The transcript content is the only thing allowed to look important.

## Layout

Single-column, page-centered: the transcript "page" is a `42rem`-max-width card centered under a masthead and a two-tab switcher (Live Session / File Transcription). Both tabs share one page metaphor and one event stream from the engine — dropping a file or starting a live session fills the same kind of ruled page, just by a different route.

Settings (model, language, microphone) live in a collapsible drawer above the tabs so they never compete with the transcript itself for attention — opened on demand, not shown by default.

Responsive behavior is minimal by necessity (this is a desktop window, minimum 640×480): a single breakpoint at `30rem` tightens padding and narrows the transcript's margin column rather than reflowing the structure.

## Elevation & Depth

Soft, ambient lift, never a hard block shadow — panels and the primary button sit slightly off the page via a diffuse, offset shadow (`rgba` of the ink color, heavily blurred, pulled tight to the element). Depth signals "this is raised paper," not "this is a UI card floating in space."

### Shadow Vocabulary
- **Panel lift** (`0 6px 18px -12px var(--shadow)`): the active tab's panel, resting.
- **Action lift** (`0 8px 20px -10px var(--shadow)`, deepens on hover): the primary Start button.
- **Note lift** (`0 10px 24px -10px var(--shadow)`): manila notes, which sit above everything else.

### Named Rules
**The Diffuse-Only Rule.** Every shadow has a soft blur and a real offset. A hard, zero-blur shadow never appears in this system — it belongs to a different (neobrutalist) world.

## Shapes

Small, consistent radii (3–6px) everywhere except two deliberate asymmetric exceptions that carry meaning: the active tab's panel has a sharp top-left corner (`border-radius: 0 6px 6px 6px`) so it reads as continuous with the tab above it, and manila notes share the same sharp-corner-first shape (`2px 8px 8px 8px`) as if pinned at that corner. No other element uses an asymmetric radius.

## Components

### Buttons
- **Primary action** ("Start Live Session"): ink-filled, paper text, `6px` radius, `0.85rem 1.9rem` padding, lifts 1px on hover with a deepening shadow. This is the only filled, high-contrast control on the page — reserved for the single most important action per screen.
- **Stop / secondary**: outline only (`1px solid rule-strong`), text `ink-soft`; on hover its border and text shift to Report Red, since stopping a live session is the one secondary action allowed to reference the live-capture color.
- **Tab**: unfilled, uppercase, tracked label; the selected tab gets `paper-raised` background and merges visually into its panel below (shared border, no gap).
- **Settings toggle**: bordered outline pill, `ink-soft` at rest, `ink` when the drawer is open.

### Drop Zone
- Dashed `2px` border in `rule-strong`; on drag-over the border and text shift to Report Red with a `live-ink` tinted background — the only other place red appears, and only transiently, while a file is actually being accepted.

### Transcript Line
- Two-column grid: a `5.5rem` margin column (timestamp, mono, tabular numerals; source tag below it) and the transcript text. New lines fade and rise in (`180ms`, one shared "line arrives" motion). A hairline `rule` divider separates lines; the last line in a list has none.

### Stamps
- **Live**: Report Red on `live-ink`, rotated `-2deg`, a small CSS-drawn dot (not a glyph) before the label. This is the system's one "rubber stamp hits paper" moment (scale-in + rotate, `220ms`) — reserved for this state alone.
- **Starting / Transcribing**: neutral (`ink-soft` on `paper`), unrotated, a flatter fade-and-scale-in. Deliberately calmer than the LIVE stamp so red's arrival still reads as a distinct event.

### Notes (toast/error surface)
- Manila background, dark ink text, asymmetric sharp-corner shape, slides in from the right edge, dismissible by click, auto-clears after 8s.

### Settings Drawer / Fields
- Bordered, `paper-raised` panel; each field is a label (`ink-soft`, small, bold) stacked over its control; selects and text inputs share one border/radius/focus treatment.

## Do's and Don'ts

### Do:
- **Do** keep Report Red to exactly one meaning (live capture). If a new feature needs a "this matters" color, reach for weight or the manila note material first.
- **Do** distinguish SYS/MIC by type style (upright vs. italic small caps), never by introducing a second accent hue.
- **Do** use the diffuse ambient shadow family for anything that needs to feel "lifted off the page"; never a hard offset shadow.
- **Do** keep the primary action button singular per screen — one filled, ink-colored button, everything else outlined or plain.

### Don't:
- **Don't** add a chat-style colored badge/chip for speaker tags — the direction explicitly rejects that pattern.
- **Don't** use Report Red for errors, links, or hover states outside the Stop button's live-capture reference.
- **Don't** give any element besides the LIVE stamp the rotated "stamp impact" motion — it's a signature moment, not a default animation.
- **Don't** introduce a display/headline typeface; this system has no "hero" text register.
