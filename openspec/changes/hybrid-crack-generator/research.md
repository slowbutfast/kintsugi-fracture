## Source material

**2026-11-09, project owner (chat):**

> can you propose how we can combine the rim growth and shard plane crack generation algorithms? i think the shard planes are great for getting wider, edge to edge, fractures, and then the rim growth is good for getting the smaller, interior cracks. [...] one of the things that's missing from the rim growth algorithm is that sometimes the cracks don't span all the way to the edge of the geometry where in real life these cracks would [...] literally fracture the object. So if they don't [...] split up the object into multiple parts then [it] doesn't reconstruct well [...] I'm actually more open to only isolating it to basically like [vase] mode geometries [...] restricting the inputs to only be like bowl-shaped objects or like cup-shaped objects more or less. [...] can you propose how we can expose the settings unique to the shard plane algorithm? Because I think right now I'm still seeing the original settings for the original algorithms we had and they don't really affect the shard plane generator. [...] if we do expose these knobs [...] then we can make it specific to the hybrid algorithm.

### Raised but not acted on

- **Exposing knobs for the plain `shard` generator.** The owner leaves this open. It is not adopted: once `hybrid` exists, shard-only knobs would be throwaway UI. The knobs are scoped to `hybrid` only, and setting `hairline_count=0` in `hybrid` reproduces pure macro through-fractures with full knob control.
- **Literal vase-mode (single-perimeter) printing.** "base mode" is read as *vase mode*, meaning open-top, single-wall vessels such as bowls, cups, and vases. It is not a slicer print setting. See the glossary.
- **Ribbon (through-wall) mode for the hybrid.** `shard` is vein-only (`kintsugi.py:3603`). The hybrid inherits that restriction. Making through-fractures physically separate the ceramic solid into multiple disconnected STL mesh components is a separate decision, because it changes the export contract (more than one ceramic body).
- **Making `hybrid` the default generator.** Deferred until visual contact-sheet sign-off. `growth` stays the default while `growth`, `shard`, `hybrid`, and `voronoi` remain selectable.

## Glossary

| Term | Means | Does NOT mean |
| :--- | :--- | :--- |
| Through-fracture (Macro seam) | A Stage-1 seam that partitions the exterior wall surface map: a rim-to-rim wedge (`wall_z_max` to `wall_z_max`), a closed tilted loop, or a rim-to-seam wedge that T-junctions into an earlier through-fracture. Produced by the shard primitives | Any long crack that dead-ends in the wall, or a cut that physically splits the 3D ceramic mesh into separate STL solids |
| Hairline (Interior crack) | A Stage-2 growth crack (nucleated on the rim or at a verified T-junction anchor along a Stage-1 through-fracture) that either dead-ends inside a fragment or T-junctions into another seam | A crack that by itself is required to partition the wall |
| Fragment | A connected region of the unrolled exterior wall surface `(u, z)`, periodic in `u`, on `[0, period) × [wall_z_min, wall_z_max]` after removing every seam inflated to width `W` on a `0.25 mm` raster grid (components `>= 2%` of free area) | A separate disconnected ceramic mesh body in STL export. In vein mode the ceramic stays one connected solid body |
| Vase-mode geometry | An open-top, single-wall vessel (bowl, cup, vase) that passes the cylindrical radial parameterisation (`miss_fraction <= 0.05`), has an interior cavity wall (`has_wall=True`, i.e. at least one `z` slice with `>= 95%` two-wall radial hits), and meets `wall_thickness_p5 >= 1.60 mm` | Printing in Cura/Prusa "spiral vase" single-extrusion mode |
| Knob | A hybrid-only parameter (`through_count`, `through_shape`, `tilt_deg`, `hairline_count`, `hairline_reach`, `roughness`) with an `auto` default derived from `R`, which the user can override | The existing global `R`, `seed`, `seam_width`, and `mode` controls |

## External research

None needed. This change recombines two in-repo generators (`generate_shard_crack_paths` and `generate_crack_growth_paths`).

| Source | What it establishes | Licence | Accessed |
| :--- | :--- | :--- | :--- |
| `kintsugi.py` (`generate_shard_crack_paths`, `generate_crack_growth_paths`) | Existing in-repo shard primitives, growth stepping, `_first_growth_collision`, and `analyze_growth_paths` audit | Project internal | 2026-11-09 |

## Candidate tech

| Option | Decision | Reason | Date |
| :--- | :--- | :--- | :--- |
| Run shard first (Stage 1), then growth (Stage 2) with Stage-1 seams pre-committed as obstacles | Adopted | `generate_crack_growth_paths` already resolves every candidate step against the committed `paths` list through `_first_growth_collision`, with stop-on-hit T-junctions. Pre-seeding that list makes hairlines terminate on through-fractures with no new collision engine | 2026-11-09 |
| Default `through_shape="auto"` to a rim-to-rim `wedge` for Seam 1, while keeping `loop` available via override and making `tilt_deg` steer both shapes | Adopted | Guarantees an unmistakable edge-reaching rim-to-rim break by default while keeping closed tilted loops selectable; applying `tilt_deg` to both wedge nadir/skew and loop inclination ensures the `tilt_deg` knob is never a silent no-op | 2026-11-09 |
| Nucleate Stage-2 hairlines from both rim seeds (clear of Stage-1 rim endpoints) and interior anchors along Stage-1 macro seams | Adopted | Rim seeds provide downward-propagating cracks from the lip, while macro-seam anchors let secondary hairlines branch directly off the main fracture into the shard interior as real ceramic cracks do | 2026-11-09 |
| Run growth first, then fit shard planes around it | Rejected | The shard primitives are global shapes (loop, rim-to-rim wedge). Fitting them around an existing network requires heavy rejection sampling and loses the partition guarantee | 2026-11-09 |
| Post-process growth so dead-end tips extend to the nearest rim or seam | Rejected | Produces the right topology, but the extensions are geometrically unrelated to the crack's heading and look drawn rather than fractured | 2026-11-09 |
| Expose the 6 hybrid knobs as R-derived `auto` values with optional overrides and HTTP 400 on non-`hybrid` generators | Adopted | `R` stays the single primary control; explicit overrides are honoured and echoed in `parameters.hybrid`; sending hybrid knobs to `growth`/`shard`/`voronoi` fails loudly instead of silently doing nothing | 2026-11-09 |

## Patterns adopted

- **Two-stage hierarchical fracture synthesis.** Primary macro fractures partition the vessel wall surface into fragments (`num_fragments >= 2` for `S >= 0.2`), and secondary interior hairlines populate the fragments and branch off macro seams (`generate_hybrid_crack_paths` in `kintsugi.py`).
- **Pre-committed obstacle graph reuse.** Passing Stage-1 polylines into `generate_crack_growth_paths` as initial committed paths reuses `_first_growth_collision` for region-bounded stopping and T-junction snapping.
- **Fail-fast parameter validation.** Sending hybrid-only parameters when `generator != "hybrid"` returns `HTTP 400` in `web_app.py` (`ValueError` in `kintsugi.py`).

## Verified facts

All rows were checked on `main` at `d063b58` (shard PR #5 and menus PR #7 merged).

| Claim | Value | How verified | Date | Volatility |
| :--- | :--- | :--- | :--- | :--- |
| Shard seams always partition the wall; growth often does not | Wall-partition rate over seeds 0–19: `shard` splits 20/20 on all 4 models; `growth` splits 2–8/20 at `R=0.6` and 11–17/20 at `R=0.3` | `partition_probe.py` (scratch) on `generate_crack_paths` output | 2026-11-09 | decays with generator changes |
| Vein mode never separates the ceramic into disconnected bodies | Vein depth `min(0.75 W, 0.5 t)` (`_vein_depth`). Ceramic body count is 1 in 43/48 vein runs | `kintsugi._vein_depth`; `frag_probe.py` (scratch), R=0.3, seeds 0–5, 4 models | 2026-11-09 | stable |
| `shard` rejects ribbon mode | `generator='shard' is only supported in 'vein' mode in Stage 1` | `kintsugi.py:3603`; probe hit it on every ribbon run | 2026-11-09 | stable |
| What the shard generator reads | Only `S` (tiers `<0.2` none / `<0.35` 1 seam / `<0.70` 2 seams / `>=0.70` 2 seams), `W`, `period`, `rbar`, and wall range. Never `N` or `H`. Tilt, kink, and harmonic are fixed per tier, and `_shard_wedge_path` does not currently read `tilt_deg` | `_shard_severity_config`, `_shard_wedge_path`, `generate_shard_crack_paths` (`kintsugi.py:2177-2660`) | 2026-11-09 | decays when hybrid adds wedge tilt |
| What the GUI sends today | `R`, `generator`, `mode`, `seed`, `seam_width`. With `shard`, `R` is a 3-step switch and `ribbon` is disabled | `static/index.html`, `web_app.py:173-181` | 2026-11-09 | stable |
| Growth uses committed paths as obstacles and exempts branch origins | `_first_growth_collision(paths, path_id, a, b, ...)` checks every committed segment in `paths`, including periodic copies `{-P, 0, +P}`, and exempts `(exempt_path_id, exempt_origin)` within `1.10 * r_clear / sin(30°)` | `kintsugi.py:1121`, `kintsugi.py:1441-1447`, `kintsugi.py:1638-1640` | 2026-11-09 | stable |
| Combined audit already exists | `analyze_growth_paths(paths, params)` computes `crossings`, `clearance_violations`, `min_clearance`, and `min_junction_angle_deg` for any path set, and already validates shard Seam 2 | `kintsugi.py:1985`, `kintsugi.py:2639` | 2026-11-09 | stable |
| Growth `N` and `H` formulas | `N = floor(2 + 8S)`, `H = H_mesh * (0.2 + 0.8S)` | `compute_parameters` (`kintsugi.py`) | 2026-11-09 | stable |
| `validate_and_load_mesh` currently skips wall thickness check when `has_wall=False` | `_probe_wall_range` sets `has_wall = bool(np.any(fraction >= 0.95))` (`kintsugi.py:354-355`), and lines 536–551 only check `wall_envelope_passes(p5)` inside `if bool(wall_probe.get("has_wall", True)):`, allowing solid non-hollow meshes through `/api/validate` | `kintsugi.py:354-355`, `kintsugi.py:534-552` | 2026-11-09 | decays when fixed by this change |

**How the partition fact was measured.** The probe rasterises the seams at seam width on a 0.25 mm grid covering `u` (periodic) by `[wall_z_min, wall_z_max]`. A run counts as "split" if the free area has two or more connected components, each larger than 2% of the free area.

| Model | R | Growth split | Shard split | Shard regions per run |
| :--- | :--- | :--- | :--- | :--- |
| tea_bowl | 0.3 | 11/20 | 20/20 | 2–3 |
| vase | 0.3 | 17/20 | 20/20 | 2–3 |
| bowl_urdformer | 0.3 | 12/20 | 20/20 | 2–3 |
| cup_unitree | 0.3 | 13/20 | 20/20 | 2–3 |
| tea_bowl | 0.6 | 2/20 | 20/20 | 2–3 |
| vase | 0.6 | 8/20 | 20/20 | 2–3 |
| bowl_urdformer | 0.6 | 4/20 | 20/20 | 2–3 |
| cup_unitree | 0.6 | 7/20 | 20/20 | 2–3 |

## Unverified assumptions

| Assumption | Confidence | Verification cost |
| :--- | :--- | :--- |
| The growth split rates above are an *upper bound*. The probe's band stops at `wall_z_min`, so two rim-to-floor growth cracks count as a split even though the floor still joins them physically. Shard seams never reach the floor because the wedge nadir is at least `wall_z_min + 0.18 * height` | High | Add a floor cap to the probe; ~10 min |
| Pre-committed shard seams + rim exclusions don't starve growth trunks at `hairline_count <= 10` | Medium | Run the prototype across seeds `42..61` on all presets and inspect the clearance/count audit |
| A third through-fracture (`through_count = 3`), T-junctioning onto any earlier macro seam, fits within the clearance rules on a 70 mm vase and gracefully falls back to 2 seams if all 16 candidates fail | Medium | Prototype `_shard_extra_seam_candidate` generalised to any earlier seam |
| Vein-only visual/topological wall partitioning (`num_fragments >= 2`) satisfies the owner's reconstruction goal without splitting the ceramic STL into multiple disconnected solid bodies | Medium | Owner confirms at visual sign-off |

## Superseded claims

- **"Shard splits the ceramic into separate pieces."** Not in vein mode. Fragments are connected topological regions of the exterior wall surface map, not separate meshes (`_vein_depth` fact above).
- **"`num_fragments = 1 + len(macro_paths)` is an exact fragment count."** Superseded: Stage-2 rim hairlines that T-junction into a macro seam also partition a wall region. `num_fragments` must be measured by raster connected-component analysis on `[0, period) × [wall_z_min, wall_z_max]` (with `num_through_fragments` reported separately for Stage 1).

## Links out

- Shard primitives and audits: `openspec/changes/kintsugi-shard-seams/` and `kintsugi.py:2172-2660`
- Growth generator: `kintsugi.py:1313`
- Real demo models used above: `openspec/changes/real-model-test-corpus/research.md`
