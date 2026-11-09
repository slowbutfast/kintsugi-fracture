## Why

On a broken vessel, long macro fractures divide the exterior wall surface into distinct shard regions, and smaller hairlines branch inside each region. Neither existing generator produces both halves:
- **Growth (`growth`)** produces organic interior branching detail, but its cracks frequently dead-end: at `R = 0.6`, its seam network divides the unrolled wall surface into separate regions in only 2–8 of 20 seeds per model (and even that is an upper bound because `wall_z_min` stops above the solid floor).
- **Shard (`shard`)** partitions the wall surface into 2–3 regions in 20/20 seeds across all 4 tested models (`tea_bowl`, `vase`, `bowl_urdformer`, `cup_unitree`), but produces only 1–2 smooth macro seams with zero interior detail, and exposes no meaningful user controls (`R` acts only as a 3-step switch).

Note: Like `shard`, `hybrid` operates in **`vein` mode only**, so its seams partition the *exterior wall surface map* into closed regions ("fragments") for visual kintsugi reconstruction while `ceramic_body.stl` remains a single connected solid body. See `research.md` (*Verified facts* and *Glossary*).

## What Changes

- **New two-stage `hybrid` generator (`generate_hybrid_crack_paths` in `kintsugi.py`):**
  1. **Through-fractures (Stage 1 — shard stage).** For `S = 1 - clip(R, 0, 1) >= 0.2` (or when `through_count` is explicitly overridden for `S > 0`), generates 1–3 macro shard seams (`through_count`), where Seam 2 and Seam 3 T-junction onto any earlier macro seam (`_shard_extra_seam_candidate`). When `through_shape="auto"` (or `"wedge"`), Seam 1 is a rugged rim-to-rim `wedge` (`wall_z_max` to `wall_z_max`) so the primary break reaches the upper rim edge at both ends; `through_shape="loop"` selects the closed tilted loop primitive (which does not reach the rim, and falls back to a wedge on short walls). `tilt_deg` steers both the loop plane inclination and the wedge nadir depth/asymmetry so `tilt_deg` is active under every shape. For `S < 0.2` (`R > 0.8`) with `auto` knobs, `hybrid` matches `shard` and produces 0 seams (`num_fragments = 1`).
  2. **Interior hairlines (Stage 2 — growth stage).** Runs `generate_crack_growth_paths` with the Stage-1 macro seams pre-committed into its `paths` list. Because `_first_growth_collision` checks every committed segment (including periodic copies), growing hairlines automatically T-junction into macro through-fractures or terminate inside a fragment with zero new collision logic. Primary hairline trunks (`hairline_count`) nucleate from a deterministic split of **rim seeds** (kept at least `1.5 * (W + 0.8 mm)` clear of Stage-1 rim crossings in both rejection sampling and gap fallback) and **interior anchors along Stage-1 macro seams** (enqueued with `exempt_path_id` and `exempt_origin` set to the parent macro seam so the initial step does not self-collide, departing downward at `60°–85°` from the seam tangent).
  3. **Combined graph audit & raster fragment count.** Validates the union of Stage-1 and Stage-2 paths via `analyze_growth_paths` for zero crossings, non-incident segment clearance `>= W + 0.8 mm` outside the junction exemption neighborhood, and junction angles `>= 30°`. Computes `num_fragments` (and `num_through_fragments` for Stage 1 alone) by rasterising the seams at width `W` on a `0.25 mm` periodic `(u, z)` grid over `[0, period) × [wall_z_min, wall_z_max]` and counting connected free-wall components `>= 2%` of free area.
- **Hybrid-only knobs (`auto` by default, derived from `S = 1 - R`):**

  | Knob | Range | `auto` Default (from `S = 1 - R`) |
  | :--- | :--- | :--- |
  | `through_count` | `1–3` | `0` for `S < 0.20`, `1` for `0.20 <= S < 0.35`, `2` for `0.35 <= S < 0.70`, `3` for `S >= 0.70` |
  | `through_shape` | `auto`, `wedge`, `loop` | `wedge` (edge-reaching rim-to-rim break; `loop` is a closed interior ring, falling back to `wedge` on short walls) |
  | `tilt_deg` | `5.0–30.0` | Shard tier value (`14.0` for `S < 0.35`, `20.0` for `0.35 <= S < 0.70`, `26.0` for `S >= 0.70`), steering both wedge nadir/skew and loop tilt |
  | `hairline_count` | `0–10` (`0` = through-fractures only) | Named tier table: `0` for `S < 0.20`, `3` for `0.20 <= S < 0.35`, `5` for `0.35 <= S < 0.70`, `7` for `S >= 0.70` primary hairline trunks |
  | `hairline_reach` | `0.2–1.0` × wall height | Growth's `H` ratio, `0.2 + 0.8 * S` |
  | `roughness` | `0.5–2.0` | `1.0` (scales Stage-1 harmonic/kink amplitude and Stage-2 step heading delta before `_clamp_heading`) |

  - **API (`POST /api/fracture`):** Accepts these 6 knobs as optional form fields. Sending any hybrid knob when `generator != "hybrid"` returns `HTTP 400` (`ValueError` in `kintsugi.py`), so controls never silently do nothing.
  - **Result telemetry:** `parameters.hybrid` echoes each knob's resolved value (including `through_shape_requested`, `hairline_rim_count`, `hairline_seam_count`, `num_through_fragments`, and `num_fragments`), allowing the UI to display `"Auto (...)"`.
  - **GUI (`static/index.html`, `static/viewer.js`):** Adds `Hybrid (Shard + Growth)` to the generator selector and menu, shows a collapsible `#hybrid-settings` panel only when `generator === "hybrid"`, and disables `ribbon` mode when `hybrid` is selected.
- **Vessels only, enforced globally at validation time:** `validate_and_load_mesh` now raises a `ValueError` when `has_wall=False` (i.e. when no horizontal probe slice has `>= 95%` two-wall radial hits in `_probe_wall_range`), closing the solid-cylinder validation defect recorded in `real-model-test-corpus` across all generators and modes.
- **Unchanged:** `growth` remains the default generator, and `growth`, `shard`, and `voronoi` produce byte-identical output across the baseline preset and severity suite.

## Capabilities

### New Capabilities
- None. The hybrid generator is added inside the existing fracture engine and web GUI capabilities.

### Modified Capabilities
- `mesh-fracture-engine`:
  - Adds `generator="hybrid"`: two-stage through-fracture + interior hairline synthesis, raster-verified `num_fragments >= 2` guarantee for `S >= 0.2`, combined graph audit invariants, and the 6 `auto`-defaulted hybrid knobs with fail-fast rejection on other generators.
  - Enforces `has_wall=True` inside `validate_and_load_mesh` globally so solid non-hollow bodies are rejected at validation time.
- `retro-web-gui`:
  - Adds `Hybrid (Shard + Growth)` to the generator selector and mode menu, adds the conditional `#hybrid-settings` control group with `Auto` defaults, disables `ribbon` mode when `hybrid` is active, and rejects hybrid knobs sent with non-`hybrid` generators (`HTTP 400`).

## Impact

- **Code:**
  - `kintsugi.py`: `validate_and_load_mesh` (`has_wall` gate), `_poisson_rim_seeds` (rim exclusions in both rejection and gap fallback), `_shard_wedge_path` (`tilt_deg` and `roughness_scale` support), `generate_crack_growth_paths` (optional pre-committed paths, junctions, rim exclusions, seam-anchored hairlines with `exempt_path_id`/`exempt_origin`, and roughness scale), `_shard_extra_seam_candidate` (generalized Seam 2/3 T-junction search across all existing macro seams), `_count_wall_fragments` (0.25 mm periodic raster connected components), `generate_hybrid_crack_paths`, `generate_crack_paths`, `generate_kintsugi_mesh`, and CLI arguments.
  - `web_app.py`: Optional hybrid form fields on `POST /api/fracture`, `HTTP 400` validation when sent with `generator != "hybrid"`, and `num_fragments` in the response JSON.
  - `static/index.html` and `static/viewer.js`: `Hybrid` selector/menu item, `#hybrid-settings` panel, `ribbon` disable logic, and `Auto (...)` resolved label updates.
  - `tools/spike_contact_sheet.py`: Support `--generator hybrid` and `--generator all`.
- **Tests:**
  - `tests/test_crack_hybrid.py` (new) and `tests/test_web_api.py` (run via `./.venv/bin/python -m unittest`): Pre-change SHA-256 baseline digests for `growth` and `shard`, hybrid determinism, raster `num_fragments >= 2`, zero crossings, clearance `>= W + 0.8 mm`, junction angles `>= 30°`, verification that every one of the 6 knobs alters the output paths under its supported shapes, `HTTP 400` on non-`hybrid` knob combinations, and solid-body validation rejection (`has_wall=False`), using seeds outside reserved hold-out ranges (`300–399` and `>= 600`).
