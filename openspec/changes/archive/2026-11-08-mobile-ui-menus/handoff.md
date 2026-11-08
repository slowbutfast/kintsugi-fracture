# OpenCode Orchestration Handoff: OpenSpec Change 'mobile-ui-menus'

You are the orchestration agent for OpenSpec change 'mobile-ui-menus' running in OpenCode.
Your primary directive is to execute this change using the **`openspec-apply-sub`** skill, which delegates task implementation to the `spec-coder-sub` subagent.

## 1. Orchestration Directive
- **Change Name**: `mobile-ui-menus`
- **Target Skill**: `openspec-apply-sub` (or `/opsx:apply-sub mobile-ui-menus`)
- **Architecture Paradigm**: Vertical Slice Architecture (VSA). Maintain strict isolation between feature compartments and avoid horizontal abstractions.

## 2. Target Context Map
| File Path (relative to repo root) | Target Lines | Modification Summary |
|---|---|---|
| `static/index.html` | `L30-L127` | Replace static `.menu-bar` buttons with `.menu-entry` + `.menu-dropdown` containers (`#menu-file`, `#menu-presets`, `#menu-mode`, `#menu-help`) and action items (`#menu-upload`, `#menu-fracture`, `#menu-download-ceramic`, `#menu-download-gold`, `#menu-download-3mf`, `#menu-reset-camera`, `#menu-about`); add `#mobile-tabs` (`model`, `fracture`, `export` with `#export-badge`) inside `<aside class="sidebar">`; tag `.panel` elements with `data-tab-panel="model|fracture|export"`; and add `#help-dialog` modal inside `<main class="window">`. |
| `static/xp.css` | `L75-L113, L190-L498, L612-L682` | Add `.menu-entry`, `.menu-dropdown`, `.menu-option`, `.menu-separator`, `.menu-section-label`, `.mobile-tabs`, `.mobile-tab`, `.tab-badge`, and `#help-dialog` / `.xp-dialog` rules; update `@media (max-width: 900px)` for `100dvh` on `.window`, `order: -1` and `height: clamp(200px, 36dvh, 310px)` on `.viewport-shell`, `.panel[data-tab-panel]:not(.mobile-panel-active) { display: none; }`, `font-size: 16px` on `.xp-select` / `.xp-input`, $\ge 40\text{px}$ touch targets, and sticky `#fracture-button`. |
| `static/viewer.js` | `L19-L43, L119-L134, L238-L295, L460-L530` | Add `ResizeObserver` on `ui.viewport` (`#viewport`) inside `initViewer()`; implement `switchMobileTab(tabName)`, `openMenu(name)`, `closeMenus()`, `syncMenuChecks()`, dynamic `#menu-presets` population in `loadPresets()`, `File` menu download link synchronization (`#menu-download-ceramic`, `#menu-download-gold`, `#menu-download-3mf`) and `#export-badge` notification in `setDownload()`, and `#help-dialog` open/close handlers. |
| `tests/test_web_api.py` | `L232-L257` | Add `test_mobile_ui_and_menus_markup_served` verifying `GET /`, `GET /xp.css`, and `GET /viewer.js` serve all required menu, tab, `100dvh`, `font-size: 16px`, `switchMobileTab`, `syncMenuChecks`, and `ResizeObserver` bindings. |

## 3. Technical & Architectural Boundaries
- **In-Scope Decisions**:
  - Keep existing `<select id="preset-select">`, `<select id="generator-select">`, and `<input name="mode">` as the canonical form controls read by `fracture()`, and synchronize the `Presets` (`#menu-presets`) and `Mode` (`#menu-mode`) dropdown menu items bidirectionally via `syncMenuChecks()` (disabling `ribbon` when `shard` is active).
  - Mark each `.panel` in `static/index.html` with `data-tab-panel="model"`, `data-tab-panel="fracture"`, or `data-tab-panel="export"`, and toggle `.mobile-panel-active` via `switchMobileTab(tabName)` (`fracture` active by default). Scope `.panel[data-tab-panel]:not(.mobile-panel-active) { display: none; }` strictly inside `@media (max-width: 900px)` so desktop (`> 900px`) continues showing all 4 panels simultaneously.
  - Attach `new ResizeObserver(() => onResize()).observe(ui.viewport)` inside `initViewer()` (guarded by `typeof ResizeObserver !== "undefined"`).
  - Unhide `#export-badge` on the `Export` tab when `setDownload()` enables download URLs and hide `#export-badge` when the user switches to the `Export` tab.
- **Hard Exclusions / No-Go**:
  - Do NOT modify `.env`, `.env.*`, or credential files.
  - Do NOT modify backend FastAPI routes in `web_app.py` or geometry generation in `kintsugi.py`.
  - Do NOT introduce external frontend dependencies, build steps, or CSS frameworks.
  - Do NOT perform code modifications outside the Target Context Map without prior task coverage.
  - Do NOT break any existing DOM IDs (`#preset-select`, `#file-input`, `#upload-zone`, `#generator-select`, `#mode-select`, `#ratio-slider`, `#seed-input`, `#seam-width-input`, `#fracture-button`, `#download-ceramic`, `#download-gold`, `#download-3mf`, `#viewport`, `#status-operation`, `#status-mesh`, `#status-kernel`).

## 4. Visual & UI Design Specifications
- **Theme**: Windows XP Luna / Retro 2001 CAD Minimalist (`DESIGN.md`)
- **Key Tokens**:
  - Primary Titlebar: `#0058ee` to `#3a93ff` | Menu Hover Highlight: `#316ac5` | Background Surface: `#ece9d8` | Dropdown/Input Surface: `#ffffff`
  - Text: Primary `#222222`, Muted `#444444`, Disabled `#888888`
  - Primary Action CTA (`#fracture-button`): `#70c040` to `#3e8e18` | Export Ready Badge (`#export-badge`): `#2e8b14`
- **Component Anatomy & States**:
  - `.menu-dropdown`: `background: #ffffff`, `border: 1px solid #808080`, `box-shadow: 2px 2px 4px rgba(0, 0, 0, 0.35)`, `z-index: 200`; `.menu-option` uses a 2-column grid (`18px 1fr`) with `✓` in the left gutter for active items, `#316ac5` background with `#ffffff` text on hover/focus, and `#888888` muted disabled state when inactive.
  - `#mobile-tabs`: 3-column horizontal tab strip (`Model`, `Fracture`, `Export`) hidden on desktop (`> 900px`) and displayed on `@media (max-width: 900px)`. Active `.mobile-tab.active` uses `background: #ece9d8`, `font-weight: 700`, and `border-top: 2px solid #0058ee`.
  - `#help-dialog`: Centered Windows XP modal dialog (`z-index: 500`) with royal-blue `.titlebar`, pipeline summary, and close/OK button.
- **Responsive Layout**:
  - Desktop (`> 900px`): 2-column `.window-body` (`285px` sidebar left, `1fr` 3D viewport right), `#mobile-tabs` hidden, all 4 `.panel` sections visible.
  - Mobile (`<= 900px`): `.window` uses `100dvh`; `.viewport-shell` pinned at top (`order: -1`, `height: clamp(200px, 36dvh, 310px)`); `#mobile-tabs` visible below viewport; only `.panel.mobile-panel-active` displayed; `#fracture-button` sticky at bottom (`min-height: 44px`); `.xp-select` and `.xp-input` use `font-size: 16px` (preventing iOS Safari auto-zoom) with touch targets $\ge 40\text{px}$.

## 5. Test Scaffolding & Verification Commands
- **Primary Test Runner**: `.venv/bin/python -m unittest tests/test_web_api.py -v`
- **Full Regression Suite**: `.venv/bin/python -m unittest discover -s tests -p "test_*.py" -v`
- **TDD Requirement**: Task group ## 1 MUST scaffold failing unit/integration tests before touching implementation code. Verify they fail initially.

## 6. Implementation Task Checklist
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

## 7. Post-Implementation & Verification Obligations
When `spec-coder-sub` finishes:
1. Verify all checkboxes in `tasks.md` are marked `- [x]`. Only tick boxes that genuinely ran and passed.
2. Check data preservation: confirm all existing DOM IDs and preset options remain intact.
3. Ensure `openspec/changes/mobile-ui-menus/verification.md` is populated with:
   - Executive Summary & Environment
   - Requirement Adherence Audit Matrix (mapping every spec scenario to its verifying test)
   - Resolved Assumptions & Empirical Proof
   - Nomenclature & Code Symbol Audit
   - Verbatim Execution Logs
4. Automatically run verification via `openspec-verify-change`.
5. If clean with no critical issues, sync specs: `openspec specs apply --change "mobile-ui-menus"`.
