## Why

Real ceramic breaks into pieces, and then hairlines run inside each piece. The two generators each produce only half of that.
- **Growth** gives good interior detail, but its cracks often dead-end. At R = 0.6 its seam network divides the wall into separate regions in only 2–8 of 20 seeds per model, and that is an upper bound.
- **Shard** divides the wall in 20/20 seeds on all four models we tested, into 2–3 fragments. But it is just one or two smooth seams with no interior detail.

The figures are in research.md, Verified facts.

There's a second problem: nothing the GUI exposes meaningfully steers shard.
- To shard, R is only a three-step switch.
- Ribbon mode raises an error.
- Its real parameters (seam count, loop vs wedge, tilt, kink) are fixed per tier.

## What Changes

- **New `hybrid` generator, run in two stages, in `generate_hybrid_crack_paths`:**
  1. **Through-fractures (shard stage).** 1–3 shard seams, where each later seam T-junctions into an earlier one. Together they must divide the wall into at least 2 fragments. Seam 3 is new and generalises the existing seam-2 candidate search to target any earlier seam.
  2. **Hairlines (growth stage).** The existing growth generator runs with the stage-1 seams already in its committed path list. Its stop-on-hit collision code therefore makes a hairline either T-junction into a through-fracture or dead-end inside a fragment, and no new collision code is needed. Rim seeds are kept clear of where stage-1 seams cross the rim. Hairline count and reach come from R, scaled down so the fragments stay readable.
  3. **Combined audit.** `analyze_growth_paths` checks the union of both stages for zero crossings, clearance of at least W + 0.8 mm, and junction angles of at least 30°. The result reports `num_fragments`.
- **Hybrid-only knobs.** Each knob defaults to `auto`, a value derived from R, so R stays the main control and a bare R gives a sensible result:

  | Knob | Range | Auto (from S = 1 − R) |
  | :--- | :--- | :--- |
  | `through_count` | 1–3 | 1 for S < 0.35, 2 for S < 0.70, 3 above |
  | `through_shape` | `auto`, `wedge`, `loop` | 50/50 per seed (today's behaviour), with loop falling back to wedge on short walls |
  | `tilt_deg` | 5–30 | Shard tier value (14, 20 or 26) |
  | `hairline_count` | 0–10 (0 = through-fractures only) | `max(0, N(S) − 2·through_count)` |
  | `hairline_reach` | 0.2–1.0 × wall height | Growth's `H` ratio, `0.2 + 0.8S` |

  - **API:** `POST /api/fracture` accepts these knobs as optional form fields. Sending any of them with a generator other than `hybrid` returns HTTP 400, so a knob never silently does nothing.
  - **Result:** `parameters.hybrid` echoes each knob's resolved value, so the UI can show "Auto (2)".
  - **GUI:** a "Hybrid settings" group appears only when the generator is `hybrid`. While `hybrid` (like `shard`) is selected, ribbon mode is disabled.
- **Vessels only, enforced.** Hybrid (in fact every generator) needs an open-top, single-wall vessel. `validate_and_load_mesh` now rejects bodies with no wall (`has_wall=False`) at validation time, instead of at fracture time. This fixes the solid-vase defect recorded in `real-model-test-corpus`. The existing radial-probe and envelope gates already reject everything else that isn't a bowl, cup or vase (Benchy and the like).
- **Unchanged:** `growth` stays the default, and `growth`, `shard` and `voronoi` keep their current output for every (R, seed). Hybrid is vein-only, like shard.

## Capabilities

### New Capabilities
- None. The hybrid is a generator inside the existing fracture capability.

### Modified Capabilities
- `mesh-fracture-engine`:
  - adds the `hybrid` generator: the two-stage contract, the fragment guarantee (at least 2 fragments whenever S ≥ 0.2), the combined audit invariants, and the knob ranges and `auto` rules;
  - validation rejects bodies with no wall.
- `retro-web-gui`: the generator selector gains Hybrid; a hybrid-only knob group with Auto defaults; ribbon disabled for hybrid; knobs sent with other generators rejected by the API.

## Impact

- **Code:**
  - `kintsugi.py`:
    - `generate_hybrid_crack_paths`;
    - growth accepts pre-committed obstacle paths and rim exclusions (a keyword argument; the default reproduces today's paths exactly);
    - the seam-3 candidate search;
    - fragment counting;
    - dispatch in `generate_crack_paths`;
    - the `has_wall` rejection.
  - `web_app.py`: knob form fields, plus their validation.
  - `static/index.html` and `static/viewer.js`: the Hybrid option in the selector and menu, and the knob group.
  - `tools/spike_contact_sheet.py`: `--generator hybrid`.
- **Tests:**
  - **Hybrid:** determinism per (model, R, seed, knobs); fragments ≥ 2; zero crossings and clearance; knob overrides are honoured.
  - **API:** knobs sent with other generators return 400.
  - **Regression:** byte-identical growth and shard paths with the new keyword argument at its defaults.
  - **Validation:** a solid body is rejected.
  - **Seeds:** stay out of the reserved hold-out ranges (300–399, ≥ 600).
- **Performance:** about the cost of growth alone, plus the shard stage, which is cheap (≤ 16 candidates per extra seam). No new dependencies.
- **Out of scope:**
  - ribbon (through-wall) hybrid fractures that produce multiple ceramic bodies;
  - knobs for plain `shard`;
  - switching the default generator to `hybrid` (decided after visual sign-off).
