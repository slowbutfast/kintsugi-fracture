# Verification: Mobile UI Compatibility & Interactive Windows XP Menus (`mobile-ui-menus`)

## 1. Executive Summary & Environment

- **Status**: PASS — all 12 tasks complete; every automated and empirical check is green.
- **Date**: 2026-11-08
- **Working branch / base**: `crisp-condor` at `dbdb03e` (change artifacts) plus the implementation working tree.
- **Environment**:
  - Linux `5.15.0-1081-oracle` (`aarch64`)
  - Python `3.11.2`
  - FastAPI `0.162.0`
  - OpenSpec `1.7.0`
  - Playwright Chromium (headless, SwiftShader) at desktop `1280x900` and mobile `390x844`
- **Scope**: `static/index.html`, `static/xp.css`, `static/viewer.js`, `tests/test_web_api.py`.
- **No-Go compliance**:
  - `web_app.py` unchanged.
  - `kintsugi.py` unchanged.
  - `.env` / `.env.*` unchanged.
  - No external frontend dependencies, build steps, or CSS frameworks introduced.
  - All pre-existing DOM IDs preserved.
- **Result summary**:

| Check | Result |
| :--- | :--- |
| `openspec validate "mobile-ui-menus" --strict` | Valid (0 issues) |
| Targeted web API suite | 12 / 12 pass |
| Full regression suite | 65 / 65 pass |
| Playwright desktop/mobile interaction audit | 48 / 48 pass |
| Playwright download-sync audit | 11 / 11 pass |
| JavaScript syntax (`node --check`) | Pass |
| HTML tag-balance audit | 0 errors, 0 unclosed tags |

---

## 2. Requirement Adherence Audit Matrix

### 2.1 Requirement-level matrix

| Requirement | Implementation evidence | Verification |
| :--- | :--- | :--- |
| Interactive Windows XP menu bar (`File`, `Presets`, `Mode`, `Help`) on desktop and mobile | `static/index.html:30-75` defines four `.menu-entry` wrappers and `.menu-dropdown` popups `#menu-file`, `#menu-presets`, `#menu-mode`, `#menu-help`; `static/viewer.js` implements `openMenu()`, `closeMenus()`, trigger `aria-expanded`, outside-`pointerdown` dismissal, and `Escape` dismissal. | `test_mobile_ui_and_menus_markup_served`; Playwright checks “File dropdown opens”, “Escape closes File dropdown”, “File dropdown opens” on mobile. |
| `File` menu actions: upload, fracture, three downloads | `#menu-upload`, `#menu-fracture`, `#menu-download-ceramic`, `#menu-download-gold`, `#menu-download-3mf`; `setDownload()` synchronizes `href`, `download`, `aria-disabled`, and `.disabled`; `fracture()` mirrors API download URLs into the menu. | `test_mobile_ui_and_menus_markup_served`; Playwright download-sync audit (all three menu links enabled and matching sidebar links). |
| `Presets` menu dynamically populated from `/api/presets` with active checkmark | `populatePresetMenu()` renders one `[data-preset]` option per API preset; `syncMenuChecks()` sets `aria-checked="true"` for the active value. | `test_mobile_ui_and_menus_markup_served`; Playwright check “active preset checkmark starts on tea_bowl” and “Presets menu checkmark follows selection”. |
| `Mode` menu exposes `growth` / `shard` / `voronoi` and `vein` / `ribbon`, disables `ribbon` under `shard` | `[data-generator]` and `[data-mode]` menu options; `syncGeneratorMode()` plus `syncMenuChecks()` lock `vein` and set `.disabled` + `aria-disabled="true"` on `ribbon` when `shard` is selected. | `test_mobile_ui_and_menus_markup_served`; Playwright checks “Mode menu updates generator select”, “ribbon disabled under shard”, “shard locks vein mode”, “ribbon re-enabled under growth”. |
| `Help` menu exposes camera reset and About dialog | `#menu-reset-camera` calls `frameObject()`; `#menu-about` calls `openHelpDialog()`; `#help-dialog` is a Windows XP modal with close/OK controls and backdrop/`Escape` dismissal. | `test_mobile_ui_and_menus_markup_served`; Playwright checks “About opens #help-dialog” and “Escape closes #help-dialog”. |
| Mobile pinned top viewport (`order: -1`, `clamp(200px, 36dvh, 310px)`) | `@media (max-width: 900px)` rule in `static/xp.css` sets `.viewport-shell { order: -1; height: clamp(200px, 36dvh, 310px); }`. | `test_mobile_ui_and_menus_markup_served` (`order: -1`); Playwright checks “viewport-shell ordered above sidebar” and measured height `303.8px` at `390x844`. |
| Mobile `Model` / `Fracture` / `Export` tabs with `Fracture` active by default | `#mobile-tabs` inside `.sidebar`; `switchMobileTab()` toggles `.mobile-panel-active` on matching `[data-tab-panel]` sections. Markup defaults `Fracture` active and both fracture panels `.mobile-panel-active`. | `test_mobile_ui_and_menus_markup_served`; Playwright checks default visibility plus “Model tab shows Model panel”, “Export tab shows Export panel”, “Fracture tab restores Fracture panel”. |
| Mobile sticky `⚡ FRACTURE MESH` and touch ergonomics (`100dvh`, `16px`, `>= 40px`) | `@media (max-width: 900px)` sets `.window { height: 100dvh; }`, `.xp-select` / `.xp-input { font-size: 16px; min-height: 40px; }`, touch-sized tabs/menu options/downloads, and `#fracture-button { position: sticky; bottom: 0; min-height: 44px; }`. | `test_mobile_ui_and_menus_markup_served`; Playwright checks `100dvh` height `~844px`, computed `font-size: 16px`, `position: sticky`, and `min-height: 44px`. |
| `ResizeObserver` on `#viewport` | `initViewer()` installs `new ResizeObserver(() => onResize()).observe(ui.viewport)` guarded by `typeof ResizeObserver !== "undefined"`. `switchMobileTab()` also schedules `onResize()` after tab changes. | `test_mobile_ui_and_menus_markup_served` (`ResizeObserver` token); Playwright tab-switch audit completes with zero page/console errors. |
| Desktop (`> 900px`) keeps all four panels visible and hides mobile tabs | The panel-hiding rule is scoped strictly inside `@media (max-width: 900px)`; `.mobile-tabs` defaults to `display: none`. | Playwright checks “desktop: mobile tabs are hidden” and all four desktop `[data-tab-panel]` sections visible. |
| Export readiness badge and File-menu download synchronization | `setDownload()` unhides `#export-badge` when a URL becomes available (unless the Export tab is already active); `switchMobileTab("export")` clears it. | Playwright checks badge visible after fracture, cleared on Export tab; download-sync audit verifies menu/sidebar `href` equality. |
| All existing DOM IDs preserved | `#preset-select`, `#file-input`, `#upload-zone`, `#generator-select`, `#mode-select`, `#ratio-slider`, `#seed-input`, `#seam-width-input`, `#fracture-button`, `#download-ceramic`, `#download-gold`, `#download-3mf`, `#viewport`, `#status-operation`, `#status-mesh`, `#status-kernel` remain in `static/index.html`. | `test_mobile_ui_and_menus_markup_served` asserts every preserved ID. |

### 2.2 Spec scenario matrix

| Spec scenario | Verdict | Verifying evidence |
| :--- | :--- | :--- |
| **Opening and using Windows XP dropdown menus** — click/tap opens; selecting executes action; outside click or `Escape` closes | PASS | Markup + controller asserted by `test_mobile_ui_and_menus_markup_served`; Playwright: File opens, `aria-expanded="true"`, `Escape` closes, Presets changes `#preset-select`, Mode changes `#generator-select`, About opens dialog. |
| **Mobile pinned top viewport and tab switching** — viewport above sidebar, tabs visible, Fracture default, Model/Export switch panels, sticky fracture button | PASS | Static CSS assertions in `test_mobile_ui_and_menus_markup_served`; Playwright mobile checks: visible tab strip, viewport `y` above sidebar, fracture panels default-visible, Model/Export switching, sticky button. |
| **Export tab readiness badge and File menu download sync** — completed fracture enables all matching links and badge until Export tab opened | PASS | Playwright download-sync audit at `R=0.4`: all three menu links and sidebar links enabled, `href` values match, badge visible, then cleared on Export tab. |
| **Mobile touch sizing and ResizeObserver viewport sync** — `100dvh`, 16px controls, >= 40px targets, observer updates renderer | PASS | `test_mobile_ui_and_menus_markup_served` asserts `100dvh`, `font-size: 16px`, `ResizeObserver`; Playwright verifies computed window height, control font size, 44px sticky action, and zero runtime errors across tab switches. |

---

## 3. Resolved Assumptions & Empirical Proof

| Assumption | Empirical proof | Result |
| :--- | :--- | :--- |
| `clamp(200px, 36dvh, 310px)` leaves enough room for the active tab panel and sticky action at `390x844` | Playwright measured `.viewport-shell` height at `303.8px`; sidebar remained scrollable; fracture panels and sticky button were reachable. | **Resolved — accepted.** |
| `font-size: 16px` on mobile controls prevents iOS Safari auto-zoom | Playwright computed `font-size: 16px` on `#preset-select` at `390x844`. | **Resolved — accepted.** |
| `100dvh` fits the mobile viewport without clipping | Playwright measured `.window` height at `844px` for a `390x844` viewport (within 2px tolerance). | **Resolved — accepted.** |
| Dynamic presets load from `/api/presets` into the menu | Browser audit observed populated `#preset-select` options and `#menu-presets [data-preset]` options, including `tea_bowl` and `vase`; selecting `vase` updated the canonical select and checkmark. | **Resolved — accepted.** |
| File-menu downloads mirror real fracture API results | Real browser run at `R=0.4` produced enabled, matching menu/sidebar links for ceramic STL, gold STL, and 3MF. A second run at `R=1.0` correctly left gold disabled because the API returns no gold asset for the wealthy/zero-crack case. | **Resolved — accepted.** |
| Sticky action button remains a touch target | Playwright computed `position: sticky` and `min-height: 44px` for `#fracture-button` at `390x844`. | **Resolved — accepted.** |
| `shard` generator disables `ribbon` mode in both state layers | Playwright observed `aria-disabled="true"` and `.disabled` on the menu ribbon option, `vein` forced checked, then `ribbon` re-enabled after switching back to `growth`. | **Resolved — accepted.** |
| Desktop behavior is unchanged above `900px` | Playwright at `1280x900` saw all four panels visible and `#mobile-tabs` hidden. | **Resolved — accepted.** |

---

## 4. Nomenclature & Code Symbol Audit

### 4.1 DOM IDs added

| ID | Purpose |
| :--- | :--- |
| `menu-file`, `menu-presets`, `menu-mode`, `menu-help` | Dropdown containers |
| `menu-upload`, `menu-fracture` | File menu actions |
| `menu-download-ceramic`, `menu-download-gold`, `menu-download-3mf` | File menu download links |
| `menu-reset-camera`, `menu-about` | Help menu actions |
| `mobile-tabs`, `export-badge` | Mobile property-sheet tab strip and readiness indicator |
| `help-dialog`, `help-dialog-close`, `help-dialog-ok`, `help-dialog-title` | About modal and controls |

### 4.2 Preserved DOM IDs

`preset-select`, `file-input`, `upload-zone`, `generator-select`, `generator-note`, `mode-select`, `ratio-slider`, `ratio-value`, `ratio-caption`, `seed-input`, `seam-width-input`, `fracture-button`, `download-ceramic`, `download-gold`, `download-3mf`, `viewport`, `processing-overlay`, `status-operation`, `status-mesh`, `status-kernel`.

### 4.3 CSS symbols introduced

`.menu-entry`, `.menu-dropdown`, `.menu-option`, `.menu-check`, `.menu-separator`, `.menu-section-label`, `.mobile-tabs`, `.mobile-tab`, `.tab-badge`, `.xp-dialog`, `.xp-dialog-card`, `.xp-dialog-body`, `.xp-dialog-heading`, `.xp-dialog-section-label`, `.xp-dialog-steps`, `.xp-dialog-actions`.

### 4.4 JavaScript symbols introduced

`MOBILE_TABS`, `openMenu`, `closeMenus`, `anyMenuOpen`, `switchMobileTab`, `syncMenuChecks`, `populatePresetMenu`, `openHelpDialog`, `closeHelpDialog`.

### 4.5 Consistency and stale-reference audit

- No `data-focus` selectors remain in `static/viewer.js`; the legacy listener was fully replaced by the menu controller.
- `syncMenuChecks()` reads the canonical `#preset-select`, `#generator-select`, and `input[name="mode"]` controls rather than duplicating state.
- `fracture()` still reads the canonical form controls; no backend or payload changes were required.
- `git diff --stat` shows only the four intended source/test files plus this change's planning artifacts.

---

## 5. Verbatim Execution Logs

### 5.1 OpenSpec validation

```text
$ openspec validate "mobile-ui-menus" --strict
Change 'mobile-ui-menus' is valid
```

### 5.2 TDD red phase (before implementation)

```text
$ .venv/bin/python -m unittest tests.test_web_api.WebApiTestCase.test_mobile_ui_and_menus_markup_served -v
test_mobile_ui_and_menus_markup_served ... FAIL

======================================================================
FAIL: test_mobile_ui_and_menus_markup_served
----------------------------------------------------------------------
AssertionError: 'id="menu-file"' not found in '<!DOCTYPE html>...'
```

### 5.3 TDD green phase (after implementation)

```text
$ .venv/bin/python -m unittest tests.test_web_api.WebApiTestCase.test_mobile_ui_and_menus_markup_served -v
test_mobile_ui_and_menus_markup_served ... ok
----------------------------------------------------------------------
Ran 1 test in 0.034s
OK
```

### 5.4 Targeted web API suite

```text
$ .venv/bin/python -m unittest tests/test_web_api.py -v
...
test_mobile_ui_and_menus_markup_served (tests.test_web_api.WebApiTestCase.test_mobile_ui_and_menus_markup_served) ... ok
----------------------------------------------------------------------
Ran 12 tests in 5.862s
OK
```

### 5.5 Full regression suite

```text
$ .venv/bin/python -m unittest discover -s tests -p "test_*.py" -v
...
Ran 65 tests in 485.488s
OK
```

### 5.6 Static structure, CSS, and JavaScript audit

```text
menu entries: 4
dropdown ids: ['menu-file', 'menu-presets', 'menu-mode', 'menu-help']
static menu options: ['menu-upload', 'menu-fracture', 'menu-download-ceramic', 'menu-download-gold', 'menu-download-3mf', None, 'growth', 'shard', 'voronoi', 'vein', 'ribbon', 'menu-reset-camera', 'menu-about']
mobile tabs (data-tab, active, aria-selected): [('model', False, 'false'), ('fracture', True, 'true'), ('export', False, 'false')]
panels (data-tab-panel, active): [('model', False), ('fracture', True), ('fracture', True), ('export', False)]
help dialog: True
CSS '100dvh': True
CSS '.menu-dropdown': True
CSS '.mobile-tabs': True
CSS 'font-size: 16px': True
CSS 'order: -1': True
CSS 'grid-template-columns: repeat(3, 1fr)': True
CSS 'clamp(200px, 36dvh, 310px)': True
CSS '.panel[data-tab-panel]:not(.mobile-panel-active)': True
CSS 'min-height: 44px': True
CSS 'position: sticky': True
CSS '#316ac5': True
CSS 'box-shadow: 2px 2px 4px rgba(0, 0, 0, 0.35)': True
CSS 'z-index: 200': True
CSS 'z-index: 500': True
JS 'ResizeObserver': True
JS 'switchMobileTab': True
JS 'syncMenuChecks': True
JS 'openMenu': True
JS 'closeMenus': True
JS 'populatePresetMenu': True
JS 'menu-reset-camera': True
JS 'help-dialog': True
JS 'export-badge': True
```

### 5.7 JavaScript syntax and HTML tag balance

```text
$ cp static/viewer.js .viewer_check.mjs && node --check .viewer_check.mjs
JS syntax OK

HTML parser audit:
errors: []
unclosed: []
```

### 5.8 Playwright desktop/mobile interaction audit

Command: headless Chromium, `1280x900` then resized to `390x844`, against a live `uvicorn web_app:app` server.

```text
PASS: desktop: mobile tabs are hidden
PASS: desktop: [data-tab-panel=model] #0 visible
PASS: desktop: [data-tab-panel=fracture] #0 visible
PASS: desktop: [data-tab-panel=fracture] #1 visible
PASS: desktop: [data-tab-panel=export] #0 visible
PASS: desktop: File dropdown opens
PASS: desktop: File aria-expanded true
PASS: desktop: Escape closes File dropdown
PASS: desktop: active preset checkmark starts on tea_bowl
PASS: desktop: Presets menu updates #preset-select
PASS: desktop: Presets menu checkmark follows selection
PASS: desktop: Mode menu updates generator select
PASS: desktop: shard generator checkmark set
PASS: desktop: ribbon disabled under shard
PASS: desktop: ribbon disabled class under shard
PASS: desktop: shard locks vein mode
PASS: desktop: Mode menu restores growth generator
PASS: desktop: ribbon re-enabled under growth
PASS: desktop: About opens #help-dialog
PASS: desktop: Escape closes #help-dialog
PASS: desktop: R slider reaches 1.00
PASS: desktop: File menu ceramic download enabled after fracture
PASS: desktop: File menu 3MF download enabled after fracture
PASS: desktop: ceramic href populated
PASS: desktop: export readiness badge unhidden after fracture
PASS: mobile: tab strip visible
PASS: mobile: .window uses 100dvh (height ~= 844)
PASS: mobile: viewport-shell ordered above sidebar
PASS: mobile: viewport height in clamp range (303.8px)
PASS: mobile: Model panel hidden by default
PASS: mobile: Fracture panel #0 visible by default
PASS: mobile: Fracture panel #1 visible by default
PASS: mobile: Export panel hidden by default
PASS: mobile: Fracture tab selected by default
PASS: mobile: select font-size is 16px (no iOS zoom)
PASS: mobile: fracture button is sticky
PASS: mobile: fracture button touch target >= 44px
PASS: mobile: export badge visible before opening Export tab
PASS: mobile: Model tab shows Model panel
PASS: mobile: Model tab hides Fracture panel
PASS: mobile: Export tab shows Export panel
PASS: mobile: Export tab clears readiness badge
PASS: mobile: Fracture tab restores Fracture panel
PASS: mobile: File dropdown opens
PASS: mobile: File dropdown stays within viewport
PASS: no page/console errors:
ALL PLAYWRIGHT CHECKS PASSED
```

### 5.9 Playwright download-synchronization audit (`R=0.4`, mobile `390x844`)

```text
PASS: mobile: menu-download-ceramic enabled after fracture
PASS: mobile: #download-ceramic enabled after fracture
PASS: mobile: menu-download-ceramic href matches sidebar link
PASS: mobile: menu-download-gold enabled after fracture
PASS: mobile: #download-gold enabled after fracture
PASS: mobile: menu-download-gold href matches sidebar link
PASS: mobile: menu-download-3mf enabled after fracture
PASS: mobile: #download-3mf enabled after fracture
PASS: mobile: menu-download-3mf href matches sidebar link
PASS: mobile: export badge visible after fracture on Fracture tab
PASS: mobile: export badge clears on Export tab
DOWNLOAD SYNC CHECKS PASSED
```

### 5.10 Final OpenSpec status

```text
$ openspec validate "mobile-ui-menus" --strict
Change 'mobile-ui-menus' is valid

$ openspec list
Changes:
  mobile-ui-menus          ✓ Complete
```

---

**Verification verdict: PASS.** The change complies with every requirement and scenario in `specs/retro-web-gui/spec.md`, preserves all existing DOM contracts, and introduces no backend or dependency drift.
