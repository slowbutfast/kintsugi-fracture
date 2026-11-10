## MODIFIED Requirements

### Requirement: Real-time parameter controls and fracture execution
The web GUI SHALL provide interactive controls for income ratio $R$, fracture generator (`growth`, `shard`, `hybrid`, or `voronoi`), fracture mode (`vein` vs `ribbon`), and seed, with asynchronous fracture execution and progress feedback. The default fracture generator SHALL be `growth` (Rim Growth) and the default fracture mode SHALL be `vein` (Vein Inlay). When the user selects the `shard` generator (`Shard Planes`) or the `hybrid` generator (`Hybrid (Shard + Growth)`), the web GUI SHALL automatically select `vein` mode and disable the `ribbon` mode option while `shard` or `hybrid` remains active. When `hybrid` is selected, the web GUI SHALL reveal a `#hybrid-settings` control group exposing `through_count`, `through_shape` (distinguishing the edge-reaching `Rim-to-Rim Wedge` default from the closed interior `Closed Tilted Loop`), `tilt_deg`, `hairline_count`, `hairline_reach`, and `roughness` with `Auto` defaults, and SHALL display the resolved values and surface fragment count (`num_fragments`) returned in `parameters.hybrid` after fracture execution. If a client sends any hybrid knob to `POST /api/fracture` when `generator` is not `"hybrid"`, the API SHALL return `HTTP 400 Bad Request`.

#### Scenario: Triggering fracture computation with vein default
- **WHEN** user loads the application, sets $R = 0.35$, and clicks the green `⚡ FRACTURE MESH` button
- **THEN** system dispatches a `POST /api/fracture` request defaulting to `generator: "growth"` and `mode: "vein"`, updates the 3D viewport with the resulting ceramic body and gold lightning veins upon completion, and displays computed volume metrics

#### Scenario: Selecting Shard Planes generator in the Web GUI
- **WHEN** user selects `Shard Planes — tilted kintsugi seams` (`value="shard"`) in `#generator-select` and clicks `⚡ FRACTURE MESH`
- **THEN** the UI automatically checks the `vein` mode radio button, disables the `ribbon` mode radio button, hides `#hybrid-settings`, updates `#generator-note` to indicate Vein Inlay only, and dispatches `POST /api/fracture` with `generator="shard"` and `mode="vein"`

#### Scenario: Selecting Hybrid generator and using Hybrid settings in the Web GUI
- **WHEN** user selects `Hybrid — macro shards + interior hairlines` (`value="hybrid"`) in `#generator-select` or `#menu-mode`
- **THEN** the UI unhides `#hybrid-settings`, automatically checks `vein` mode and disables `ribbon` mode, sends `generator="hybrid"` (plus any overridden hybrid knobs) to `POST /api/fracture`, and updates `#hybrid-resolved-note` in `#hybrid-settings` with the resolved values and fragment count from `parameters.hybrid`

#### Scenario: Rejecting hybrid knobs with non-hybrid generator via API
- **WHEN** a client sends `POST /api/fracture` with `generator="growth"` or `generator="shard"` alongside any hybrid form parameter (e.g. `through_count=2` or `hairline_count=4`)
- **THEN** `POST /api/fracture` returns `HTTP 400 Bad Request` with an error detail explaining that hybrid parameters are only valid when `generator="hybrid"`

#### Scenario: Wealthy parameter setting
- **WHEN** user sets $R \ge 1.0$
- **THEN** system immediately updates the status label to `Pristine / Wealthy (0 cracks)` and renders the intact ceramic body without gold veins

#### Scenario: Seams omitted feedback
- **WHEN** fracture response returns `seams_omitted: true` with $R < 1.0$
- **THEN** system displays `Seams Omitted` in the status indicator without claiming pristine wealth or displaying stale sub-millimeter thickness thresholds
