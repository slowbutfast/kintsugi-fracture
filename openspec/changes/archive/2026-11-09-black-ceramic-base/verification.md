# Verification: Kuro-Raku Black Ceramic Base on Gallery Off-White Viewport (`black-ceramic-base`)

## 1. Executive Summary & Environment

- **Status**: PASS — all tasks complete; all unit and regression tests pass with zero failures.
- **Date**: 2026-11-09
- **Working branch / base**: `feat/black-ceramic-base` branched from `origin/main` (`d063b58`).
- **Environment**:
  - Linux `5.15.0-1081-oracle` (`x86_64` container)
  - Python `3.11.2`
  - Node.js `v20.18.0`
  - Three.js `0.160.0`
  - OpenSpec `1.7.0`
- **Scope & Target Context Map**:
  - `static/viewer.js` (L71-L76, L96-L97, L114, L133-L138): Configured `ceramicMaterial` with Kuro-raku matte black (`0x18181b`, roughness 0.65, metalness 0.10); set `scene.background = new THREE.Color(0xf0ede0)`; updated hemisphere ground bounce to `0xdcd8cc`; adjusted `GridHelper` lines to `0xb8b4a6` / `0xd0ccc0` with `0.40` opacity.
  - `static/xp.css` (L29-L30): Set `--viewport-bg: #f0ede0;` and `--ceramic-body: #18181b;`.
  - `tools/spike_contact_sheet.py` (L34-L36): Synchronized `CERAMIC = (24, 24, 27)`.
  - `tools/render.py` (L113): Synchronized `CERAMIC, GOLD = (24, 24, 27), (230, 175, 40)`.
  - `tools/render_remediation.py` (L112): Synchronized `CERAMIC, GOLD = (24, 24, 27), (230, 175, 40)`.
  - `DESIGN.md` (L39-L40, L136-L138): Updated design tokens for `viewport-bg: "#f0ede0"` and `ceramic-body: "#18181b"`, and updated design rationale to Kuro-raku matte black ceramic on gallery off-white.
  - `tests/test_web_api.py` (L362-L369): Added assertions verifying `--ceramic-body: #18181b`, `--viewport-bg: #f0ede0`, `0x18181b`, and `0xf0ede0`.
- **Result summary**:

| Check | Result |
| :--- | :--- |
| `openspec validate "black-ceramic-base" --strict` | Valid (0 issues) |
| Web API suite (`tests/test_web_api.py`) | 12 / 12 pass |
| Full regression suite (`unittest discover`) | 65 / 65 pass |
| JavaScript syntax (`node --check`) | Pass (0 errors) |

---

## 2. Requirement Adherence Audit Matrix

### 2.1 Requirement-level matrix

| Requirement | Implementation evidence | Verification |
| :--- | :--- | :--- |
| Interactive Three.js 3D viewport with Kuro-raku black ceramic | `static/viewer.js:71-76` sets `color: 0x18181b`, `roughness: 0.65`, `metalness: 0.10`. | `test_mobile_ui_and_menus_markup_served` asserts `0x18181b`; `node --check` passes. |
| Gallery off-white viewport background canvas | `static/viewer.js:96-97` sets `scene.background = new THREE.Color(0xf0ede0)`; `static/xp.css:29` sets `--viewport-bg: #f0ede0;`. | `test_mobile_ui_and_menus_markup_served` asserts `--viewport-bg: #f0ede0` and `0xf0ede0`. |
| Softened ground lighting bounce & floor grid | `static/viewer.js:114` sets `HemisphereLight(0xffffff, 0xdcd8cc, 1.4)`; `static/viewer.js:133-138` sets `GridHelper(260, 26, 0xb8b4a6, 0xd0ccc0)` at `0.40` opacity. | Verified in Three.js initialization and test suite execution. |
| Offline rendering tool consistency | `tools/spike_contact_sheet.py:35`, `tools/render.py:113`, and `tools/render_remediation.py:112` set `CERAMIC = (24, 24, 27)`. | Static code inspection and test discovery pass. |
| Design specification and design tokens updated | `DESIGN.md:39-40` and `DESIGN.md:136-138` reflect `#18181b` and `#f0ede0` tokens and Kuro-raku stoneware aesthetic. | Static document check. |

### 2.2 Spec scenario matrix

| Spec scenario | Verdict | Verifying evidence |
| :--- | :--- | :--- |
| **Real-time 3D inspection**: system renders ceramic body with Kuro-raku matte black diffuse roughness (`#18181b`) and gold seams with metallic specular reflection (`#ffd700`) against gallery off-white canvas (`#f0ede0`) | PASS | `tests/test_web_api.py:test_mobile_ui_and_menus_markup_served` passes; CSS and JS tokens verified; full regression suite (65/65) green. |

---

## 3. Test Execution Logs

### 3.1 Web API Test Suite
```text
.venv/bin/python -m unittest tests/test_web_api.py -v
test_api_fracture_defaults_to_vein_growth (tests.test_web_api.WebApiTestCase.test_api_fracture_defaults_to_vein_growth) ... ok
test_api_fracture_empty_gold_pipeline (tests.test_web_api.WebApiTestCase.test_api_fracture_empty_gold_pipeline) ... ok
test_api_fracture_success (tests.test_web_api.WebApiTestCase.test_api_fracture_success) ... ok
test_api_fracture_thin_wall_rejected (tests.test_web_api.WebApiTestCase.test_api_fracture_thin_wall_rejected) ... ok
test_api_fracture_wealthy (tests.test_web_api.WebApiTestCase.test_api_fracture_wealthy) ... ok
test_api_presets (tests.test_web_api.WebApiTestCase.test_api_presets) ... ok
test_api_upload_too_large (tests.test_web_api.WebApiTestCase.test_api_upload_too_large) ... ok
test_api_validate_ok (tests.test_web_api.WebApiTestCase.test_api_validate_ok) ... ok
test_api_validate_open_mesh (tests.test_web_api.WebApiTestCase.test_api_validate_open_mesh) ... ok
test_api_validate_thin_wall_rejected (tests.test_web_api.WebApiTestCase.test_api_validate_thin_wall_rejected) ... ok
test_job_retention (tests.test_web_api.WebApiTestCase.test_job_retention) ... ok
test_mobile_ui_and_menus_markup_served (tests.test_web_api.WebApiTestCase.test_mobile_ui_and_menus_markup_served) ... ok

----------------------------------------------------------------------
Ran 12 tests in 5.713s

OK
```

### 3.2 Full Regression Test Suite
```text
.venv/bin/python -m unittest discover -s tests -p "test_*.py" -v
Ran 65 tests in 491.624s

OK
```
