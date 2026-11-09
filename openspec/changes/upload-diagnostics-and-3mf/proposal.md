## Why

Custom STL uploads on the hosted app fail with "JSON parse error … line 1". The PR #10 diagnostics showed this is a **platform error**: Vercel rejects request bodies over 4.5 MB with a plain-text 413 `FUNCTION_PAYLOAD_TOO_LARGE` before our code runs. The browser then failed trying to parse that text as JSON (research.md, Verified facts). Users get a misleading message, and nothing tells them the real limit.

Separately, 3MF is what every modern slicer saves by default. It's often smaller than STL, and it records its own units. But uploads only accept `.stl`/`.obj`, so users have to convert first.

## What Changes

- **Request diagnostics become specified behaviour.** This adopts PR #10 (`e055b34`) as the starting point and adds tests.
  - **Server:** every request gets a **request id**, returned in `X-Kintsugi-Request-Id`. There is one log line per `/api/*` request, plus upload logging.
  - **Errors are always JSON.** Every **app error** is a JSON envelope `{detail, error_type, status, path, request_id}`. This includes unhandled exceptions, which today return plain-text 500s.
  - **Client:** `requestJson` reads the body as text before parsing. It logs status, diagnostic headers and a body preview to the console, and reports **platform errors** by name, not as parse errors.
- **The upload limit is advertised and checked up front.**
  - `GET /api/health` reports `max_upload_bytes` and `accepted_formats`.
  - The **upload limit** is `KINTSUGI_MAX_UPLOAD_BYTES` if set. Otherwise it is a conservative default under the platform limit when `VERCEL` is set, and 50 MB elsewhere.
  - The viewer refuses an over-limit file before sending it. The message names the file size and the limit, and suggests running locally or exporting a smaller file.
  - **BREAKING (hosted only):** uploads between the hosted limit and 50 MB used to fail with a confusing parse error. They now fail immediately with a clear message. They never worked on Vercel.
- **`.3mf` upload support.** A dependency-free reader in a new `mesh_formats.py` (`zipfile` + `xml.etree`) resolves the root model through `_rels/.rels` and accepts exactly one **build item**. It then:
  - applies build-item and **component** transforms;
  - follows **Production-extension references** (`p:path`) within the package;
  - converts the `unit` attribute to millimetres;
  - ignores materials and colours;
  - returns one **flattened mesh** to the existing validation pipeline.

  It rejects, with specific messages:
  - more than one build item;
  - objects whose `type` is not `model`;
  - references that are missing or point outside the package;
  - our own **Kintsugi assembly** (`CeramicBody` + `GoldSeams`).

  The viewer previews 3MF with a small JavaScript reader (`static/threemf.js`) that follows the same rules. It inflates with the `fflate` already bundled with three.js, and is tested against the Python reader under Node.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `retro-web-gui`:
  - "Model preset selection and custom upload" now accepts `.3mf`, and its 50 MB cap becomes a deployment-dependent, advertised upload limit that the client checks before uploading.
  - New requirement for request diagnostics and structured error responses.
- `mesh-fracture-engine`: new requirement for loading a 3MF package into one flattened millimetre mesh, with the reject rules above. The existing input envelope (watertight, units, extents, vessel, wall) applies unchanged after loading.

## Impact

- **Code:**
  - `web_app.py`: middleware, error handlers and upload logging from PR #10; the configurable upload limit; `/api/health` fields; `.3mf` accepted in the suffix checks.
  - `kintsugi.py`: `_load_trimesh` dispatches `.3mf` to `mesh_formats.load_3mf`; the CLI accepts `.3mf`.
  - **New** `mesh_formats.py`: the 3MF reader.
  - `static/viewer.js`: `requestJson` from PR #10, the pre-upload size check, and the 3MF preview reader.
  - `static/index.html`: `accept=".stl,.obj,.3mf"` and the upload hint text.
- **Tests:**
  - **New** `tests/test_mesh_formats.py`, with synthetic 3MF fixtures built in-test using `zipfile`.
  - `tests/test_web_api.py`: diagnostics headers, JSON error envelope, health limits, and 3MF validate and fracture.
- **Dependencies:** none new. `networkx`/`lxml` are deliberately not added.
- **PR #10:** superseded by this change's implementation PR. Close it once that PR lands.
- **Deploy:** setting `KINTSUGI_MAX_UPLOAD_BYTES` on Vercel is optional; the built-in hosted default applies otherwise.
