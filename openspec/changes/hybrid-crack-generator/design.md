> [!NOTE]
> This document specifies **visual, aesthetic, and UI design decisions only** (color palettes, contrast ratios, typography, component anatomy, responsive layout, and interaction design).
> All technical system architecture (APIs, state stores, concurrency, security) is defined in `architecture.md`.

## 1. Visual Direction & Aesthetic Philosophy

- **Domain Aesthetic**: Windows XP Luna (`Kintsugi Studio 2001`, per `DESIGN.md`) with inset bevelled group boxes, compact Tahoma controls, and clear telemetry readouts.
- **Progressive Disclosure**: The 6 hybrid knobs (`through_count`, `through_shape`, `tilt_deg`, `hairline_count`, `hairline_reach`, `roughness`) are nested inside a dedicated `#hybrid-settings` `<fieldset class="hybrid-fieldset">` inside the `Fracture Parameters` panel (`static/index.html`) that is `hidden` whenever `generator !== "hybrid"`.
- **Auto-Derived Transparency**: Each knob defaults to `Auto` (derived from $S = 1 - R$). After a fracture run completes, `#hybrid-resolved-note` displays the resolved values and raster surface fragment count (`num_fragments`) from `result.parameters.hybrid`.

---

## 2. Color Palette & Contrast Audit (WCAG AA/AAA)

All `#hybrid-settings` controls inherit the existing Windows XP Luna palette in `static/index.html`:

| Role / Token | Hex / Value | Usage |
| :--- | :--- | :--- |
| `--xp-surface` | `#ece9d8` | Sidebar panel and `#hybrid-settings` fieldset background |
| `--xp-input-bg` | `#ffffff` | `<select>` and number/slider readout background |
| `--xp-border-dark` | `#aca899` | Fieldset groove border |
| `--xp-text` | `#000000` | Primary label and input text |
| `--xp-muted` | `#4a473b` | `Auto (...)` resolved value note and field hints |
| `--xp-blue` | `#0054e3` | Active focus border and fieldset legend accent |

### Contrast Compliance Matrix

| Foreground Token | Background Token | Contrast Ratio | WCAG Target | Status |
| :--- | :--- | :--- | :--- | :--- |
| `--xp-text` (`#000000`) | `--xp-surface` (`#ece9d8`) | `17.4:1` | `>= 4.5:1` | **PASS (AAA)** |
| `--xp-muted` (`#4a473b`) | `--xp-surface` (`#ece9d8`) | `7.5:1` | `>= 4.5:1` | **PASS (AAA)** |
| `--xp-blue` (`#0054e3`) | `--xp-surface` (`#ece9d8`) | `5.3:1` | `>= 4.5:1` | **PASS (AA)** |

---

## 3. Typography Hierarchy

| Level | Font Family | Size | Weight | Line Height | Intended Usage |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Fieldset Legend` | `Tahoma, Verdana, sans-serif` | `11px` | `700` | `1.2` | `Hybrid Pattern Settings` legend in `#003399` |
| `Field Label` | `Tahoma, Verdana, sans-serif` | `11px` | `700` | `1.3` | Control labels (`Macro Seams`, `Macro Layout`, `Plane Tilt`, `Hairlines`, `Hairline Reach`, `Roughness`) |
| `Control / Select` | `Tahoma, Verdana, sans-serif` | `11px` (`16px` mobile) | `400` | `1.3` | `<select class="xp-select">` |
| `Mono / Readout` | `"Lucida Console", monospace` | `11px` | `400` | `1.3` | `#hybrid-resolved-note` readout |

---

## 4. Component Anatomy & States

### Component: `#hybrid-settings` (`<fieldset class="hybrid-fieldset" id="hybrid-settings" hidden>`)

- **Visual Hierarchy & Placement**: Placed inside the `Fracture Parameters` panel in `static/index.html` immediately below `#generator-note`.
- **Controls Inside `#hybrid-settings`**:
  1. **Macro Seams (`#hybrid-through-count`)**: `<select class="xp-select">` with options `auto` (`Auto (from R)`), `1` (`1 seam`), `2` (`2 seams`), `3` (`3 seams`).
  2. **Macro Layout (`#hybrid-through-shape`)**: `<select class="xp-select">` with options `auto` (`Auto (Rim-to-Rim Wedge)`), `wedge` (`Rim-to-Rim Wedge (Edge-Reaching)`), `loop` (`Closed Tilted Loop (Interior Ring)`).
  3. **Plane Tilt (`#hybrid-tilt-deg`)**: `<select class="xp-select">` with `auto` (`Auto (14°–26°)`), `10`, `14`, `18`, `20`, `24`, `26`, `30`. Steers both wedge nadir/skew and loop inclination.
  4. **Interior Hairlines (`#hybrid-hairline-count`)**: `<select class="xp-select">` with `auto` (`Auto (0–7 from R)`), `0` (`0 (Macro seams only)`), `1`..`10`.
  5. **Hairline Reach (`#hybrid-hairline-reach`)**: `<select class="xp-select">` with `auto` (`Auto (from R)`), `0.2`, `0.4`, `0.6`, `0.8`, `1.0`.
  6. **Fracture Roughness (`#hybrid-roughness`)**: `<select class="xp-select">` with `auto` (`Auto (1.0×)`), `0.5` (`0.5× Smooth`), `0.75` (`0.75×`), `1.0` (`1.0× Standard`), `1.25` (`1.25×`), `1.5` (`1.5× Rugged`), `2.0` (`2.0× Jagged`).
- **Component States**:
  - **Hidden (`generator !== "hybrid"`)**: `hidden` attribute present; zero layout space occupied; none of its form fields are appended to `POST /api/fracture`.
  - **Active (`generator === "hybrid"`)**: `hidden` attribute removed; `Ribbon (Through-Wall)` radio button and `#menu-mode` ribbon option are disabled (`disabled = true`, `aria-disabled="true"`), and `Vein Inlay` is selected; `#generator-note` reads `"Macro shard fractures + interior hairlines (Vein Inlay surface partition)."`.
  - **Post-Fracture Resolved Echo (`#hybrid-resolved-note`)**: Displays e.g. `"Resolved: 2 macro seams (wedge, 20°), 5 hairlines (reach 0.68, rough 1.0×) → 3 surface fragments"`.

---

## 5. Responsive Layout & Breakpoints

| Viewport | Breakpoint | Layout Pattern | Navigation / Sizing Rules |
| :--- | :--- | :--- | :--- |
| **Mobile** | `<= 900px` | Inside `[data-tab-panel="fracture"]` | `.xp-select` uses `font-size: 16px`, `min-height: 40px` touch targets; `#hybrid-settings` uses a 2-column compact grid so all 6 controls fit cleanly above the sticky `⚡ FRACTURE MESH` button |
| **Desktop** | `> 900px` | 2-column compact grid inside `.sidebar` | Standard `11px` Tahoma controls inside grooved XP fieldset |

---

## 6. Interaction, Motion & Sound

- **Generator Selection**: Switching `#generator-select` or clicking `[data-generator="hybrid"]` in `#menu-mode` immediately toggles `#hybrid-settings` and syncs the `✓` checkmark in `#menu-mode`.
- **Reset to Auto**: Each `<select>` defaults to `value="auto"`, so changing $R$ automatically re-derives all `auto` knobs on the next fracture without requiring manual resets.

---

## 7. Do's and Don'ts

- **DO** omit hybrid knob fields (or send them only when `generator === "hybrid"` and `value !== "auto"`) in `viewer.js` so `growth`, `shard`, and `voronoi` requests never send hybrid parameters.
- **DO** disable `ribbon` mode whenever `generator === "hybrid"` or `generator === "shard"`.
- **DON'T** display `#hybrid-settings` when `growth`, `shard`, or `voronoi` is selected.
