---
version: alpha
name: Windows XP Luna Retro Minimalist
description: Early-2000s desktop computing aesthetic (Windows XP Luna) married with clean, minimalist 3D generative studio workflow.
colors:
  # Window frame and desktop foundation
  desktop: "#3a6ea5"
  surface: "#ece9d8"
  surface-light: "#ffffff"
  surface-inset: "#f0ede0"
  
  # Borders & 3D bevels
  border-highlight: "#ffffff"
  border-light: "#ece9d8"
  border-shadow: "#918e82"
  border-dark: "#404040"
  
  # Titlebar Luna Blue gradient
  titlebar-start: "#0058ee"
  titlebar-mid: "#3593ff"
  titlebar-end: "#072a8c"
  on-titlebar: "#ffffff"
  
  # UI text & labels
  on-surface: "#222222"
  on-surface-muted: "#555555"
  on-surface-disabled: "#888888"
  
  # Action buttons & accents
  action-start: "#70c040"
  action-end: "#3e8e18"
  action-border: "#286010"
  on-action: "#ffffff"
  
  # Window control buttons
  close-hover: "#e81123"
  
  # 3D Viewport materials
  viewport-bg: "#1a1f2c"
  ceramic-body: "#f8f6f0"
  ceramic-wireframe: "#444b5d"
  gold-seam: "#ffd700"
  gold-sheen: "#fff3a8"

typography:
  title:
    fontFamily: Tahoma, "Segoe UI", sans-serif
    fontSize: 12px
    fontWeight: 700
    lineHeight: 1.2
  menu:
    fontFamily: Tahoma, "Segoe UI", sans-serif
    fontSize: 11px
    fontWeight: 400
    lineHeight: 1.2
  body:
    fontFamily: Tahoma, "Segoe UI", sans-serif
    fontSize: 11px
    fontWeight: 400
    lineHeight: 1.3
  label:
    fontFamily: Tahoma, "Segoe UI", sans-serif
    fontSize: 11px
    fontWeight: 700
    lineHeight: 1.2
  button:
    fontFamily: Tahoma, "Segoe UI", sans-serif
    fontSize: 11px
    fontWeight: 700
    lineHeight: 1.2
  status:
    fontFamily: Tahoma, "Segoe UI", sans-serif
    fontSize: 10px
    fontWeight: 400
    lineHeight: 1.1
  code:
    fontFamily: "Courier New", monospace
    fontSize: 11px
    fontWeight: 400
    lineHeight: 1.2

rounded:
  none: 0px
  window-top: 6px
  button: 3px

spacing:
  xs: 2px
  sm: 4px
  md: 8px
  lg: 12px
  xl: 16px

components:
  window:
    background: "{colors.surface}"
    borderTopLeftRadius: "{rounded.window-top}"
    borderTopRightRadius: "{rounded.window-top}"
    boxShadow: "2px 2px 10px rgba(0, 0, 0, 0.4)"
  titlebar:
    background: "linear-gradient(to right, {colors.titlebar-start}, {colors.titlebar-mid} 85%, {colors.titlebar-end})"
    color: "{colors.on-titlebar}"
    padding: "{spacing.sm} {spacing.md}"
    borderTopLeftRadius: "{rounded.window-top}"
    borderTopRightRadius: "{rounded.window-top}"
  inset-panel:
    background: "{colors.surface-light}"
    borderColor: "{colors.border-shadow} {colors.border-highlight} {colors.border-highlight} {colors.border-shadow}"
    borderStyle: "solid"
    borderWidth: "2px"
    padding: "{spacing.md}"
  action-button:
    background: "linear-gradient(to bottom, {colors.action-start}, {colors.action-end})"
    color: "{colors.on-action}"
    borderColor: "{colors.action-border}"
    borderRadius: "{rounded.button}"
    padding: "{spacing.sm} {spacing.lg}"
    fontWeight: "bold"
---

# Windows XP Luna Retro Minimalist Design System

## Overview
This visual design system recreates the iconic, nostalgic tactility of the early-2000s desktop computing era (Windows XP Luna theme), refactored for a focused, minimalist 3D generative studio utility.

Rather than cluttering the screen with bloated dialogs, the UI preserves the crispness of a single, well-crafted native desktop window floating above a muted classic desktop background. Inside, modern interactive WebGL rendering meets beveled buttons, classic Tahoma typography, and inset data panels.

## Aesthetic Pillars
1. **Faithful 2000s Tactility**:
   - Distinct 3D beveled borders: `border: 2px solid; border-color: #ffffff #808080 #808080 #ffffff;` for raised surfaces (buttons, window edges).
   - Inset 3D panels: `border-color: #808080 #ffffff #ffffff #808080;` for text boxes, canvas wells, and dropdowns.
   - Smooth royal blue gradient title bar with glossy sheen highlights.
2. **Functional Minimalism**:
   - Every control serves an explicit function: choosing a 3D model, tuning the inequality slider $R$, selecting the fracture mode, and triggering the cut.
   - Generous viewport real estate dedicated to inspecting the 3D ceramic and gold geometry.
3. **Contrast & Material Authenticity**:
   - Contrast between the tactile cream/silver desktop UI (`#ece9d8`) and the deep navy/slate 3D canvas viewport (`#1a1f2c`).
   - The 3D model renders with realistic PBR materials: off-white matte porcelain (`#f8f6f0`) and lustrous, specular metallic gold (`#ffd700`) with dynamic light glints.

## Component Specifications

### 1. Window Frame & Titlebar
- **Window Container**: Rounded top corners (6px), squared bottom. 3px beveled outer frame.
- **Titlebar**: Royal blue horizontal gradient (`#0058ee` to `#3593ff` to `#072a8c`), bold white Tahoma text with subtle drop shadow.
- **Window Controls**:
  - Minimize (`_`), Maximize (`□`), and Close (`✕`).
  - Close button features the iconic coral-red square hover state (`#e81123`).

### 2. Menu Bar & Inset Wells
- **Menu Bar**: Traditional horizontal bar with keyboard mnemonic underlines: `File(F)`, `Presets(P)`, `Mode(M)`, `Help(H)`.
- **Inset Wells**: Used to house the Three.js viewport canvas and parameter groups. Inset 2px border simulates a recessed cavity in the physical monitor housing.

### 3. Sliders & Inputs
- **Track**: Inset groove (`height: 4px; border: 1px solid #808080; background: #ffffff;`).
- **Thumb**: Classic beveled rectangular slider knob (`width: 12px; height: 20px; background: #ece9d8; border: 2px outset #ffffff;`).
- **Live Label**: Displays instantaneous status readout (e.g. `R = 0.25 (Severe Inequality)`).

### 4. Primary "Fracture" Action Button
- Inspired by the iconic Windows XP "Start" button:
  - Vibrant green gradient: `#70c040` $\to$ `#3e8e18`.
  - Crisp 1px dark olive border (`#286010`).
  - White bold text with subtle text shadow.
  - Active/click state switches to pressed inset gradient.

### 5. Status Bar
- Divided horizontal strip at the bottom of the window:
  - Cell 1: Operation status (`"Ready"`, `"Computing Manifold3D booleans..."`).
  - Cell 2: Mesh face & vertex counts (`"Faces: 18,410 | Watertight: OK"`).
  - Cell 3: Engine metadata (`"Kernel: Manifold3D v3.5"`).

## Do's and Don'ts

### Do:
- **Do** use exact pixel-based sizing (`11px`, `12px`) for Tahoma font styles to preserve the authentic rendering look.
- **Do** use CSS system cursors: `cursor: default` for chrome, `cursor: pointer` for buttons, and `cursor: ew-resize` or `cursor: grab` for 3D orbit manipulation.
- **Do** ensure all form controls (radio buttons, sliders, dropdowns) have visible keyboard focus rings.
- **Do** keep the Three.js orbit controls responsive, with smooth damping and automatic model centering.

### Don't:
- **Don't** use flat modern minimalist styling (e.g. rounded pills, borderless buttons, pastel purple gradients) that break the 2000s desktop immersion.
- **Don't** use heavy external CSS frameworks (Tailwind, Bootstrap) or Node.js build pipelines; keep the styling in a single, crisp, readable `xp.css`.
- **Don't** allow the 3D canvas to clip outside its recessed inset well.
