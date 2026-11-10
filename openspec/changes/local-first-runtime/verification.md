## Executive Summary & Environment

- **Status**: All executable specs verified passing; one manual cross-browser gate
  (4.1) intentionally remains unchecked.
- **Date**: 2026-11-10
- **Environment**: Linux `aarch64`, Python 3.11.2, Node.js 22.23.2,
  FastAPI 0.162.4, Starlette 1.10.0, uvicorn 0.54.0, manifold3d 3.5.4,
  trimesh 5.2.0, Chromium 1248 (headless, via Playwright for browser smoke tests).

The change is implemented as two cooperating tracks:

1. **Native local studio** — `pyproject.toml` exposes
   `kintsugi-studio = "web_app:studio"`. The launcher reuses an existing
   Kintsugi instance on `127.0.0.1:8000`, otherwise bind-probes
   `8000–8009`, warns on non-loopback `--host`, and opens the browser through a
   readiness-polling thread.
2. **Static hosted companion** — `app.py` and the Vercel `functions` block are
   gone. `vercel.json` serves `static/` plus the root `presets/` assets as a
   CDN. The GUI loads `presets/index.json` when disconnected, connects to a
   companion engine only after a **Connect Engine** user gesture, rewrites every
   `/outputs/...` URL through `resolveEngineUrl`, and checks the `api_version`
   handshake.

Server-side defense is a **pure ASGI** `SecurityCORSMiddleware`: untrusted
`Host` headers (DNS rebinding), unauthorized origins on state-changing methods,
and unauthorized `/outputs/*` reads all return `403` before the request body is
consumed. Allowed preflights receive CORS and
`Access-Control-Allow-Private-Network: true`; credentials are never allowed.

**Gate 4.1 (real HTTPS Vercel preview + Chrome LNA prompt + Firefox + Safari)
was not executed** because this environment has no deployed Vercel preview and
no interactive Firefox/Safari sessions. Real headless Chromium smoke tests did
execute the same-origin studio, the hosted static disconnected fallback, the
Connect Engine gesture, a live companion fracture, and `/outputs` rewriting
(§ Empirical Execution Logs).

---

## Requirement Adherence Audit Matrix

### `local-runtime` specification

| Capability | Requirement & Scenario | Verification Method / Test File | Status |
| :--- | :--- | :--- | :--- |
| `local-runtime` | `### Requirement: Native local launcher entrypoint` | `tests/test_local_runtime.py::PackagingTestCase`; `kintsugi-studio --help`; live launch log | **PASS** |
| `local-runtime` | `#### Scenario: Successful local launch` | `LauncherTestCase`; live `studio(["--no-open"])` binds `127.0.0.1:8000`; browser call asserted with patched `webbrowser.open` | **PASS** |
| `local-runtime` | `#### Scenario: Headless launch with no browser open` | `test_existing_instance_is_reused_without_starting_a_server`; live `--no-open` run | **PASS** |
| `local-runtime` | `#### Scenario: Non-loopback host warning` | `test_non_loopback_host_logs_a_security_warning` | **PASS** |
| `local-runtime` | `### Requirement: Deterministic port negotiation and instance reuse` | `LauncherTestCase` port/reuse tests | **PASS** |
| `local-runtime` | `#### Scenario: Existing Kintsugi Studio instance detected` | `test_existing_instance_is_reused_without_starting_a_server`; live reuse (`reuse_exit=0`) | **PASS** |
| `local-runtime` | `#### Scenario: Port collision fallback` | `test_port_collision_probes_forward_and_binds_first_free_port` (binds 8003); `test_exhausted_port_range_returns_nonzero`; real browser connected on 8001 | **PASS** |
| `local-runtime` | `### Requirement: Pure ASGI server-side origin and host security` | `SecurityMiddlewareTestCase`; source grep; curl evidence | **PASS** |
| `local-runtime` | `#### Scenario: Allowed origin preflight with Private Network Access` | `test_allowed_production_preflight_has_cors_and_lna_headers`; curl `204` + PNA header | **PASS** |
| `local-runtime` | `#### Scenario: Unauthorized preflight rejected` | `test_evil_origin_preflight_is_rejected_without_cors_headers`; curl `403` | **PASS** |
| `local-runtime` | `#### Scenario: Unauthorized simple POST rejected before body read` | ASGI harness asserts `body_events == []`, `downstream_called is False`; curl `403` | **PASS** |
| `local-runtime` | `#### Scenario: DNS rebinding rejected via Host header verification` | `test_dns_rebinding_host_header_is_rejected`; `test_loopback_host_variants_are_accepted`; curl `403` | **PASS** |
| `local-runtime` | `#### Scenario: No credential exposure` | `test_no_credentials_header_on_any_cross_origin_response` | **PASS** |
| `local-runtime` | `### Requirement: Guard timing instrumentation` | `test_guard_timing_is_recorded_on_a_successful_fracture` | **PASS** |
| `local-runtime` | `#### Scenario: Guard timing recorded` | `tests/test_local_runtime.py::GuardTimingTestCase` asserts float `timings["guard"]` | **PASS** |

### `retro-web-gui` specification delta

| Capability | Requirement & Scenario | Verification Method / Test File | Status |
| :--- | :--- | :--- | :--- |
| `retro-web-gui` | `### Requirement: Hosted companion engine connection and Local Network Access` | `test_gui_exposes_companion_controls_and_engine_module`; Chromium Connect Engine run | **PASS** (real LNA prompt deferred to Gate 4.1) |
| `retro-web-gui` | `#### Scenario: User-initiated engine connection` | Chromium: initial `Disconnected` → click → `Connected (127.0.0.1:8000, v1.0)` | **PASS** |
| `retro-web-gui` | `#### Scenario: Blocked or offline companion fallback` | `setEngineStatus("error")` reveals `#engine-link` → `http://127.0.0.1:<port>`; markup test asserts the control exists | **PASS** (link not browser-clicked) |
| `retro-web-gui` | `#### Scenario: Port range search on companion connection` | `test_probe_engine_falls_forward_across_the_port_range` (`[8000, 8001]`); chromium connected to 8001 | **PASS** |
| `retro-web-gui` | `### Requirement: Dynamic asset URL rewriting` | `tests/test_viewer_js.py` resolve tests; Chromium fracture downloads on 8001 | **PASS** |
| `retro-web-gui` | `#### Scenario: Fracture downloads resolve against local engine` | `${base}/outputs/<job>/...` asserted in Chromium; `loadParts` uses `resolveEngineUrl` | **PASS** |
| `retro-web-gui` | `### Requirement: Static preset manifest fallback` | `test_static_preset_manifest_populates_all_bundled_presets`; Chromium static host with zero `/api/health` calls | **PASS** |
| `retro-web-gui` | `#### Scenario: Presets populated statically` | Static host populated `tea_bowl`, `benchy`, `vase` and loaded `/presets/tea_bowl.stl` | **PASS** |
| `retro-web-gui` | `### Requirement: API version compatibility handshake` | `test_api_version_requires_a_matching_major`; health `api_version: "1.0"` | **PASS** |
| `retro-web-gui` | `#### Scenario: Version mismatch alert` | `apiVersionCompatible("2.0") === false`; viewer warns to update the clone | **PASS** |

---

## Resolved Assumptions & Empirical Proof

| Assumption from research/architecture | How Verified in Code/Tests | Result / Value | Volatility |
| :--- | :--- | :--- | :--- |
| Vercel can be forced to static-only once `app.py` is removed | `app.py` deleted; `vercel.json` has `"framework": null`, `"outputDirectory": "."`, no `functions`; JSON parsed | Static configuration valid; deployment credentials unavailable | stable |
| Loopback Host is the DNS-rebinding boundary | `_host_allowed()` accepts only `127.0.0.1`, `localhost`, `::1`, plus explicit `--host`/env | curl Host=`attacker.example:8000` → `403` | stable |
| A Kintsugi instance is distinguishable from a generic HTTP service | `/api/health` must return `service: "kintsugi-studio"` | `_probe_health()` + probe tests; live reuse `reuse_exit=0` | stable |
| Port discovery must stay inside 8000–8009 | `ENGINE_PORTS` and launcher candidate range | Node probe test and real browser connected on 8001 | stable |
| Simple multipart POSTs bypass CORS preflight | middleware checks `Origin` on every unsafe method before `receive` | ASGI harness: `body_events == []`, downstream never called | stable |
| Credentials are unnecessary for loopback companion | `Access-Control-Allow-Credentials` is never emitted and is stripped | `test_no_credentials_header_on_any_cross_origin_response` | stable |
| Preset manifests can be static | `static/presets/index.json` + `presetsFromStaticIndex()` | Chromium loaded all three presets with zero API polling | stable |
| `/outputs` URLs are relative to the engine, not the CDN | `resolveEngineUrl()` in `requestJson`, `loadParts`, downloads | Chromium produced `http://127.0.0.1:8001/outputs/...` links | stable |
| The wealthy pass-through still needs a guard key | early return sets `timings["guard"] = 0.0` | guard test passes for `R=1.0` | stable |

---

## Nomenclature & Code Symbol Audit

| Glossary Term | Final Code Identifier | Location / File | Verified Compliant? |
| :--- | :--- | :--- | :--- |
| Local runtime / launcher | `studio(argv=None)` | `web_app.py` | Yes |
| Console script | `kintsugi-studio = "web_app:studio"` | `pyproject.toml` | Yes |
| Security middleware | `SecurityCORSMiddleware` (pure ASGI) | `web_app.py` | Yes |
| Origin allow-list | `_origin_allowed`, `PRODUCTION_ORIGIN`, `PREVIEW_ORIGIN_RE` | `web_app.py` | Yes |
| DNS-rebinding guard | `_host_allowed`, `_hostname_from_host_header` | `web_app.py` | Yes |
| Port probe / bind probe | `_probe_health`, `_port_available` | `web_app.py` | Yes |
| Browser launcher thread | `_open_when_ready` | `web_app.py` | Yes |
| Health contract | `GET /api/health` → `service`, `api_version` | `web_app.py` | Yes |
| Guard timing | `timings["guard"]` | `kintsugi.py` | Yes |
| Engine URL resolver | `resolveEngineUrl` | `static/engine.js`; wrapper in `static/viewer.js` | Yes |
| Companion probe | `probeEngine`, `ENGINE_PORTS` | `static/engine.js` | Yes |
| Static preset mapping | `presetsFromStaticIndex` | `static/engine.js` | Yes |
| Version handshake | `apiVersionCompatible`, `EXPECTED_API_VERSION` | `static/engine.js` | Yes |
| Static manifest | `static/presets/index.json`; `GET /presets/index.json` | `static/presets/`, `web_app.py` | Yes |

Audit grep confirms no production use of `BaseHTTPMiddleware` (the only match in
`web_app.py` is the docstring saying it is deliberately not used). `app.py` no
longer exists in the tree.

---

## Landed Tech Footprint & Patterns

| Adopted Pattern / Package | Implementation File(s) | Verification Command / Suite |
| :--- | :--- | :--- |
| PEP 621 packaging + setuptools `py-modules` | `pyproject.toml` | `pip install -e .`; `kintsugi-studio --help` |
| Pure ASGI security middleware | `web_app.py` | `tests.test_local_runtime` |
| Deterministic port negotiation | `web_app.py` | `tests.test_local_runtime.LauncherTestCase` |
| Vanilla ES module companion helpers (no new npm deps) | `static/engine.js` | `tests.test_viewer_js` under Node 22 |
| Windows XP status-bar indicator | `static/index.html`, `static/xp.css` | `tests.test_local_runtime` markup test; Chromium smoke |
| Static CDN deployment | `vercel.json`, `.vercelignore`, deleted `app.py`, `static/presets/index.json` | `python -m json.tool vercel.json`; static Chromium run |
| Guard timing instrumentation | `kintsugi.py` | `tests.test_local_runtime.GuardTimingTestCase` |

No runtime dependency was added: `pyproject.toml` mirrors `requirements.txt`
exactly. Playwright was installed only into the disposable local `.venv` for the
headless browser smoke tests and is not a project dependency.

---

## Invalidated Hypotheses & Mid-Build Adjustments

| Original Belief | What Proved Wrong | Final Resolution | Rationale |
| :--- | :--- | :--- | :--- |
| Starlette `TestClient` loopback requests would pass the Host check | Default `TestClient` sends `Host: testserver`, which is correctly rejected | Existing web tests now use `base_url="http://127.0.0.1:8000"` | Keeps the production Host policy strict instead of allow-listing a test-only host |
| A static manifest under `static/presets/` is automatically served by `/presets` | The local server mounts the root `presets/` directory, not `static/presets/` | Added an explicit `GET /presets/index.json` route before the STL mount | Preserves local fallback and avoids duplicating 80 KB of preset STLs |
| Removing `app.py` alone guarantees a static Vercel build | Vercel could still infer a Python framework from project metadata | Added `"framework": null` and root `"outputDirectory": "."` with static rewrites | Makes static-only intent explicit |
| Guard only applies to fractured jobs | The wealthy `R ≥ 1` path returns before the F1 audit | Record an explicit `timings["guard"] = 0.0` on pass-through | Keeps the health/telemetry contract uniform |
| A hosted page could be simulated with any loopback hostname | `isSameOriginLocalLocation()` treats `127.0.0.1`/`localhost` as same-origin | Browser verification used `kintsugi.test` with a resolver override and a configured allowed origin | Correctly exercised the hosted-disconnected path |

---

## Implementation-Discovered Deferrals

- **Deferred Item**: Gate 4.1 real cross-browser verification (Chrome LNA prompt on
  the deployed HTTPS Vercel preview, Firefox CORS, Safari mixed-content fallback).
  - **Reason**: Requires a deployed preview plus interactive Firefox/Safari and
    an HTTPS origin; unavailable in this headless environment. Headless Chromium
    covered same-origin, static fallback, Connect Engine, fracture, and `/outputs`
    rewriting.
- **Deferred Item**: Track B browser-local execution (Pyodide/`manifold3d`/TypeScript).
  - **Reason**: Explicit non-goal of this change; remains a documented feasibility
    study in `architecture.md`/`research.md`.
- **Deferred Item**: Replacing the legacy `python web_app.py` invocation with the
  browser-opening launcher.
  - **Reason**: Backward compatibility was required; `main()` remains the direct
    server entrypoint and `kintsugi-studio` is the new zero-friction path.

---

## Empirical Execution Logs & Evidence

### Targeted runtime tests

```text
$ ./.venv/bin/python -m unittest tests.test_local_runtime -v
...
Ran 20 tests in 0.355s

OK
```

### Node/JavaScript viewer tests

```text
$ ./.venv/bin/python -m unittest tests.test_viewer_js -v
...
Ran 19 tests in 0.216s

OK
```

### Full regression suite

```text
$ ./.venv/bin/python -m unittest discover -s tests -v
...
Ran 184 tests in 257.808s

OK
```

### Live loopback launch, CORS/LNA, DNS rebinding, and instance reuse

```text
$ ./.venv/bin/python -c 'import web_app; raise SystemExit(web_app.studio(["--no-open"]))'
HEALTH
{"status":"ok","service":"kintsugi-studio","api_version":"1.0","kernel":"Manifold3D","max_upload_bytes":52428800,"accepted_formats":[".stl",".obj",".3mf"]}
ALLOWED_PREFLIGHT
HTTP/1.1 204 No Content
access-control-allow-origin: https://kintsugi-fracture-joeshmo.vercel.app
vary: Origin
access-control-allow-methods: GET, POST, OPTIONS
access-control-allow-headers: Content-Type, Accept, X-Requested-With
access-control-max-age: 600
access-control-allow-private-network: true
EVIL_PREFLIGHT_STATUS
403
EVIL_SIMPLE_POST_STATUS
403
DNS_REBIND_STATUS
403
STATIC_INDEX_STATUS
200
200
INSTANCE_REUSE
2026-11-10 18:48:17,095 INFO kintsugi.web Kintsugi Studio is already running at http://127.0.0.1:8000 (api_version=1.0); reusing it
reuse_exit=0
LAUNCHER_LOG
2026-11-10 18:48:16,206 INFO kintsugi.web Kintsugi Studio 2001 listening at http://127.0.0.1:8000
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

### Headless Chromium: same-origin local studio

Real Chromium (Playwright, cached `chromium-1248`) loaded the live
`http://127.0.0.1:8000/` studio and executed `viewer.js` end to end:

```text
ENGINE_STATUS_MARKUP
<span class="engine-status-text" id="engine-status" title="Local Engine: Connected (Same-Origin)">Local Engine: Connected (Same-Origin)</span>
PRESET_OPTIONS
<option value="tea_bowl">Japanese Tea Bowl</option>
<option value="benchy">3D Benchy</option>
<option value="vase">Small Vase</option>
CANVAS_PRESENT
1
```

(The only Chromium stderr lines were headless dbus/GPU warnings, not application
errors.)

### Headless Chromium: hosted static fallback and Connect Engine

A static server on `http://kintsugi.test:9000` served `static/index.html` and the
root preset STLs (Vercel rewrite semantics). On load, the page made **zero**
`/api/health` requests and populated presets from `presets/index.json`. Playwright
then clicked **Connect Engine** against the live engine:

```text
INITIAL_STATUS: Local Engine: Disconnected
STATIC_PRESETS: ['Japanese Tea Bowl', '3D Benchy', 'Small Vase']
CONNECTED_STATUS: Local Engine: Connected (127.0.0.1:8000, v1.0)
CONNECT_BUTTON_DISABLED: False
FALLBACK_LINK: http://127.0.0.1:8000 Open Local Studio ↗
PRESETS_AFTER_CONNECT: ['Japanese Tea Bowl', '3D Benchy', 'Small Vase']
API_HEALTH_REQUESTS_BEFORE_CLICK
0
ENGINE_HEALTH_AND_PRESET_REQUESTS
INFO:     127.0.0.1:36808 - "GET /api/health HTTP/1.1" 200 OK
INFO:     127.0.0.1:36808 - "GET /api/presets HTTP/1.1" 200 OK
```

This run used `KINTSUGI_ALLOWED_ORIGINS=http://kintsugi.test:9000` to model the
production allow-list entry; the real production origin is covered by the
preflight test and curl log above. It is **not** a substitute for the Chrome LNA
permission prompt on HTTPS, which remains Gate 4.1.

### Headless Chromium: companion fracture and `/outputs` rewriting

After connecting from the hosted static page, Playwright clicked **FRACTURE MESH**.
The live job completed and every download was qualified against the active
companion engine. The engine was discovered on `8001`, which also exercises the
real port fallback path:

```text
CERAMIC_DOWNLOAD: http://127.0.0.1:8001/outputs/b2c56471ec64/ceramic_body.stl
GOLD_DOWNLOAD: http://127.0.0.1:8001/outputs/b2c56471ec64/gold_seams.stl
THREEMF_DOWNLOAD: http://127.0.0.1:8001/outputs/b2c56471ec64/kintsugi_assembly.3mf
MESH_STATUS: Faces: 65,968 | Parts: 2 | Ceramic 65576.9 mm³ | Gold 198.8 mm³
```

### OpenSpec strict validation

```text
$ openspec validate local-first-runtime --strict
Change 'local-first-runtime' is valid
```

### Editable install / console script

```text
$ ./.venv/bin/pip install -e .
Successfully installed kintsugi-studio-1.0.0
$ ./.venv/bin/kintsugi-studio --help
usage: kintsugi-studio [-h] [--host HOST] [--port PORT] [--no-open]
                       [--log-level LOG_LEVEL]

Launch Kintsugi Studio 2001 on loopback and open the browser
```

### Metrics & Data Invariants

| Metric / Count | Before | After | Delta / Observation |
| :--- | :--- | :--- | :--- |
| Discovered unittest suite | 156 tests | 184 tests | +28: 20 `test_local_runtime` tests and 8 new Node/engine tests |
| Bundled presets | 3 (`tea_bowl`, `benchy`, `vase`) | 3 | No preset lost; static manifest mirrors all three |
| Vercel Python functions | 1 (`app.py`) | 0 | Static CDN only |
| Server middleware classes | 1 (`RequestContextMiddleware`) | 2 (+ pure ASGI `SecurityCORSMiddleware`) | No `BaseHTTPMiddleware` |
| Concurrent engine instances on reuse | 2 (would duplicate) | 1 | Live `reuse_exit=0`; no second uvicorn |
| Fragment/geometry output | unchanged | unchanged | Core fracture code untouched apart from timing; full suite clean |

---

## Quick Re-Verification (60-Second Audit)

```bash
./.venv/bin/python -m unittest tests.test_local_runtime tests.test_viewer_js -v
openspec validate local-first-runtime --strict
```

Expected output:

```text
Ran 39 tests in ...s

OK
Change 'local-first-runtime' is valid
```

For the whole repository:

```bash
./.venv/bin/python -m unittest discover -s tests -v
```

Expected output:

```text
Ran 184 tests in ...s

OK
```
