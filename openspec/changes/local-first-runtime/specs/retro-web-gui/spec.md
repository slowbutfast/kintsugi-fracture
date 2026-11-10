# retro-web-gui Specification Delta

## ADDED Requirements

### Requirement: Hosted companion engine connection and Local Network Access
The web GUI SHALL support connecting to a local Kintsugi Studio engine (`http://127.0.0.1:8000`) when hosted on a remote or static origin. Connection attempts SHALL be triggered by an explicit user gesture ("Connect Engine" button) to satisfy browser Local Network Access (LNA) security policies. If connection fails or is blocked by browser mixed-content policies (such as in Apple Safari), the GUI SHALL provide an immediate fallback link to navigate directly to `http://127.0.0.1:8000`.

#### Scenario: User-initiated engine connection
- **WHEN** user clicks "Connect Engine" on the hosted web interface
- **THEN** system sends a CORS health probe to `http://127.0.0.1:8000/api/health`, verifies `service: "kintsugi-studio"`, and transitions the UI status badge to connected

#### Scenario: Blocked or offline companion fallback
- **WHEN** user clicks "Connect Engine" and the probe fails or is blocked by browser mixed-content restrictions
- **THEN** system displays an explanatory message with a direct link to open `http://127.0.0.1:8000` in a new browser tab

#### Scenario: Port range search on companion connection
- **WHEN** user clicks "Connect Engine" and port 8000 is not reachable
- **THEN** system attempts sequential probes across `8001` through `8009` before displaying the unreachable state

### Requirement: Dynamic asset URL rewriting
When operating against a remote or cross-origin companion engine, the web GUI SHALL qualify all relative download and mesh preview paths (`/outputs/...`) with the base URL of the active companion engine.

#### Scenario: Fracture downloads resolve against local engine
- **WHEN** a fracture job completes via a companion engine at `http://127.0.0.1:8000`
- **THEN** download links and Three.js 3D viewport preview loaders fetch assets from `http://127.0.0.1:8000/outputs/<job_id>/...` rather than the hosted origin

### Requirement: Static preset manifest fallback
The web GUI SHALL support loading presets from a static `presets/index.json` file when running disconnected from a local engine on a static host.

#### Scenario: Presets populated statically
- **WHEN** the web GUI is loaded on a static hosting origin without an active local engine connection
- **THEN** the preset selection menu populates from `presets/index.json` and loads the initial preview mesh from the static preset path

### Requirement: API version compatibility handshake
The web GUI SHALL verify the `api_version` field returned by `GET /api/health` against its expected version (`1.0`).

#### Scenario: Version mismatch alert
- **WHEN** the connected local engine reports a major `api_version` differing from the web GUI
- **THEN** system displays a warning advising the user to update their local repository clone
