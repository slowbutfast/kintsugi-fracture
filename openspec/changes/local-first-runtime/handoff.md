# OpenCode Orchestration Handoff: OpenSpec Change 'local-first-runtime'

You are the orchestration agent for OpenSpec change 'local-first-runtime' running in OpenCode.
Your primary directive is to execute this change using the **`openspec-apply-sub`** skill, which delegates task implementation to the `spec-coder-sub` subagent.

## 1. Orchestration Directive
- **Change Name**: local-first-runtime
- **Target Skill**: `openspec-apply-sub` (or `/opsx:apply-sub local-first-runtime`)
- **Architecture Paradigm**: Vertical Slice Architecture (VSA). Maintain strict isolation between feature compartments and avoid horizontal abstractions.
- **TDD Requirement**: Task group ## 1 MUST scaffold failing unit/integration tests before touching implementation code. Run `./.venv/bin/python -m unittest tests.test_local_runtime -v` to confirm they fail initially.

## 2. Target Context Map
| File Path (relative to repo root) | Target Lines | Modification Summary |
|---|---|---|
| `pyproject.toml` | `[NEW]` (`L1–L32`) | Define PEP 621 package metadata, dependencies matching `requirements.txt`, console script `[project.scripts] kintsugi-studio = "web_app:studio"`, and setuptools `py-modules`. |
| `web_app.py` | `L50–L86` | Implement pure ASGI `SecurityCORSMiddleware`. Enforce server-side `Origin` checks on all POSTs and `/outputs/*` reads (rejecting untrusted origins with 403 before reading bodies). Enforce `Host` header check against loopback to prevent DNS rebinding. Handle standard CORS and client-side LNA request options. `allow_credentials=False`. |
| `web_app.py` | `L258–L266` | Update `GET /api/health` to return `"service": "kintsugi-studio"`, `"api_version": "1.0"`, `"max_upload_bytes": 52428800`, `"accepted_formats": [".stl", ".obj", ".3mf"]`. |
| `web_app.py` | `L524–L537` | Implement `studio(argv=None)` entrypoint: deterministic port probe (8000–8009), instance reuse via `/api/health`, non-loopback security warning, and browser launcher thread. |
| `vercel.json` | `L1–L10` | Remove `functions` block. Configure static asset delivery and rewrites for `static/` and `presets/`. |
| `app.py` | `[DELETE]` | Remove `app.py` so Vercel's FastAPI framework preset does not detect a Python function and deploys purely as static assets. |
| `static/presets/index.json` | `[NEW]` | Provide static JSON array of presets (`tea_bowl`, `vase`, `benchy`) for offline / disconnected loading. |
| `static/viewer.js` | `L390–L435` | Implement `resolveEngineUrl(path)` to dynamically qualify relative API endpoints and `/outputs/...` asset URLs with `state.engineBaseUrl`. |
| `static/viewer.js` | `L689–L750` | Implement companion engine connection flow: "Connect Engine" user gesture button, sequential port range probing (8000–8009), manual port input, `api_version` handshake check, fallback to `/presets/index.json`, and "Open Local App (127.0.0.1:8000) ↗" fallback link. |
| `static/viewer.js` | `L900–L935` | Ensure fracture downloads and 3D preview meshes resolve through `resolveEngineUrl` so assets load from the local engine. |
| `static/index.html` | Header / Status bar | Add connection status indicator badge, "Connect Engine" button, and fallback link in Windows XP style. |
| `kintsugi.py` | `L4804–L4816` | Wrap the F1 STL round-trip and manifold audit (`_export_trimesh` + `_stl_bad_edge_count`) in timing measurement and record `timings["guard"]`. |
| `tests/test_local_runtime.py` | `[NEW]` (`L1–L160`) | Unit test suite covering dependency parity, pure ASGI CORS origin filtering, simple POST rejection, Host header DNS rebinding defense, LNA request handling, port negotiation (8000–8009), and `timings["guard"]`. |
| `tests/test_viewer_js.py` | `L1–L120` | Add unit tests for `resolveEngineUrl` and static preset index loading under Node.js runtime. |

## 3. Technical & Architectural Boundaries
- **In-Scope Decisions**:
  - Native local execution on `127.0.0.1:8000` is the primary, zero-friction path.
  - Vercel is strictly a static CDN serving the GUI; no serverless Python computation.
  - Simple CORS request defense: Reject unauthorized `Origin` on state-changing POSTs and `/outputs/*` with HTTP 403 before reading bodies.
  - DNS rebinding defense: Enforce `Host` header is loopback.
  - Chrome Local Network Access (LNA) user-gesture connection flow; Safari fallback link to `http://127.0.0.1:8000`.
  - Deterministic port range probe across 8000–8009.
  - Real production origin `https://kintsugi-fracture-joeshmo.vercel.app`; preview regex is trusted only with `--allow-previews` opt-in.
- **Hard Exclusions / No-Go**:
  - Do NOT modify `.env`, `.env.*`, or credential files.
  - Do NOT introduce unapproved external dependencies (maintain parity between `pyproject.toml` and `requirements.txt`).
  - Do NOT alter core fracture geometry, procedural algorithms, or export mesh formats in `kintsugi.py` or `mesh_formats.py`.
  - Do NOT re-introduce `BaseHTTPMiddleware` (pure ASGI middleware only).

## 4. Visual & UI Design Specifications
- **Theme**: Windows XP Luna Local Companion
- **Key Tokens**:
  - Primary: `#0058ee` (Luna Royal Blue titlebar gradient)
  - Secondary: `#ece9d8` (Classic 3D Face background)
  - Surface: `#ffffff` | Background: `#f0ede0` (Viewport canvas off-white)
  - Text: Primary `#000000`, Muted `#666666`
  - Status: Success `#2e7d32` (Connected green), Warning `#ed6c02` (Connecting amber), Error `#d32f2f` (Disconnected red)
- **Typography**: Tahoma, 11px body/status, 12px titlebar, 10px bold badge.
- **Component Anatomy & States**:
  - Same-origin local (`127.0.0.1:8000`): Green indicator dot, `Local Engine: Connected (Same-Origin)`.
  - Hosted disconnected: Amber indicator dot, `Local Engine: Disconnected`, `[Connect Engine]` button.
  - Connecting: `Connecting to 127.0.0.1:8000…` with disabled button state.
  - Connected: Green dot, `Local Engine: Connected (127.0.0.1:8000, v1.0)`, `[Open Local Studio ↗]` link.
  - Blocked / Offline: Red indicator, clear error text, direct link `Open Local App (127.0.0.1:8000) ↗`.

## 5. Test Scaffolding & Verification Commands
- **Primary Test Runner**:
  ```bash
  ./.venv/bin/python -m unittest tests.test_local_runtime -v
  ./.venv/bin/python -m unittest tests.test_viewer_js -v
  ./.venv/bin/python -m unittest discover -s tests -v
  ```
- **Strict OpenSpec Validation**:
  ```bash
  openspec validate local-first-runtime --strict
  ```
- **TDD Requirement**: Task group ## 1 MUST scaffold failing unit/integration tests before touching implementation code. Verify they fail initially.

## 6. Implementation Task Checklist

### 1. Test Scaffolding (TDD)
- [ ] 1.1 Scaffold failing unit tests in `tests/test_local_runtime.py` for `pyproject.toml` dependency parity with `requirements.txt`
- [ ] 1.2 Scaffold failing tests for pure ASGI CORS origin filtering matching `https://kintsugi-fracture-joeshmo.vercel.app` and preview URLs
- [ ] 1.3 Scaffold failing tests for server-side rejection of simple `POST` requests and `/outputs/*` reads from unauthorized `Origin` headers before body consumption
- [ ] 1.4 Scaffold failing tests for `Host` header DNS rebinding rejection (rejecting hosts outside loopback)
- [ ] 1.5 Scaffold failing tests for Local Network Access (LNA) client behavior: `targetAddressSpace: "loopback"` and permission fallback
- [ ] 1.6 Scaffold failing tests for port negotiation (8000–8009), instance reuse via `/api/health`, and non-loopback host warning in `studio()`
- [ ] 1.7 Scaffold failing tests for `timings["guard"]` instrumentation in `kintsugi.py`
- [ ] 1.8 Scaffold JavaScript unit tests in `tests/test_viewer_js.py` for `resolveEngineUrl` and static preset index loading

### 2. Packaging & Security Middleware Implementation
- [ ] 2.1 Create `pyproject.toml` with PEP 621 metadata, dependencies matching `requirements.txt`, and console script `kintsugi-studio = "web_app:studio"`
- [ ] 2.2 Implement pure ASGI `SecurityCORSMiddleware` in `web_app.py` enforcing strict origin validation, state-changing POST checks, Host header validation, and standard CORS/LNA handling without `BaseHTTPMiddleware`
- [ ] 2.3 Implement launcher entrypoint `studio(argv=None)` in `web_app.py` with sequential port probing (8000–8009), instance reuse, and security warnings
- [ ] 2.4 Add `timings["guard"]` measurement around the F1 STL round-trip and manifold audit in `kintsugi.py`
- [ ] 2.5 Generate `static/presets/index.json` containing metadata for bundled presets
- [ ] 2.6 Update `vercel.json` with static rewrites; remove `app.py` so Vercel deploys purely as static CDN assets

### 3. Web GUI Companion Integration
- [ ] 3.1 Implement `resolveEngineUrl` in `static/viewer.js` to dynamically prefix API calls and output download URLs with the active engine base URL
- [ ] 3.2 Update preset loading in `static/viewer.js` to fall back to `/presets/index.json` when disconnected from a local engine
- [ ] 3.3 Add "Connect Engine" user gesture button, sequential port range probing (8000–8009), connection status badge, and "Open Local App (127.0.0.1:8000) ↗" fallback link to the Windows XP interface
- [ ] 3.4 Implement `api_version` handshake in `GET /api/health` and verify compatibility on companion connection

### 4. Verification & Empirical Audit
- [ ] 4.1 Perform Gate 4.1 cross-browser verification on real HTTPS Vercel preview (root `/` loads the GUI, Chrome LNA prompt, Firefox CORS, Safari mixed content fallback)
- [ ] 4.2 Run full regression test suite (`python -m unittest discover -s tests -v`) and verify clean pass across all generators
- [ ] 4.3 Strictly validate OpenSpec change artifacts (`openspec validate local-first-runtime --strict`)
- [ ] 4.4 Populate `verification.md` with Requirement Adherence Matrix, resolved assumptions, and verbatim execution logs

## 7. Post-Implementation & Verification Obligations
When `spec-coder-sub` finishes:
1. Verify all checkboxes in `tasks.md` are marked `- [x]`. Only tick boxes that genuinely ran and passed.
2. Check data preservation: confirm record/feature counts before and after if touching data models.
3. Ensure `<changeDir>/verification.md` is populated with:
   - Executive Summary & Environment
   - Requirement Adherence Audit Matrix (mapping every spec scenario to its verifying test)
   - Resolved Assumptions & Empirical Proof
   - Nomenclature & Code Symbol Audit
   - Verbatim Execution Logs
4. Automatically run verification via `openspec-verify-change`.
5. If clean with no critical issues, sync specs: `openspec specs apply --change "local-first-runtime"`.
