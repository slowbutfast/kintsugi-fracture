"""Ceramic vessel envelope tests.

Run with:  .venv/bin/python -m unittest tests.test_envelope -v
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import manifold3d as mf

from tests import fixtures


def _annular_cylinder(wall_mm: float, *, outer_radius: float = 25.0,
                      height: float = 70.0, base: float = 3.0,
                      circular_segments: int = 96) -> mf.Manifold:
    """Closed cylinder with the requested uniform wall thickness."""
    inner_radius = outer_radius - float(wall_mm)
    profile = [
        (0.0, 0.0),
        (outer_radius, 0.0),
        (outer_radius, height),
        (inner_radius, height),
        (inner_radius, base),
        (0.0, base),
    ]
    return mf.Manifold.revolve(
        mf.CrossSection([profile]), circular_segments=circular_segments
    )


def _write_cylinder(directory: Path, wall_mm: float, name: str) -> Path:
    path = directory / f"{name}.stl"
    fixtures.write_stl(
        fixtures.manifold_to_trimesh(_annular_cylinder(wall_mm)), path
    )
    return path


class CeramicEnvelopeTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory(prefix="kintsugi-envelope-")
        cls.root = Path(cls._tmp.name)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def test_envelope_rejection_thin_mesh(self) -> None:
        import kintsugi
        import sample_models

        thin_15 = _write_cylinder(self.root, 1.5, "thin_1p5")
        fixture = self.root / "thin_cylinder_fixture.stl"
        fixtures.write_stl(
            fixtures.manifold_to_trimesh(
                sample_models.create_thin_cylinder_fixture()
            ),
            fixture,
        )

        for label, path in (("1.5 mm cylinder", thin_15), ("thin fixture", fixture)):
            with self.subTest(case=label):
                with self.assertRaises(ValueError) as ctx:
                    kintsugi.validate_and_load_mesh(path, S=0.0)
                message = str(ctx.exception).lower()
                self.assertIn("wall thickness", message)
                self.assertIn("1.60", message)

                for mode in ("vein", "ribbon"):
                    with self.subTest(case=label, mode=mode):
                        with tempfile.TemporaryDirectory() as tmp:
                            with self.assertRaises(ValueError):
                                kintsugi.generate_kintsugi_mesh(
                                    path, tmp, R=0.4, mode=mode, seed=7
                                )

    def test_envelope_acceptance_near_boundary(self) -> None:
        import kintsugi

        near_boundary = _write_cylinder(self.root, 1.7, "near_boundary_1p7")
        validation = kintsugi.validate_and_load_mesh(near_boundary, S=0.0)
        self.assertIsNotNone(validation.manifold)
        self.assertGreaterEqual(
            validation.probe["wall_thickness_p5"], 1.6 - 1e-6
        )

        with tempfile.TemporaryDirectory() as tmp:
            result = kintsugi.generate_kintsugi_mesh(
                near_boundary,
                tmp,
                R=0.6,
                mode="vein",
                seed=7,
                generator="growth",
            )
            self.assertFalse(result["seams_omitted"])
            self.assertIsNotNone(result["gold_path"])
            self.assertGreater(result["triangle_counts"]["gold"], 0)

    def test_wall_envelope_boundary_comparison(self) -> None:
        import kintsugi

        self.assertTrue(kintsugi.wall_envelope_passes(1.60))
        self.assertTrue(kintsugi.wall_envelope_passes(1.6000001))
        self.assertFalse(kintsugi.wall_envelope_passes(1.5999999))
        self.assertFalse(kintsugi.wall_envelope_passes(1.0))


if __name__ == "__main__":
    unittest.main()
