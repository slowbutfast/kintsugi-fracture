## Source material

**2026-11-09, project owner (chat):**

> why can't we just make all the processing/file upload local? as in the web gui just serves a visual interface that's cached, and then all the processing/uploading runs locally? why have we decided to handle the processing all online?

**2026-11-10, project owner (chat):**

> can you archive the last openspec change, and merge pr #11? then once that's done, draft a detailed technical proposal for how we can port everything from the engine and whatnot to run locally? and i guess also a feasibility/risks section for the effort required to port everything to be able to run locally from the web browser.

**2026-11-10, project owner (chat, feedback on local-first plan):**

> wait, i was thinking of not making the vercel deployment a demo, but rather serving the web gui, but keeping the processing local.

Context: the engine has always run locally through `python web_app.py`. Hosted processing only arrived on 2026-11-08, when the owner asked to deploy to Vercel. The serverless function was the only way to make the hosted URL work. No design decision ever chose server-side processing.

### Raised but not acted on

- **A standalone desktop executable** (PyInstaller, Briefcase, Tauri plus a Python sidecar). This is the next step after a one-command launcher, if one is ever wanted. It isn't needed for personal use.

## Glossary

| Term | Means | Does NOT mean |
| :--- | :--- | :--- |
| Native local | The existing Python engine and FastAPI app run on the user's machine and the browser talks to `127.0.0.1` | Code running inside the browser tab |
| Hosted companion | The static Web GUI served from Vercel (`https://kintsugi-fracture-joeshmo.vercel.app`) connecting to the native local engine (`http://127.0.0.1:8000`) | A serverless Python function executing on Vercel |
| Browser-local | The engine runs inside the browser tab (WebAssembly), with no server process. The page is static files that can be cached | A hosted interface calling a native local server |
| Shim | A Python module named `manifold3d` that implements only the subset of the API the engine uses, by calling manifold's JavaScript/WebAssembly build through Pyodide's FFI | The real `manifold3d` Python package |
| Pyodide | CPython plus a scientific stack compiled to WebAssembly, loaded in a page or a Worker | A Python-to-JS transpiler |
| Parity | The browser-local engine gives the same accept/reject decisions and statistically equivalent fracture output as native, checked within stated tolerances | Byte-identical output, which is not expected across a different boolean backend and floating-point environment |

## External research

| Source | What it establishes | Licence | Accessed |
| :--- | :--- | :--- | :--- |
| Chrome Modern Web Guidance: Local Network Access (https://developer.chrome.com/docs/modern-web-guidance/guides/security/local-network-access?hl=en) | PNA preflight header rollout is paused. Chrome 142+ introduces user-permission prompts for Local Network Access (LNA). Requests from public origins to loopback require user permission via a user gesture | BSD-3-Clause | 2026-11-10 |
| WebKit Bug 171934 (https://bugs.webkit.org/show_bug.cgi?id=171934) | Apple Safari continues to block all HTTPS-to-HTTP loopback (`http://127.0.0.1`) fetch requests as mixed content. No browser flag or header permits this | Open Source | 2026-11-10 |
| MDN: CORS Simple Requests (https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/CORS#simple_requests) | `multipart/form-data` POST requests do not trigger CORS preflight (`OPTIONS`). Unauthenticated endpoints accepting POST must validate `Origin` and `Host` server-side before consuming payloads | CC0 | 2026-11-10 |
| Pyodide "Packages built in Pyodide" (https://pyodide.org/en/stable/usage/packages-in-pyodide.html, page header "Version 314.0.7") | `numpy` 2.4.6 and `scipy` 1.18.0 are built for Pyodide. **`manifold3d` is not.** `trimesh` and `rtree` are not in the built list | MPL-2.0 (Pyodide) | 2026-11-10 |
| PyPI `manifold3d` files (https://pypi.org/project/manifold3d/#files) | The latest release is 3.5.4. Its 46 wheels are all Linux, macOS or Windows (CPython 3.9–3.14). **No `wasm32`, `emscripten` or `pyodide` wheel exists for 3.5.4** | Apache-2.0 | 2026-11-10 |
| manifold WASM TypeScript declarations (`bindings/wasm/manifold-encapsulated-types.d.ts`, `master`) | Exposes: `rayCast(origin, endpoint): RayHit[]`, `subtract`/`intersect`/`add`, `static union(Manifold[])`, `hull()`, `static hull(points)`, `decompose()`, `static revolve(CrossSection, …)`, `cube`/`sphere`/`cylinder`, `ofMesh`/`getMesh`, `volume`, `numTri`, `status`, `isEmpty`, `transform`/`translate`/`rotate` (degrees), and `CrossSection`. Uses `Float32Array` for `vertProperties` | Apache-2.0 | 2026-11-10 |
| manifold WASM Memory Guidance (https://github.com/elalish/manifold/blob/master/bindings/wasm/documents/bindings.md) | Manifold C++ WASM objects must be manually freed via `.delete()`. Memory leaks occur if objects rely on JS garbage collection | Apache-2.0 | 2026-11-10 |

## Candidate tech

| Option | Decision | Reason | Date |
| :--- | :--- | :--- | :--- |
| **Track A: native local**, one-command launcher for existing FastAPI app on `127.0.0.1` | Primary path | Zero engine changes; eliminates hosted 4.5 MB body and 300 s execution limits | 2026-11-10 |
| **Hosted GUI companion** (`https://kintsugi-fracture-joeshmo.vercel.app` calling `127.0.0.1:8000`) | Secondary web path | Preserves the hosted URL for convenience while executing all computation locally. Gated by user gesture in Chrome; falls back to direct local URL in Safari | 2026-11-10 |
| `pyproject.toml` plus console script (`uv run kintsugi-studio`) | Adopted | Standard PEP 621 packaging; runs from clone with zero path restructuring | 2026-11-10 |
| **Track B1: Pyodide plus `manifold3d` shim over manifold's WASM build** | Spike first | Keeps the 4,998-line engine in Python; shim covers ~20 API entry points | 2026-11-10 |
| **Track B2: compile `manifold3d` Python binding for Pyodide** (pyodide-build, nanobind) | Fallback if B1 fails | Upstream lacks wasm wheel; would require custom toolchain maintenance per Pyodide release | 2026-11-10 |
| **Track B3: port engine to TypeScript** | Rejected for now | Highest effort and risk: rewrites 5k lines of sensitive geometry and baseline tolerances | 2026-11-10 |

## Patterns adopted

- **Local-first web app with companion UI**: A browser interface served statically from Vercel edge CDN or loopback, connecting to the user's local engine for heavy computation.
- **Strict Server-Side Origin & Host Verification**: Rejects cross-origin POSTs and DNS rebinding requests before reading request bodies.
- **Adapter for native extension**: Replace one native dependency with a thin module of the same name. Lands in Track B1's `manifold3d` shim.
- **Web Worker for heavy compute**: Run Pyodide off the main thread so the viewer stays responsive.

## Verified facts

| Claim | Value | How verified | Date | Volatility |
| :--- | :--- | :--- | :--- | :--- |
| The engine already runs locally | `web_app.main()` starts uvicorn on `--host 127.0.0.1 --port 8000` | Read `web_app.py` | 2026-11-10 | stable |
| Real production Vercel origin | `https://kintsugi-fracture-joeshmo.vercel.app` | Vercel deployment project settings | 2026-11-10 | stable |
| Ray-cast runtime call count | ~11,000 calls per fracture (~10,854 for `tea_bowl`; ~11,528 for `bowl_urdformer`) across 6 call sites in `kintsugi.py` | Measured with counting wrapper on `Manifold.ray_cast` (R=0.5, seed=1) | 2026-11-10 | stable |
| Ray-cast native execution time | 0.16–0.37 s total natively | Measured in counting wrapper | 2026-11-10 | stable |
| Engine coordinate precision | Uses `mf.Mesh64(vertices, faces)` and `to_mesh64()` (float64) | Read `kintsugi.py:205, 217` | 2026-11-10 | stable |
| Real-model output exceeds hosted limits | `bowl_urdformer` hybrid ceramic is 162,512 triangles (~8.1 MB binary STL), exceeding Vercel's 4.5 MB response limit | Triangle count and format arithmetic | 2026-11-10 | stable |
| Simple POST requests bypass CORS preflight | `multipart/form-data` POSTs execute without `OPTIONS` preflight under browser CORS | MDN CORS spec; verified with curl/test scripts | 2026-11-10 | stable |
| Safari HTTPS-to-loopback block | Safari blocks all `fetch("http://127.0.0.1:8000/...")` from `https://...` as mixed content | WebKit Bug 171934 | 2026-11-10 | stable |

## Unverified assumptions

| Assumption | Confidence | Verification cost |
| :--- | :--- | :--- |
| Released `manifold-3d` npm package includes `rayCast` with matching distance semantics | Medium | Standalone Node test in Gate 0 (<30 mins) |
| Manifold WASM `vertProperties` float32 coordinate truncation produces watertight booleans without self-intersections on dense models | Medium-low | Gate 0 real mesh test |
| Python-to-JS FFI crossing overhead for ~11,000 ray casts in Pyodide remains under 2.0 s total | Medium | Measure in Track B spike |
| `trimesh` installs in Pyodide with `micropip` as a pure-Python wheel | Medium-high | Test in Track B spike |

## Links out

- Deployment overlay: `vercel.json`, `static/`, `presets/`
- Archived upload change with hosted limits: `openspec/changes/archive/2026-11-10-upload-diagnostics-and-3mf/`
