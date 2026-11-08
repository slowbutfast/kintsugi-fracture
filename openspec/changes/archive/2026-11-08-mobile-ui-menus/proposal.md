# Proposal: Mobile UI Compatibility & Interactive Windows XP Menus (`mobile-ui-menus`)

## Why

On mobile viewports (`max-width: 900px`), Kintsugi Studio 2001 currently stacks all four sidebar form panels above the 3D viewport (`static/xp.css:664-682`), pushing the 3D vessel completely below the fold, causing touch-scroll vs. 3D-orbit conflicts, and exposing `11px` `<select>`/`<input>` controls that trigger forced iOS Safari page zoom. Additionally, the top Windows XP `<nav class="menu-bar">` (`File`, `Presets`, `Mode`, `Help`) only focuses desktop inputs rather than providing interactive dropdown menus.

## What Changes

- **Interactive Windows XP Dropdown Menus (`File`, `Presets`, `Mode`, `Help`)**:
  - Upgrade `<nav class="menu-bar">` in `static/index.html`, `static/xp.css`, and `static/viewer.js` so clicking/tapping `File`, `Presets`, `Mode`, or `Help` opens a classic beveled Windows XP `.menu-dropdown` on both desktop and mobile:
    - **`File` (`#menu-file`)**: Upload custom `.stl`/`.obj` model, trigger `⚡ Fracture Mesh Now`, and download generated `Ceramic Body (.stl)`, `Gold Seams (.stl)`, and `Kintsugi Assembly (.3mf)`.
    - **`Presets` (`#menu-presets`)**: Dynamically populated from `/api/presets` with a checkmark (`✓`) next to the active preset.
    - **`Mode` (`#menu-mode`)**: Select generator (`Rim Growth`, `Shard Planes`, `Periodic Voronoi`) and cut mode (`Vein Inlay`, `Ribbon Cut`) with synchronized checkmarks (`✓`) and automatic `vein`-mode lock when `Shard Planes` is active.
    - **`Help` (`#menu-help`)**: `Reset 3D Camera View` (`frameObject()`) and `About Kintsugi Studio 2001…` modal (`#help-dialog`).
- **Pinned Top 3D Viewport + Tabbed XP Control Sheet on Mobile (`max-width: 900px`)**:
  - Order `.viewport-shell` first (`order: -1`, `height: clamp(200px, 36dvh, 310px)`) at the top of `.window-body` on mobile so the 3D vessel is always visible.
  - Add a 3-tab Windows XP tab bar (`#mobile-tabs`: `Model`, `Fracture` [default active], `Export` with ready badge `#export-badge`) that switches the visible `.panel[data-tab-panel]` section below the viewport on mobile while keeping all panels simultaneously visible on desktop (`> 900px`).
  - Keep `#fracture-button` (`⚡ FRACTURE MESH`) sticky at the bottom of `.sidebar` on mobile so the user can fracture from any tab.
- **Mobile Touch Ergonomics, `100dvh` & `ResizeObserver`**:
  - Use `100dvh` (with `100vh` fallback) on `.window` so mobile browser chrome never clips the status bar or sticky action button.
  - Enlarge mobile touch targets ($\ge 40\text{px}$ height) and set `font-size: 16px` on `.xp-select` and `.xp-input` inside `@media (max-width: 900px)` to prevent iOS Safari auto-zoom.
  - Attach a `ResizeObserver` to `#viewport` in `static/viewer.js` and update `.viewport-hint` on coarse-pointer (touch) devices.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `retro-web-gui`: Add `Requirement: Interactive Windows XP menu bar and mobile tabbed layout` defining the `File`/`Presets`/`Mode`/`Help` dropdown menus, the mobile pinned top 3D viewport + `Model`/`Fracture`/`Export` tab switcher + sticky Fracture button, and mobile touch/viewport ergonomics (`100dvh`, `16px` inputs, `ResizeObserver`).

## Impact

- **`static/index.html`** (`L30-L127`): Add dropdown menu markup (`#menu-file`, `#menu-presets`, `#menu-mode`, `#menu-help`), `#help-dialog` modal, `#mobile-tabs` tablist (`model`, `fracture`, `export`), and `data-tab-panel` attributes on sidebar panels.
- **`static/xp.css`** (`L75-L113, L190-L498, L612-L682`): Add Windows XP dropdown menu, modal dialog, and mobile tab bar styles; update `@media (max-width: 900px)` for pinned top viewport, tabbed panels, sticky action button, `100dvh`, and touch target sizing.
- **`static/viewer.js`** (`L19-L43, L119-L134, L238-L295, L460-L530`): Wire `ResizeObserver`, `switchMobileTab()`, dropdown menu toggle/dismissal, bidirectional menu checkmark sync, and `#help-dialog`.
- **`tests/test_web_api.py`** (`L49-L75`): Add automated verification of mobile UI tabs, dropdown menu markup, `100dvh` CSS rules, and JS wiring.
