"""API integration tests for the retro Kintsugi web GUI backend.

Run with:  .venv/bin/python -m unittest tests.test_web_api -v
"""

from __future__ import annotations

import os
import re
import tempfile
import unittest
import unittest.mock
from pathlib import Path

from fastapi.testclient import TestClient

import manifold3d as mf

import web_app
import sample_models
from tests import fixtures
from web_app import app


class WebApiTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory(prefix="kintsugi-web-fixtures-")
        cls.bowl = Path(cls._tmp.name) / "bowl.stl"
        cls.open_bowl = Path(cls._tmp.name) / "open_bowl.stl"
        cls.thin = Path(cls._tmp.name) / "thin_cylinder.stl"
        cls.solid = Path(cls._tmp.name) / "solid_cylinder.stl"
        fixtures.write_bowl(cls.bowl)
        fixtures.write_open_bowl(cls.open_bowl)
        fixtures.write_stl(
            fixtures.manifold_to_trimesh(
                sample_models.create_thin_cylinder_fixture()
            ),
            cls.thin,
        )
        fixtures.write_solid_cylinder(cls.solid)
        cls.bowl_bytes = cls.bowl.read_bytes()
        cls.open_bowl_bytes = cls.open_bowl.read_bytes()
        cls.thin_bytes = cls.thin.read_bytes()
        cls.solid_bytes = cls.solid.read_bytes()
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.client.close()
        cls._tmp.cleanup()

    def test_api_presets(self) -> None:
        response = self.client.get("/api/presets")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        presets = body["presets"] if isinstance(body, dict) else body
        ids = {preset["id"] for preset in presets}
        self.assertTrue({"tea_bowl", "benchy", "vase"}.issubset(ids))
        self.assertNotIn("thin_cylinder", ids)
        for preset in presets:
            self.assertTrue(preset["mesh_url"].startswith("/"))

    def test_api_fracture_success(self) -> None:
        response = self.client.post(
            "/api/fracture",
            files={
                "file": (
                    "bowl.stl",
                    self.bowl_bytes,
                    "application/octet-stream",
                )
            },
            data={"R": "0.4", "mode": "ribbon", "seed": "7"},
        )
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()

        self.assertGreater(body["num_cracks"], 0)
        self.assertFalse(body["seams_omitted"])
        self.assertIsNone(body["seams_omitted_reason"])
        self.assertGreater(body["volumes"]["ceramic"], 0.0)
        self.assertGreater(body["volumes"]["gold"], 0.0)
        self.assertIn("guard_evaluations", body)
        self.assertGreaterEqual(body["guard_evaluations"], 1)

        downloads = body["downloads"]
        self.assertIsNotNone(downloads["ceramic_stl"])
        self.assertIsNotNone(downloads["gold_stl"])
        self.assertIsNotNone(downloads["three_mf"])

        for key in ("ceramic_stl", "gold_stl", "three_mf"):
            asset = self.client.get(downloads[key])
            self.assertEqual(asset.status_code, 200, key)
            self.assertGreater(len(asset.content), 0, key)

    def test_api_fracture_empty_gold_pipeline(self) -> None:
        with unittest.mock.patch.object(
            web_app.kintsugi,
            "_build_vein_cutter",
            return_value=mf.Manifold(),
        ):
            response = self.client.post(
                "/api/fracture",
                data={
                    "preset": "tea_bowl",
                    "R": "0.6",
                    "mode": "vein",
                    "seed": "7",
                },
            )
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertTrue(body["seams_omitted"])
        self.assertIsNone(body["downloads"]["gold_stl"])
        self.assertEqual(body["num_cracks"], 0)
        self.assertEqual(body["triangle_counts"]["gold"], 0)
        self.assertAlmostEqual(body["volumes"]["gold"], 0.0)
        self.assertIsNotNone(body["downloads"]["ceramic_stl"])

    def test_api_fracture_defaults_to_vein_growth(self) -> None:
        response = self.client.post(
            "/api/fracture",
            data={"preset": "tea_bowl", "R": "0.5", "seed": "7"},
        )
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body["parameters"]["mode"], "vein")
        self.assertEqual(body["parameters"]["generator"], "growth")

    def test_api_fracture_thin_wall_rejected(self) -> None:
        response = self.client.post(
            "/api/fracture",
            files={
                "file": (
                    "thin_cylinder.stl",
                    self.thin_bytes,
                    "application/octet-stream",
                )
            },
            data={"R": "0.62", "mode": "vein", "seed": "620"},
        )
        self.assertEqual(response.status_code, 400, response.text)
        detail = response.json()["detail"].lower()
        self.assertIn("wall thickness", detail)
        self.assertIn("1.60", detail)

    def test_api_validate_thin_wall_rejected(self) -> None:
        response = self.client.post(
            "/api/validate",
            files={
                "file": (
                    "thin_cylinder.stl",
                    self.thin_bytes,
                    "application/octet-stream",
                )
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertFalse(body["valid"])
        detail = body["detail"].lower()
        self.assertIn("wall thickness", detail)
        self.assertIn("1.60", detail)

    def test_api_fracture_wealthy(self) -> None:
        response = self.client.post(
            "/api/fracture",
            data={"preset": "tea_bowl", "R": "1.0", "mode": "ribbon", "seed": "7"},
        )
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()

        self.assertEqual(body["num_cracks"], 0)
        self.assertFalse(body["seams_omitted"])
        self.assertIsNone(body["seams_omitted_reason"])
        self.assertIn("guard_evaluations", body)
        self.assertEqual(body["guard_evaluations"], 0)
        self.assertIsNone(body["downloads"]["gold_stl"])
        self.assertIsNotNone(body["downloads"]["ceramic_stl"])

        ceramic = self.client.get(body["downloads"]["ceramic_stl"])
        self.assertEqual(ceramic.status_code, 200)
        self.assertGreater(len(ceramic.content), 0)

    def test_api_validate_ok(self) -> None:
        response = self.client.post(
            "/api/validate",
            files={
                "file": (
                    "bowl.stl",
                    self.bowl_bytes,
                    "application/octet-stream",
                )
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertTrue(body["valid"])
        self.assertEqual(len(body["extents"]), 3)
        self.assertGreater(body["volume"], 0.0)
        self.assertGreater(body["vertices"], 0)
        self.assertGreaterEqual(body["wall_thickness_p5"], 1.6)

    def test_api_validate_open_mesh(self) -> None:
        response = self.client.post(
            "/api/validate",
            files={
                "file": (
                    "open_bowl.stl",
                    self.open_bowl_bytes,
                    "application/octet-stream",
                )
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertFalse(body["valid"])
        self.assertIn("closed solid", body["detail"].lower())

    def test_api_upload_too_large(self) -> None:
        too_large = b"x" * (51 * 1024 * 1024)
        response = self.client.post(
            "/api/fracture",
            files={
                "file": (
                    "huge.stl",
                    too_large,
                    "application/octet-stream",
                )
            },
            data={"R": "1.0", "mode": "ribbon", "seed": "7"},
        )
        self.assertEqual(response.status_code, 413, response.text)

    def test_mobile_ui_and_menus_markup_served(self) -> None:
        html_response = self.client.get("/")
        self.assertEqual(html_response.status_code, 200, html_response.text)
        html = html_response.text

        menu_ids = (
            "menu-file",
            "menu-presets",
            "menu-mode",
            "menu-help",
            "menu-upload",
            "menu-fracture",
            "menu-download-ceramic",
            "menu-download-gold",
            "menu-download-3mf",
            "menu-reset-camera",
            "menu-about",
            "mobile-tabs",
            "export-badge",
            "help-dialog",
        )
        for element_id in menu_ids:
            self.assertIn(f'id="{element_id}"', html, element_id)

        for tab in ("model", "fracture", "export"):
            self.assertIn(f'data-tab="{tab}"', html, tab)
            self.assertIn(f'data-tab-panel="{tab}"', html, tab)

        for preserved_id in (
            "preset-select",
            "file-input",
            "generator-select",
            "mode-select",
            "ratio-slider",
            "seed-input",
            "fracture-button",
            "download-ceramic",
            "download-gold",
            "download-3mf",
            "viewport",
            "status-operation",
            "status-mesh",
            "status-kernel",
        ):
            self.assertIn(f'id="{preserved_id}"', html, preserved_id)

        css_response = self.client.get("/xp.css")
        self.assertEqual(css_response.status_code, 200, css_response.text)
        css = css_response.text
        for token in (
            "100dvh",
            ".menu-dropdown",
            ".mobile-tabs",
            "font-size: 16px",
            "order: -1",
            "--ceramic-body: #18181b",
            "--viewport-bg: #f0ede0",
        ):
            self.assertIn(token, css, token)

        js_response = self.client.get("/viewer.js")
        self.assertEqual(js_response.status_code, 200, js_response.text)
        js = js_response.text
        for token in (
            "ResizeObserver",
            "switchMobileTab",
            "syncMenuChecks",
            "0x18181b",
            "0xf0ede0",
        ):
            self.assertIn(token, js, token)

    def test_api_fracture_hybrid_success_and_knob_telemetry(self) -> None:
        response = self.client.post(
            "/api/fracture",
            data={
                "preset": "tea_bowl",
                "R": "0.5",
                "mode": "vein",
                "seed": "42",
                "generator": "hybrid",
                "through_count": "1",
                "through_shape": "wedge",
                "tilt_deg": "25",
                "hairline_count": "3",
                "hairline_reach": "0.5",
                "roughness": "1.2",
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body["parameters"]["generator"], "hybrid")
        self.assertGreater(body["num_cracks"], 0)
        self.assertGreaterEqual(body["num_fragments"], 2)
        hybrid = body["parameters"]["hybrid"]
        self.assertEqual(hybrid["through_count"], 1)
        self.assertEqual(hybrid["through_shape"], "wedge")
        self.assertAlmostEqual(hybrid["tilt_deg"], 25.0)
        self.assertEqual(hybrid["hairline_count"], 3)
        self.assertAlmostEqual(hybrid["hairline_reach"], 0.5)
        self.assertAlmostEqual(hybrid["roughness"], 1.2)
        self.assertGreaterEqual(hybrid["num_through_fragments"], 2)
        self.assertGreaterEqual(hybrid["num_fragments"], 2)
        self.assertIsNotNone(body["downloads"]["ceramic_stl"])
        self.assertIsNotNone(body["downloads"]["gold_stl"])

    def test_api_fracture_hybrid_rejects_knobs_for_other_generator(
        self,
    ) -> None:
        response = self.client.post(
            "/api/fracture",
            data={
                "preset": "tea_bowl",
                "R": "0.5",
                "mode": "vein",
                "seed": "42",
                "generator": "growth",
                "through_count": "2",
            },
        )
        self.assertEqual(response.status_code, 400, response.text)
        self.assertIn("hybrid", response.json()["detail"].lower())

    def test_api_fracture_hybrid_rejects_malformed_integer_knobs(
        self,
    ) -> None:
        for value in ("abc", "2.5"):
            with self.subTest(through_count=value):
                response = self.client.post(
                    "/api/fracture",
                    data={
                        "preset": "tea_bowl",
                        "R": "0.5",
                        "mode": "vein",
                        "seed": "42",
                        "generator": "hybrid",
                        "through_count": value,
                    },
                )
                self.assertEqual(
                    response.status_code, 400, response.text
                )
                self.assertIn(
                    "through_count", response.json()["detail"].lower()
                )

    def test_api_fracture_hybrid_rejects_ribbon_mode(self) -> None:
        response = self.client.post(
            "/api/fracture",
            data={
                "preset": "tea_bowl",
                "R": "0.5",
                "mode": "ribbon",
                "seed": "42",
                "generator": "hybrid",
            },
        )
        self.assertEqual(response.status_code, 400, response.text)
        detail = response.json()["detail"].lower()
        self.assertIn("hybrid", detail)
        self.assertIn("vein", detail)

    def test_api_validate_rejects_solid_body_without_wall(self) -> None:
        response = self.client.post(
            "/api/validate",
            files={
                "file": (
                    "solid_cylinder.stl",
                    self.solid_bytes,
                    "application/octet-stream",
                )
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertFalse(body["valid"])
        self.assertIn("wall", body["detail"].lower())

    def test_web_ui_exposes_hybrid_generator_and_settings(self) -> None:
        html_response = self.client.get("/")
        self.assertEqual(html_response.status_code, 200)
        html = html_response.text
        self.assertIn('value="hybrid"', html)
        self.assertIn('data-generator="hybrid"', html)
        self.assertIn('id="hybrid-settings"', html)
        for control in (
            "hybrid-through-count",
            "hybrid-through-shape",
            "hybrid-tilt-deg",
            "hybrid-hairline-count",
            "hybrid-hairline-reach",
            "hybrid-roughness",
            "hybrid-resolved-note",
        ):
            self.assertIn(f'id="{control}"', html, control)
        self.assertGreaterEqual(html.count('value="auto"'), 6)

        js_response = self.client.get("/viewer.js")
        self.assertEqual(js_response.status_code, 200)
        js = js_response.text
        for token in (
            "hybridSettings",
            "syncHybridSettings",
            "renderHybridResolved",
            "hybrid-through-count",
            "hybrid.auto_through_count",
            "num_fragments",
        ):
            self.assertIn(token, js, token)

        css_response = self.client.get("/xp.css")
        self.assertEqual(css_response.status_code, 200)
        css = css_response.text
        self.assertIn(".hybrid-fieldset", css)
        self.assertIn(".hybrid-grid", css)

    def test_job_retention(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "web"
            output_dir.mkdir(parents=True)
            with unittest.mock.patch.dict(
                os.environ, {"KINTSUGI_MAX_JOBS": "2"}, clear=False
            ), unittest.mock.patch.object(
                web_app, "OUTPUT_DIR", output_dir
            ):
                for _ in range(3):
                    response = self.client.post(
                        "/api/fracture",
                        data={
                            "preset": "tea_bowl",
                            "R": "1.0",
                            "mode": "ribbon",
                            "seed": "7",
                        },
                    )
                    self.assertEqual(response.status_code, 200, response.text)
                job_dirs = [path for path in output_dir.iterdir() if path.is_dir()]
                self.assertEqual(len(job_dirs), 2)


_REQUEST_ID = re.compile(r"^[0-9a-f]{12}$")
_ENVELOPE_KEYS = {"detail", "error_type", "status", "path", "request_id"}


class WebDiagnosticsTestCase(unittest.TestCase):
    """Request ids, JSON error envelopes and logging (upload-diagnostics-and-3mf)."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory(prefix="kintsugi-web-diag-")
        cls.bowl = Path(cls._tmp.name) / "bowl.stl"
        fixtures.write_bowl(cls.bowl)
        cls.bowl_bytes = cls.bowl.read_bytes()
        cls.client = TestClient(app)
        # Unhandled exceptions must come back as JSON responses, not be re-raised.
        cls.quiet_client = TestClient(app, raise_server_exceptions=False)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.client.close()
        cls.quiet_client.close()
        cls._tmp.cleanup()

    def assertEnvelope(self, response, status: int, path: str) -> dict:
        self.assertEqual(response.status_code, status, response.text)
        self.assertIn("application/json", response.headers["content-type"])
        body = response.json()
        self.assertTrue(_ENVELOPE_KEYS.issubset(body), body)
        self.assertEqual(body["status"], status)
        self.assertEqual(body["path"], path)
        self.assertRegex(body["request_id"], _REQUEST_ID)
        self.assertEqual(body["request_id"], response.headers["X-Kintsugi-Request-Id"])
        return body

    # -- request id ---------------------------------------------------------
    def test_every_response_carries_a_request_id(self) -> None:
        for path in ("/api/health", "/api/presets", "/"):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                self.assertRegex(
                    response.headers["X-Kintsugi-Request-Id"], _REQUEST_ID
                )

    def test_request_ids_are_unique_per_request(self) -> None:
        ids = {
            self.client.get("/api/health").headers["X-Kintsugi-Request-Id"]
            for _ in range(5)
        }
        self.assertEqual(len(ids), 5)

    # -- error envelope ---------------------------------------------------------
    def test_unknown_preset_returns_envelope(self) -> None:
        response = self.client.post(
            "/api/fracture", data={"preset": "no_such_preset", "R": "0.5"}
        )
        body = self.assertEnvelope(response, 400, "/api/fracture")
        self.assertIn("no_such_preset", body["detail"])
        self.assertEqual(body["error_type"], "HTTPException")

    def test_unknown_path_returns_envelope(self) -> None:
        response = self.client.get("/api/definitely-not-a-route")
        self.assertEnvelope(response, 404, "/api/definitely-not-a-route")

    def test_oversized_upload_returns_413_envelope(self) -> None:
        with unittest.mock.patch.object(web_app, "MAX_UPLOAD_BYTES", 1000):
            response = self.client.post(
                "/api/validate",
                files={"file": ("big.stl", b"x" * 2000, "application/octet-stream")},
            )
        body = self.assertEnvelope(response, 413, "/api/validate")
        self.assertIn("limit", body["detail"].lower())

    def test_request_validation_error_does_not_echo_upload_bytes(self) -> None:
        response = self.client.post(
            "/api/fracture",
            files={"file": ("x.stl", b"BINARYMARKER" * 40, "application/octet-stream")},
            data={"R": "not-a-number"},
        )
        body = self.assertEnvelope(response, 422, "/api/fracture")
        self.assertEqual(body["error_type"], "RequestValidationError")
        self.assertNotIn("BINARYMARKER", response.text)
        self.assertIn("R", response.text)

    def test_missing_file_field_returns_envelope(self) -> None:
        response = self.client.post("/api/validate", data={"unrelated": "1"})
        body = self.assertEnvelope(response, 422, "/api/validate")
        self.assertIn("file", response.text)
        self.assertIsInstance(body["detail"], list)

    def test_unhandled_exception_returns_json_500_and_logs_traceback(self) -> None:
        with unittest.mock.patch.object(
            web_app.kintsugi,
            "validate_and_load_mesh",
            side_effect=RuntimeError("boom"),
        ), self.assertLogs("kintsugi.web", level="ERROR") as logs:
            response = self.quiet_client.post(
                "/api/validate",
                files={"file": ("bowl.stl", self.bowl_bytes, "application/octet-stream")},
            )
        body = self.assertEnvelope(response, 500, "/api/validate")
        self.assertEqual(body["error_type"], "RuntimeError")
        self.assertIn("boom", body["detail"])
        joined = "\n".join(logs.output)
        self.assertIn(body["request_id"], joined)
        self.assertIn("Traceback", joined)

    # -- logging ----------------------------------------------------------------
    def test_validate_logs_arrival_upload_and_completion(self) -> None:
        with self.assertLogs("kintsugi.web", level="INFO") as logs:
            response = self.client.post(
                "/api/validate",
                files={"file": ("bowl.stl", self.bowl_bytes, "application/octet-stream")},
            )
        self.assertEqual(response.status_code, 200, response.text)
        request_id = response.headers["X-Kintsugi-Request-Id"]
        mine = [line for line in logs.output if request_id in line]
        self.assertTrue(any("-> POST /api/validate" in line for line in mine), mine)
        self.assertTrue(
            any("<- POST /api/validate" in line and "status=200" in line for line in mine),
            mine,
        )
        upload = [line for line in mine if "bowl.stl" in line]
        self.assertTrue(upload, mine)
        self.assertIn(str(len(self.bowl_bytes)), upload[0])

    def test_rejected_validation_logs_the_reason(self) -> None:
        with self.assertLogs("kintsugi.web", level="INFO") as logs:
            response = self.client.post(
                "/api/validate",
                files={"file": ("junk.stl", b"not a mesh at all", "application/octet-stream")},
            )
        self.assertEqual(response.status_code, 200, response.text)
        request_id = response.headers["X-Kintsugi-Request-Id"]
        self.assertTrue(
            any(request_id in line and "rejected" in line for line in logs.output),
            logs.output,
        )


class WebUploadLimitAndFormatsTestCase(unittest.TestCase):
    """Advertised upload limit and the .3mf format over HTTP."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory(prefix="kintsugi-web-3mf-")
        root = Path(cls._tmp.name)
        cls.bowl_3mf = root / "bowl.3mf"
        fixtures.write_bowl_3mf(cls.bowl_3mf)
        cls.bowl_3mf_bytes = cls.bowl_3mf.read_bytes()
        cls.two_items = root / "two.3mf"
        box = fixtures.manifold_to_trimesh(fixtures.bowl_manifold())
        fixtures.build_3mf(
            cls.two_items,
            objects=[fixtures.mesh_object(1, box), fixtures.mesh_object(2, box)],
            build_items=[{"objectid": 1}, {"objectid": 2}],
        )
        cls.two_items_bytes = cls.two_items.read_bytes()
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.client.close()
        cls._tmp.cleanup()

    # -- health and limit resolution -----------------------------------------------
    def test_health_reports_limit_and_formats(self) -> None:
        body = self.client.get("/api/health").json()
        self.assertEqual(body["status"], "ok")
        self.assertEqual(body["max_upload_bytes"], web_app.MAX_UPLOAD_BYTES)
        self.assertEqual(body["accepted_formats"], [".stl", ".obj", ".3mf"])

    def test_upload_limit_resolution_order(self) -> None:
        self.assertEqual(web_app._upload_limit({}), 50 * 1024 * 1024)
        self.assertEqual(web_app._upload_limit({"VERCEL": "1"}), 4 * 1024 * 1024)
        self.assertEqual(
            web_app._upload_limit({"KINTSUGI_MAX_UPLOAD_BYTES": "1234"}), 1234
        )
        self.assertEqual(
            web_app._upload_limit(
                {"VERCEL": "1", "KINTSUGI_MAX_UPLOAD_BYTES": "9999999"}
            ),
            9999999,
        )

    def test_reported_and_enforced_limit_follow_the_constant(self) -> None:
        with unittest.mock.patch.object(web_app, "MAX_UPLOAD_BYTES", 2000):
            self.assertEqual(
                self.client.get("/api/health").json()["max_upload_bytes"], 2000
            )
            over = self.client.post(
                "/api/validate",
                files={"file": ("a.stl", b"x" * 3000, "application/octet-stream")},
            )
            under = self.client.post(
                "/api/validate",
                files={"file": ("b.stl", b"x" * 1500, "application/octet-stream")},
            )
        self.assertEqual(over.status_code, 413, over.text)
        self.assertEqual(under.status_code, 200, under.text)
        self.assertFalse(under.json()["valid"])

    # -- 3MF over the API -----------------------------------------------------------
    def test_validate_accepts_a_3mf_vessel(self) -> None:
        response = self.client.post(
            "/api/validate",
            files={"file": ("bowl.3mf", self.bowl_3mf_bytes, "model/3mf")},
        )
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertTrue(body["valid"], body)
        self.assertGreaterEqual(body["wall_thickness_p5"], 1.6)

    def test_validate_reports_3mf_structure_rejections(self) -> None:
        response = self.client.post(
            "/api/validate",
            files={"file": ("two.3mf", self.two_items_bytes, "model/3mf")},
        )
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertFalse(body["valid"])
        self.assertIn("single-object", body["detail"].lower())

    def test_fracture_accepts_a_3mf_upload(self) -> None:
        response = self.client.post(
            "/api/fracture",
            files={"file": ("bowl.3mf", self.bowl_3mf_bytes, "model/3mf")},
            data={"R": "0.5", "mode": "vein", "seed": "7"},
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertGreater(response.json()["num_cracks"], 0)

    def test_ui_advertises_3mf_and_serves_the_viewer_modules(self) -> None:
        index = self.client.get("/").text
        self.assertIn('accept=".stl,.obj,.3mf"', index)
        self.assertIn('id="upload-subtitle"', index)
        self.assertIn("Upload a custom STL, OBJ or 3MF", index)
        for module in ("/threemf.js", "/upload.js"):
            with self.subTest(module=module):
                response = self.client.get(module)
                self.assertEqual(response.status_code, 200)
                self.assertIn("javascript", response.headers["content-type"])
        viewer = self.client.get("/viewer.js").text
        self.assertIn('from "./threemf.js"', viewer)
        self.assertIn('from "./upload.js"', viewer)
        self.assertIn("three/addons/libs/fflate.module.js", viewer)
        self.assertIn("requestJson(", viewer)

    def test_unsupported_suffix_lists_the_accepted_formats(self) -> None:
        for route, extra in (("/api/validate", {}), ("/api/fracture", {"R": "0.5"})):
            with self.subTest(route=route):
                response = self.client.post(
                    route,
                    files={"file": ("model.ply", b"ply\n", "application/octet-stream")},
                    data=extra,
                )
                self.assertEqual(response.status_code, 400, response.text)
                detail = response.json()["detail"]
                for suffix in (".stl", ".obj", ".3mf"):
                    self.assertIn(suffix, detail)


if __name__ == "__main__":
    unittest.main()
