## Source material

**2026-11-09, project owner (chat):**

> can you propose how we can combine the rim growth and shard plane crack generation algorithms? i think the shard planes are great for getting wider, edge to edge, fractures, and then the rim growth is good for getting the smaller, interior cracks. [...] one of the things that's missing from the rim growth algorithm is that sometimes the cracks don't span all the way to the edge of the geometry where in real life these cracks would [...] literally fracture the object. So if they don't [...] split up the object into multiple parts then [it] doesn't reconstruct well [...] I'm actually more open to only isolating it to basically like [vase] mode geometries [...] restricting the inputs to only be like bowl-shaped objects or like cup-shaped objects more or less. [...] can you propose how we can expose the settings unique to the shard plane algorithm? Because I think right now I'm still seeing the original settings for the original algorithms we had and they don't really affect the shard plane generator. [...] if we do expose these knobs [...] then we can make it specific to the hybrid algorithm.

### Raised but not acted on

- **Exposing knobs for the plain `shard` generator.** The owner leaves this open. It is not adopted: once `hybrid` exists, shard-only knobs would be throwaway UI. The knobs are scoped to `hybrid` only.
- **Literal vase-mode (single-perimeter) printing.** "base mode" is read as *vase mode*, meaning open-top, single-wall vessels such as bowls, cups and vases. It is not a print setting. See the glossary.
- **Ribbon (through-wall) mode for the hybrid.** `shard` is vein-only (`kintsugi.py:3603`). The hybrid inherits that restriction for now. Making through-fractures physically separate the ceramic is a separate decision, because it changes the export contract (more than one ceramic body).
- **Making `hybrid` the default generator.** It is deferred until the owner signs it off visually. `growth` stays the default.

## Glossary

| Term | Means | Does NOT mean |
| :--- | :--- | :--- |
| Through-fracture | A seam that partitions the wall: a rim-to-rim wedge, a closed tilted loop, or a wedge that T-junctions into another through-fracture. Produced by the shard primitives | Any long crack |
| Hairline | A growth-generator crack that either dead-ends inside a fragment or T-junctions into a seam | A crack that by itself separates the wall |
| Fragment | A connected region of the unrolled wall `(u, z)`, periodic in `u`, after removing every through-fracture inflated to seam width | A separate ceramic mesh body. In vein mode the ceramic stays one body |
| Vase-mode geometry | An open-top, single-wall vessel (bowl, cup, vase) that passes the cylindrical parameterisation and has a two-hit wall | Printing in Cura/Prusa "spiral vase" mode |
| Knob | A hybrid-only parameter with an `auto` default derived from `R`, which the user can override | The existing R, seed, seam width and mode controls |

## External research

None needed. This change recombines two in-repo generators.

## Candidate tech

| Option | Decision | Reason | Date |
| :--- | :--- | :--- | :--- |
| Run shard first, then growth with the shard seams pre-committed as obstacles | Adopted | `generate_crack_growth_paths` already resolves every candidate step against the committed `paths` list through `_first_growth_collision`, with stop-on-hit T-junctions. Pre-seeding that list makes hairlines terminate on through-fractures with no new collision code | 2026-11-09 |
| Run growth first, then fit shard planes around it | Rejected | The shard primitives are global shapes (loop, rim-to-rim wedge). Fitting them around an existing network means rejection sampling against many obstacles, and the partition guarantee is lost | 2026-11-09 |
| Post-process growth so dead-end tips extend to the nearest rim or seam | Rejected | It produces the right topology, but the extensions are geometrically unrelated to the crack's heading. It looks drawn, not fractured | 2026-11-09 |
| Expose the knobs as R-derived `auto` values with optional overrides | Adopted | R stays the single main control. Overrides are explicit, and the result echoes their resolved values | 2026-11-09 |

## Patterns adopted

- **Two-stage fracture hierarchy.** Primary fractures partition the body, and secondary cracks fill in the fragments. This is the usual pattern in procedural fracture tools, where Voronoi cells come first and detail cracks second. Here: shard stage → growth stage, inside `generate_hybrid_crack_paths`.
- **Reject unknown parameters instead of ignoring them.** A knob sent with a generator that does not use it gets an HTTP 400. That directly answers "settings don't affect the shard generator".

## Verified facts

All rows were checked on `main` at `d063b58` (shard PR #5 and menus PR #7 merged).

| Claim | Value | How verified | Date | Volatility |
| :--- | :--- | :--- | :--- | :--- |
| Shard seams always partition the wall; growth often does not | Wall-partition rate over seeds 0–19 (see the method below this table) | `partition_probe.py` (scratch) on `generate_crack_paths` output | 2026-11-09 | decays with generator changes |
| Vein mode never separates the ceramic, whatever the generator | Vein depth `min(0.75 W, 0.5 t)` (`_vein_depth`). Ceramic body count is 1 in 43/48 vein runs; the other 5 had 2 bodies, not inspected | `kintsugi._vein_depth`; `frag_probe.py` (scratch), R=0.3, seeds 0–5, 4 models | 2026-11-09 | stable |
| `shard` rejects ribbon mode | `generator='shard' is only supported in 'vein' mode in Stage 1` | `kintsugi.py:3603`; the probe hit it on every ribbon run | 2026-11-09 | stable |
| What the shard generator reads | Only `S` (through tiers <0.2 none / <0.35 one seam / <0.70 / ≥0.70), `W`, `period`, `rbar` and the wall range. Never `N` or `H`. Tilt, kink and harmonic are fixed per tier | `_shard_severity_config`, `generate_shard_crack_paths` | 2026-11-09 | stable |
| What the GUI sends | R, generator, mode, seed, seam width. With `shard`, R is a 3-step switch and `ribbon` raises | `static/index.html`, `web_app.py:175-180` | 2026-11-09 | stable |
| Growth uses committed paths as obstacles | `_first_growth_collision(paths, path_id, a, b, ...)` checks every committed segment, including periodic copies | `kintsugi.py:1121` | 2026-11-09 | stable |
| Combined audit exists | `analyze_growth_paths(paths, params)` gives crossings, clearance violations, min clearance and junction angles for any path set, and already validates shard seam 2 | `generate_shard_crack_paths` | 2026-11-09 | stable |
| Growth N and H | `N = floor(2 + 8S)`, `H = H_mesh · (0.2 + 0.8S)` | `compute_parameters` | 2026-11-09 | stable |

**How the partition fact was measured.** The probe rasterises the seams at seam width on a 0.25 mm grid. The grid covers `u` (periodic) by `[wall_z_min, wall_z_max]`. A run counts as "split" if the free area has two or more components, each larger than 2% of the free area.

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
| The growth split rates above are an *upper bound*. The probe's band stops at `wall_z_min`, so two rim-to-floor growth cracks count as a split even though the floor still joins them physically. Shard seams never reach the floor, because the wedge nadir is at least `wall_z_min + 0.18·height`, so the shard numbers are unaffected | High | Add a floor cap to the probe; ~10 min |
| Pre-committed shard seams don't starve growth trunks of rim seed positions at N(S) ≤ 10 | Medium | Run the probe on the prototype; the clearance audit reports it |
| A third through-fracture, a T onto either earlier seam, fits within the clearance rules on a 70 mm vase | Medium | Prototype `_shard_second_seam_candidate` generalised to any seam |
| Vein-only is acceptable for the owner, since "split into parts" is visual and topological, not separate bodies | Medium | Owner confirms at sign-off |

## Superseded claims

- **"Shard splits the ceramic into separate pieces."** Not in vein mode. Fragments are regions of the wall surface, not separate meshes (vein-depth fact above).

## Links out

- Shard primitives and audits: `openspec/changes/kintsugi-shard-seams/` and `kintsugi.py:2172-2660`
- Growth generator: `kintsugi.py:1313`
- Real demo models used above: `openspec/changes/real-model-test-corpus/research.md`
