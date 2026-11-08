> [!NOTE]
> This document specifies **visual, aesthetic, and UI/UX design decisions only** (3D fracture seam aesthetic geometry, contact sheet visual comparison layout, color palette, and rendering states).
> All technical architecture, APIs, state management, and backend protocols are defined in `architecture.md`.

## 1. Aesthetic Direction & Domain Exemplars

- **Core Aesthetic Philosophy**: Authentic *Hon-urushi Kintsugi* macroscopic shard seam aesthetics. Unlike tip-by-tip crack growth (which radiates downward from the lip like tree roots), `generator="shard"` creates sweeping, tilted fracture curves that visually divide the vessel exterior into 2–3 macroscopic shard regions—either a crescent/wedge rim break (**Primitive A**) or a tilted circumscribing loop (**Primitive B**), optionally joined by a second seam at a clean T-junction ($\ge 30^\circ$ arrival angle).
- **Reserve ($R$) and Severity ($S$) Aesthetics**:
  - $R$ is the vessel reserve metric; severity is $S = 1 - \text{clip}(R, 0, 1)$.
  - $R = 0.5$ ($S = 0.5$): Moderate fracture damage. 1 or 2 seams with subtle harmonic undulation and crisp crystalline kinks ($\tau \in [1.08, 1.20]$).
  - $R = 0.2$ ($S = 0.8$): Pronounced fracture damage. 2 seams with larger harmonic swing and sharper step deflections ($\tau \in [1.12, 1.30]$).
  - $R = 0.0$ ($S = 1.0$): Maximum fracture damage. 2 rugged stoneware macroscopic shard seams ($\tau \in [1.15, 1.35]$).
  - *Note on Sparsity*: While growth mode generates 15–20 fine cracks at $S = 1.0$, Stage 1 of shard mode deliberately focuses on the macroscopic shard boundary silhouettes (2 primary seams). Stage 2 will introduce secondary hairline branches connecting to these primary seams.
- **Stage 1 UI Scope**: No Web GUI (`static/index.html` / `static/app.js`) controls are modified in Stage 1. Visual validation is conducted via the 12-case rendered contact sheet (`reports/contact_sheet_shard.png`) compared side-by-side against `reports/contact_sheet.png` (`generator="growth"`), or via `--generator both`.

---

## 2. Color Palette & Contrast Audit (Contact Sheet & 3D Preview)

The contact sheet renderer (`tools/spike_contact_sheet.py`) reuses the established Kintsugi Studio 2001 inspection palette:

| Token | Role | Hex / Value | Usage |
| :--- | :--- | :--- | :--- |
| `--surface-bg` | Contact Sheet Background | `#F6F2EA` | Warm archival rice-paper canvas behind 2D `(u, z)` unwrap and 3D render cells |
| `--ceramic-body` | Ceramic Exterior | `#2D2B2A` / `#D8D1C5` | Matte stoneware body in 3D projection |
| `--gold-urushi` | Gold Vein Inlay | `#D4AF37` | Carve & fill gold seam highlight along projected 3D crack paths |
| `--rim-band` | Valid Wall Envelope Bounds | `#7A6F5D` | Dashed horizontal markers for `wall_z_min` and `wall_z_max` in 2D unwrap plots |

### WCAG 2.1 Contrast Compliance

| Foreground Element | Background Surface | Contrast Ratio | WCAG Target |
| :--- | :--- | :--- | :--- |
| Cell Title & Metrics (`#1E1C1A`) | Contact Sheet Card (`#F6F2EA`) | `14.6:1` | **PASS (AAA)** |
| Gold Seam Trace (`#B8860B` on 2D plot) | Unwrapped Wall Canvas (`#FFFFFF`) | `4.6:1` | **PASS (AA)** |

---

## 3. Typography Hierarchy (Contact Sheet Annotations)

| Level | Font Family | Size | Weight | Line Height | Intended Usage |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `H1` | DejaVu Sans / Sans | `16pt` | `700` | `1.2` | Contact sheet header (`generator=shard` vs `generator=growth`) |
| `H2` | DejaVu Sans / Sans | `11pt` | `600` | `1.3` | Cell title (`Tea Bowl / Tall Vase | R={0.0, 0.2, 0.5} | seed={0, 1}`) |
| `Mono / Data` | DejaVu Sans Mono | `9pt` | `400` | `1.3` | Tortuosity $\tau$, min clearance (mm), seam count, and junction count |

---

## 4. Component Anatomy & States

### Component: `12-Case Spike Contact Sheet (reports/contact_sheet_shard.png)`

- **Visual Hierarchy & Placement**: A 12-case grid covering 2 vessel presets (`Tea Bowl`, `Tall Vase`) $\times$ 3 reserve levels ($R \in \{0.5, 0.2, 0.0\}$, corresponding to $S \in \{0.5, 0.8, 1.0\}$) $\times$ 2 deterministic seeds (`seed=0`, `seed=1`).
- **Visual States by Reserve $R$**:
  - **$R = 0.5$ ($S = 0.5$, Moderate Damage)**: Moderate harmonic undulation with controlled kink steps ($\tau \in [1.08, 1.20]$).
  - **$R = 0.2$ ($S = 0.8$, High Damage)**: Broader plane tilt excursion and pronounced crystalline steps ($\tau \in [1.12, 1.30]$).
  - **$R = 0.0$ ($S = 1.0$, Rugged Stoneware Fracture)**: Maximum harmonic amplitude and sharpest angular step deflections ($\tau \in [1.15, 1.35]$) bounded strictly inside the wall envelope without flat-run ledges.

---

## 5. Responsive Layout & Breakpoints

Not applicable in Stage 1 (no Web GUI changes; contact sheet is rendered at fixed high-resolution inspection dimensions for side-by-side comparison).

---

## 6. Interaction, Motion & Sound

Not applicable in Stage 1 (CLI and batch contact-sheet generator only).

---

## 7. Do's and Don'ts

- **DO** truncate open rim-to-rim wedge seams at exact wall-band crossings via `_truncate_polyline_z` so every rim entry/exit meets the lip at a natural oblique angle without flat-run ledges.
- **DO** cap closed loop vertical amplitudes before sampling, and fall back to Primitive A (Wedge) if available wall height forces $\alpha < 5^\circ$, preventing loops from degenerating into flat horizontal stripes.
- **DON'T** use `np.clip` on vertical seam coordinates (which recreates horizontal rim/floor ledge artifacts).
- **DON'T** emit a second seam unless its intersection with Seam 1 is verified inside $[\text{wall\_z\_min} + W, \text{wall\_z\_max} - W]$ at $\ge 30^\circ$ with $\ge W + 0.8\text{ mm}$ clearance and registered in `params["_growth_junctions"]`.
