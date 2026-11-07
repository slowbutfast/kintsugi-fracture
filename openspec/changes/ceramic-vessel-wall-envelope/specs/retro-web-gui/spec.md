## MODIFIED Requirements

### Requirement: Model preset selection and custom upload
The web GUI SHALL allow selecting bundled preset 3D models or uploading a custom watertight `.stl` or `.obj` file. Input models must conform to the ceramic vessel envelope ($p_5 \ge 1.6\text{ mm}$).

#### Scenario: Preset model selection
- **WHEN** user chooses a preset model (e.g. `Japanese Tea Bowl` or `Tall Vase`) from the dropdown
- **THEN** system immediately loads and renders the model in the 3D viewport and updates the status bar with mesh metadata

#### Scenario: Custom file upload
- **WHEN** user drags and drops a custom `.stl` file onto the upload zone
- **THEN** the viewer parses it for preview and calls `POST /api/validate`, which runs `validate_and_load_mesh` in a temporary directory; the status bar reports `Watertight ✓` or `Not a valid closed solid: <detail>` (including wall thickness rejection if $p_5 < 1.6\text{ mm}$), and the fracture button stays disabled while the upload is invalid

#### Scenario: Upload size cap
- **WHEN** an upload exceeds 50 MB
- **THEN** the API rejects it with HTTP 413 and stores no file

#### Scenario: Job retention
- **WHEN** a new fracture job starts
- **THEN** job directories older than `KINTSUGI_JOB_TTL_S` (default 3600 s) are deleted, and at most `KINTSUGI_MAX_JOBS` (default 50) directories are retained, oldest first

### Requirement: Real-time parameter controls and fracture execution
The web GUI SHALL provide interactive controls for income ratio $R$, fracture mode (`vein` vs `ribbon`), and seed, with asynchronous fracture execution and progress feedback. The default fracture mode SHALL be `vein` (Vein Inlay).

#### Scenario: Triggering fracture computation with vein default
- **WHEN** user loads the application, sets $R = 0.35$, and clicks the green `⚡ FRACTURE MESH` button
- **THEN** system dispatches a `POST /api/fracture` request defaulting to `mode: "vein"`, updates the 3D viewport with the resulting ceramic body and gold lightning veins upon completion, and displays computed volume metrics

#### Scenario: Wealthy parameter setting
- **WHEN** user sets $R \ge 1.0$
- **THEN** system immediately updates the status label to `Pristine / Wealthy (0 cracks)` and renders the intact ceramic body without gold veins
