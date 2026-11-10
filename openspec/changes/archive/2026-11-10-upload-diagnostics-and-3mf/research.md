## Source material

**2026-11-09, project owner (chat):**

> can you now investigate why i'm getting "json parse error. failed to parse line 1" when uploading custom .stl's? could you begin the debugging actually not by investigating anything or testing anything but rather just making the error codes more verbose/descriptive and outputting it into the console?

> can add the new verbose bugging changes to a pr?

PR #10 (`debug/verbose-upload-errors`, commit `e055b34`) was opened. The owner then pasted this console entry from the PR #10 preview deployment:

```text
[kintsugi] ✗ Validate upload: HTTP 413 returned non-JSON body
status: 413
bodyPreview: "Request Entity Too Large\n\nFUNCTION_PAYLOAD_TOO_LARGE\n\niad1::vpl8b-1794261342893-0dcc5580ae76\n"
headers: { "content-type": "text/plain; charset=utf-8", "content-length": "93", "x-vercel-id": "iad1::vpl8b-1794261342893-0dcc5580ae76", … }
parseError: "JSON.parse: unexpected character at line 1 column 1 of the JSON data"
stage: "parse-json"
```

> would it make sense to add .3mf as an acceptable upload file format? why hasn't it been added as an option already?

> can you switch to main (if you haven't already). and can you propose a new openspec change that includes the new verbose error logs, as well as support for .3mf upload file format.

### Raised but not acted on

- **Getting around the Vercel body limit** with direct-to-blob uploads (Vercel Blob or a presigned URL) or with client-side compression or ASCII→binary STL conversion. These remove or shrink the limit instead of reporting it. Blob storage is new infrastructure and a new dependency, which needs its own decision. Compression needs the server to decode the bytes, which changes the upload contract. Deferred. This change makes the limit visible and explains it up front.
- **The response-size limit on downloads.** `/outputs/*.stl` is served by the same function, so a result STL over the platform limit fails when downloading, not when uploading. It is related but separate. Out of scope; the new diagnostics will name it if it happens (`Could not load mesh … from /outputs/…`).
- **Multi-object 3MF projects** (several build items, plates, assemblies). The engine fractures exactly one closed solid. These are rejected with a clear message, not merged.
- **Colours and materials from 3MF** (`basematerials`, `colorgroup`, textures). They're irrelevant to fracture. Ignored.
- **Merging PR #10 on its own first.** This change adopts PR #10's code as the starting point, so its behaviour is specified and tested. PR #10 itself shipped no tests.

## Glossary

| Term | Means | Does NOT mean |
| :--- | :--- | :--- |
| Platform error | A response produced by the hosting layer (Vercel's edge or function router) before or instead of our app, e.g. `FUNCTION_PAYLOAD_TOO_LARGE`. It has no `X-Kintsugi-Request-Id` header and is usually `text/plain` | An error raised in `web_app.py` or `kintsugi.py` |
| App error | An error response produced by `web_app.py`. Always JSON, with `detail`, `error_type`, `status`, `path` and `request_id` | Any non-2xx response |
| Request id | The 12-hex-character id generated per request by the web app, returned in `X-Kintsugi-Request-Id` and written on every server log line for that request | Vercel's `x-vercel-id`, which identifies the platform request |
| Upload limit | The largest upload *file* the current deployment accepts: `KINTSUGI_MAX_UPLOAD_BYTES` if set, else a lower default on Vercel and 50 MB elsewhere | The platform's request-body limit, which also counts multipart overhead and other form fields |
| 3MF package | A ZIP (OPC) container whose root model is referenced from `_rels/.rels`, normally at `3D/3dmodel.model` | A single XML file |
| Build item | A `<build><item objectid=… transform=…>` entry: one thing to print | An `<object>` definition, which may be unused or used several times |
| Component | An `<object>` that contains `<components><component objectid=… transform=…>` and no mesh of its own | A mesh part |
| Production-extension reference | A `<component p:path="/3D/Objects/x.model" objectid=…>` pointing into another model file in the same package | A reference to a file outside the package, which is invalid |
| Kintsugi assembly | Our own exported `kintsugi_assembly.3mf`: one build item whose components are named `CeramicBody` and `GoldSeams` | Any two-part 3MF |
| Flattened mesh | The union of every triangle reachable from the single build item, with all transforms and the unit scale applied, as one `trimesh.Trimesh` in millimetres | A boolean union. Overlapping parts are not merged geometrically |

## External research

| Source | What it establishes | Licence | Accessed |
| :--- | :--- | :--- | :--- |
| three.js r160 `examples/jsm/loaders/3MFLoader.js` (unpkg) | Imports `three` and `../libs/fflate.module.js` (resolves under our `three/addons/` import map). Applies build-item and component transforms. Stores `unit` but **never scales by it**. Has **no `p:path` support**: objects from all `3D/*.model` parts go into one flat map keyed by bare id, so ids that collide across parts resolve to the wrong object. Object `type` is stored but never used. Returns a `THREE.Group` with names preserved | MIT | 2026-11-09 |
| Vercel docs, Functions limitations | The Functions request and response body limit is 4.5 MB, and the platform answers larger requests itself with 413 `FUNCTION_PAYLOAD_TOO_LARGE`. The search used for this change did not return the exact byte definition (MB vs MiB) | Docs | 2026-11-08 / 2026-11-09 |
| 3MF Core Specification (3mf.io) | `<model unit>` ∈ {micron, millimeter, centimeter, inch, foot, meter}, default millimeter; transforms are 12 values for a row-major 4×3 affine matrix with translation in the last three values; object `type` ∈ {model, solidsupport, support, surface, other} | BSD-2-Clause (spec) | Not re-fetched for this change; see Unverified assumptions |

## Candidate tech

| Option | Decision | Reason | Date |
| :--- | :--- | :--- | :--- |
| A server reader built on `zipfile` + `xml.etree` in a new module `mesh_formats.py` | Adopted | No new dependencies. Same approach as our exporter (`multi-material-export` spec), and we only need vertices, triangles, transforms and units | 2026-11-09 |
| trimesh's built-in 3MF loader | Rejected | Imports `networkx` and `lxml`, which are not in `requirements.txt`. It would work locally (both happen to be installed) and fail on Vercel. It also can't enforce our one-build-item and reject rules | 2026-11-09 |
| Viewer preview via three.js `3MFLoader` | Rejected | Wrong preview for Production-extension files (id collisions across parts) and no unit scaling. It would preview a different shape from the one the server validates | 2026-11-09 |
| A viewer-side reader (`static/threemf.js`) that scans the zip directory itself, inflates with the `inflateSync` from `three/addons/libs/fflate.module.js`, and uses a small attribute-only XML scanner, mirroring the server rules | Adopted | Same rules on both sides; no new CDN origin; runs under Node so it is tested against the Python reader. Revised during implementation: the first plan (fflate `unzipSync` with a `filter`, plus `DOMParser`) fails because three r160 bundles fflate 0.6.9, whose `unzipSync` has no options | 2026-11-09 |
| The verbose diagnostics from PR #10 (`requestJson`, request-id middleware, JSON error handlers) | Adopted as the starting point | It already diagnosed the real failure (Source material). This change specifies and tests it | 2026-11-09 |
| An advertised upload limit, reported by `GET /api/health` and checked in the browser before uploading | Adopted | A file over the platform limit never reaches the app, so only the client can explain it up front | 2026-11-09 |

## Patterns adopted

- **Structured error envelope with a correlation id** (the usual API practice of putting a request id on responses and logs): `{detail, error_type, status, path, request_id}` plus `X-Kintsugi-Request-Id`. Lands in `web_app.py`.
- **Read the body as text, then parse** on the client, so a non-JSON body is reported with its status and preview rather than a parser message. Lands in `static/viewer.js` `requestJson`.
- **Fail loudly on unsupported structure** when reading containers: reject what we can't represent faithfully (multiple build items, non-model object types) instead of guessing. Same principle as the engine's input envelope.

## Verified facts

| Claim | Value | How verified | Date | Volatility |
| :--- | :--- | :--- | :--- | :--- |
| The "JSON parse error, line 1" on custom STL uploads is a Vercel platform 413 | `status 413`, `text/plain`, body `FUNCTION_PAYLOAD_TOO_LARGE`, no `X-Kintsugi-Request-Id` header | Owner's console log from the PR #10 preview (Source material) | 2026-11-09 | stable while hosted on Vercel Functions |
| Our 50 MB cap can't apply on Vercel | `MAX_UPLOAD_BYTES = 50 * 1024 * 1024` is checked inside `_save_upload`, which never runs for a platform-rejected request | Read `web_app.py` on `main` `aeeb872`; consistent with the missing request id above | 2026-11-09 | stable |
| PR #10's verbose diagnostics pass the existing web API tests | `python -m unittest tests.test_web_api`: 18 tests OK | Run on `debug/verbose-upload-errors` before opening PR #10 | 2026-11-09 | decays with main |
| The current upload contract is `.stl`/`.obj` only | `retro-web-gui` spec "Model preset selection and custom upload"; `static/index.html` `accept=".stl,.obj"`; `web_app.py` suffix checks in `_resolve_input` and `api_validate` | Read on `main` `aeeb872` | 2026-11-09 | stable |
| The engine loads every input through one function | `_load_trimesh(path)` → `trimesh.load(..., force="mesh", process=False)` at `kintsugi.py:253`, used by `validate_and_load_mesh` | Read `kintsugi.py` on `main` | 2026-11-09 | stable |
| trimesh's 3MF reader needs undeclared dependencies | `trimesh.exchange.threemf` imports `networkx` and `lxml`; neither is in `requirements.txt`; both present in the local `.venv` | `inspect.getsource` plus `importlib.util.find_spec` in `.venv`; read `requirements.txt` | 2026-11-09 | stable |
| Our exporter's structure is detectable | `export_kintsugi_3mf` writes `unit="millimeter"`, one build item, a parent object whose components reference objects named `CeramicBody` and `GoldSeams` | Read `kintsugi.py:4534-4580` | 2026-11-09 | stable |
| three.js r160 `3MFLoader` limits | No unit scaling, no `p:path`, object `type` unused | Source read (External research) | 2026-11-09 | stable at r160 |
| three r160 bundles fflate 0.6.9, and its `unzipSync(data)` takes no options | No `filter`; every entry is inflated; `inflateSync(data, out?)` is exported; failures are thrown as strings | Fetched `examples/jsm/libs/fflate.module.js` from unpkg (banner `version 0.6.9`) and read the `unzipSync` and `inflateSync` definitions | 2026-11-09 | stable at r160; changes if the three version in `index.html` is bumped |
| A 3MF of the fixture bowl is much smaller than its binary STL | 8,102 bytes vs 38,484 bytes (21%) | `os.stat` on `write_bowl_3mf` output and on the STL written by `fixtures.write_bowl` | 2026-11-09 | stable |
| The new reader works where trimesh's 3MF loader can't | With `networkx`/`lxml` made unimportable, `validate_and_load_mesh` loads the 3MF while `trimesh.load` raises `ModuleNotFoundError` | Script blocking both modules via `sys.modules`, run in `.venv` | 2026-11-09 | stable |
| STL and 3MF routes agree on a vessel | Same face count and extents; p5 wall thickness equal within 1e-4 mm (the STL stores float32) | `test_validate_and_load_mesh_accepts_3mf_like_the_stl` | 2026-11-09 | stable |
| Viewer reader and server reader agree | Triangle geometry within 1e-3 mm and the same rejection reasons on 9 accepted and 15 rejected fixtures; deliberately breaking the unit factor or the transform order fails the test | `tests/test_viewer_js.py` (Node 22) plus two mutation runs | 2026-11-09 | decays with either reader |
| The request-id and error-envelope behaviour of PR #10 already held before this change | 10 of the 17 new API tests passed on the PR #10 code before any server change; the other 7 (limit, `.3mf`, suffix message) failed (8 failure reports, because one test has two subtests) | Ran the new test classes right after writing them | 2026-11-09 | stable |

## Unverified assumptions

| Assumption | Confidence | Verification cost |
| :--- | :--- | :--- |
| The exact Vercel body limit is 4,500,000 bytes, not 4.5 MiB | Medium. The Vercel default upload limit is set conservatively below both | One preview upload of a ~4.45 MB file, about 5 minutes |
| Bambu Studio and OrcaSlicer write single-object projects with the Production extension (`3D/Objects/*.model` + `p:path`), while PrusaSlicer writes plain core meshes in `3D/3dmodel.model` | Medium | Export one cube from each slicer and inspect the zip, about 15 minutes |
| Slicers record modifier and negative volumes only in vendor config (`Metadata/model_settings.config`, `Metadata/Slic3r_PE_model.config`), not in core XML | Medium | Same exports, with a modifier added |
| 3MF unit enumeration and transform layout are as stated in External research. The transform layout agrees with three.js's `parseTransform` (translation in values 10–12) | High | Re-read the Core Spec section 3.4, about 10 minutes |
| A 3MF is usually smaller than the equivalent binary STL, which helps under the upload limit | Medium | Compare sizes for the bowl and cup demo models |

## Superseded claims

- **"The upload failure is a JSON or STL parsing problem."** It isn't. The parse error was a symptom of reading Vercel's plain-text 413 as JSON (Verified facts).
- **"Use trimesh to read 3MF; it's in `available_formats()`."** It's available locally only because of incidental installs. It would fail on Vercel (Verified facts).

## Links out

- PR #10: https://github.com/slowbutfast/kintsugi-fracture/pull/10 (branch `debug/verbose-upload-errors`, commit `e055b34`)
- Upload contract: `openspec/specs/retro-web-gui/spec.md`, requirement "Model preset selection and custom upload"
- 3MF export contract: `openspec/specs/multi-material-export/spec.md`
- Vercel deployment notes: `vercel.json`, `app.py`
