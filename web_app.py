#!/usr/bin/env python3
"""FastAPI backend for the Windows XP-themed Kintsugi Studio 2001 GUI."""

from __future__ import annotations

import argparse
import logging
import os
import shutil
import tempfile
import time
import traceback
import uuid
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

import kintsugi
from sample_models import PRESETS, ensure_presets, preset_path

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
PRESET_DIR = BASE_DIR / "presets"
# Vercel's filesystem is read-only outside /tmp, and /tmp is per-instance:
# downloads are best effort there (a follow-up request can land on a cold
# instance).  KINTSUGI_OUTPUT_DIR overrides the location everywhere.
_DEFAULT_OUTPUT_DIR = (
    Path(tempfile.gettempdir()) / "kintsugi-web"
    if os.getenv("VERCEL")
    else BASE_DIR / "output" / "web"
)
OUTPUT_DIR = Path(os.getenv("KINTSUGI_OUTPUT_DIR") or _DEFAULT_OUTPUT_DIR)
MAX_UPLOAD_BYTES = 50 * 1024 * 1024

STATIC_DIR.mkdir(parents=True, exist_ok=True)
PRESET_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
ensure_presets(PRESET_DIR)

app = FastAPI(title="Kintsugi Studio 2001", version="1.0")

# Diagnostics: one log line per API request, a request id echoed in the
# ``X-Kintsugi-Request-Id`` header, and JSON bodies for every error the app
# itself produces.  Platform errors (proxy limits, timeouts) never reach this
# code; the browser console logs those from the response headers instead.
logger = logging.getLogger("kintsugi.web")
if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    )
    logger.addHandler(_handler)
logger.setLevel(os.getenv("KINTSUGI_LOG_LEVEL", "INFO").upper())
logger.propagate = False


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "-")


def _error_payload(
    request: Request, status: int, detail, error_type: str
) -> JSONResponse:
    return JSONResponse(
        {
            "detail": detail,
            "error_type": error_type,
            "status": status,
            "path": request.url.path,
            "request_id": _request_id(request),
        },
        status_code=status,
        headers={"X-Kintsugi-Request-Id": _request_id(request)},
    )


@app.middleware("http")
async def _log_requests(request: Request, call_next):
    request_id = uuid.uuid4().hex[:12]
    request.state.request_id = request_id
    started = time.perf_counter()
    is_api = request.url.path.startswith("/api/")
    if is_api:
        logger.info(
            "[%s] -> %s %s content-type=%s content-length=%s",
            request_id,
            request.method,
            request.url.path,
            request.headers.get("content-type", "-"),
            request.headers.get("content-length", "-"),
        )
    try:
        response = await call_next(request)
    except Exception as exc:  # pragma: no cover - last-resort boundary
        logger.error(
            "[%s] unhandled %s on %s %s: %s\n%s",
            request_id,
            type(exc).__name__,
            request.method,
            request.url.path,
            exc,
            traceback.format_exc(),
        )
        return _error_payload(
            request, 500, f"{type(exc).__name__}: {exc}", type(exc).__name__
        )
    response.headers["X-Kintsugi-Request-Id"] = request_id
    if is_api:
        logger.info(
            "[%s] <- %s %s status=%s %.0f ms",
            request_id,
            request.method,
            request.url.path,
            response.status_code,
            (time.perf_counter() - started) * 1000.0,
        )
    return response


@app.exception_handler(StarletteHTTPException)
async def _http_exception_handler(request: Request, exc: StarletteHTTPException):
    logger.warning(
        "[%s] HTTP %s on %s: %s",
        _request_id(request),
        exc.status_code,
        request.url.path,
        exc.detail,
    )
    return _error_payload(request, exc.status_code, exc.detail, "HTTPException")


@app.exception_handler(RequestValidationError)
async def _validation_exception_handler(
    request: Request, exc: RequestValidationError
):
    logger.warning(
        "[%s] request validation failed on %s: %s",
        _request_id(request),
        request.url.path,
        exc.errors(),
    )
    return _error_payload(
        request, 422, jsonable_errors(exc), "RequestValidationError"
    )


def jsonable_errors(exc: RequestValidationError) -> list:
    """Strip non-serialisable context (e.g. raw upload bytes) from errors."""
    cleaned = []
    for error in exc.errors():
        cleaned.append(
            {
                key: (value if key in ("loc", "msg", "type") else str(value)[:200])
                for key, value in error.items()
                if key != "input" or not isinstance(value, (bytes, bytearray))
            }
        )
    return cleaned


@app.exception_handler(Exception)
async def _unhandled_exception_handler(request: Request, exc: Exception):
    logger.error(
        "[%s] unhandled %s on %s: %s\n%s",
        _request_id(request),
        type(exc).__name__,
        request.url.path,
        exc,
        "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)),
    )
    return _error_payload(
        request, 500, f"{type(exc).__name__}: {exc}", type(exc).__name__
    )

app.mount("/outputs", StaticFiles(directory=str(OUTPUT_DIR)), name="outputs")
app.mount("/presets", StaticFiles(directory=str(PRESET_DIR)), name="presets")


@app.get("/api/presets")
def api_presets() -> JSONResponse:
    return JSONResponse({"presets": ensure_presets(PRESET_DIR)})


@app.get("/api/health")
def api_health() -> dict:
    return {"status": "ok", "kernel": "Manifold3D"}


def _job_limits() -> tuple[float, int]:
    ttl = float(os.getenv("KINTSUGI_JOB_TTL_S", "3600"))
    max_jobs = max(1, int(os.getenv("KINTSUGI_MAX_JOBS", "50")))
    return ttl, max_jobs


def _prune_jobs() -> None:
    """Delete expired job directories and keep only the newest max_jobs."""
    if not OUTPUT_DIR.exists():
        return
    ttl, max_jobs = _job_limits()
    now = time.time()
    jobs = [path for path in OUTPUT_DIR.iterdir() if path.is_dir()]
    for path in jobs:
        try:
            age = now - path.stat().st_mtime
        except OSError:
            continue
        if age > ttl:
            shutil.rmtree(path, ignore_errors=True)
    jobs = [path for path in OUTPUT_DIR.iterdir() if path.is_dir()]
    jobs.sort(key=lambda path: path.stat().st_mtime)
    while len(jobs) > max_jobs:
        shutil.rmtree(jobs.pop(0), ignore_errors=True)


def _save_upload(source, destination: Path) -> int:
    """Stream an upload to disk and return the number of bytes written."""
    total = 0
    with destination.open("wb") as handle:
        while True:
            chunk = source.read(1024 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > MAX_UPLOAD_BYTES:
                handle.close()
                destination.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=413,
                    detail=(
                        f"Upload exceeds the {MAX_UPLOAD_BYTES // (1024 * 1024)} "
                        "MB limit"
                    ),
                )
            handle.write(chunk)
    return total


def _resolve_input(
    job_dir: Path,
    file: UploadFile | None,
    preset: str | None,
) -> Path:
    if file is not None and file.filename:
        suffix = Path(file.filename).suffix.lower()
        if suffix not in (".stl", ".obj"):
            raise HTTPException(
                status_code=400,
                detail="Custom models must be .stl or .obj files",
            )
        destination = job_dir / f"input{suffix}"
        _save_upload(file.file, destination)
        return destination

    if preset:
        if preset not in {item["id"] for item in PRESETS}:
            raise HTTPException(status_code=400, detail=f"Unknown preset: {preset}")
        return preset_path(preset, PRESET_DIR)

    raise HTTPException(
        status_code=400,
        detail="Provide either a preset id or an uploaded .stl/.obj file",
    )


@app.post("/api/validate")
def api_validate(request: Request, file: UploadFile = File(...)) -> JSONResponse:
    request_id = _request_id(request)
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded")
    suffix = Path(file.filename).suffix.lower()
    if suffix not in (".stl", ".obj"):
        raise HTTPException(
            status_code=400,
            detail="Custom models must be .stl or .obj files",
        )

    with tempfile.TemporaryDirectory(prefix="kintsugi-validate-") as tmp:
        path = Path(tmp) / f"input{suffix}"
        saved = _save_upload(file.file, path)
        logger.info(
            "[%s] validate upload name=%r content_type=%s bytes=%d",
            request_id,
            file.filename,
            file.content_type,
            saved,
        )
        try:
            validation = kintsugi.validate_and_load_mesh(path, S=0.0)
            mesh, manifold = validation
        except ValueError as exc:
            logger.info("[%s] validate rejected: %s", request_id, exc)
            return JSONResponse(
                {
                    "valid": False,
                    "detail": str(exc),
                    "error_type": type(exc).__name__,
                    "bytes_received": saved,
                    "extents": None,
                    "volume": None,
                    "vertices": None,
                    "wall_thickness_p5": None,
                }
            )
        return JSONResponse(
            {
                "valid": True,
                "detail": "Watertight closed solid",
                "extents": [float(value) for value in mesh.extents],
                "volume": float(manifold.volume()),
                "vertices": int(len(mesh.vertices)),
                "wall_thickness_p5": float(
                    validation.probe.get("wall_thickness_p5", 0.0)
                ),
            }
        )


@app.post("/api/fracture")
def api_fracture(
    request: Request,
    file: UploadFile | None = File(default=None),
    preset: str | None = Form(default=None),
    R: float = Form(default=0.5),
    mode: str = Form(default="vein"),
    seed: int = Form(default=42),
    seam_width: float | None = Form(default=None),
    generator: str = Form(default="growth"),
    through_count: str | None = Form(default=None),
    through_shape: str | None = Form(default=None),
    tilt_deg: str | None = Form(default=None),
    hairline_count: str | None = Form(default=None),
    hairline_reach: str | None = Form(default=None),
    roughness: str | None = Form(default=None),
) -> JSONResponse:
    job_id = uuid.uuid4().hex[:12]
    job_dir = OUTPUT_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    _prune_jobs()
    three_mf = job_dir / "kintsugi_assembly.3mf"
    hybrid_options = {
        key: value
        for key, value in {
            "through_count": through_count,
            "through_shape": through_shape,
            "tilt_deg": tilt_deg,
            "hairline_count": hairline_count,
            "hairline_reach": hairline_reach,
            "roughness": roughness,
        }.items()
        if value is not None
    } or None

    try:
        input_path = _resolve_input(job_dir, file, preset)
        logger.info(
            "[%s] fracture input=%s upload=%r bytes=%d R=%s mode=%s "
            "generator=%s seed=%s seam_width=%s hybrid=%s",
            _request_id(request),
            "upload" if file is not None and file.filename else f"preset:{preset}",
            file.filename if file is not None else None,
            input_path.stat().st_size,
            R,
            mode,
            generator,
            seed,
            seam_width,
            hybrid_options,
        )
        result = kintsugi.generate_kintsugi_mesh(
            input_path,
            job_dir,
            R=R,
            mode=mode,
            seed=seed,
            seam_width=seam_width,
            output_3mf_path=three_mf,
            generator=generator,
            hybrid_options=hybrid_options,
        )
    except ValueError as exc:
        # Remove the half-created job so failed runs do not leak assets.
        shutil.rmtree(job_dir, ignore_errors=True)
        logger.info("[%s] fracture rejected: %s", _request_id(request), exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except HTTPException:
        shutil.rmtree(job_dir, ignore_errors=True)
        raise
    except Exception as exc:  # pragma: no cover - defensive boundary
        shutil.rmtree(job_dir, ignore_errors=True)
        logger.error(
            "[%s] fracture crashed with %s: %s\n%s",
            _request_id(request),
            type(exc).__name__,
            exc,
            traceback.format_exc(),
        )
        raise HTTPException(status_code=500, detail=f"Fracture failed: {exc}") from exc

    downloads = {
        "ceramic_stl": f"/outputs/{job_id}/ceramic_body.stl",
        "gold_stl": (
            f"/outputs/{job_id}/gold_seams.stl"
            if result["gold_path"] is not None
            else None
        ),
        "three_mf": f"/outputs/{job_id}/kintsugi_assembly.3mf",
    }

    seams_omitted = bool(result.get("seams_omitted", False))
    # Seams are only omitted when the gold boolean is degenerate; valid ceramic
    # runs (R < 1.0) must always yield continuous gold.  Do not report a wall
    # thickness threshold here: sub-1.6 mm inputs are rejected before fracture.
    seams_omitted_reason = "gold solid is empty" if seams_omitted else None

    return JSONResponse(
        {
            "job_id": job_id,
            "num_cracks": result["num_cracks"],
            "num_fragments": result.get("num_fragments", 1),
            "seams_omitted": seams_omitted,
            "seams_omitted_reason": seams_omitted_reason,
            "cutter_attempts": result.get("cutter_attempts", 0),
            "cutter_variants": result.get("cutter_variants", 0),
            "guard_evaluations": result.get("guard_evaluations", 0),
            "debris_unmoved": result.get("debris_unmoved", 0),
            "volumes": result["volumes"],
            "triangle_counts": result["triangle_counts"],
            "parameters": result["parameters"],
            "timings": result["timings"],
            "downloads": downloads,
        }
    )


# The static site is mounted last so the API routes above take precedence.
app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Kintsugi Studio 2001 web server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args(argv)

    import uvicorn

    uvicorn.run(app, host=args.host, port=args.port)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
