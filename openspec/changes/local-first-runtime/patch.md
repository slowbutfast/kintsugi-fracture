# Patch Ledger: local-first-runtime

## Patch Ledger

| Patch ID | Date | Trigger / Feedback Source | Target Files | Status |
| :--- | :--- | :--- | :--- | :--- |
| `PATCH-01` | 2026-11-10 | Unit test failure after middleware landed | `tests/test_crack_shard.py`, `tests/test_web_api.py` | VERIFIED |
| `PATCH-02` | 2026-11-10 | TDD failure on wealthy pass-through guard test | `kintsugi.py` | VERIFIED |
| `PATCH-03` | 2026-11-10 | Verification audit: local static manifest 404 | `web_app.py`, `tests/test_local_runtime.py` | VERIFIED |
| `PATCH-04` | 2026-11-10 | Verification audit: static-only Vercel hardening | `vercel.json`, `.vercelignore`, `pyproject.toml` | VERIFIED |

---

### [PATCH-01] Loopback Host policy vs. TestClient's `testserver`

- **Date**: 2026-11-10 18:41 UTC
- **Feedback Source**: Unit Test Failure
- **Reported Issue**:
  ```text
  FAIL: test_api_fracture_success
  AssertionError: 403 != 200
  {"detail":"Untrusted Host header","error_type":"SecurityError","status":403}
  ```
- **Root Cause**: Starlette's `TestClient(app)` defaults to `Host: testserver`.
  The new DNS-rebinding guard correctly rejects any Host outside loopback, so the
  pre-existing web tests were exercising an unrealistic host.
- **Target Files**: `tests/test_crack_shard.py`, `tests/test_web_api.py`
- **Expected Resolution**: Test clients send `Host: 127.0.0.1:8000`, matching a
  real local browser; the production allow-list stays strict.
- **Verification Command**: `./.venv/bin/python -m unittest tests.test_web_api tests.test_crack_shard -v`
- **Status**: VERIFIED (184-test full suite green)

---

### [PATCH-02] Wealthy pass-through omitted `timings["guard"]`

- **Date**: 2026-11-10 18:39 UTC
- **Feedback Source**: TDD — `GuardTimingTestCase` with `R=1.0`
- **Reported Issue**:
  ```text
  KeyError: 'guard'
  ```
- **Root Cause**: `generate_kintsugi_mesh()` returns early for `severity == 0.0`
  before the F1 round-trip audit loop. Only the fractured path assigned
  `timings["guard"]`, so the pass-through response violated the uniform telemetry
  contract.
- **Target Files**: `kintsugi.py`
- **Expected Resolution**: The wealthy path records a measured `0.0`; fractured
  paths accumulate real guard elapsed time.
- **Verification Command**: `./.venv/bin/python -m unittest tests.test_local_runtime.GuardTimingTestCase -v`
- **Status**: VERIFIED

---

### [PATCH-03] Local `/presets/index.json` was shadowed by the STL mount

- **Date**: 2026-11-10 18:54 UTC
- **Feedback Source**: Verification audit (static fallback review)
- **Reported Issue**:
  ```text
  GET /presets/index.json -> 404 File not found
  ```
- **Root Cause**: `app.mount("/presets", StaticFiles(PRESET_DIR))` serves the root
  `presets/` directory (STLs only). The new manifest lives under
  `static/presets/index.json`, so the mount answered first with 404.
- **Target Files**: `web_app.py`, `tests/test_local_runtime.py`
- **Expected Resolution**: An explicit `GET /presets/index.json` route is declared
  before the STL mount and returns the three-preset JSON array.
- **Verification Command**: `./.venv/bin/python -m unittest tests.test_local_runtime -v`
- **Status**: VERIFIED

---

### [PATCH-04] Static-only Vercel hardening

- **Date**: 2026-11-10 18:56 UTC
- **Feedback Source**: Verification audit (deployment risk review)
- **Reported Issue**: Removing `app.py` alone did not explicitly prevent a Python
  framework/build inference from `pyproject.toml`/`requirements.txt`.
- **Root Cause**: Vercel zero-config can infer a Python project from repository
  metadata even without the old FastAPI entrypoint.
- **Target Files**: `vercel.json`, `.vercelignore`, `pyproject.toml`
- **Expected Resolution**: `framework: null`, root static output, and an ignore
  list excluding all Python sources and requirement files guarantee a static CDN
  deployment.
- **Verification Command**: `python3 -m json.tool vercel.json`; `openspec validate local-first-runtime --strict`
- **Status**: VERIFIED

---

## Status: No Outstanding Patches

All recorded patches are verified. The only remaining task is the manual
cross-browser Gate 4.1, which is not a code defect and is tracked in `tasks.md`
and `verification.md`.
