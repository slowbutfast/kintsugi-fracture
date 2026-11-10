"""Local-first runtime tests: packaging, ASGI security, launcher, guard timing.

Run with:  ./.venv/bin/python -m unittest tests.test_local_runtime -v
"""

from __future__ import annotations

import asyncio
import re
import tempfile
import tomllib
import unittest
import unittest.mock
from pathlib import Path

import kintsugi
import web_app
from fastapi.testclient import TestClient
from tests import fixtures

ROOT = Path(__file__).resolve().parent.parent
PRODUCTION_ORIGIN = "https://kintsugi-fracture-joeshmo.vercel.app"
PREVIEW_ORIGIN = "https://kintsugi-fracture-abc123-joeshmo.vercel.app"
EVIL_ORIGIN = "https://evil.example"
LOOPBACK_BASE = "http://127.0.0.1:8000"


def _canonical_requirement(spec: str) -> tuple[str, str]:
    """Split a requirement into (normalised name, version specifier)."""
    spec = spec.strip()
    match = re.match(r"^([A-Za-z0-9_.-]+)\s*(.*)$", spec)
    if not match:
        raise AssertionError(f"unparseable requirement: {spec!r}")
    name = match.group(1).lower().replace("_", "-").replace(".", "-")
    return name, re.sub(r"\s+", "", match.group(2))


def _requirements(path: Path) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        name, specifier = _canonical_requirement(line)
        parsed[name] = specifier
    return parsed


def _headers(message) -> dict[str, str]:
    return {
        key.decode("latin-1").lower(): value.decode("latin-1")
        for key, value in message.get("headers", [])
    }


def _scope(method: str, path: str, headers: dict[str, str]) -> dict:
    return {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": path,
        "raw_path": path.encode("ascii"),
        "query_string": b"",
        "root_path": "",
        "headers": [
            (key.lower().encode("latin-1"), value.encode("latin-1"))
            for key, value in headers.items()
        ],
        "client": ("127.0.0.1", 50000),
        "server": ("127.0.0.1", 8000),
        "state": {},
    }


class _Downstream:
    def __init__(self) -> None:
        self.called = False

    async def __call__(self, scope, receive, send) -> None:
        self.called = True
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"{}"})


def _exercise_middleware(method: str, path: str, headers: dict[str, str]) -> dict:
    """Run the security middleware in front of a recording downstream app."""
    middleware = web_app.SecurityCORSMiddleware(_Downstream())
    sent: list[dict] = []
    body_events: list[bool] = []

    async def receive():
        body_events.append(True)
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        sent.append(message)

    asyncio.run(middleware(_scope(method, path, headers), receive, send))
    start = next(item for item in sent if item["type"] == "http.response.start")
    body = b"".join(
        item.get("body", b"")
        for item in sent
        if item["type"] == "http.response.body"
    )
    return {
        "status": start["status"],
        "headers": _headers(start),
        "body": body,
        "downstream_called": middleware.app.called,
        "body_events": body_events,
    }


class PackagingTestCase(unittest.TestCase):
    def test_pyproject_dependencies_match_requirements(self) -> None:
        pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        project = pyproject["project"]
        declared = dict(
            _canonical_requirement(item) for item in project["dependencies"]
        )
        self.assertEqual(declared, _requirements(ROOT / "requirements.txt"))

    def test_console_script_and_modules_are_declared(self) -> None:
        pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        self.assertEqual(
            pyproject["project"]["scripts"]["kintsugi-studio"], "web_app:studio"
        )
        modules = set(pyproject["tool"]["setuptools"]["py-modules"])
        self.assertTrue(
            {"web_app", "kintsugi", "mesh_formats", "sample_models"}.issubset(modules)
        )


class SecurityMiddlewareTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(web_app.app, base_url=LOOPBACK_BASE)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.client.close()

    def test_allowed_production_preflight_has_cors_and_lna_headers(self) -> None:
        response = self.client.options(
            "/api/fracture",
            headers={
                "Origin": PRODUCTION_ORIGIN,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Private-Network": "true",
            },
        )
        self.assertEqual(response.status_code, 204, response.text)
        self.assertEqual(
            response.headers.get("access-control-allow-origin"), PRODUCTION_ORIGIN
        )
        self.assertIn(
            "POST", response.headers.get("access-control-allow-methods", "").split(", ")
        )
        self.assertEqual(
            response.headers.get("access-control-allow-private-network"), "true"
        )
        self.assertIsNone(response.headers.get("access-control-allow-credentials"))
        self.assertIn("Origin", response.headers.get("vary", ""))

    def test_preview_origin_matches_the_documented_pattern(self) -> None:
        response = self.client.options(
            "/api/health",
            headers={
                "Origin": PREVIEW_ORIGIN,
                "Access-Control-Request-Method": "GET",
            },
        )
        self.assertEqual(response.status_code, 204, response.text)
        self.assertEqual(
            response.headers.get("access-control-allow-origin"), PREVIEW_ORIGIN
        )

    def test_evil_origin_preflight_is_rejected_without_cors_headers(self) -> None:
        response = self.client.options(
            "/api/fracture",
            headers={
                "Origin": EVIL_ORIGIN,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Private-Network": "true",
            },
        )
        self.assertEqual(response.status_code, 403, response.text)
        self.assertIsNone(response.headers.get("access-control-allow-origin"))
        self.assertIsNone(response.headers.get("access-control-allow-private-network"))
        self.assertNotIn("access-control-allow-origin", response.headers)

    def test_evil_simple_post_is_rejected_before_the_body_is_read(self) -> None:
        result = _exercise_middleware(
            "POST",
            "/api/fracture",
            {
                "host": "127.0.0.1:8000",
                "origin": EVIL_ORIGIN,
                "content-type": "multipart/form-data; boundary=x",
            },
        )
        self.assertEqual(result["status"], 403)
        self.assertFalse(result["downstream_called"])
        self.assertEqual(result["body_events"], [])

    def test_evil_outputs_read_is_rejected_before_the_body_is_read(self) -> None:
        result = _exercise_middleware(
            "GET",
            "/outputs/job/ceramic_body.stl",
            {"host": "127.0.0.1:8000", "origin": EVIL_ORIGIN},
        )
        self.assertEqual(result["status"], 403)
        self.assertFalse(result["downstream_called"])
        self.assertEqual(result["body_events"], [])

    def test_outputs_read_from_an_allowed_origin_reaches_the_app(self) -> None:
        result = _exercise_middleware(
            "GET",
            "/outputs/job/ceramic_body.stl",
            {"host": "127.0.0.1:8000", "origin": PRODUCTION_ORIGIN},
        )
        self.assertEqual(result["status"], 200)
        self.assertTrue(result["downstream_called"])
        self.assertEqual(
            result["headers"].get("access-control-allow-origin"), PRODUCTION_ORIGIN
        )

    def test_dns_rebinding_host_header_is_rejected(self) -> None:
        response = self.client.get(
            "/api/health", headers={"Host": "attacker.example:8000"}
        )
        self.assertEqual(response.status_code, 403, response.text)

        result = _exercise_middleware(
            "GET",
            "/api/health",
            {"host": "attacker.example:8000"},
        )
        self.assertEqual(result["status"], 403)
        self.assertFalse(result["downstream_called"])

    def test_loopback_host_variants_are_accepted(self) -> None:
        for host in ("127.0.0.1:8000", "localhost:8000", "[::1]:8000"):
            with self.subTest(host=host):
                response = self.client.get("/api/health", headers={"Host": host})
                self.assertEqual(response.status_code, 200, response.text)

    def test_health_advertises_service_and_api_version(self) -> None:
        body = self.client.get("/api/health").json()
        self.assertEqual(body["service"], "kintsugi-studio")
        self.assertEqual(body["api_version"], "1.0")
        self.assertEqual(body["max_upload_bytes"], 50 * 1024 * 1024)
        self.assertEqual(body["accepted_formats"], [".stl", ".obj", ".3mf"])

    def test_no_credentials_header_on_any_cross_origin_response(self) -> None:
        for method, path in (("GET", "/api/health"), ("GET", "/api/presets")):
            with self.subTest(path=path):
                response = self.client.request(
                    method, path, headers={"Origin": PRODUCTION_ORIGIN}
                )
                self.assertIsNone(
                    response.headers.get("access-control-allow-credentials")
                )
                self.assertEqual(
                    response.headers.get("access-control-allow-origin"),
                    PRODUCTION_ORIGIN,
                )

    def test_middleware_is_pure_asgi_not_base_http_middleware(self) -> None:
        from starlette.middleware.base import BaseHTTPMiddleware

        middleware = web_app.SecurityCORSMiddleware(_Downstream())
        self.assertNotIsInstance(middleware, BaseHTTPMiddleware)
        self.assertTrue(callable(middleware.__call__))

    def test_gui_exposes_companion_controls_and_engine_module(self) -> None:
        html = self.client.get("/").text
        for element_id in (
            "engine-status",
            "engine-dot",
            "connect-engine",
            "engine-port-input",
            "engine-link",
        ):
            self.assertIn(f'id="{element_id}"', html, element_id)

        viewer = self.client.get("/viewer.js").text
        for token in ("resolveEngineUrl", "./engine.js", "probeEngine", "connectEngine"):
            self.assertIn(token, viewer, token)

        engine = self.client.get("/engine.js")
        self.assertEqual(engine.status_code, 200)
        for token in ("probeEngine", "ENGINE_PORTS", "presetsFromStaticIndex"):
            self.assertIn(token, engine.text, token)

        css = self.client.get("/xp.css").text
        for token in (".engine-dot", ".engine-connected", ".engine-error"):
            self.assertIn(token, css, token)

        manifest = self.client.get("/presets/index.json")
        self.assertEqual(manifest.status_code, 200, manifest.text)
        self.assertEqual(
            [preset["id"] for preset in manifest.json()], ["tea_bowl", "benchy", "vase"]
        )


class LauncherTestCase(unittest.TestCase):
    def test_existing_instance_is_reused_without_starting_a_server(self) -> None:
        health = {"service": "kintsugi-studio", "api_version": "1.0"}
        with unittest.mock.patch.object(
            web_app, "_probe_health", return_value=health
        ) as probe, unittest.mock.patch("uvicorn.run") as run, unittest.mock.patch(
            "webbrowser.open"
        ) as open_browser:
            code = web_app.studio(["--no-open"])
        self.assertEqual(code, 0)
        run.assert_not_called()
        open_browser.assert_not_called()
        probe.assert_called_with(8000, host="127.0.0.1", timeout=0.5)

    def test_browser_opens_when_reusing_an_instance(self) -> None:
        health = {"service": "kintsugi-studio", "api_version": "1.0"}
        with unittest.mock.patch.object(
            web_app, "_probe_health", return_value=health
        ), unittest.mock.patch("uvicorn.run") as run, unittest.mock.patch(
            "webbrowser.open"
        ) as open_browser:
            code = web_app.studio([])
        self.assertEqual(code, 0)
        run.assert_not_called()
        open_browser.assert_called_once_with("http://127.0.0.1:8000")

    def test_port_collision_probes_forward_and_binds_first_free_port(self) -> None:
        with unittest.mock.patch.object(
            web_app, "_probe_health", return_value=None
        ), unittest.mock.patch.object(
            web_app,
            "_port_available",
            side_effect=lambda host, port: port >= 8003,
        ), unittest.mock.patch("uvicorn.run") as run:
            code = web_app.studio(["--no-open"])
        self.assertEqual(code, 0)
        run.assert_called_once()
        self.assertEqual(run.call_args.kwargs.get("port"), 8003)

    def test_exhausted_port_range_returns_nonzero(self) -> None:
        with unittest.mock.patch.object(
            web_app, "_probe_health", return_value=None
        ), unittest.mock.patch.object(
            web_app, "_port_available", return_value=False
        ), unittest.mock.patch("uvicorn.run") as run:
            code = web_app.studio(["--no-open"])
        self.assertNotEqual(code, 0)
        run.assert_not_called()

    def test_non_loopback_host_logs_a_security_warning(self) -> None:
        with unittest.mock.patch.object(
            web_app, "_probe_health", return_value=None
        ), unittest.mock.patch.object(
            web_app, "_port_available", return_value=True
        ), unittest.mock.patch("uvicorn.run"), self.assertLogs(
            web_app.logger, level="WARNING"
        ) as logs:
            code = web_app.studio(["--host", "0.0.0.0", "--no-open"])
        self.assertEqual(code, 0)
        joined = " ".join(logs.output).lower()
        self.assertIn("0.0.0.0", joined)
        self.assertIn("unauthenticated", joined)


class GuardTimingTestCase(unittest.TestCase):
    def test_guard_timing_is_recorded_on_a_successful_fracture(self) -> None:
        with tempfile.TemporaryDirectory(prefix="kintsugi-guard-") as tmp:
            bowl = Path(tmp) / "bowl.stl"
            fixtures.write_bowl(bowl)
            result = kintsugi.generate_kintsugi_mesh(
                bowl, tmp, R=1.0, mode="ribbon", seed=7
            )
        self.assertIn("guard", result["timings"])
        self.assertIsInstance(result["timings"]["guard"], float)
        self.assertGreaterEqual(result["timings"]["guard"], 0.0)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
