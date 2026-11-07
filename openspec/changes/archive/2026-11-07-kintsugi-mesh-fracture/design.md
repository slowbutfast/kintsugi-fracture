---
version: alpha
name: Windows XP Luna Retro Minimalist
description: Early-2000s desktop computing aesthetic (Windows XP Luna) married with a clean, focused 3D generative studio workflow.
colors:
  primary: "#0058ee"
  secondary: "#3a6ea5"
  background: "#3a6ea5"
  surface: "#ece9d8"
  text:
    primary: "#222222"
    muted: "#555555"
  border: "#918e82"
  status:
    success: "#3e8e18"
    warning: "#ffd700"
    error: "#e81123"
typography:
  fontFamily:
    sans: 'Tahoma, "Segoe UI", sans-serif'
    mono: '"Courier New", monospace'
  scale:
    h1: "12px, weight 700"
    h2: "11px, weight 700"
    body: "11px, weight 400"
    caption: "10px, weight 400"
spacing:
  xs: "2px"
  sm: "4px"
  md: "8px"
  lg: "12px"
  xl: "16px"
rounded:
  sm: "0px"
  md: "3px"
  lg: "6px"
  full: "9999px"
---

# Design — Kintsugi Studio 2001

The authoritative full visual specification and token source is the repository
root [`DESIGN.md`](../../../../DESIGN.md). This artifact records how that system
is applied to the user-facing GUI introduced by `retro-web-gui`.

## 1. Visual Overview & Philosophy

- **Aesthetic tone:** nostalgic, tactile early-2000s desktop utility; cream
  chrome and royal-blue titlebar floating above a muted blue desktop.
- **Target surfaces:** a single-window local web app served at
  `http://localhost:8000`, with a large recessed WebGL viewport.
- **Visual references:** Windows XP Luna titlebar and bevels, classic Tahoma
  UI text, and a dark studio viewport for inspecting ceramic and gold PBR
  materials.

## 2. Color System & Contrast Rationale

| Token | Value | Semantic role | Paired background | Approx. contrast | Note |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `text.primary` | `#222222` | Body and labels | `#ece9d8` | 13.04:1 | AA/AAA |
| `text.muted` | `#555555` | Captions, hints | `#ece9d8` | 6.11:1 | AA |
| `titlebar-start` | `#0058ee` | Titlebar, left stop | `#ffffff` title text | 5.78:1 | AA |
| `titlebar-mid` | `#3593ff` | Titlebar, mid stop | `#ffffff` title text | 3.10:1 | Decorative gradient stop; title text is bold with shadow |
| `titlebar-end` | `#072a8c` | Titlebar, right stop | `#ffffff` title text | 12.22:1 | AAA |
| `action-end` | `#3e8e18` | Fracture button | `#ffffff` button text | 4.13:1 | Bold button label with text shadow |
| `ceramic-body` | `#f8f6f0` | 3D ceramic preview | `#1a1f2c` viewport | 15.23:1 | High separation |

The titlebar and action-button gradients come directly from `DESIGN.md`. Their
lightest gradient stops are decorative/glossy and sit slightly below the 4.5:1
normal-text threshold; bold labels and the required text shadow preserve
legibility. No non-token colour is introduced in the GUI.

## 3. Typography Hierarchy

| Level | Family | Size | Weight | Line height | Usage |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `title` | Tahoma / Segoe UI | `12px` | `700` | `1.2` | Window title |
| `label` | Tahoma / Segoe UI | `11px` | `700` | `1.2` | Panel headings, fields, buttons |
| `body` | Tahoma / Segoe UI | `11px` | `400` | `1.3` | Menu items, controls, body copy |
| `status` | Tahoma / Segoe UI | `10px` | `400` | `1.1` | Status-bar cells |
| `code` | Courier New | `11px` | `400` | `1.2` | Numeric readouts |

## 4. Component Anatomy & States

### Window frame and titlebar

- **Placement:** centred on the blue desktop; 6px top corners, squared bottom,
  3px raised bevel.
- **States:** normal; maximized (fills desktop); minimized (titlebar only).
- **Close button:** coral-red `#e81123` hover state.

### Menu bar

- **Placement:** directly below the titlebar.
- **Items:** `File(F)`, `Presets(P)`, `Mode(M)`, `Help(H)` with underlined
  mnemonics.
- **Hover:** white raised face with a 1px shadow border.

### Inset wells

- **Placement:** viewport and parameter readouts.
- **Border:** `#918e82` top/left and `#ffffff` bottom/right, 2px, producing a
  recessed cavity.
- **Viewport overflow:** hidden, so the WebGL canvas cannot clip outside the
  well.

### Slider and inputs

- **Track:** 4px white groove with a 1px `#808080` border.
- **Thumb:** 12×20px cream rectangle with a 2px outset white bevel.
- **Focus:** visible 1px dotted dark outline with 1px offset.
- **Cursor:** `ew-resize` for the slider, `default` for chrome.

### Primary fracture button

- **Idle:** green gradient `#70c040` → `#3e8e18`, 1px `#286010` border,
  3px radius, white bold text with shadow.
- **Hover:** brightness increase.
- **Active:** inverted/pressed gradient with inset shadow.
- **Busy/disabled:** desaturated, cursor `wait`, with a retro processing modal
  in the viewport.

### Status bar

- **Placement:** bottom strip, three recessed cells.
- **Content:** operation status; face/part and volume metrics; kernel metadata
  (`Manifold3D v3.5`).

## 5. Responsive Layout & Breakpoints

| Viewport | Breakpoint | Layout pattern | Rules |
| :--- | :--- | :--- | :--- |
| Desktop | `≥ 900px` | 238px sidebar + flexible viewport | Full window chrome, fixed status bar |
| Narrow | `< 900px` | Single-column stack, viewport min 280px | Sidebar scrolls with page; touch controls remain 23px+ high |

The local GUI is intended for desktop/robot-rig operation; the narrow layout is
a fallback, not a mobile product target.

## 6. Interaction, Motion & Sound

- **Transition:** hover/active feedback is immediate (XP-style), with only the
  processing spinner using a continuous 0.8s rotation.
- **Feedback:** the status bar reports loading, wealthy/pristine state, crack
  count, volumes and errors. The fracture overlay blocks the viewport while a
  Manifold3D job is running.
- **Viewport motion:** OrbitControls damping (factor `0.08`) provides smooth
  orbit/pan/zoom without modern easing curves.
- **Audio:** none.

## 7. Do's and Don'ts

- **DO** keep the GUI zero-build: vanilla HTML/CSS/ES modules plus CDN Three.js.
- **DO** use the exact Tahoma sizes (`10px`, `11px`, `12px`) and the tokens in
  `DESIGN.md`.
- **DO** keep the ceramic material matte off-white (`#f8f6f0`) and the seam
  material metallic gold (`#ffd700`).
- **DON'T** introduce rounded pills, flat borderless buttons, or modern
  pastel-purple styling.
- **DON'T** add a Node/npm build pipeline or heavy CSS frameworks.
- **DON'T** allow the WebGL canvas to escape its recessed well.
