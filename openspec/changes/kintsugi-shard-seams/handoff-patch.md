# Surgical Patch Handoff: OpenSpec Change 'kintsugi-shard-seams' [PATCH-01]

## 1. Executive Objective & Diagnostic Feedback
- **Change Name**: `kintsugi-shard-seams`
- **Patch ID**: `PATCH-01`
- **Objective**: Expose the fracture generator selector (`growth`, `shard`, `voronoi`) in the Kintsugi Studio 2001 Web GUI (`static/index.html`, `static/viewer.js`, `static/xp.css`), automatically enforce `mode="vein"` when `shard` is selected, and update project documentation (`README.md` and OpenSpec `retro-web-gui` / `design.md` / `proposal.md` specs).
- **Feedback & Diagnostic Trace**:
  ```
  i'm not seeing the shard option in the generator choices, or for that matter, i don't see choices to choose the generator option in the ui as well. can you propose an ui fix that exposes this option because i'm not able to see it. and then also how we can update the documentation as well. use the openspec-handoff-patch skill
  ```
- **Root Cause Analysis**:
  Stage 1 initially deferred Web GUI controls while wiring `generator` only in `kintsugi.py` and `web_app.py` (`api_fracture`). Consequently, `static/index.html` has no `<select id="generator-select">` control inside the `Fracture Controls` panel, `static/viewer.js` never appends `generator` to the `FormData` sent to `POST /api/fracture`, and `README.md` only describes the older CLI options without `--generator {growth,shard,voronoi}` or Web GUI generator selection.

## 2. Strict Target Context Map
| File Path (relative to repo root) | Target Lines | Modification Summary |
|---|---|---|
| `static/index.html` | `L64-L84` | Inside `<section class="panel"><h2 class="panel-title">Fracture Controls</h2>`, add `<label class="field-label" for="generator-select">Generator</label>`, `<select class="xp-select" id="generator-select" aria-label="Fracture generator">` with `<option value="growth" selected>Rim Growth — branching lightning (default)</option>`, `<option value="shard">Shard Planes — tilted kintsugi seams</option>`, and `<option value="voronoi">Periodic Voronoi — legacy cellular</option>`, plus `<div class="field-note" id="generator-note">Rim-seeded branching cracks.</div>` right above the `Mode` `<fieldset>`. |
| `static/viewer.js` | `L19-L40, L370-L433, L435-L499` | Bind `generator: $("generator-select")` and `generatorNote: $("generator-note")` in `ui`. Add `syncGeneratorMode()` so when `ui.generator.value === "shard"`, the `vein` radio button is checked, the `ribbon` radio button is disabled (`ribbonInput.disabled = true`), and `ui.generatorNote.textContent` updates to `"Tilted shard seams (Vein Inlay only)."`; when `growth` or `voronoi` is selected, re-enable `ribbon`. In `fracture()`, append `form.append("generator", ui.generator ? ui.generator.value : "growth")`. Call `syncGeneratorMode()` in `start()` and on `ui.generator` `"change"`. |
| `static/xp.css` | `L284-L305` | Add `.radio-option input[type="radio"]:disabled + span { color: var(--on-surface-disabled); cursor: not-allowed; }` so the disabled `Ribbon Cut` radio option visually reflects its disabled state using `--on-surface-disabled` (`#888888`). |
| `README.md` | `L10-L60` | Update "How it works" step 3 and "Usage" (CLI, Python, Web GUI) to document all three generators: `growth` (default rim-seeded branching), `shard` (tilted shard-plane seams, `vein` mode), and `voronoi` (legacy periodic Voronoi), plus `--generator growth|shard|voronoi`. |
| `openspec/changes/kintsugi-shard-seams/proposal.md` | `L13-L68` | Update What Changes, Capabilities (`retro-web-gui`), and Impact to include the Web GUI `#generator-select` control and `README.md` updates. |
| `openspec/changes/kintsugi-shard-seams/design.md` | `L16-L100` | Document the `#generator-select` component anatomy, states (`growth`, `shard` locking `mode="vein"`, `voronoi`), and Windows XP Luna tokens (`--surface-light`, `--border-shadow`, `--on-surface-disabled`). |
| `openspec/changes/kintsugi-shard-seams/specs/retro-web-gui/spec.md` | `[NEW]` | Add delta spec modifying `Requirement: Real-time parameter controls and fracture execution` to include the `Generator` dropdown (`growth`, `shard`, `voronoi`) and automatic `vein`-mode lock when `shard` is selected. |
| `openspec/specs/retro-web-gui/spec.md` | `L39-L50` | Sync the modified `Requirement: Real-time parameter controls and fracture execution` into the main `retro-web-gui` spec. |
| `tests/test_crack_shard.py` | `L353-L404` | Add `test_web_ui_exposes_generator_select_and_shard_option` verifying `GET /` serves `#generator-select` with `growth`, `shard`, and `voronoi` options and `GET /viewer.js` wires `generator-select`, enforces `vein` mode for `shard`, and appends `generator` to `/api/fracture`. |

## 3. Blast Radius & Invariant Guardrails
- **STRICT BLAST RADIUS**: Modify ONLY the lines and files specified in the Target Context Map.
- **FORBIDDEN**:
  - Do NOT refactor surrounding working code in `kintsugi.py` or `web_app.py`.
  - Do NOT modify `.env` or credential files.
  - Do NOT modify existing passing tests unless the test assertion itself was demonstrably incorrect.
- **INVARIANTS TO PRESERVE**: All existing 63 passing unit/integration tests MUST continue to pass, and `openspec validate --all --strict` MUST pass with 0 errors.

## 4. Visual & UI Impact (if applicable)
- **Theme**: Windows XP Luna Retro Minimalist (`DESIGN.md` / `static/xp.css`)
- **Component**: `#generator-select` (`class="xp-select"`) and `#generator-note` (`class="field-note"`) inside the `Fracture Controls` panel (`static/index.html`).
- **Tokens Used**:
  - Select surface: `var(--surface-light)` (`#ffffff`), inset border `var(--border-shadow) var(--border-highlight) var(--border-highlight) var(--border-shadow)` (`#918e82` / `#ffffff`)
  - Disabled radio label when `shard` is active: `var(--on-surface-disabled)` (`#888888`)
  - Note caption: `var(--on-surface-muted)` (`#555555`), `10px` Tahoma

## 5. Reproduction & Verification Protocol
1. **Reproduce First**: Scaffold `test_web_ui_exposes_generator_select_and_shard_option` in `tests/test_crack_shard.py` and run `.venv/bin/python -m unittest tests.test_crack_shard.CrackShardTestCase.test_web_ui_exposes_generator_select_and_shard_option -v`. Confirm it fails before `static/index.html` and `static/viewer.js` are updated.
2. **Apply Minimal Fix**: Make targeted edits in `static/index.html`, `static/viewer.js`, `static/xp.css`, `README.md`, and the OpenSpec spec/design/proposal files.
3. **Verify Fix**: Re-run `.venv/bin/python -m unittest tests.test_crack_shard.CrackShardTestCase.test_web_ui_exposes_generator_select_and_shard_option -v`. Confirm it passes.
4. **Full Regression Suite**: Run `.venv/bin/python -m unittest discover -s tests -p "test_*.py" -v` and `openspec validate --all --strict`. Confirm 100% clean passes.

## 6. Surgical Patch Checklist
- [x] P01.1 Scaffold `test_web_ui_exposes_generator_select_and_shard_option` in `tests/test_crack_shard.py`, run `.venv/bin/python -m unittest tests.test_crack_shard.CrackShardTestCase.test_web_ui_exposes_generator_select_and_shard_option -v`, and confirm failure.
- [x] P01.2 Implement minimal fix in `static/index.html`, `static/viewer.js`, `static/xp.css`, `README.md`, and OpenSpec artifacts (`proposal.md`, `design.md`, `specs/retro-web-gui/spec.md`, `openspec/specs/retro-web-gui/spec.md`).
- [x] P01.3 Re-run `.venv/bin/python -m unittest tests.test_crack_shard.CrackShardTestCase.test_web_ui_exposes_generator_select_and_shard_option -v` and confirm PASS.
- [x] P01.4 Run full test suite `.venv/bin/python -m unittest discover -s tests -p "test_*.py" -v` and `openspec validate --all --strict` and confirm zero regressions.
- [x] P01.5 Update `openspec/changes/kintsugi-shard-seams/tasks.md` checkboxes to `- [x]`, mark `PATCH-01` as `RESOLVED` in `patch.md`, and append the verification log to `verification.md`.
