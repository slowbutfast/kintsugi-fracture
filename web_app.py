#!/usr/bin/env python3
"""FastAPI backend for the Windows XP-themed Kintsugi Studio 2001 GUI."""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import shutil
import socket
import tempfile
import threading
import time
import traceback
import urllib.parse
import urllib.request
import uuid
import webbrowser
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

# Uploads: one limit per deployment, advertised by /api/health and enforced
# while streaming.  Vercel rejects request bodies over 4.5 MB itself, before
# this app runs, so the hosted default sits safely below that (a 4 MiB file
# plus multipart overhead stays under 4.5 MB whichever way "MB" is defined).
ACCEPTED_SUFFIXES = (".stl", ".obj", ".3mf")
DEFAULT_UPLOAD_LIMIT_BYTES = 50 * 1024 * 1024
HOSTED_UPLOAD_LIMIT_BYTES = 4 * 1024 * 1024

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


def _upload_limit(env=None) -> int:
    """Resolve the upload limit in bytes: env override, hosted default, else 50 MiB."""
    env = os.environ if env is None else env
    raw = env.get("KINTSUGI_MAX_UPLOAD_BYTES")
    if raw:
        try:
            value = int(raw)
        except ValueError:
            value = 0
        if value > 0:
            return value
        logger.warning("ignoring invalid KINTSUGI_MAX_UPLOAD_BYTES=%r", raw)
    if env.get("VERCEL"):
        return HOSTED_UPLOAD_LIMIT_BYTES
    return DEFAULT_UPLOAD_LIMIT_BYTES


MAX_UPLOAD_BYTES = _upload_limit()

# ---------------------------------------------------------------------------
# Local-first security: allow the hosted static GUI to talk to loopback only.
# ---------------------------------------------------------------------------
PRODUCTION_ORIGIN = "https://kintsugi-fracture-joeshmo.vercel.app"
PREVIEW_ORIGIN_RE = re.compile(
    r"^https://kintsugi-fracture-[a-zA-Z0-9_-]+-joeshmo\.vercel\.app$"
)
LOOPBACK_HOSTNAMES = {"127.0.0.1", "localhost", "::1"}
UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def _extra_origins() -> set[str]:
    raw = os.getenv("KINTSUGI_ALLOWED_ORIGINS", "")
    return {
        item.strip().rstrip("/").lower()
        for item in raw.split(",")
        if item.strip()
    }


def _extra_hosts() -> set[str]:
    allowed: set[str] = set()
    for name in ("KINTSUGI_ALLOWED_HOSTS", "KINTSUGI_SERVER_HOST"):
        raw = os.getenv(name, "")
        allowed.update(item.strip().lower() for item in raw.split(",") if item.strip())
    return allowed


def _previews_allowed() -> bool:
    """Vercel preview hostnames are first-come-first-served; opt in explicitly."""
    return os.getenv("KINTSUGI_ALLOW_PREVIEWS", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _origin_allowed(origin: str | None) -> bool:
    """True for loopback origins, production, and opted-in preview URLs."""
    if not origin:
        return False
    candidate = origin.strip().rstrip("/")
    try:
        parsed = urllib.parse.urlsplit(candidate)
    except ValueError:
        return False
    if parsed.scheme != "http" and parsed.scheme != "https":
        return False
    if parsed.path or parsed.query or parsed.fragment:
        return False
    hostname = (parsed.hostname or "").lower()
    if parsed.scheme == "http" and hostname in LOOPBACK_HOSTNAMES:
        return True
    normalized = f"{parsed.scheme}://{parsed.netloc.lower()}"
    if normalized == PRODUCTION_ORIGIN:
        return True
    if _previews_allowed() and PREVIEW_ORIGIN_RE.match(normalized):
        return True
    return normalized in _extra_origins()


def _hostname_from_host_header(value: str) -> str:
    raw = value.strip().lower()
    if raw.startswith("["):
        end = raw.find("]")
        return raw[1:end] if end > 1 else ""
    if raw.count(":") == 1:
        host, _, port = raw.partition(":")
        if port and not port.isdigit():
            return ""
        return host
    return raw


def _host_allowed(host_header: str | None) -> bool:
    """DNS-rebinding defense: only loopback Host values (or --host) pass."""
    if not host_header:
        return False
    hostname = _hostname_from_host_header(host_header)
    return hostname in LOOPBACK_HOSTNAMES or hostname in _extra_hosts()


def _cors_headers(
    origin: str,
    *,
    preflight: bool = False,
    requested_headers: str | None = None,
) -> list[tuple[bytes, bytes]]:
    headers = [
        (b"access-control-allow-origin", origin.encode("latin-1")),
        (b"vary", b"Origin"),
        (b"access-control-allow-methods", b"GET, POST, OPTIONS"),
    ]
    if preflight:
        headers.append(
            (
                b"access-control-allow-headers",
                (
                    requested_headers
                    or "Content-Type, Accept, X-Requested-With"
                ).encode("latin-1"),
            )
        )
        headers.append((b"access-control-max-age", b"600"))
    # Local Network Access is enforced by the browser's permission prompt plus
    # standard CORS.  The deprecated PNA preflight header is intentionally not
    # required; credentials are never enabled either.
    return headers


async def _send_security_error(send, status: int, detail: str) -> None:
    body = json.dumps(
        {"detail": detail, "error_type": "SecurityError", "status": status}
    ).encode("utf-8")
    headers = [
        (b"content-type", b"application/json; charset=utf-8"),
        (b"content-length", str(len(body)).encode("ascii")),
        (b"vary", b"Origin"),
    ]
    await send({"type": "http.response.start", "status": status, "headers": headers})
    await send({"type": "http.response.body", "body": body})


class SecurityCORSMiddleware:
    """Pure ASGI origin, Host, CORS and Local Network Access enforcement.

    The middleware never wraps or buffers the request body and never uses
    ``BaseHTTPMiddleware``.  Unauthorized state-changing requests and
    ``/outputs/*`` reads are answered with 403 before the inner app (or even
    ``receive``) is called.
    """

    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = {
            key.decode("latin-1").lower(): value.decode("latin-1")
            for key, value in scope.get("headers", [])
        }
        method = scope.get("method", "GET").upper()
        path = scope.get("path", "")
        origin = headers.get("origin")

        if not _host_allowed(headers.get("host")):
            logger.warning(
                "rejected request with untrusted Host header %r on %s %s",
                headers.get("host"),
                method,
                path,
            )
            await _send_security_error(send, 403, "Untrusted Host header")
            return

        allowed_origin = bool(origin) and _origin_allowed(origin)

        if method == "OPTIONS" and origin:
            if not allowed_origin:
                logger.warning(
                    "rejected cross-origin preflight from %r on %s", origin, path
                )
                await _send_security_error(send, 403, "Origin not allowed")
                return
            response_headers = _cors_headers(
                origin,
                preflight=True,
                requested_headers=headers.get("access-control-request-headers"),
            )
            response_headers.append((b"content-length", b"0"))
            await send(
                {
                    "type": "http.response.start",
                    "status": 204,
                    "headers": response_headers,
                }
            )
            await send({"type": "http.response.body", "body": b""})
            return

        # Simple CORS requests (multipart POSTs bypass preflight) and all
        # download reads are checked server-side before touching the body.
        if origin and not allowed_origin:
            if method in UNSAFE_METHODS or path.startswith("/outputs/"):
                logger.warning(
                    "rejected cross-origin %s from %r on %s", method, origin, path
                )
                await _send_security_error(send, 403, "Origin not allowed")
                return

        if not (origin and allowed_origin):
            await self.app(scope, receive, send)
            return

        async def send_with_cors(message) -> None:
            if message["type"] == "http.response.start":
                kept = [
                    (key, value)
                    for key, value in message.get("headers", [])
                    if key.lower()
                    not in (
                        b"access-control-allow-origin",
                        b"access-control-allow-credentials",
                    )
                ]
                kept.extend(_cors_headers(origin))
                message = {**message, "headers": kept}
            await send(message)

        await self.app(scope, receive, send_with_cors)


def _describe_bytes(count: int) -> str:
    if count >= 1024 * 1024:
        return f"{count / (1024 * 1024):.1f} MB"
    return f"{count / 1024:.1f} KB"


def _safe_name(name: str | None) -> str:
    """User-chosen file names are logged as a truncated repr, never raw."""
    return repr(name)[:120]


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


class RequestContextMiddleware:
    """Pure ASGI middleware: request id, response header, arrival/completion logs.

    It deliberately does not build responses.  Unhandled exceptions propagate
    to the ``Exception`` handler below (one place produces the 500 envelope),
    which reads the request id this middleware stored in ``scope["state"]``.
    """

    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        request_id = uuid.uuid4().hex[:12]
        scope.setdefault("state", {})["request_id"] = request_id
        method = scope.get("method", "-")
        path = scope.get("path", "")
        is_api = path.startswith("/api/")
        started = time.perf_counter()
        seen: dict = {}

        if is_api:
            headers = {
                key.decode("latin-1").lower(): value.decode("latin-1")
                for key, value in scope.get("headers", [])
            }
            logger.info(
                "[%s] -> %s %s content-type=%s content-length=%s",
                request_id,
                method,
                path,
                headers.get("content-type", "-"),
                headers.get("content-length", "-"),
            )

        async def send_with_request_id(message) -> None:
            if message["type"] == "http.response.start":
                seen["status"] = message["status"]
                kept = [
                    (key, value)
                    for key, value in message.get("headers", [])
                    if key.lower() != b"x-kintsugi-request-id"
                ]
                kept.append((b"x-kintsugi-request-id", request_id.encode("ascii")))
                message = {**message, "headers": kept}
            await send(message)

        try:
            await self.app(scope, receive, send_with_request_id)
        except Exception:
            if is_api:
                logger.info(
                    "[%s] <- %s %s status=500 (unhandled) %.0f ms",
                    request_id,
                    method,
                    path,
                    (time.perf_counter() - started) * 1000.0,
                )
            raise
        if is_api:
            logger.info(
                "[%s] <- %s %s status=%s %.0f ms",
                request_id,
                method,
                path,
                seen.get("status", "-"),
                (time.perf_counter() - started) * 1000.0,
            )


app.add_middleware(RequestContextMiddleware)
# Outermost user middleware: reject untrusted Host/Origin before diagnostics or
# any body parsing.  Starlette inserts at position 0, so the last addition wraps
# RequestContextMiddleware.
app.add_middleware(SecurityCORSMiddleware)


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
        jsonable_errors(exc),
    )
    return _error_payload(
        request, 422, jsonable_errors(exc), "RequestValidationError"
    )


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


@app.get("/presets/index.json", include_in_schema=False)
def static_presets_manifest() -> JSONResponse:
    """Serve the static preset manifest in front of the preset STL mount.

    The hosted CDN uses the same file; exposing it locally keeps the viewer's
    disconnected fallback working when the API is unavailable.
    """
    manifest = STATIC_DIR / "presets" / "index.json"
    try:
        return JSONResponse(json.loads(manifest.read_text(encoding="utf-8")))
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=404, detail="Static preset manifest not found"
        ) from exc


app.mount("/presets", StaticFiles(directory=str(PRESET_DIR)), name="presets")


@app.get("/api/presets")
def api_presets() -> JSONResponse:
    return JSONResponse({"presets": ensure_presets(PRESET_DIR)})


@app.get("/api/health")
def api_health() -> dict:
    return {
        "status": "ok",
        "service": "kintsugi-studio",
        "api_version": "1.0",
        "kernel": "Manifold3D",
        "max_upload_bytes": MAX_UPLOAD_BYTES,
        "accepted_formats": list(ACCEPTED_SUFFIXES),
    }


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
                        "Upload exceeds the "
                        f"{_describe_bytes(MAX_UPLOAD_BYTES)} limit for this "
                        "deployment"
                    ),
                )
            handle.write(chunk)
    return total


def _upload_suffix(filename: str) -> str:
    """Return the lower-case suffix of an accepted upload or raise HTTP 400."""
    suffix = Path(filename).suffix.lower()
    if suffix not in ACCEPTED_SUFFIXES:
        raise HTTPException(
            status_code=400,
            detail=(
                "Custom models must be one of: "
                + ", ".join(ACCEPTED_SUFFIXES)
            ),
        )
    return suffix


def _resolve_input(
    job_dir: Path,
    file: UploadFile | None,
    preset: str | None,
) -> Path:
    if file is not None and file.filename:
        suffix = _upload_suffix(file.filename)
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
    suffix = _upload_suffix(file.filename)

    with tempfile.TemporaryDirectory(prefix="kintsugi-validate-") as tmp:
        path = Path(tmp) / f"input{suffix}"
        saved = _save_upload(file.file, path)
        logger.info(
            "[%s] validate upload name=%s content_type=%s bytes=%d",
            request_id,
            _safe_name(file.filename),
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
            "[%s] fracture input=%s upload=%s content_type=%s bytes=%d R=%s "
            "mode=%s generator=%s seed=%s seam_width=%s hybrid=%s",
            _request_id(request),
            "upload" if file is not None and file.filename else f"preset:{preset}",
            _safe_name(file.filename if file is not None else None),
            file.content_type if file is not None else None,
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


def _is_loopback_host(host: str) -> bool:
    return host.strip().lower().strip("[]") in LOOPBACK_HOSTNAMES


def _connect_host(host: str) -> str:
    """Use 127.0.0.1 for probing unless an IPv6 loopback was requested."""
    return "::1" if host.strip().lower().strip("[]") == "::1" else "127.0.0.1"


def _http_url(host: str, port: int) -> str:
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"
    return f"http://{host}:{port}"


def _probe_health(port: int, host: str = "127.0.0.1", timeout: float = 0.5):
    """Return /api/health JSON when a Kintsugi Studio instance owns the port."""
    url = f"{_http_url(host, port)}/api/health"
    # Loopback probes must never be routed through an HTTP proxy.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(url, timeout=timeout) as response:
            if response.status != 200:
                return None
            payload = json.loads(response.read().decode("utf-8"))
    except Exception:  # noqa: BLE001 - any failure simply means "not ours"
        return None
    if isinstance(payload, dict) and payload.get("service") == "kintsugi-studio":
        return payload
    return None


def _port_available(host: str, port: int) -> bool:
    """Bind-probe a port so an unrelated listener is never mistaken for us."""
    family = socket.AF_INET6 if ":" in host else socket.AF_INET
    with socket.socket(family, socket.SOCK_STREAM) as sock:
        try:
            sock.bind((host, port))
        except OSError:
            return False
    return True


def _open_when_ready(url: str, timeout: float = 15.0) -> None:
    parsed = urllib.parse.urlsplit(url)
    port = parsed.port or 8000
    host = parsed.hostname or "127.0.0.1"
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if _probe_health(port, host=host, timeout=0.5):
            webbrowser.open(url)
            return
        time.sleep(0.1)
    logger.warning("server at %s did not become ready; open it manually", url)


def studio(argv: list[str] | None = None) -> int:
    """One-command local launcher: reuse, probe 8000-8009, then serve loopback."""
    parser = argparse.ArgumentParser(
        prog="kintsugi-studio",
        description="Launch Kintsugi Studio 2001 on loopback and open the browser",
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--no-open", action="store_true", help="do not open a browser")
    parser.add_argument(
        "--allow-previews",
        action="store_true",
        help="trust Vercel preview origins matching this project's pattern",
    )
    parser.add_argument(
        "--log-level", default=os.getenv("KINTSUGI_LOG_LEVEL", "info").lower()
    )
    args = parser.parse_args(argv)

    loopback = _is_loopback_host(args.host)
    if not loopback:
        logger.warning(
            "SECURITY WARNING: --host %s exposes unauthenticated Kintsugi "
            "Studio endpoints to the local network. Use 127.0.0.1 unless you "
            "intend to share this instance.",
            args.host,
        )
    if args.allow_previews:
        os.environ["KINTSUGI_ALLOW_PREVIEWS"] = "1"
        logger.warning(
            "SECURITY NOTICE: trusting Vercel preview origins matching %s. "
            "Preview hostnames are first-come-first-served; use only while "
            "reviewing a deployment.",
            PREVIEW_ORIGIN_RE.pattern,
        )
    os.environ["KINTSUGI_SERVER_HOST"] = args.host

    probe_host = _connect_host(args.host)
    start_port = max(1, int(args.port))
    candidates = list(range(start_port, min(start_port + 9, 65535) + 1))

    chosen = None
    for port in candidates:
        health = _probe_health(port, host=probe_host, timeout=0.5)
        if health:
            url = _http_url(probe_host, port)
            logger.info(
                "Kintsugi Studio is already running at %s (api_version=%s); reusing it",
                url,
                health.get("api_version", "unknown"),
            )
            if not args.no_open:
                webbrowser.open(url)
            return 0
        if _port_available(args.host, port):
            chosen = port
            break

    if chosen is None:
        logger.error(
            "no free port in %s-%s; stop the process occupying the range",
            candidates[0],
            candidates[-1],
        )
        return 1

    url = _http_url(probe_host, chosen)
    logger.info("Kintsugi Studio 2001 listening at %s", url)
    if not args.no_open:
        threading.Thread(
            target=_open_when_ready, args=(url,), daemon=True
        ).start()

    import uvicorn

    uvicorn.run(
        app,
        host=args.host,
        port=chosen,
        log_level=args.log_level,
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
