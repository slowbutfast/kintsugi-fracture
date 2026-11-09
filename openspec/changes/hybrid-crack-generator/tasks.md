# Tasks — hybrid-crack-generator

## 1. TDD Baseline & Failing Tests

- [x] 1.1 Capture pre-change SHA-256 baseline digests for `generate_crack_paths` (`generator="growth"` and `generator="shard"`) across `tea_bowl` and `vase` at `R in {0.2, 0.3, 0.35, 0.65, 0.75, 0.8}` and seeds `42, 43, 44` before modifying `kintsugi.py`, and embed them in `tests/test_crack_hybrid.py`
- [x] 1.2 Add failing tests in `tests/test_crack_hybrid.py` for validation-time `has_wall=False` rejection on solid non-hollow meshes in `validate_and_load_mesh`
- [x] 1.3 Add failing tests in `tests/test_crack_hybrid.py` for `generate_hybrid_crack_paths` determinism, low-severity behaviour (`S < 0.2` returns `[]` and `num_fragments == 1`), Stage-1 edge-reaching default (`through_shape="auto"` -> `wedge`), Seam 2/3 T-junction generalization (`_shard_extra_seam_candidate`), and `0.25 mm` periodic raster fragment guarantee (`num_through_fragments >= 2` and `num_fragments >= 2` across seeds `42..61` for `S >= 0.2`)
- [x] 1.4 Add failing tests in `tests/test_crack_hybrid.py` for Stage-2 pre-committed obstacle collision, rim exclusion around Stage-1 rim crossings (in both rejection sampling and largest-gap fallback), macro-seam interior hairline anchors with `exempt_path_id`/`exempt_origin` (`hairline_seam_count > 0`), and combined `analyze_growth_paths` audit invariants (`crossings == 0`, `min_clearance >= W + 0.8 mm`, junction angle `>= 30°`)
- [x] 1.5 Add failing tests in `tests/test_crack_hybrid.py` and `tests/test_web_api.py` verifying that varying each of the 6 hybrid knobs (`through_count`, `through_shape`, `tilt_deg` under both `"wedge"` and `"loop"`, `hairline_count`, `hairline_reach`, `roughness`) produces distinct output polylines, echoes resolved telemetry in `parameters["hybrid"]`, rejects `mode="ribbon"`, and returns `HTTP 400` / `ValueError` when hybrid knobs are sent with `generator != "hybrid"`

## 2. Core Generator & Validation

- [x] 2.1 Update `validate_and_load_mesh` (`kintsugi.py:534-552`) to raise a `ValueError` when `not bool(wall_probe.get("has_wall", True))` so solid bodies without an interior cavity (`< 95%` two-wall radial hits on every horizontal slice) are rejected at validation time
- [x] 2.2 Implement `_resolve_hybrid_config(params, hybrid_options)` and `_validate_hybrid_options(generator, hybrid_options)` in `kintsugi.py` to validate knob ranges, compute `auto` defaults from `S = 1 - R` (including the named `hairline_count` tier table `0 / 3 / 5 / 7` and `S < 0.2` fallback), and reject non-`None` hybrid knobs when `generator != "hybrid"`
- [x] 2.3 Update `_shard_wedge_path` (`kintsugi.py:2297-2344`) to accept optional `apply_tilt: bool = False` and `roughness_scale: float = 1.0` so `tilt_deg` steers wedge nadir depth and longitudinal skew in `hybrid` while keeping plain `shard` byte-identical, and generalize `_shard_second_seam_candidate` (`kintsugi.py:2453-2583`) into `_shard_extra_seam_candidate(params, rng, existing_paths, attempt_index)`
- [x] 2.4 Extend `_poisson_rim_seeds` (`kintsugi.py:899-930`) to enforce `excluded_u` and `exclusion_radius` across both rejection sampling and the largest-gap fallback, and extend `generate_crack_growth_paths` (`kintsugi.py:1313-1660`) with keyword-only parameters (`initial_paths`, `initial_junctions`, `excluded_rim_u`, `hairline_count`, `hairline_reach`, `roughness_scale`, `seam_anchor_count`) using `exempt_path_id` and `exempt_origin` for macro-seam anchors while keeping default invocations byte-identical
- [x] 2.5 Implement `_count_wall_fragments(paths, params)` (`0.25 mm` periodic `(u, z)` raster connected-component counter), `generate_hybrid_crack_paths`, and `generator="hybrid"` dispatch in `generate_crack_paths`, `generate_kintsugi_mesh`, and the CLI (`_build_parser` / `main`)

## 3. API & Tooling

- [x] 3.1 Update `POST /api/fracture` in `web_app.py` (`L172-L244`) to accept optional form fields `through_count`, `through_shape`, `tilt_deg`, `hairline_count`, `hairline_reach`, and `roughness`, validate them against `generator`, pass `hybrid_options` to `generate_kintsugi_mesh`, and return `num_fragments` in the response payload
- [x] 3.2 Update `tools/spike_contact_sheet.py` (`L495-L565`) to accept `--generator hybrid` and `--generator all` for side-by-side contact-sheet comparisons

## 4. Web GUI

- [x] 4.1 Add `Hybrid — macro shards + interior hairlines` (`value="hybrid"`, `data-generator="hybrid"`) and the collapsible `#hybrid-settings` `<fieldset>` with the 6 `Auto`-defaulted controls and `#hybrid-resolved-note` to `static/index.html`
- [x] 4.2 Update `static/viewer.js` (`syncMenuChecks`, `syncGeneratorMode`, `runFracture`) to toggle `#hybrid-settings` visibility, disable `ribbon` mode when `generator === "hybrid"`, append hybrid knobs to `FormData` only when `generator === "hybrid"`, and render resolved values and `num_fragments` from `result.parameters.hybrid`

## 5. Verification

- [x] 5.1 Run full regression test suite (`./.venv/bin/python -m unittest discover -s tests -v`), verify clean passes across all new and existing tests, and verify zero SHA-256 baseline drift on `growth` and `shard`
- [x] 5.2 Populate `verification.md` with Requirement Adherence Matrix, resolved assumptions, and verbatim execution logs
