# Design Specification: Mobile UI Compatibility & Interactive Windows XP Menus (`mobile-ui-menus`)

> **Authority & Inheritance**: This change modifies the user-facing Kintsugi Studio 2001 web interface (`static/index.html`, `static/xp.css`, `static/viewer.js`). All visual and interactive tokens inherit directly from `DESIGN.md` (Windows XP Luna / Retro 2001 CAD Minimalist theme).

---

## 1. Visual Direction & Theme Polarity

- **Theme Polarity**: Classic Windows XP Luna Light Surface (`#ece9d8` beige chassis, `#ffffff` dropdown/modal surfaces, `#0058ee` Royal Blue window chrome, `#316ac5` Luna selection blue) paired with the dark slate 3D CAD viewport (`#0f1218` to `#1c222e`).
- **Aesthetic Philosophy**: Preserve authentic early-2000s Windows XP CAD desktop nostalgia (chiseled 3D beveled borders, classic popup menus with left checkmark gutter, property-sheet folder tabs, and glossy Luna green action buttons) while making every control effortless to reach and operate on modern smartphones (`<= 900px`) and desktop browsers (`> 900px`).

---

## 2. Color Palette & Contrast Audit (WCAG 2.1 AA)

| Token Name | Hex / Value | Role & Usage | Contrast Target | Ratio | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `--surface` | `#ece9d8` | Primary XP `.window` & `.sidebar` chassis, inactive mobile tab background | `--on-surface` (`#222222`) | `12.6:1` | **PASS (AAA)** |
| `--surface-light` | `#ffffff` | Dropdown menu surface (`.menu-dropdown`), active mobile tab, `#help-dialog` card body, `.xp-select` / `.xp-input` | `--on-surface` (`#222222`) | `15.9:1` | **PASS (AAA)** |
| `--menu-hover-bg` | `#316ac5` | Classic XP Luna `.menu-option` hover/active highlight & focus indicator | `#ffffff` | `5.3:1` | **PASS (AA)** |
| `--titlebar-start` / `--titlebar-end` | `#0058ee` / `#3a93ff` | `.titlebar` gradient, active `.mobile-tab` top accent bar (`2px solid #0058ee`) | `#ffffff` | `5.1:1` | **PASS (AA)** |
| `--on-surface` | `#222222` | Primary UI label, `.menu-option`, and `.mobile-tab` text | `--surface` (`#ece9d8`) | `12.6:1` | **PASS (AAA)** |
| `--on-surface-muted` | `#444444` | Secondary descriptions (`.field-note`), `.menu-section-label`, modal body copy | `--surface-light` (`#ffffff`) | `9.7:1` | **PASS (AAA)** |
| `--on-surface-disabled` | `#888888` | Disabled `.menu-option:disabled` / `.menu-option.disabled` text (intentionally exempt under WCAG 2.1 SC 1.4.3 for inactive UI controls) | `--surface-light` (`#ffffff`) | `3.5:1` | **PASS (Disabled Control)** |
| `--action-start` / `--action-end` | `#70c040` / `#3e8e18` | Sticky & desktop `#fracture-button` (`⚡ FRACTURE MESH`) primary action gradient | `#ffffff` (with `1px` `#1b4907` shadow) | `4.6:1` | **PASS (AA)** |
| `--badge-ready-bg` | `#2e8b14` | Mobile `Export` tab `#export-badge` notification dot | `#ffffff` | `4.5:1` | **PASS (AA)** |

---

## 3. Typography Hierarchy

| Level | Font Family | Desktop Size | Mobile (`<= 900px`) Size | Weight | Line Height | Intended Usage |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `Window / Modal Title` | `'Tahoma', 'Segoe UI', sans-serif` | `13px` | `13px` | `700` | `1.2` | `.titlebar-text` & `#help-dialog` header |
| `Panel & Tab Title` | `'Tahoma', 'Segoe UI', sans-serif` | `11px` | `12px` | `700` | `1.2` | `.panel-title`, `.mobile-tab`, `.menu-item` trigger |
| `Menu Option` | `'Tahoma', 'Segoe UI', sans-serif` | `11px` | `13px` | `400` | `1.3` | `.menu-option` items inside `.menu-dropdown` |
| `Form Control Input / Select` | `'Tahoma', 'Segoe UI', sans-serif` | `11px` | `16px` | `400` | `1.3` | `.xp-select`, `.xp-input` (`16px` on mobile prevents iOS Safari forced page zoom) |
| `Primary Action CTA` | `'Tahoma', 'Segoe UI', sans-serif` | `12px` | `13px` | `700` | `1.2` | `#fracture-button` (`⚡ FRACTURE MESH`) |
| `Status / Telemetry` | `'Lucida Console', monospace` | `11px` | `11px` | `400` | `1.35` | `.status-bar` cells (`#status-operation`, `#status-mesh`, `#status-kernel`) |

---

## 4. Component Anatomy & States

### Component 1: Interactive Windows XP Menu Bar (`.menu-bar`, `.menu-entry`, `.menu-dropdown`, `.menu-option`)

- **Visual Hierarchy & Placement**: Positioned immediately below `.titlebar`. Contains four `.menu-entry` wrappers (`File`, `Presets`, `Mode`, `Help`), each pairing a `.menu-item` trigger button with an absolute-positioned `.menu-dropdown[role="menu"]` popup (`#menu-file`, `#menu-presets`, `#menu-mode`, `#menu-help`, `z-index: 200`).
- **Component States**:
  - **Default / Idle**: `.menu-item` has transparent background, `1px solid transparent` border, `#222222` text. `.menu-dropdown[hidden]` is hidden (`display: none !important`).
  - **Hover / Open Trigger**: `.menu-item:hover` and `.menu-item[aria-expanded="true"]` display a classic XP raised/sunken bevel (`background: #e0ddd0`, `border-color: var(--border-highlight) var(--border-shadow) var(--border-shadow) var(--border-highlight)`).
  - **Dropdown Surface**: `background: #ffffff`, `border: 1px solid #808080`, `box-shadow: 2px 2px 4px rgba(0, 0, 0, 0.35)`, `min-width: 210px`, `padding: 2px`.
  - **Menu Option Default / Hover**: `.menu-option` uses a 2-column grid (`18px 1fr`) where the left gutter renders `✓` (`data-checked="true"` or `.menu-check`) for active preset/generator/mode choices. Hovering or focusing an enabled `.menu-option` sets `background: #316ac5` and `color: #ffffff`.
  - **Disabled**: `.menu-option:disabled` and `.menu-option.disabled` (`aria-disabled="true"`) render `color: #888888`, `pointer-events: none`, and suppress hover highlight when download links (`#menu-download-ceramic`, `#menu-download-gold`, `#menu-download-3mf`) or `ribbon` mode under `shard` are inactive.

### Component 2: Windows XP Property-Sheet Mobile Tabs (`#mobile-tabs`, `.mobile-tab`, `#export-badge`)

- **Visual Hierarchy & Placement**: Placed at the top of `<aside class="sidebar">`. Hidden on desktop (`display: none`); displayed as a 3-column horizontal tab strip (`display: grid; grid-template-columns: repeat(3, 1fr); gap: 2px`) on `@media (max-width: 900px)`.
- **Component States**:
  - **Inactive Tab**: `background: #dedad0`, `color: #333333`, `border: 1px solid var(--border-shadow)`, `border-bottom: 1px solid var(--border-highlight)`, `min-height: 38px`.
  - **Active Tab (`.mobile-tab.active`, `aria-selected="true"`)**: `background: var(--surface)` (`#ece9d8`), `font-weight: 700`, `border-top: 2px solid #0058ee`, `border-bottom-color: var(--surface)` so the active tab visually merges into the active `.panel[data-tab-panel]` below it.
  - **Export Ready Badge (`#export-badge`)**: Inline indicator (`●`) inside the `Export` tab (`color: #2e8b14`, `font-weight: 700`) unhidden when STL/3MF artifacts become ready and hidden once the user switches to the `Export` tab.

### Component 3: Windows XP About Modal (`#help-dialog`)

- **Visual Hierarchy & Placement**: Modal overlay inside `.window` (`position: fixed; inset: 0; background: rgba(0, 0, 0, 0.45); z-index: 500; display: flex; align-items: center; justify-content: center;`) containing an `.xp-dialog-card` (`width: min(380px, calc(100vw - 24px))`) with a royal-blue `.titlebar`, concise Kintsugi Studio 2001 pipeline overview, and a close/OK button (`#help-dialog-close` / `#help-dialog-ok`).

---

## 5. Responsive Layout & Breakpoints

| Viewport | Breakpoint | Layout Pattern | Navigation & Sizing Rules |
| :--- | :--- | :--- | :--- |
| **Desktop** | `> 900px` | 2-column `.window-body` (`285px` `.sidebar` left, `1fr` `.viewport-shell` right) | `#mobile-tabs` hidden; all 4 `.panel` sections visible simultaneously in `.sidebar`; compact `11px` desktop controls. |
| **Mobile / Tablet** | `<= 900px` | Single-column split-screen: pinned top `.viewport-shell` (`order: -1`, `height: clamp(200px, 36dvh, 310px)`) + tabbed `.sidebar` below | Outer `.window` fits `100dvh`; `#mobile-tabs` switches visible `.panel[data-tab-panel]` (`model`, `fracture` [default], `export`); `#fracture-button` sticky at bottom (`min-height: 44px`); touch targets $\ge 40\text{px}$; `.xp-select` / `.xp-input` `font-size: 16px`. |
| **Compact Phone** | `<= 480px` | Compact titlebar & status bar | `.titlebar-text` truncates cleanly with ellipsis; `.viewport-hint` compacts cleanly; `.status-bar` wraps cleanly (`grid-template-columns: 1fr auto`). |

---

## 6. Interaction, Motion & Sound

- **Instant Retro Responsiveness**: Classic Windows XP menus and property tabs switch instantaneously (`0ms` display toggle) for authentic crisp desktop feel; `#fracture-button` retains subtle press feedback (`transform: translateY(1px)` on `:active`).
- **Dismissal Ergonomics**: Clicking any menu option, clicking outside `.menu-entry`, or pressing `Escape` immediately closes all open `.menu-dropdown` popups and `#help-dialog`.
- **Viewport Stability**: `ResizeObserver` on `#viewport` updates Three.js renderer dimensions and camera aspect ratio without jarring layout jumps whenever mobile tabs or browser toolbars resize.

---

## 7. Do's and Don'ts

- **DO** keep `<select id="preset-select">`, `<select id="generator-select">`, and `<input name="mode">` as the single source of truth for application state, synchronizing `.menu-dropdown` checkmarks through `syncMenuChecks()`.
- **DO** enforce `font-size: 16px` on `.xp-select` and `.xp-input` inside `@media (max-width: 900px)` so iOS Safari never auto-zooms the page on tap.
- **DON'T** allow `.window-body` to scroll the 3D canvas off-screen on mobile; `.viewport-shell` must stay pinned at the top while only the active tab panel scrolls if needed.
- **DON'T** break any existing DOM IDs (`#preset-select`, `#file-input`, `#upload-zone`, `#generator-select`, `#mode-select`, `#ratio-slider`, `#seed-input`, `#seam-width-input`, `#fracture-button`, `#download-ceramic`, `#download-gold`, `#download-3mf`, `#viewport`, `#status-operation`, `#status-mesh`, `#status-kernel`).
