## Why

The current fracture engine relies on a periodic Voronoi diagram perturbed by a trigonometric noise field. In PATCH-01, bounding the noise gradient to prevent spatial folding on presets forced noise amplitude down to a flat 1.35 mm, transforming the fissures into sterile, straight-edged Voronoi tiles ("bathroom-tile grout") rather than organic Kintsugi cracks. Furthermore, the Voronoi noise field carries a mathematical proof gap that folds at small vessel radii ($r_{bar} \le 12\text{ mm}$).

We are executing an aesthetic and architectural pivot from polygonal Voronoi tiling to an authentic **sequential rim-seeded crack growth engine with stop-on-hit**, ensuring dramatic lightning morphology, natural T-junctions, and zero unintended crossings by construction, while preserving our rock-solid Manifold3D CSG pipeline and retro Windows XP web interface.

## What Changes

- **Sequential Rim-Seeded Crack Growth**: Cracks initiate at Poisson-spaced impact seeds along the upper vessel rim and propagate downwards into the trauma band via bounded random-walk heading deviation ($\pm 60^\circ$ from downwards), creating organic lightning fissures without relying on a global 2D displacement field.
- **Stop-on-Hit Collision & Snapping**:
  - Proximity trigger radius is set to the clearance distance $R_{\text{clear}} = W + 0.8\text{ mm}$.
  - When an advancing segment makes earliest contact with an existing segment at an arrival angle $\ge 30^\circ$, it snaps to the contact point, terminates growth, and **subdivides the hit segment with a new shared vertex**, forming a clean T-junction.
  - If arrival angle is $< 30^\circ$, heading is resampled up to 3 times; if still $< 30^\circ$, growth terminates at the last committed point, leaving a free end at $\ge W + 0.8\text{ mm}$ clearance.
  - An explicit **Junction Exemption Zone** around branch vertices prevents newborn child branches from colliding with their parents.
- **Thin-Wall Ceramic Backing & Kissing-Edge Prevention**:
  - Vein inlay depth is defined as $d_i = \min(0.75W, 0.5t_i, t_i - 0.8\text{ mm})$.
  - Where $d_i < 0.25\text{ mm}$ (e.g. on thin walls $t_i \le 1.05\text{ mm}$), the cutter point is **omitted**, ending the channel cleanly and preventing tangent non-manifold kissing contacts.
- **Severity & Growth Budgets**:
  - Economic severity $S$ controls seed count $N(S) = \lfloor 2 + 8S \rfloor$, branch probability $P = 0.15 \cdot S$, and per-trunk jittered penetration limits $z_{\text{limit}} = \text{wall\_z\_max} - H(S) \cdot (1 + \delta)$ to prevent flat horizontal termination lines.
- **Aesthetic Verification Gate**: Adds an automated contact sheet generator (`tools/test_report.py run --renders`) producing a 12-image matrix (`reports/contact_sheet.png`) for visual review, backed by an empirical tortuosity floor ($\text{median} \ge 1.05$) measured per junction-to-junction segment.
- **Legacy Voronoi Status**: Voronoi is retained as an unmaintained legacy generator accessible via CLI flag `--generator voronoi` for comparative A/B audits; it will be marked for deprecation and removal once the growth generator is verified.
- **UI Default Update**: Sets **Vein Inlay** as the default fracture mode in the Windows XP Luna GUI.

## Capabilities

### New Capabilities
*(None - all changes evolve existing capabilities)*

### Modified Capabilities
- `mesh-fracture-engine`: Modifies crack graph generation requirements to use rim-seeded growth with stop-on-hit T-junctions; defines explicit clearance trigger radii, junction exemption zones, and heading rules; guarantees planarity on shipped growth paths; and enforces non-puncture ceramic clearance with $0.25\text{ mm}$ minimum depth cutoff for vein inlays.
- `retro-web-gui`: Updates default fracture mode selection to Vein Inlay.

## Impact

- **Affected Code**: `kintsugi.py` (implements `generate_crack_growth_paths`, updates vein cutter depth and cutoff), `web_app.py`, `static/index.html`, `static/viewer.js`, `tools/test_report.py`.
- **Dependencies**: Zero new dependencies. Uses standard `numpy` and existing math utilities.
- **Backward Compatibility & Breaking Changes**:
  - **BREAKING (Visual Output)**: Because the default crack generator changes from Voronoi to crack growth, identical random seeds will yield completely different, organic fracture patterns. This is intentional for an artistic installation.
  - **BREAKING (API Default)**: `POST /api/fracture` defaults to `vein` mode and `growth` generator.
  - **Preserved**: Output container schemas (`ceramic_body.stl`, `gold_seams.stl`, `kintsugi_assembly.3mf`) remain 100% structurally conforming to 3MF Core Specifications.
