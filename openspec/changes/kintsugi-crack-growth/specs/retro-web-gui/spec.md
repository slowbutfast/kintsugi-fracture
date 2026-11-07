## MODIFIED Requirements

### Requirement: Real-time parameter controls and fracture execution
The web GUI SHALL provide interactive controls for income ratio $R$, fracture mode (`vein` vs `ribbon`), fracture generator (`growth` vs `voronoi`), and seed, with asynchronous fracture execution and progress feedback. The default fracture mode SHALL be `vein` (Vein Inlay) and the default generator SHALL be `growth` (Organic Lightning).

#### Scenario: Triggering fracture computation with growth generator
- **WHEN** user selects `vein` mode, sets $R = 0.35$, selects `growth` generator, and clicks the green `⚡ FRACTURE MESH` button
- **THEN** system displays a retro processing indicator, dispatches a `POST /api/fracture` request with `generator: "growth"`, updates the 3D viewport with the resulting ceramic body and gold lightning veins upon completion, and displays computed volume metrics

#### Scenario: Legacy Voronoi generator fallback
- **WHEN** user selects `Voronoi Tiling (Legacy)` in the parameter dialog
- **THEN** system dispatches `POST /api/fracture` with `generator: "voronoi"` and renders the legacy polygonal tessellation

#### Scenario: Wealthy parameter setting
- **WHEN** user sets $R \ge 1.0$
- **THEN** system immediately updates the status label to `Pristine / Wealthy (0 cracks)` and renders the intact ceramic body without gold veins
