## Automated Tests

- `./.venv/bin/python -m unittest tests.test_local_runtime -v`:
  - **Dependency Parity**: Asserts that `pyproject.toml` dependencies match `requirements.txt`.
  - **ASGI CORS Allowed Origins**: Verifies that requests with `Origin: https://kintsugi-studio.vercel.app` and preview URLs receive proper CORS response headers (`access-control-allow-origin`, `vary: Origin`, `access-control-allow-methods: GET, POST, OPTIONS`).
  - **ASGI CORS Malicious Origin Rejection**: Verifies that requests with `Origin: https://evil.example` receive HTTP 403 on OPTIONS preflight and never receive CORS allow headers.
  - **No Credentials**: Verifies `access-control-allow-credentials: true` is never returned.
  - **Local Network Access (LNA) / PNA**: Verifies that OPTIONS preflight with `Access-Control-Request-Private-Network: true` receives `Access-Control-Allow-Private-Network: true` only when Origin is allowed.
  - **Port Reuse & Probe**: Verifies that `studio()` detects an already running Kintsugi Studio instance on port 8000 and exits cleanly without spawning duplicates, and probes 8001–8009 when port 8000 is occupied.
  - **Guard Timing**: Verifies that `generate_kintsugi_mesh` includes `"guard"` in `timings`.
- `./.venv/bin/python -m unittest tests.test_viewer_js -v`:
  - Verifies JavaScript helper functions for `resolveEngineUrl` under Node.js runtime.
- `./.venv/bin/python -m unittest discover -s tests -v`:
  - Runs full project test suite ensuring zero regressions across all generators and formats.
- `openspec validate local-first-runtime --strict`:
  - Strictly validates all OpenSpec change artifacts against the `tdd-rnd` schema.

## Manual Verification

- **Gate 0 Cross-Browser Companion Flow**:
  - **WHEN** user visits the hosted Vercel preview in Chrome and clicks "Connect Engine"
  - **THEN** Chrome displays the Local Network Access permission prompt, approving it updates the status badge to Connected, and custom fracture execution succeeds.
  - **WHEN** user visits the hosted Vercel preview in Safari and clicks "Connect Engine"
  - **THEN** mixed-content block is captured gracefully, and the UI displays a clear explanation with the direct link to open `http://127.0.0.1:8000`.
- **One-Command Native Launch**:
  - **WHEN** user executes `kintsugi-studio` from the command line
  - **THEN** the system launches loopback server on `http://127.0.0.1:8000` and automatically opens the browser window showing the Windows XP Studio interface in same-origin mode.
- **Port Reuse Behavior**:
  - **WHEN** user runs `kintsugi-studio` while another instance is already serving on port 8000
  - **THEN** the launcher prints that Kintsugi is already running, opens the browser, and terminates without error.
