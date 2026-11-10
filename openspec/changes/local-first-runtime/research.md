## Source material

**2026-11-09, project owner (chat):**

> why can't we just make all the processing/file upload local? as in the web gui just serves a visual interface that's cached, and then all the processing/uploading runs locally? why have we decided to handle the processing all online?

**2026-11-10, project owner (chat):**

> can you archive the last openspec change, and merge pr #11? then once that's done, draft a detailed technical proposal for how we can port everything from the engine and whatnot to run locally? and i guess also a feasibility/risks section for the effort required to port everything to be able to run locally from the web browser.

Context: the engine has always run locally through `python web_app.py`. Hosted processing only arrived on 2026-11-08, when the owner asked to deploy to Vercel. The serverless function was the only way to make the hosted URL work. No design decision ever chose server-side processing.

### Raised but not acted on

- **A hosted interface calling a server on the user's machine.** That is, the cached page on Vercel talks to `http://localhost:8000`. Rejected for now: browsers increasingly restrict public origins from calling private-network addresses (Chrome's Private Network Access), and it adds CORS and mixed-content handling for no gain over serving the whole app locally. See Unverified assumptions.
- **A standalone desktop executable** (PyInstaller, Briefcase, Tauri plus a Python sidecar). This is the next step after a one-command launcher, if one is ever wanted. It isn't needed for personal use.
- **Removing the Vercel deployment.** That's the owner's call. Architecture proposes a demo-only mode as the alternative to deleting it.

## Glossary

| Term | Means | Does NOT mean |
| :--- | :--- | :--- |
| Native local | The existing Python engine and FastAPI app run on the user's machine and the browser talks to `127.0.0.1` | Code running inside the browser tab |
| Browser-local | The engine runs inside the browser tab (WebAssembly), with no server process. The page is static files that can be cached | A hosted interface calling a native local server |
| Hosted | The Vercel deployment: static assets plus a Python serverless function | Anything on the user's machine |
| Shim | A Python module named `manifold3d` that implements only the subset of the API the engine uses, by calling manifold's JavaScript/WebAssembly build through Pyodide's FFI | The real `manifold3d` Python package |
| Pyodide | CPython plus a scientific stack compiled to WebAssembly, loaded in a page or a Worker | A Python-to-JS transpiler |
| Parity | The browser-local engine gives the same accept/reject decisions and statistically equivalent fracture output as native, checked within stated tolerances | Byte-identical output, which is not expected across a different boolean backend and floating-point environment |

## External research

| Source | What it establishes | Licence | Accessed |
| :--- | :--- | :--- | :--- |
| Pyodide "Packages built in Pyodide" (https://pyodide.org/en/stable/usage/packages-in-pyodide.html, page header "Version 314.0.7") | `numpy` 2.4.6 and `scipy` 1.18.0 are built for Pyodide. **`manifold3d` is not.** `trimesh` and `rtree` are not in the built list | MPL-2.0 (Pyodide) | 2026-11-10 |
| PyPI `manifold3d` files (https://pypi.org/project/manifold3d/#files) | The latest release is 3.5.4. Its 46 wheels are all Linux, macOS or Windows (CPython 3.9–3.14). **No `wasm32`, `emscripten` or `pyodide` wheel exists for 3.5.4**; older releases were not checked | Apache-2.0 | 2026-11-10 |
| manifold WASM TypeScript declarations (`bindings/wasm/manifold-encapsulated-types.d.ts`, `master`) | It exposes everything the engine uses: `rayCast(origin, endpoint): RayHit[]`, `subtract`/`intersect`/`add`, `static union(Manifold[])`, `hull()`, `static hull(points)`, `decompose()`, `static revolve(CrossSection, …)`, `cube`/`sphere`/`cylinder`, `ofMesh`/`getMesh`, `volume`, `numTri`, `status`, `isEmpty`, `transform`/`translate`/`rotate` (degrees), and `CrossSection` | Apache-2.0 | 2026-11-10 |
| manifold Python binding (`bindings/python/manifold3d.cpp`, `master`) and core header (`include/manifold/manifold.h`) | Python `ray_cast` binds the core `Manifold::RayCast(vec3 origin, vec3 endpoint)`, a public core method. Neither file mentions Pyodide, Emscripten or wasm | Apache-2.0 | 2026-11-10 |

## Candidate tech

| Option | Decision | Reason | Date |
| :--- | :--- | :--- | :--- |
| **Track A: native local**, a one-command launcher for the existing FastAPI app on `127.0.0.1` | Adopted as the primary path | Zero engine changes, and it removes every hosted-only limit seen so far (Verified facts) | 2026-11-10 |
| `pyproject.toml` plus a console script, run from a clone (`uv run kintsugi-studio` or `pip install -e .`) | Adopted | The repo has no `pyproject.toml` today. Running from a clone keeps `BASE_DIR`-relative `static/` and `presets/` working without restructuring into a package | 2026-11-10 |
| An installable wheel (`pipx install kintsugi-studio`) | Deferred | Needs the flat top-level modules moved into a package so `static/` and `presets/` ship as package data. That's a larger rename touching every import and test | 2026-11-10 |
| **Track B1: Pyodide plus a `manifold3d` shim over manifold's WASM build** | Spike first | Keeps the 4,998-line engine in Python. The shim covers about 20 API entry points (Verified facts) | 2026-11-10 |
| **Track B2: compile the `manifold3d` Python binding for Pyodide** (pyodide-build, nanobind) | Fallback if B1 fails | Identical engine code, but we'd own a custom wheel build for every Pyodide release, and there's no upstream wasm wheel today | 2026-11-10 |
| **Track B3: port the engine to TypeScript** | Rejected for now | Rewriting about 5k lines of numerically delicate code and re-deriving every regression baseline. Highest effort and risk | 2026-11-10 |
| trimesh's 3MF loader in the browser | Not needed | `mesh_formats.py` already reads 3MF with the standard library only | 2026-11-10 |

## Patterns adopted

- **Local-first web app**: a browser interface served from the user's own machine, the same pattern as Jupyter (`jupyter lab` opens `http://127.0.0.1:8888`). Lands in the Track A launcher.
- **Adapter for a native extension**: replace one native dependency with a thin module of the same name, backed by another implementation, so callers don't change. Lands in Track B1's `manifold3d` shim.
- **Web Worker for heavy compute**: run Pyodide off the main thread so the viewer stays responsive. Lands in Track B1's worker host.

## Verified facts

| Claim | Value | How verified | Date | Volatility |
| :--- | :--- | :--- | :--- | :--- |
| The engine already runs locally | `web_app.main()` starts uvicorn on `--host 127.0.0.1 --port 8000` by default and serves both the UI and the API | Read `web_app.py` on `main` `8ec7e34` | 2026-11-10 | stable |
| Runtime dependencies | `numpy`, `scipy`, `trimesh`, `manifold3d`, `fastapi`, `uvicorn`, `python-multipart` (`requirements.txt`). No `pyproject.toml` or `setup.py` | Read the repo root | 2026-11-10 | stable |
| What the engine uses from scipy | `scipy.ndimage` (fragment counting) and `scipy.spatial.Voronoi`/`cKDTree` (legacy Voronoi generator). Nothing else | `grep` of imports in `kintsugi.py` | 2026-11-10 | stable |
| What the engine uses from trimesh | Mesh container and STL I/O: `Trimesh`, `load`, `exchange.stl.export_stl`, `is_watertight`, `is_volume`, `merge_vertices`, `remove_unreferenced_vertices`, `update_faces`, `fix_normals`, `edges_unique`, `Scene`. No ray or proximity queries, so no `rtree` or embree | `grep` of `trimesh.` and method calls in `kintsugi.py` | 2026-11-10 | stable |
| What the engine uses from manifold | 42 `mf.Manifold` sites; `ray_cast` ×6 (envelope probe, wall probe, projection); `volume` ×11; `is_empty` ×9; `decompose` ×4; `revolve` ×3; `CrossSection` ×3; `batch_boolean` ×2 (`OpType.Add`); `hull` ×2; `hull_points`, `cube`, `sphere`, `cylinder`, `transform`, `translate`, `rotate`, `num_tri`, `status`; operators `-` and `^` on the main cut | `grep -o` over `kintsugi.py` and `sample_models.py` | 2026-11-10 | stable |
| Every one of those manifold operations exists in the JS/WASM build | See External research (signatures quoted) | Declarations file on `master` | 2026-11-10 | decays with the manifold release |
| Native timings (R=0.5, seed=1, vein, this container) | `tea_bowl`: growth 1.59 s, hybrid 2.75 s. `bowl_urdformer`: growth 3.83 s, hybrid 11.45 s. Stage sums are lower than the totals: for urdformer hybrid, validate 0.38, crack_graph 0.42, projection 0.10, cutter 1.04, csg 0.98, debris_swap 0.45, export 0.02 (≈3.4 s), leaving ≈8 s not broken out in `timings` | `generate_kintsugi_mesh(...)["timings"]` on `main` | 2026-11-10 | decays |
| Real-model output exceeds the hosted response limit | `bowl_urdformer` hybrid ceramic is 162,512 triangles, a binary STL of 84 + 50 × 162,512 ≈ 8.1 MB, over Vercel's 4.5 MB response limit. That result can't be downloaded from the hosted app | Triangle count from the run above; STL size by format arithmetic | 2026-11-10 | decays |
| Hosted-only failures found so far | 4.5 MB request limit (PR #10 diagnosis); per-instance `/tmp`, so downloads can return 404 on another instance; 300 s function limit; a public upload surface (the PR #11 memory follow-up) | PR #10 console log, `web_app.py` comments, the PR #11 review | 2026-11-09/10 | stable while hosted |

## Unverified assumptions

| Assumption | Confidence | Verification cost |
| :--- | :--- | :--- |
| The **released** `manifold-3d` npm package includes `rayCast` (it is on `master`; the release wasn't checked) | Medium | Read the published package's `.d.ts`, or call it in Node. Under 30 minutes, part of the B1 spike |
| Python `RayHit.distance` and JS `RayHit.distance` use the same convention. The engine multiplies by `ray_length`, which implies a 0–1 fraction along the segment | Medium | One ray against a unit cube in each. Part of the spike |
| `trimesh` installs into Pyodide with `micropip` as a pure-Python wheel, with numpy as its only hard dependency | Medium-high | `micropip.install("trimesh")` in Pyodide under Node. Part of the spike |
| The engine's pure-Python hot loops (crack growth, `_segment_contact`) run 1.5–3× slower under Pyodide than natively | Medium (commonly reported range, not measured here) | Time `generate_crack_paths` in Pyodide vs native. Part of the spike |
| The first-load payload (Pyodide core + numpy + scipy + trimesh + manifold WASM) is a few tens of MB, cached after the first visit | Medium | Measure in the spike with the browser network panel |
| Chrome's Private Network Access rules would block or prompt for a public page calling `http://localhost` | Medium | Only matters if the "hosted interface plus local server" idea is revived |
| Fracture output from manifold WASM matches native closely enough for parity. Floating-point differences in ray casts can change `rbar`, which feeds every downstream step | Medium-low | Compare accept/reject, crack counts and volumes over the preset and real-model matrix in the spike |

## Superseded claims

- **"We decided to process online."** No such decision exists. Hosting was a deployment convenience requested on 2026-11-08 (Source material).

## Links out

- Deployment overlay: `app.py`, `vercel.json`, `.vercelignore`
- Archived upload change, with the hosted limits and the memory follow-up: `openspec/changes/archive/2026-11-10-upload-diagnostics-and-3mf/`
- Local preset drop folder proposal (branch `docs/kintsugi-shard-seams`, commit `d7e502b`): `openspec/changes/local-preset-drop-folder/`
