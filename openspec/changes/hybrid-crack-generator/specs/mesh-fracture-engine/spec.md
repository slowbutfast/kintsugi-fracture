## ADDED Requirements

### Requirement: Validation-time vessel wall requirement

`validate_and_load_mesh` SHALL reject any input whose radial wall probe finds no horizontal slice with at least 95% two-hit radial samples (`has_wall == False`) by raising a `ValueError` that states the input has no usable wall. This rejection SHALL occur during validation, before any crack generation, so solid bodies with no interior cavity never reach the fracture stage.

#### Scenario: Solid non-hollow body rejected at validation
- **WHEN** a closed solid cylinder with no interior cavity is passed to `validate_and_load_mesh`
- **THEN** the function raises a `ValueError` whose message states that the input has no usable wall, and no crack paths or output files are produced

#### Scenario: Open-top vessel with a measurable wall accepted
- **WHEN** a watertight open-top bowl with a two-hit radial wall across its wall range is passed to `validate_and_load_mesh`
- **THEN** validation succeeds and the returned probe reports `has_wall == True`

### Requirement: Hybrid two-stage crack generation

The system SHALL support an opt-in `generator="hybrid"` in `generate_crack_paths` and `generate_kintsugi_mesh`. Hybrid SHALL run only in `mode="vein"` and SHALL raise a `ValueError` for `mode="ribbon"`. It SHALL implement two stages in `generate_hybrid_crack_paths`:

1. **Through-fracture stage.** Generate between one and three shard-style macro seams. The first seam is a rim-to-rim wedge or a closed tilted loop. Each later seam T-junctions into any earlier macro seam and is truncated at the earliest intersection across all existing macro seams. The through-fracture set SHALL partition the unrolled wall into at least two fragments whenever $S \ge 0.2$.
2. **Hairline stage.** Run `generate_crack_growth_paths` with the stage-1 seams pre-committed as obstacle paths and with rim seeds excluded around every stage-1 rim crossing. Hairlines SHALL either T-junction into a through-fracture or dead-end inside a fragment. A configured number of hairlines SHALL start at interior macro-seam anchors whose first growth task sets `exempt_path_id` and `exempt_origin` so the first step does not collide with the parent seam.

The combined Stage-1 and Stage-2 path set SHALL be validated directly with `analyze_growth_paths(paths, params)` without silently pruning paths. The result SHALL report `num_through_fragments` and `num_fragments` from `_count_wall_fragments`.

#### Scenario: Two-stage partition on a vessel
- **WHEN** `generate_hybrid_crack_paths` is called at $S \ge 0.2$ on a supported vessel
- **THEN** it returns a combined path set with at least one stage-1 through-fracture, `num_through_fragments >= 2`, and `num_fragments >= 2`

#### Scenario: Low severity auto behaviour
- **WHEN** $S < 0.2$ and both `through_count` and `hairline_count` are `auto`
- **THEN** `generate_hybrid_crack_paths` returns an empty path list, reports `through_count = 0`, `hairline_count = 0`, and `num_fragments = 1`

#### Scenario: Low severity explicit override
- **WHEN** $0 < S < 0.2$ and `through_count >= 1` or `hairline_count >= 1` is supplied explicitly
- **THEN** Stage 1 uses the lowest shard tier baselines (`harmonic = 0.015`, `kink_deg = 4.0`, `tilt_deg = 14.0`) instead of returning an empty path list

#### Scenario: Stage-1 auto shape reaches the rim
- **WHEN** `through_shape="auto"` and the generator selects a wedge, or a loop is unavailable and falls back to a wedge
- **THEN** the resulting macro seam is an open wedge whose two endpoints reach the upper rim within the stage-1 truncation bounds

#### Scenario: Seam 2 and Seam 3 T-junction into any earlier seam
- **WHEN** a later macro seam is requested
- **THEN** `_shard_extra_seam_candidate` targets any earlier macro seam, truncates at the earliest hit across all existing macro seams, inserts a shared vertex in the hit seam, and rejects candidates below the 30° arrival angle or `W + 0.8 mm` clearance rules

#### Scenario: Hairline obstacles and rim exclusion
- **WHEN** the hairline stage runs after stage 1
- **THEN** stage-1 seams are present in the growth generator's committed obstacle list, and no rim seed is placed within the exclusion radius of a stage-1 rim crossing in either rejection sampling or the largest-gap fallback

#### Scenario: Macro-seam interior hairline anchors
- **WHEN** `hairline_count >= 2` and a stage-1 macro seam is available
- **THEN** at least one hairline trunk starts at an interior point on a macro seam, its first growth task carries `exempt_path_id`/`exempt_origin` for that seam, and its first step survives collision resolution

#### Scenario: Combined audit invariants
- **WHEN** the union of stage-1 and stage-2 paths is audited
- **THEN** `analyze_growth_paths` reports zero crossings, zero clearance violations, `min_clearance >= W + 0.8 mm`, and every reported junction angle is at least 30°

#### Scenario: Periodic raster fragment counter
- **WHEN** `_count_wall_fragments(paths, params)` rasterises seams at half-width $0.5W$ on a 0.25 mm grid over $[0, period) \times [wall\_z\_min, wall\_z\_max]$
- **THEN** it counts 4-connected free-wall components whose area is at least 2% of the total free area, with periodicity in $u$ and no wrap-around double counting

#### Scenario: Deterministic hybrid output
- **WHEN** `generate_hybrid_crack_paths` is called twice with the same model, $R$, seed, and resolved knobs
- **THEN** both runs produce byte-identical path arrays

### Requirement: Hybrid knob ranges and Auto resolution

The system SHALL accept hybrid-only knobs `through_count` (1–3), `through_shape` (`auto`, `wedge`, `loop`), `tilt_deg` (5–30), `hairline_count` (0–10), `hairline_reach` (0.2–1.0), and `roughness`. Each knob SHALL default to `auto` and resolve from $S = 1 - R$:

| Knob | Auto rule |
| :--- | :--- |
| `through_count` | 1 for $S < 0.35$, 2 for $S < 0.70$, 3 above |
| `through_shape` | 50/50 per seed, with loop falling back to wedge when unavailable |
| `tilt_deg` | Shard tier value 14, 20 or 26 |
| `hairline_count` | 0 for $S < 0.20$, 3 for $S < 0.35$, 5 for $S < 0.70$, 7 above |
| `hairline_reach` | $0.2 + 0.8S$ |
| `roughness` | 1.0 |

The resolved values SHALL be echoed in `parameters["hybrid"]`, together with actual placed counts and `num_through_fragments` / `num_fragments`. Sending a non-`None` hybrid knob with any generator other than `"hybrid"` SHALL raise a `ValueError`.

#### Scenario: Auto values resolved from severity
- **WHEN** `generate_hybrid_crack_paths` runs at $S = 0.5$ with all knobs at `auto`
- **THEN** `parameters["hybrid"]` reports `through_count = 2`, `hairline_count = 5`, `hairline_reach = 0.6`, and a shard-tier `tilt_deg` of 20

#### Scenario: Explicit knob override echoed
- **WHEN** a caller supplies `through_count`, `through_shape`, `tilt_deg`, `hairline_count`, `hairline_reach` or `roughness`
- **THEN** the supplied value is validated against its range, used by generation, and echoed in `parameters["hybrid"]`

#### Scenario: Hybrid knobs rejected for other generators
- **WHEN** a non-`None` hybrid knob is passed with `generator="growth"`, `"shard"` or `"voronoi"`
- **THEN** the system raises a `ValueError` instead of silently ignoring the knob
