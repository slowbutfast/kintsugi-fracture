## ADDED Requirements

### Requirement: Interactive Windows XP menu bar and mobile tabbed layout
The web GUI SHALL provide interactive Windows XP dropdown menus on `<nav class="menu-bar">` (`File`, `Presets`, `Mode`, `Help`) across both desktop and mobile viewports, and SHALL adapt viewports at or below `900px` width to a pinned top 3D viewport with a 3-tab Windows XP control switcher (`Model`, `Fracture`, `Export`) and a sticky primary `⚡ FRACTURE MESH` button.

- **Windows XP Dropdown Menus**:
  - `File` (`#menu-file`) SHALL expose actions to upload a custom `.stl`/`.obj` file (`#menu-upload`), trigger `⚡ Fracture Mesh Now` (`#menu-fracture`), and download generated `Ceramic Body (.stl)` (`#menu-download-ceramic`), `Gold Seams (.stl)` (`#menu-download-gold`), and `Kintsugi Assembly (.3mf)` (`#menu-download-3mf`).
  - `Presets` (`#menu-presets`) SHALL dynamically list bundled presets from `/api/presets` with a checkmark (`✓`) indicating the active preset.
  - `Mode` (`#menu-mode`) SHALL expose generator choices (`growth`, `shard`, `voronoi`) and cut mode choices (`vein`, `ribbon`) with synchronized checkmarks (`✓`), disabling `ribbon` when `shard` is active.
  - `Help` (`#menu-help`) SHALL expose `Reset 3D Camera View` (`#menu-reset-camera`) and `About Kintsugi Studio 2001…` (`#menu-about`), which toggles an informational modal dialog (`#help-dialog`).
- **Mobile Pinned Viewport & Tabbed Control Panels (`max-width: 900px`)**:
  - `.viewport-shell` SHALL be ordered above `.sidebar` (`order: -1`) so the 3D model viewport remains pinned at the top of the window without scrolling.
  - `#mobile-tabs` SHALL render three selectable tabs (`data-tab="model"`, `data-tab="fracture"` active by default, and `data-tab="export"` with an `#export-badge` indicator when downloads are available) that toggle `.mobile-panel-active` on the matching `.panel[data-tab-panel]` sections.
  - `#fracture-button` SHALL remain sticky at the bottom of `.sidebar` on mobile viewports, and `<select>` / `<input>` controls SHALL use `font-size: 16px` with `100dvh` window sizing and a `ResizeObserver` on `#viewport`.

#### Scenario: Opening and using Windows XP dropdown menus
- **WHEN** user clicks or taps `File`, `Presets`, `Mode`, or `Help` in `<nav class="menu-bar">`
- **THEN** the corresponding `.menu-dropdown` opens (`hidden` removed, `aria-expanded="true"`), selecting an item executes its action (loading a preset, switching generator/mode with updated `✓` checkmarks, triggering upload/fracture/download, or opening `#help-dialog`), and clicking outside or pressing `Escape` closes all open dropdown menus

#### Scenario: Mobile pinned top viewport and tab switching
- **WHEN** the application is viewed on a mobile viewport (`max-width: 900px`)
- **THEN** `.viewport-shell` is positioned at the top of `.window-body` (`order: -1`), `#mobile-tabs` is visible with `Fracture` active by default (`data-tab-panel="fracture"` shown, inactive tab panels hidden), tapping `Model` or `Export` switches the visible `[data-tab-panel]` section, and `#fracture-button` remains sticky at the bottom

#### Scenario: Export tab readiness badge and File menu download sync
- **WHEN** a fracture run completes and returns download URLs for ceramic STL, gold STL, and 3MF assets
- **THEN** both the `Slicer Assets` panel links and the `File` menu download links (`#menu-download-ceramic`, `#menu-download-gold`, `#menu-download-3mf`) are enabled with matching `href` attributes, and `#export-badge` is unhidden until the user opens the `Export` tab

#### Scenario: Mobile touch sizing and ResizeObserver viewport sync
- **WHEN** the mobile layout resizes or switches tabs on a coarse-pointer / `max-width: 900px` device
- **THEN** `.window` uses dynamic viewport height (`100dvh`), `.xp-select` and `.xp-input` use `font-size: 16px` (preventing iOS Safari auto-zoom) with touch targets $\ge 40\text{px}$, and the `ResizeObserver` on `#viewport` updates the Three.js renderer dimensions
