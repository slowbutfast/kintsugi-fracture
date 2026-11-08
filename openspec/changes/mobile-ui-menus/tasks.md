## 1. Test Scaffolding (TDD)

- [ ] 1.1 Write failing test `test_mobile_ui_and_menus_markup_served` in `tests/test_web_api.py` asserting that `GET /` serves the interactive menu dropdowns (`id="menu-file"`, `id="menu-presets"`, `id="menu-mode"`, `id="menu-help"`, `id="menu-upload"`, `id="menu-fracture"`, `id="menu-download-ceramic"`, `id="menu-download-gold"`, `id="menu-download-3mf"`, `id="menu-reset-camera"`, `id="menu-about"`), the mobile property-sheet tab bar (`id="mobile-tabs"`, `data-tab="model"`, `data-tab="fracture"`, `data-tab="export"`, `id="export-badge"`), `data-tab-panel` attributes on the sidebar `.panel` sections, and the Windows XP About modal (`id="help-dialog"`).
- [ ] 1.2 Write failing assertions in `tests/test_web_api.py` verifying that `GET /xp.css` includes `100dvh`, `.menu-dropdown`, `.mobile-tabs`, and mobile input `font-size: 16px`, and that `GET /viewer.js` includes `ResizeObserver`, `switchMobileTab`, and `syncMenuChecks`.

## 2. HTML Markup for Menus, Mobile Tabs & Help Dialog

- [ ] 2.1 Update `<nav class="menu-bar">` (`static/index.html:30-35`) to replace the static `data-focus` buttons with four `.menu-entry` containers (`File`, `Presets`, `Mode`, `Help`) and their `.menu-dropdown` popups (`#menu-file`, `#menu-presets`, `#menu-mode`, `#menu-help`) including `#menu-upload`, `#menu-fracture`, `#menu-download-ceramic`, `#menu-download-gold`, `#menu-download-3mf`, `#menu-reset-camera`, and `#menu-about`.
- [ ] 2.2 Insert the `#mobile-tabs` strip (`Model`, `Fracture` [default active], `Export` with `#export-badge`) at the top of `<aside class="sidebar">`, tag each `.panel` with `data-tab-panel="model|fracture|export"` (`Model Source` -> `model`, `Inequality Metric` & `Fracture Controls` -> `fracture` with `.mobile-panel-active`, `Slicer Assets` -> `export`), and add the `#help-dialog` Windows XP About modal inside `<main class="window">` in `static/index.html`.

## 3. Windows XP Menu & Mobile Responsive Styling

- [ ] 3.1 Add desktop & shared Windows XP dropdown menu styles (`.menu-entry`, `.menu-dropdown`, `.menu-option`, checkmark gutter, `#316ac5` Luna highlight, `.menu-separator`, `.menu-section-label`), `.mobile-tabs` default hidden state, and `#help-dialog` modal styles to `static/xp.css`.
- [ ] 3.2 Update `@media (max-width: 900px)` in `static/xp.css:664-682` with the mobile split-screen layout (`100dvh` on `.window`, pinned top `.viewport-shell` with `order: -1` and `height: clamp(200px, 36dvh, 310px)`, visible `.mobile-tabs`, `.panel[data-tab-panel]:not(.mobile-panel-active) { display: none; }`, sticky `#fracture-button`, $\ge 40\text{px}$ touch targets, and `font-size: 16px` on `.xp-select` / `.xp-input` to prevent iOS Safari auto-zoom).

## 4. Client Menu Controller, Tab Switcher & ResizeObserver

- [ ] 4.1 Add DOM references for `.menu-entry`, `#menu-file`, `#menu-presets`, `#menu-mode`, `#menu-help`, `#mobile-tabs`, `[data-tab-panel]`, `#export-badge`, and `#help-dialog` in `static/viewer.js`, and attach a `ResizeObserver` on `ui.viewport` (`#viewport`) inside `initViewer()`.
- [ ] 4.2 Update `loadPresets()` and `setDownload()` in `static/viewer.js` so dynamic preset options populate `#menu-presets`, download menu links (`#menu-download-ceramic`, `#menu-download-gold`, `#menu-download-3mf`) and `#export-badge` synchronize with export availability, and `syncMenuChecks()` keeps menu checkmarks aligned with `#preset-select`, `#generator-select`, and `input[name="mode"]` (disabling `ribbon` when `shard` is active).
- [ ] 4.3 Replace the legacy `data-focus` listener (`static/viewer.js:497-502`) with the interactive dropdown menu controller (`openMenu`, `closeMenus`, menu option handlers, outside-click & `Escape` dismissal), `switchMobileTab(tabName)`, and `#help-dialog` open/close handlers.

## 5. Verification & Empirical Audit

- [ ] 5.1 Run `.venv/bin/python -m unittest discover -s tests -p "test_*.py" -v` and verify 100% test pass rate with zero regressions.
- [ ] 5.2 Verify desktop (`> 900px`) and mobile (`<= 900px`, e.g. `390x844`) layouts, dropdown menus, tab switching, and sticky `⚡ FRACTURE MESH` behavior against `specs/retro-web-gui/spec.md` and `design.md`.
- [ ] 5.3 Populate `verification.md` with the Requirement Adherence Audit Matrix, resolved assumptions, and verbatim execution logs.
