"""TDD tests for the opt-in shard-plane fracture generator.

Run with:  .venv/bin/python -m unittest tests.test_crack_shard -v
"""

from __future__ import annotations

import tempfile
import unittest
import unittest.mock
from pathlib import Path

import numpy as np
import trimesh

from tests import fixtures


def _bad_edge_count(mesh: trimesh.Trimesh) -> int:
    """Number of edges used by anything other than exactly two faces."""
    if len(mesh.edges_sorted) == 0:
        return 0
    rows = np.sort(np.asarray(mesh.edges_sorted, dtype=np.int64), axis=1)
    _, counts = np.unique(rows, axis=0, return_counts=True)
    return int(np.count_nonzero(counts != 2))


def _is_closed(points: np.ndarray, period: float) -> bool:
    import kintsugi

    return (
        len(points) >= 4
        and kintsugi._periodic_distance(points[0], points[-1], period) <= 1e-6
    )


class CrackShardTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        import kintsugi

        cls.kintsugi = kintsugi
        cls._tmp = tempfile.TemporaryDirectory(prefix="kintsugi-shard-")
        cls.root = Path(__file__).resolve().parent.parent
        cls.bowl = Path(cls._tmp.name) / "bowl.stl"
        fixtures.write_bowl(cls.bowl)
        cls.validation = kintsugi.validate_and_load_mesh(cls.bowl, S=0.0)
        cls.tea_bowl_preset = cls.root / "presets" / "tea_bowl.stl"
        cls.vase_preset = cls.root / "presets" / "vase.stl"

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def _params(self, severity: float) -> dict:
        return self.kintsugi.compute_parameters(
            severity,
            self.validation.mesh,
            manifold=self.validation.manifold,
            probe=self.validation.probe,
        )

    def _narrow_wall_params(self, severity: float) -> dict:
        params = self._params(severity)
        W = float(params["W"])
        params["wall_z_min"] = 20.0
        params["wall_z_max"] = 27.0
        params["z_wall_lo"] = 20.0 + 0.5 * W
        params["z_wall_hi"] = 27.0 + W
        return params

    # -- Task 1.1 -----------------------------------------------------------
    def test_open_wedge_seam_exact_truncation_and_rim_landing(self) -> None:
        kintsugi = self.kintsugi
        params = self._params(0.3)
        W = float(params["W"])
        period = float(params["period"])
        wall_z_max = float(params["wall_z_max"])
        lo = float(params["wall_z_min"]) + 0.5 * W
        hi = wall_z_max + 0.35 * W

        wedge = None
        for seed in range(40):
            candidate = kintsugi.generate_shard_crack_paths(
                dict(params), np.random.default_rng(seed)
            )
            if len(candidate) != 1:
                continue
            if not _is_closed(candidate[0], period):
                wedge = np.asarray(candidate[0], dtype=np.float64)
                break
        self.assertIsNotNone(wedge, "generator never produced an open wedge")

        # Raw rim endpoints lie at the upper truncation bound, i.e. no more
        # than 0.35 W above the measured rim.
        for endpoint in (wedge[0], wedge[-1]):
            self.assertGreaterEqual(float(endpoint[1]), wall_z_max - 1e-9)
            self.assertLessEqual(
                float(endpoint[1]) - wall_z_max, 0.35 * W + 1e-9
            )

        # Exact truncation must not leave two consecutive vertices parked on
        # the same horizontal truncation bound (the np.clip shelf defect).
        for first, second in zip(wedge[:-1], wedge[1:]):
            for bound in (lo, hi):
                self.assertFalse(
                    abs(float(first[1]) - bound) <= 1e-6
                    and abs(float(second[1]) - bound) <= 1e-6,
                    "flat-run shelf on truncation bound",
                )

        projected, _, _ = kintsugi.project_crack_paths(
            [wedge],
            self.validation.manifold,
            params,
            self.validation.mesh,
        )
        self.assertTrue(projected)
        first_z = float(projected[0][0]["p"][2])
        last_z = float(projected[-1][-1]["p"][2])
        for z in (first_z, last_z):
            self.assertGreaterEqual(
                z,
                wall_z_max - 0.5 * W - 1e-6,
                "projected wedge endpoint did not land on the upper rim lip",
            )

    # -- Task 1.2 -----------------------------------------------------------
    def test_closed_loop_drift_bridge_closure_and_cyclic_clearance(
        self,
    ) -> None:
        kintsugi = self.kintsugi
        params = self._params(0.3)
        W = float(params["W"])
        period = float(params["period"])
        lo = float(params["wall_z_min"]) + 0.6 * W
        hi = float(params["wall_z_max"]) - 0.6 * W
        r_clear = W + 0.8

        loop = None
        loop_params = None
        for seed in range(60):
            candidate_params = dict(params)
            candidate = kintsugi.generate_shard_crack_paths(
                candidate_params, np.random.default_rng(seed)
            )
            for path in candidate:
                points = np.asarray(path, dtype=np.float64)
                if _is_closed(points, period):
                    loop = points
                    loop_params = candidate_params
                    break
            if loop is not None:
                break
        self.assertIsNotNone(loop, "generator never produced a closed loop")
        assert loop is not None and loop_params is not None

        self.assertLessEqual(
            kintsugi._periodic_distance(loop[0], loop[-1], period), 1e-6
        )
        self.assertGreaterEqual(float(np.min(loop[:, 1])), lo - 1e-9)
        self.assertLessEqual(float(np.max(loop[:, 1])), hi + 1e-9)

        stats = kintsugi.analyze_growth_paths([loop], loop_params)
        self.assertEqual(stats["crossings"], 0)
        self.assertEqual(stats["clearance_violations"], 0)
        self.assertIsNotNone(stats["min_clearance"])
        self.assertGreaterEqual(float(stats["min_clearance"]), r_clear - 1e-6)

        # A wall band too short for a 5-degree tilt must fall back to a wedge
        # rather than degenerating into a horizontal ring.
        narrow = self._narrow_wall_params(0.3)
        saw_open = 0
        for seed in range(30):
            paths = kintsugi.generate_shard_crack_paths(
                dict(narrow), np.random.default_rng(seed)
            )
            for path in paths:
                points = np.asarray(path, dtype=np.float64)
                self.assertFalse(
                    _is_closed(points, period),
                    "narrow wall produced a closed loop instead of a wedge "
                    "fallback",
                )
                saw_open += 1
        self.assertGreater(saw_open, 0)

    # -- Task 1.3 -----------------------------------------------------------
    def test_two_seam_verified_intersection_and_fallback(self) -> None:
        kintsugi = self.kintsugi
        params = self._params(0.8)
        W = float(params["W"])
        period = float(params["period"])
        band_lo = float(params["wall_z_min"]) + W
        band_hi = float(params["wall_z_max"]) - W
        r_clear = W + 0.8

        found = 0
        for seed in range(40):
            candidate_params = dict(params)
            paths = kintsugi.generate_shard_crack_paths(
                candidate_params, np.random.default_rng(seed)
            )
            if len(paths) != 2:
                continue
            found += 1
            seam1 = np.asarray(paths[0], dtype=np.float64)
            seam2 = np.asarray(paths[1], dtype=np.float64)
            endpoint = seam2[-1]

            matches = [
                index
                for index, point in enumerate(seam1)
                if kintsugi._periodic_distance(point, endpoint, period) <= 1e-6
            ]
            self.assertTrue(
                matches,
                f"seed={seed}: Seam 2 endpoint has no shared vertex on Seam 1",
            )
            index = matches[0]
            self.assertGreaterEqual(float(endpoint[1]), band_lo - 1e-6)
            self.assertLessEqual(float(endpoint[1]), band_hi + 1e-6)

            tangent_index = index if index < len(seam1) - 1 else index - 1
            tangent = seam1[tangent_index + 1] - seam1[tangent_index]
            arrival = kintsugi._acute_angle_deg(
                seam2[-1] - seam2[-2], tangent
            )
            self.assertGreaterEqual(arrival, 30.0 - 1e-6)

            records = candidate_params.get("_growth_junctions") or []
            self.assertTrue(records, f"seed={seed}: no junction metadata")
            self.assertTrue(
                any(
                    record.get("kind") == "T"
                    and int(record.get("path", -1)) == 1
                    and kintsugi._periodic_distance(
                        np.asarray(record["point"], dtype=np.float64),
                        endpoint,
                        period,
                    )
                    <= 1e-6
                    for record in records
                ),
                f"seed={seed}: T-junction metadata missing or mislocated",
            )

            stats = kintsugi.analyze_growth_paths(paths, candidate_params)
            self.assertEqual(stats["crossings"], 0, f"seed={seed}")
            self.assertEqual(stats["clearance_violations"], 0, f"seed={seed}")
            self.assertIsNotNone(stats["min_clearance"], f"seed={seed}")
            self.assertGreaterEqual(
                float(stats["min_clearance"]), r_clear - 1e-6, f"seed={seed}"
            )

        self.assertGreater(
            found, 0, "no seed produced the two-seam verified intersection path"
        )

        # Force all 16 deterministic candidate draws to fail and assert the
        # deterministic single-seam fallback.
        fallback_params = self._params(0.8)
        with unittest.mock.patch.object(
            kintsugi,
            "_shard_second_seam_candidate",
            return_value=None,
        ) as candidate:
            paths = kintsugi.generate_shard_crack_paths(
                fallback_params, np.random.default_rng(3)
            )
            self.assertEqual(candidate.call_count, 16)
        self.assertEqual(len(paths), 1)
        self.assertEqual(fallback_params.get("_growth_junctions"), [])

    # -- Task 1.4 -----------------------------------------------------------
    def test_closed_loop_quadrant_subarc_tortuosity(self) -> None:
        kintsugi = self.kintsugi
        medians = {}
        for R, severity in ((0.5, 0.5), (0.2, 0.8), (0.0, 1.0)):
            base = self._params(severity)
            period = float(base["period"])
            values: list[float] = []
            for seed in range(28):
                paths = kintsugi.generate_shard_crack_paths(
                    dict(base), np.random.default_rng(seed)
                )
                for path in paths:
                    points = np.asarray(path, dtype=np.float64)
                    if not _is_closed(points, period):
                        continue
                    values.extend(
                        kintsugi._tortuosity_values([points], [], period)
                    )
            self.assertTrue(values, f"R={R}: no closed-loop tortuosity values")
            for value in values:
                self.assertTrue(np.isfinite(value))
                self.assertGreaterEqual(
                    value, 1.05 - 1e-9, f"R={R}: tortuosity {value:.4f}"
                )
            medians[R] = float(np.median(values))

        self.assertGreater(medians[0.2], medians[0.5] - 1e-9)
        self.assertGreater(medians[0.0], medians[0.2] - 1e-9)
        self.assertGreater(medians[0.2], medians[0.5])
        self.assertGreater(medians[0.0], medians[0.2])

    # -- Task 1.5 -----------------------------------------------------------
    def test_generate_kintsugi_mesh_shard_mode_watertight_and_ribbon_guard(
        self,
    ) -> None:
        kintsugi = self.kintsugi
        for label, preset in (
            ("tea_bowl", self.tea_bowl_preset),
            ("vase", self.vase_preset),
        ):
            with self.subTest(preset=label):
                with tempfile.TemporaryDirectory() as tmp:
                    result = kintsugi.generate_kintsugi_mesh(
                        preset,
                        tmp,
                        R=0.5,
                        mode="vein",
                        seed=0,
                        generator="shard",
                    )
                    self.assertEqual(
                        result["parameters"]["generator"], "shard"
                    )
                    self.assertIsNotNone(result["gold_path"])
                    for key in ("ceramic_path", "gold_path"):
                        mesh = trimesh.load(result[key], process=True)
                        self.assertTrue(mesh.is_watertight, f"{label}:{key}")
                        self.assertTrue(mesh.is_volume, f"{label}:{key}")
                        self.assertGreater(float(mesh.volume), 0.0, key)
                        self.assertEqual(
                            _bad_edge_count(mesh), 0, f"{label}:{key}"
                        )

        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError) as ctx:
                kintsugi.generate_kintsugi_mesh(
                    self.tea_bowl_preset,
                    tmp,
                    R=0.5,
                    mode="ribbon",
                    seed=0,
                    generator="shard",
                )
            message = str(ctx.exception).lower()
            self.assertIn("shard", message)
            self.assertIn("vein", message)

    # -- Task 1.6 -----------------------------------------------------------
    def test_api_fracture_shard_mode_validation(self) -> None:
        from fastapi.testclient import TestClient

        import web_app

        with tempfile.TemporaryDirectory() as tmp:
            with unittest.mock.patch.object(
                web_app, "OUTPUT_DIR", Path(tmp) / "web"
            ):
                Path(web_app.OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
                client = TestClient(web_app.app, base_url="http://127.0.0.1:8000")
                try:
                    response = client.post(
                        "/api/fracture",
                        data={
                            "preset": "tea_bowl",
                            "R": "0.5",
                            "mode": "vein",
                            "seed": "0",
                            "generator": "shard",
                        },
                    )
                    self.assertEqual(response.status_code, 200, response.text)
                    body = response.json()
                    self.assertEqual(
                        body["parameters"]["generator"], "shard"
                    )
                    self.assertGreater(body["num_cracks"], 0)

                    rejected = client.post(
                        "/api/fracture",
                        data={
                            "preset": "tea_bowl",
                            "R": "0.5",
                            "mode": "ribbon",
                            "seed": "0",
                            "generator": "shard",
                        },
                    )
                    self.assertEqual(
                        rejected.status_code, 400, rejected.text
                    )
                    detail = rejected.json()["detail"].lower()
                    self.assertIn("shard", detail)
                    self.assertIn("vein", detail)
                finally:
                    client.close()

    # -- Task P01.1 ---------------------------------------------------------
    def test_web_ui_exposes_generator_select_and_shard_option(self) -> None:
        from fastapi.testclient import TestClient

        import web_app

        client = TestClient(web_app.app, base_url="http://127.0.0.1:8000")
        try:
            html_res = client.get("/")
            self.assertEqual(html_res.status_code, 200)
            html = html_res.text
            self.assertIn('id="generator-select"', html)
            self.assertIn('id="generator-note"', html)
            self.assertIn('<option value="growth"', html)
            self.assertIn('<option value="shard">', html)
            self.assertIn('<option value="voronoi">', html)

            js_res = client.get("/viewer.js")
            self.assertEqual(js_res.status_code, 200)
            js = js_res.text
            self.assertIn("generator-select", js)
            self.assertIn("generator-note", js)
            self.assertIn("syncGeneratorMode", js)
            self.assertIn('form.append("generator"', js)
        finally:
            client.close()


if __name__ == "__main__":
    unittest.main()
