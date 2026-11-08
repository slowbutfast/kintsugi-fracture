## MODIFIED Requirements

### Requirement: Real-time parameter controls and fracture execution
The web GUI SHALL provide interactive controls for income ratio $R$, fracture generator (`growth`, `shard`, or `voronoi`), fracture mode (`vein` vs `ribbon`), and seed, with asynchronous fracture execution and progress feedback. The default fracture generator SHALL be `growth` (Rim Growth) and the default fracture mode SHALL be `vein` (Vein Inlay). When the user selects the `shard` generator (`Shard Planes`), the web GUI SHALL automatically select `vein` mode and disable the `ribbon` mode option while `shard` remains active.

#### Scenario: Triggering fracture computation with vein default
- **WHEN** user loads the application, sets $R = 0.35$, and clicks the green `⚡ FRACTURE MESH` button
- **THEN** system dispatches a `POST /api/fracture` request defaulting to `generator: "growth"` and `mode: "vein"`, updates the 3D viewport with the resulting ceramic body and gold lightning veins upon completion, and displays computed volume metrics

#### Scenario: Selecting Shard Planes generator in the Web GUI
- **WHEN** user selects `Shard Planes — tilted kintsugi seams` (`value="shard"`) in `#generator-select` and clicks `⚡ FRACTURE MESH`
- **THEN** the UI automatically checks the `vein` mode radio button, disables the `ribbon` mode radio button, updates `#generator-note` to indicate Vein Inlay only, and dispatches `POST /api/fracture` with `generator="shard"` and `mode="vein"`

#### Scenario: Wealthy parameter setting
- **WHEN** user sets $R \ge 1.0$
- **THEN** system immediately updates the status label to `Pristine / Wealthy (0 cracks)` and renders the intact ceramic body without gold veins

#### Scenario: Seams omitted feedback
- **WHEN** fracture response returns `seams_omitted: true` with $R < 1.0$
- **THEN** system displays `Seams Omitted` in the status indicator without claiming pristine wealth or displaying stale sub-millimeter thickness thresholds
