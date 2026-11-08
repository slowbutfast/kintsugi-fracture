"""API integration tests for the retro Kintsugi web GUI backend.

Run with:  .venv/bin/python -m unittest tests.test_web_api -v
"""

from __future__ import annotations

import os
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
        fixtures.write_bowl(cls.bowl)
        fixtures.write_open_bowl(cls.open_bowl)
        fixtures.write_stl(
            fixtures.manifold_to_trimesh(
                sample_models.create_thin_cylinder_fixture()
            ),
            cls.thin,
        )
        cls.bowl_bytes = cls.bowl.read_bytes()
        cls.open_bowl_bytes = cls.open_bowl.read_bytes()
        cls.thin_bytes = cls.thin.read_bytes()
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
        ):
            self.assertIn(token, css, token)

        js_response = self.client.get("/viewer.js")
        self.assertEqual(js_response.status_code, 200, js_response.text)
        js = js_response.text
        for token in ("ResizeObserver", "switchMobileTab", "syncMenuChecks"):
            self.assertIn(token, js, token)

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


if __name__ == "__main__":
    unittest.main()
