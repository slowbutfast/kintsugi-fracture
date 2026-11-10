## Why

Every upload and download problem we've hit since 2026-11-08 comes from **hosted** processing, not from the engine:
- the 4.5 MB request limit;
- downloads served from per-instance `/tmp`;
- the 300 s function limit;
- a public upload surface that needed memory hardening.

A real model already produces output the hosted app can't serve: the urdformer bowl's hybrid ceramic is about 8.1 MB (research.md, Verified facts). Hosting was a deployment convenience, never a design decision. For a personal, non-commercial tool, running locally is the better default, and the engine already does it.

## What Changes

Two tracks. **Track A is the proposal. Track B is a feasibility study with a gated spike.**

- **Track A: native local, one command.**
  - Add a `pyproject.toml` (PEP 621) with the current dependencies and a `kintsugi-studio` console script. It starts the existing FastAPI app on `127.0.0.1`, falls back to a free port if 8000 is taken, and opens the browser.
  - Work from a clone with `uv run kintsugi-studio` or `pip install -e .`.
  - Add a **local profile**: the 50 MB upload limit (already the non-Vercel default), outputs under `output/web/`, and the `presets/local/` drop folder from `local-preset-drop-folder` when it lands.
  - **Hosted becomes demo-only:** a `KINTSUGI_DEMO_MODE` setting, on for the Vercel deployment, turns off uploads and limits the app to bundled presets, so the public URL no longer accepts arbitrary files. Or the owner deletes the deployment instead.
  - Update `README.md`/`TESTING.md` with a local quickstart.
- **Track B: browser-local (feasibility only, no build commitment).**
  - Assess running the engine in the browser tab with Pyodide.
  - Recommend **B1**: a `manifold3d` **shim** over manifold's official WebAssembly build, run in a Web Worker, with the engine's Python unchanged.
  - Define a 1–2 day spike with go/no-go criteria (correctness parity, speed, payload size). A build change follows only if the spike passes.
- **No engine behaviour changes.** Generator output, validation rules and export formats are untouched.

## Capabilities

### New Capabilities
- `local-runtime`: how the app is launched and configured on the user's machine (launcher, port selection, browser open, local profile defaults), and the hosted demo-only mode.

### Modified Capabilities
- `retro-web-gui`: in demo mode the upload zone is disabled and explains that uploads need the local app. The upload limit, diagnostics and formats are otherwise unchanged.

Track B adds no capability until its spike passes and a follow-up change is proposed.

## Impact

- **New:** `pyproject.toml`; a launcher entry point (`web_app.main_studio`, or a small `studio.py`).
- **Edited:**
  - `web_app.py`: free-port fallback, `--open`, the demo-mode flag gating `/api/validate` and uploads to `/api/fracture`;
  - `static/viewer.js`/`index.html`: demo-mode upload-zone state from `/api/health`;
  - `README.md`, `TESTING.md`.
- **Unchanged:** `kintsugi.py`, `mesh_formats.py`, the generators, the tests' baselines.
- **Dependencies:** none new for Track A. Track B's spike uses Pyodide and `manifold-3d` (npm) in a scratch area only.
- **Deploy:** set `KINTSUGI_DEMO_MODE=1` on the Vercel project, or remove the project.
