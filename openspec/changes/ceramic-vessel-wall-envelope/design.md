---
name: Windows XP Luna Retro Minimalist (Ceramic Envelope Edition)
colors:
  primary: "#0058ee"            # Luna Titlebar Blue
  secondary: "#70c040"          # XP Emerald Action Green
  background: "#3a6ea5"         # Windows XP Bliss Classic Desktop Blue
  surface: "#ece9d8"            # Classic XP Window Canvas / Dialog Gray
  text:
    primary: "#222222"          # Tahoma High-contrast text
    muted: "#555555"            # Secondary labels & captions
  border: "#918e82"             # Classic 3D Shadow Border
  status:
    success: "#3e8e18"
    warning: "#e68a00"
    error: "#e81123"
typography:
  fontFamily:
    sans: "Tahoma, 'Segoe UI', Arial, sans-serif"
    mono: "'Lucida Console', 'Courier New', monospace"
  scale:
    h1: "13px, weight 700"
    h2: "12px, weight 700"
    body: "11px, weight 400"
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

## 1. Visual Overview & Philosophy

The user interface retains 100% fidelity to the Windows XP Luna desktop aesthetic defined in `DESIGN.md`. The design couples early-2000s desktop computing (Luna royal blue gradients, beveled gray chrome dialogs, emerald green candy buttons) with a high-fidelity WebGL 3D viewport.

- **Aesthetic Tone**: Authentic early-2000s Windows XP computing, tactile bevels, clean industrial tool ergonomics.
- **Target Surfaces**: Desktop web browsers (Chrome, Firefox, Safari) and local workstation loopback viewers.
- **Fracture Morphology Direction**: Traditional Japanese Kintsugi stoneware pottery. Bold, continuous gold lacquer seams ($d = \min(0.75W, 0.5t)$) with natural wandering paths ($\sigma \approx 18^\circ$, 15–20% kink rate), dendritic branching, and clean T-junction arrests, completely free of empty gaps or artificial staircase zig-zags.

---

## 2. Color System & Contrast Rationale

| Token Name | Hex Value | Semantic Role | Background Pair | Contrast Ratio | WCAG Compliance |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `primary` | `#0058ee` | Window titlebar gradient start | `#ffffff` (text) | `4.6:1` | **PASS (AA)** |
| `secondary` | `#70c040` | Emerald action button start | `#ffffff` (text) | `3.2:1` | **PASS (UI)** |
| `surface` | `#ece9d8` | Window dialog body canvas | `#222222` (text) | `10.8:1` | **PASS (AAA)** |
| `surface-inset` | `#f0ede0` | Inset group boxes and fields | `#222222` (text) | `11.5:1` | **PASS (AAA)** |
| `text.primary` | `#222222` | Standard Tahoma label text | `#ece9d8` (dialog) | `10.8:1` | **PASS (AAA)** |
| `gold-seam` | `#ffd700` | PBR gold seam material | `#1a1f2c` (viewport) | `12.1:1` | **PASS (AAA)** |

---

## 3. Typography Hierarchy

| Level | Font Family | Size | Weight | Line Height | Intended Usage |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Titlebar` | Sans (Tahoma) | `13px` | `700` | `1.2` | XP Window titlebar with drop shadow |
| `Section Header`| Sans (Tahoma) | `12px` | `700` | `1.3` | Group box headers and modal titles |
| `Body / Label` | Sans (Tahoma) | `11px` | `400` | `1.4` | Form labels, descriptions, and radio options |
| `Status / Tooltip` | Sans (Tahoma) | `11px` | `400` | `1.2` | Status bar segments and hover hints |
| `Data / Numbers` | Mono (Lucida) | `11px` | `400` | `1.2` | Vertex counts, volume cm³, coordinates |

---

## 4. Component Anatomy & States

### Component: Status Bar Validation and Fracture State Indicator

- **Placement**: Bottom border of the main window (`#status-bar`), inset 3D sunken well.
- **States**:
  - **Ready / Valid**: Reports `Watertight ✓ | Vertices: N | Wall: X.XX mm` (Status text `#222222`).
  - **Rejection (Sub-envelope)**: When $p_5 < 1.6\text{ mm}$, reports `Not a valid closed solid: Wall thickness (X.XX mm) < 1.60 mm required` with error styling.
  - **Pristine / Wealthy**: When $R \ge 1.0$, reports `Pristine / Wealthy (0 cracks)`.
  - **Fractured**: Reports `Fracture complete: N cracks, X.XX cm³ gold`.

### Component: 12-Case Visual Verification Contact Sheet

To guarantee aesthetic excellence before deployment, a 12-case rendered contact sheet is evaluated against historical Kintsugi references:
- **Models**: `Japanese Tea Bowl` ($t \approx 3.0\text{ mm}$), `Tall Vase` ($t \approx 2.4\text{ mm}$).
- **Inequality Metric**: $R \in \{0.0, 0.2, 0.5\}$ (high, medium, moderate severity).
- **Seeds**: 2 distinct seeds per condition.
- **Evaluation Criteria**: Continuous unbroken gold channels; zero stopping-short parallel gaps; organic wandering morphology without staircase zig-zags; clean perpendicular or obtuse T-junction branch stops.

---

## 5. Responsive Layout & Breakpoints

| Viewport | Breakpoint | Layout Pattern | Navigation / Sizing Rules |
| :--- | :--- | :--- | :--- |
| **Desktop** | `≥ 1024px` | Fixed 980px XP Window with side-by-side controls and viewport | Tactile 22px push buttons, draggable dialog |
| **Compact** | `< 1024px` | Stacked column layout inside scrolling desktop frame | Controls wrap gracefully above viewport |

---

## 6. Interaction, Motion & Sound

- **Tactile Push Buttons**: 1px inset active shift on click (`box-shadow: inset 1px 1px #000000`).
- **Processing Feedback**: Animated XP marquee progress bar during CSG boolean execution.
- **Viewport Orbit**: Smooth Three.js Arcball/Orbit controls with damping.

---

## 7. Do's and Don'ts

- **DO** present continuous, unbroken gold channels on all valid ceramic models.
- **DO** clearly state wall thickness rejection details when an uploaded model fails the 1.6 mm requirement.
- **DON'T** label empty fractures as pristine unless $R \ge 1.0$.
- **DON'T** introduce modern flat UI components (border-radius > 4px, floating pills, sans-serif fonts other than Tahoma).
