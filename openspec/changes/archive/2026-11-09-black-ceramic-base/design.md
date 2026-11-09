---
colors:
  primary: "#0058ee"
  secondary: "#316ac5"
  background: "#ece9d8"
  surface: "#ece9d8"
  viewport:
    background: "#f0ede0"
    ceramic: "#18181b"
    gold: "#ffd700"
    gridMajor: "#b8b4a6"
    gridMinor: "#d0ccc0"
  text:
    primary: "#222222"
    muted: "#555555"
  border: "#808080"
  status:
    success: "#2e8b14"
    warning: "#b8860b"
    error: "#c02020"
typography:
  fontFamily:
    sans: "'Tahoma', 'Segoe UI', sans-serif"
    mono: "'Lucida Console', monospace"
  scale:
    h1: "13px, weight 700"
    h2: "11px, weight 700"
    body: "11px (desktop) / 16px (mobile), weight 400"
    caption: "10px, weight 400"
spacing:
  xs: "2px"
  sm: "4px"
  md: "8px"
  lg: "12px"
  xl: "16px"
rounded:
  sm: "2px"
  md: "3px"
  lg: "4px"
  full: "9999px"
---

# Design Specification: Kuro-Raku Black Ceramic Base (`black-ceramic-base`)

## 1. Visual Overview & Philosophy

- **Aesthetic Tone**: Traditional Japanese Kuro-raku (黒楽) pottery gallery exhibition. Deep matte black stoneware paired with luminous metallic gold seams (`#ffd700`), presented inside an architectural gallery off-white canvas well (`#f0ede0`).
- **Target Surfaces**: Three.js WebGL 3D inspection viewport, Windows XP inset canvas well, and offline verification contact sheets.
- **Harmonious UI Framing**: The `#f0ede0` viewport canvas matches the application's `--surface-inset` well color, nestled inside the sunken 3D beveled frame (`border-color: #808080 #ffffff #ffffff #808080`), creating a clean, natural contrast against the surrounding `--surface` (`#ece9d8`) chassis.

---

## 2. Color System & Contrast Rationale

| Token Name | Hex Value | Semantic Role | Background Pair | Contrast Ratio | WCAG Compliance |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `ceramic-body` | `#18181b` | Base vessel PBR material | `viewport-bg` (`#f0ede0`) | `14.2:1` | **PASS (AAA)** |
| `gold-seam` | `#ffd700` | Fractured seam inlay material | `ceramic-body` (`#18181b`) | `10.8:1` | **PASS (AAA)** |
| `viewport-bg` | `#f0ede0` | Inset 3D canvas background | `surface` (`#ece9d8`) | `1.15:1` (Separated by 2px bevel) | **PASS (Framed Container)** |
| `grid-major` | `#b8b4a6` | Primary drafting floor grid | `viewport-bg` (`#f0ede0`) | `1.6:1` (Subtle floor guide) | **Decorative Guide** |
| `grid-minor` | `#d0ccc0` | Secondary drafting floor grid | `viewport-bg` (`#f0ede0`) | `1.3:1` (Soft floor guide) | **Decorative Guide** |

---

## 3. Typography Hierarchy

Unchanged from `DESIGN.md`:
- Window title: `13px` Tahoma, bold (`#ffffff` with text shadow).
- Sidebar labels & legends: `11px` Tahoma (`#222222`).
- Viewport HUD and status telemetry: `10px` / `11px` Lucida Console (`#222222`).

---

## 4. Component Anatomy & States

### Component: 3D Viewport Well (`.viewport-well`, `#viewport`, `canvas`)

- **Visual Hierarchy & Placement**: Located on the right side of `.window-body` (desktop) or pinned at top (mobile), enclosed within an inset 3D sunken well (`border: 2px solid; border-color: #808080 #ffffff #ffffff #808080`).
- **PBR Material Properties**:
  - `ceramicMaterial`: `color: 0x18181b`, `roughness: 0.65`, `metalness: 0.10`. Directional lights produce subtle, soft specular falloff on curved vessel lips and foot rings.
  - `goldMaterial`: `color: 0xffd700`, `roughness: 0.18`, `metalness: 0.92`. Highly specular and reflective, shining intensely against the dark ceramic body.
- **Lighting & Floor Environment**:
  - Background: `0xf0ede0` solid canvas clear color.
  - Ground bounce: `0xdcd8cc` ambient hemisphere ground reflection, keeping the underside and interior cavity of hollow vessels legible without navy tinting.
  - Floor Grid: `GridHelper` lines colored `0xb8b4a6` and `0xd0ccc0` at `0.40` opacity, providing depth without visual clutter.

---

## 5. Responsive Layout & Breakpoints

- Unchanged. Viewport height adapts smoothly across desktop (`1fr`) and mobile (`clamp(200px, 36dvh, 310px)`).

---

## 6. Interaction, Motion & Sound

- Orbiting, panning, and zooming in the 3D viewport smoothly reveal specular light glints across both the black vessel contours and the metallic gold fissures.

---

## 7. Do's and Don'ts

- **DO** maintain `roughness: 0.65` and `metalness: 0.10` on the black ceramic so directional light reveals 3D curvature.
- **DO** keep gold seams at `#ffd700` with high specular reflectivity.
- **DON'T** use pure pitch black (`#000000`) for the vessel, which eliminates surface shading.
- **DON'T** use harsh stark white (`#ffffff`) for the viewport background, which clashes with the retro Windows XP chassis.
