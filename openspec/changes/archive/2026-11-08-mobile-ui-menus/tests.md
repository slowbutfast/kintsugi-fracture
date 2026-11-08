## Automated Tests

- `.venv/bin/python -m unittest tests/test_web_api.py -v`:
  - Verifies via `test_mobile_ui_and_menus_markup_served` that `GET /` serves the updated `static/index.html` containing:
    - All four interactive menu dropdown containers (`id="menu-file"`, `id="menu-presets"`, `id="menu-mode"`, `id="menu-help"`) and menu actions (`id="menu-upload"`, `id="menu-fracture"`, `id="menu-download-ceramic"`, `id="menu-download-gold"`, `id="menu-download-3mf"`, `id="menu-reset-camera"`, `id="menu-about"`).
    - The mobile property-sheet tab bar (`id="mobile-tabs"`, `data-tab="model"`, `data-tab="fracture"`, `data-tab="export"`, `id="export-badge"`) and corresponding `data-tab-panel` attributes on the sidebar `.panel` sections.
    - The Windows XP About modal (`id="help-dialog"`).
    - All existing required DOM IDs (`#preset-select`, `#file-input`, `#generator-select`, `#mode-select`, `#ratio-slider`, `#seed-input`, `#fracture-button`, `#download-ceramic`, `#download-gold`, `#download-3mf`, `#viewport`).
  - Verifies that `GET /xp.css` serves the responsive mobile rules (`100dvh`, `.menu-dropdown`, `.mobile-tabs`, `order: -1` on `.viewport-shell`, and `font-size: 16px` mobile input zoom prevention).
  - Verifies that `GET /viewer.js` serves the interactive menu controller (`syncMenuChecks`), mobile tab switcher (`switchMobileTab`), and `ResizeObserver` viewport handler.
- `.venv/bin/python -m unittest discover -s tests -p "test_*.py" -v`:
  - Verifies full regression pass across all backend fracture generators (`growth`, `shard`, `voronoi`), vessel thickness, export formatting, and web API endpoints.

## Manual Verification

- **Interactive Top Menu Bar (`File`, `Presets`, `Mode`, `Help`) on Desktop & Mobile**:
  - **WHEN** the user clicks or taps `File`, `Presets`, `Mode`, or `Help` in `<nav class="menu-bar">`
  - **THEN** the corresponding Windows XP dropdown menu opens above the sidebar and 3D canvas (`z-index: 200`), hovering another menu item on desktop switches the open dropdown, and clicking outside or pressing `Escape` closes all dropdowns.
- **Bidirectional Menu & Sidebar State Synchronization**:
  - **WHEN** the user selects a preset (`tea_bowl`, `vase`, `benchy`) from `Presets`, or a crack generator (`growth`, `shard`, `voronoi`) or seam style (`vein`, `ribbon`) from `Mode`
  - **THEN** the corresponding `✓` checkmark updates in the dropdown menu, the sidebar `#preset-select`, `#generator-select`, or `input[name="mode"]` control updates to match (disabling `ribbon` when `shard` is active), and changing the sidebar control directly also updates the menu checkmarks.
- **File Menu Actions & Export Enablement**:
  - **WHEN** the user opens `File` before running a fracture job vs. after a fracture job completes
  - **THEN** `#menu-download-ceramic`, `#menu-download-gold`, and `#menu-download-3mf` are disabled before fracture and become enabled with matching download `href` attributes after fracture completes.
- **Help Menu Camera Reset & About Dialog**:
  - **WHEN** the user selects `Help -> Reset 3D Camera View` (`#menu-reset-camera`) or `Help -> About Kintsugi Studio 2001…` (`#menu-about`)
  - **THEN** `Reset 3D Camera View` frames the active 3D mesh in `#viewport`, and `About Kintsugi Studio 2001…` opens `#help-dialog`, which closes cleanly via its close/OK button or `Escape`.
- **Mobile Split-Screen Layout & Property-Sheet Tabs (`<= 900px`)**:
  - **WHEN** the page is viewed at a mobile viewport size (e.g., `390x844` iPhone 14 or `375x667` iPhone SE)
  - **THEN** `.viewport-shell` is pinned at the top of `.window-body` (`order: -1`, `clamp(200px, 36dvh, 310px)`), `#mobile-tabs` (`Model` / `Fracture` / `Export`) is displayed immediately below it with `Fracture` active by default, switching tabs shows only the matching `.panel[data-tab-panel]` section while resizing `#viewport` smoothly via `ResizeObserver`, and `#fracture-button` remains sticky and accessible at the bottom of `.sidebar`.
