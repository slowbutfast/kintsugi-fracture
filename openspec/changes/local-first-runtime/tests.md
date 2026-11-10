## Automated Tests

- `./.venv/bin/python -m unittest tests.test_local_runtime -v`:
  - **Dependency Parity**: Asserts that `pyproject.toml` dependencies match `requirements.txt`.
  - **ASGI CORS Allowed Origins**: Verifies that requests with `Origin: https://kintsugi-fracture-joeshmo.vercel.app` receive proper CORS response headers (`access-control-allow-origin`, `vary: Origin`, `access-control-allow-methods: GET, POST, OPTIONS`).
  - **Preview Opt-In**: Verifies that a preview-shaped origin (including a squatted `https://kintsugi-fracture-x-joeshmo.vercel.app`) is rejected by default and accepted only with `KINTSUGI_ALLOW_PREVIEWS=1` / `--allow-previews`.
  - **ASGI CORS Malicious Preflight Rejection**: Verifies that requests with `Origin: https://evil.example` receive HTTP 403 on OPTIONS preflight and never receive CORS allow headers.
  - **Server-Side Simple POST Rejection**: Verifies that a `POST /api/fracture` request with `Origin: https://evil.example` is immediately rejected with HTTP 403 Forbidden without parsing multipart bodies or creating jobs.
  - **DNS Rebinding Defense**: Verifies that requests with an unauthorized `Host` header (e.g. `attacker.com`) are rejected with HTTP 403 Forbidden.
  - **No Credentials**: Verifies `access-control-allow-credentials: true` is never returned.
  - **Local Network Access (LNA)**: Verifies standard CORS preflight handling and that the deprecated PNA header is not required; the client-side LNA flow is covered by the Node tests below.
  - **Port Reuse & Probe**: Verifies that `studio()` detects an already running Kintsugi Studio instance on port 8000 and exits cleanly without spawning duplicates, and probes 8001–8009 when port 8000 is occupied.
  - **Guard Timing**: Verifies that `generate_kintsugi_mesh` includes `"guard"` in `timings`.
- `./.venv/bin/python -m unittest tests.test_viewer_js -v`:
  - Verifies `resolveEngineUrl` and static preset index fallback under Node.js runtime.
  - Verifies loopback health/API requests declare `targetAddressSpace: "loopback"`, while public and relative URLs do not.
  - Verifies granular `loopback-network` permission queries degrade to `"prompt"` when unsupported or unrecognized.
- `./.venv/bin/python -m unittest discover -s tests -v`:
  - Runs full project test suite ensuring zero regressions across all generators and formats.
- `openspec validate local-first-runtime --strict`:
  - Strictly validates all OpenSpec change artifacts against the `tdd-rnd` schema.

## Manual Verification

- **Gate 4.1 Cross-Browser Companion Flow**:
  - **WHEN** user visits the hosted Vercel preview root URL `/` in Chrome and clicks "Connect Engine"
  - **THEN** the GUI loads from `/` (not `/static/index.html`), Chrome displays the Local Network Access permission prompt, approving it updates the status badge to Connected, and custom fracture execution succeeds.
  - **WHEN** user visits the hosted Vercel preview in Safari and clicks "Connect Engine"
  - **THEN** mixed-content block is captured gracefully, and the UI displays a clear explanation with the direct link to open `http://127.0.0.1:8000`.
- **One-Command Native Launch**:
  - **WHEN** user executes `kintsugi-studio` from the command line
  - **THEN** the system launches loopback server on `http://127.0.0.1:8000` and automatically opens the browser window showing the Windows XP Studio interface in same-origin mode.
- **Port Reuse Behavior**:
  - **WHEN** user runs `kintsugi-studio` while another instance is already serving on port 8000
  - **THEN** the launcher prints that Kintsugi is already running, opens the browser, and terminates without error.
