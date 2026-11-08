# Patch Ledger: `kintsugi-shard-seams`

### [PATCH-01] Expose Fracture Generator Selector (Growth / Shard / Voronoi) in Web GUI and Update Documentation
- **Date**: 2026-11-08 14:49:42 UTC
- **Feedback Source**: Manual Playtest
- **Reported Issue**: "i'm not seeing the shard option in the generator choices, or for that matter, i don't see choices to choose the generator option in the ui as well. can you propose an ui fix that exposes this option because i'm not able to see it. and then also how we can update the documentation as well. use the openspec-handoff-patch skill"
- **Root Cause**: Stage 1 initially scoped `generator="shard"` to CLI/API only (`web_app.py:172` accepts `generator`, but `static/index.html` lacks a `#generator-select` control in `Fracture Controls` and `static/viewer.js` never appends `form.append("generator", ...)` in `fracture()`). Additionally, `README.md` only documented legacy Voronoi/CLI flags without `--generator {growth,shard,voronoi}`.
- **Target Files**: `static/index.html, static/viewer.js, static/xp.css, README.md, openspec/changes/kintsugi-shard-seams/proposal.md, openspec/changes/kintsugi-shard-seams/design.md, openspec/changes/kintsugi-shard-seams/specs/retro-web-gui/spec.md, openspec/specs/retro-web-gui/spec.md, tests/test_crack_shard.py`
- **Expected Resolution**:
  1. `static/index.html` exposes `<select class="xp-select" id="generator-select">` inside the `Fracture Controls` panel with options `growth` ("Rim Growth — branching lightning (default)"), `shard` ("Shard Planes — tilted kintsugi seams"), and `voronoi` ("Periodic Voronoi — legacy cellular"), plus a `<div class="field-note" id="generator-note">` hint.
  2. `static/viewer.js` binds `ui.generator = $("generator-select")`, synchronizes the `Mode` radio buttons (`syncGeneratorMode()`) so selecting `shard` automatically selects `mode="vein"`, disables the `ribbon` radio option with an explanatory note (`"Shard Planes supports Vein Inlay only"`), and sends `form.append("generator", ui.generator.value)` in `POST /api/fracture`.
  3. `static/xp.css` styles disabled radio options (`.radio-option input[type="radio"]:disabled + span { color: var(--on-surface-disabled); cursor: not-allowed; }`).
  4. `README.md` documents the three generators (`growth`, `shard`, `voronoi`), the `--generator` CLI flag, the `generator` Python parameter, and the Web GUI Generator selector.
  5. `tests/test_crack_shard.py` verifies via `test_web_ui_exposes_generator_select_and_shard_option` that `GET /` serves `#generator-select` with `growth`, `shard`, and `voronoi` options and `GET /viewer.js` submits `generator` to `/api/fracture`.
- **Status**: RESOLVED
