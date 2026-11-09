# retro-web-gui Specification

## Purpose
TBD - created by archiving change kintsugi-mesh-fracture. Update Purpose after archive.
## Requirements
### Requirement: Windows XP Luna visual design system adherence
The web GUI SHALL strictly adhere to the design tokens and visual style defined in `DESIGN.md`, presenting a single-window Windows XP desktop aesthetic with a Luna royal blue gradient titlebar, beveled borders, Tahoma typography, and inset 3D wells.

#### Scenario: Visual layout rendering
- **WHEN** user opens `http://localhost:8000` in a browser
- **THEN** system renders the `Kintsugi Studio 2001` window frame with royal blue gradient titlebar (`#0058ee` to `#072a8c`), 3-button controls (`_ □ ✕`), menu bar, and Tahoma typography at 11px/12px

### Requirement: Interactive Three.js 3D viewport
The web GUI SHALL provide an interactive WebGL 3D canvas with orbit controls and physically-based rendering (PBR) materials to preview the ceramic body and gold seams before slicing, rendering the vessel against a gallery off-white inset well.

#### Scenario: Real-time 3D inspection
- **WHEN** a fractured or pristine model is displayed in the viewport
- **THEN** system renders the ceramic body with Kuro-raku matte black diffuse roughness (`#18181b`) and the gold seams with metallic specular reflection (`#ffd700`) against a gallery off-white viewport canvas (`#f0ede0`), allowing mouse orbit, pan, and zoom without clipping outside the inset frame

### Requirement: Model preset selection and custom upload
The web GUI SHALL allow selecting bundled preset 3D models or uploading a custom watertight `.stl` or `.obj` file. Input models must conform to the ceramic vessel envelope ($p_5 \ge 1.6\text{ mm}$ along inward surface normals across the wall range). The `thin_cylinder` model SHALL NOT be offered in user presets.

#### Scenario: Preset model selection
- **WHEN** user chooses a preset model (e.g. `Japanese Tea Bowl` or `Tall Vase`) from the dropdown
- **THEN** system immediately loads and renders the model in the 3D viewport and updates the status bar with mesh metadata

#### Scenario: Custom file upload
- **WHEN** user drags and drops a custom `.stl` file onto the upload zone
- **THEN** the viewer parses it for preview and calls `POST /api/validate`, which runs `validate_and_load_mesh` in a temporary directory; the status bar reports `Watertight ✓` or `Not a valid closed solid: <detail>` (including wall thickness rejection if $p_5 < 1.6\text{ mm}$), and the fracture button stays disabled while the upload is invalid

#### Scenario: Upload size cap
- **WHEN** an upload exceeds 50 MB
- **THEN** the API rejects it with HTTP 413 and stores no file

#### Scenario: Job retention
- **WHEN** a new fracture job starts
- **THEN** job directories older than `KINTSUGI_JOB_TTL_S` (default 3600 s) are deleted, and at most `KINTSUGI_MAX_JOBS` (default 50) directories are retained, oldest first

### Requirement: Real-time parameter controls and fracture execution
The web GUI SHALL provide interactive controls for income ratio $R$, fracture generator (`growth`, `shard`, or `voronoi`), fracture mode (`vein` vs `ribbon`), and seed, with asynchronous fracture execution and progress feedback. The default fracture generator SHALL be `growth` (Rim Growth) and the default fracture mode SHALL be `vein` (Vein Inlay). When the user selects the `shard` generator (`Shard Planes`), the web GUI SHALL automatically select `vein` mode and disable the `ribbon` mode option while `shard` remains active.

#### Scenario: Triggering fracture computation with vein default
- **WHEN** user loads the application, sets $R = 0.35$, and clicks the green `⚡ FRACTURE MESH` button
- **THEN** system dispatches a `POST /api/fracture` request defaulting to `generator: "growth"` and `mode: "vein"`, updates the 3D viewport with the resulting ceramic body and gold lightning veins upon completion, and displays computed volume metrics

#### Scenario: Selecting Shard Planes generator in the Web GUI
- **WHEN** user selects `Shard Planes — tilted kintsugi seams` (`value="shard"`) in `#generator-select` and clicks `⚡ FRACTURE MESH`
- **THEN** the UI automatically checks the `vein` mode radio button, disables the `ribbon` mode radio button, updates `#generator-note` to indicate Vein Inlay only, and dispatches `POST /api/fracture` with `generator="shard"` and `mode="vein"`

#### Scenario: Wealthy parameter setting
- **WHEN** user sets $R \ge 1.0$
- **THEN** system immediately updates the status label to `Pristine / Wealthy (0 cracks)` and renders the intact ceramic body without gold veins

#### Scenario: Seams omitted feedback
- **WHEN** fracture response returns `seams_omitted: true` with $R < 1.0$
- **THEN** system displays `Seams Omitted` in the status indicator without claiming pristine wealth or displaying stale sub-millimeter thickness thresholds

### Requirement: One-click slicer asset download
The web GUI SHALL provide download buttons for exporting individual binary STL files and the unified multi-material `.3mf` container.

#### Scenario: Multi-material 3MF download
- **WHEN** user clicks `Download kintsugi_assembly.3mf`
- **THEN** system downloads the single-object, two-component 3MF archive ready for dual-extrusion slicing in Bambu Studio or PrusaSlicer

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

