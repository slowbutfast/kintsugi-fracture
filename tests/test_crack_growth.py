"""PATCH-02 crack-growth morphology regression tests.

Run with:  .venv/bin/python -m unittest tests.test_crack_growth -v
"""

from __future__ import annotations

import tempfile
import unittest
import unittest.mock
from pathlib import Path

import numpy as np

from tests import fixtures


class _RecordingRNG:
    """Generator proxy that records the correlated-walk sampling calls."""

    def __init__(self, seed: int) -> None:
        self._rng = np.random.default_rng(seed)
        self.normal_calls: list[tuple[float, float]] = []
        self.uniform_calls: list[tuple[float, float]] = []

    def normal(self, loc=0.0, scale=1.0, size=None):
        self.normal_calls.append((float(loc), float(scale)))
        return self._rng.normal(loc, scale, size)

    def uniform(self, low=0.0, high=1.0, size=None):
        self.uniform_calls.append((float(low), float(high)))
        return self._rng.uniform(low, high, size)

    def random(self, size=None):
        return self._rng.random(size)

    def integers(self, low, high=None, size=None):
        return self._rng.integers(low, high, size)

    def __getattr__(self, name):
        return getattr(self._rng, name)


class CrackGrowthRegressionTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        import kintsugi

        cls._tmp = tempfile.TemporaryDirectory(prefix="kintsugi-growth-")
        cls.bowl = Path(cls._tmp.name) / "bowl.stl"
        fixtures.write_bowl(cls.bowl)
        cls.validation = kintsugi.validate_and_load_mesh(cls.bowl, S=0.0)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def _params(self, severity: float) -> dict:
        import kintsugi

        return kintsugi.compute_parameters(
            severity,
            self.validation.mesh,
            manifold=self.validation.manifold,
            probe=self.validation.probe,
        )

    def test_final_attempt_bend_snaps_near_miss(self) -> None:
        """With forward projection disabled, the final-attempt bend still T-joins."""
        import kintsugi

        with unittest.mock.patch.object(
            kintsugi, "_forward_t_junction", return_value=None
        ):
            total_t_junctions = 0
            for severity in (0.6, 1.0):
                for seed in range(6):
                    params = self._params(severity)
                    paths = kintsugi.generate_crack_growth_paths(
                        params, np.random.default_rng(seed)
                    )
                    stats = kintsugi.analyze_growth_paths(paths, params)
                    with self.subTest(S=severity, seed=seed):
                        self.assertEqual(stats["crossings"], 0)
                        self.assertEqual(stats["clearance_violations"], 0)
                        if stats["min_incidence_deg"] is not None:
                            self.assertGreaterEqual(
                                stats["min_incidence_deg"], 30.0 - 1e-6
                            )
                    total_t_junctions += int(stats["t_junctions"])
        self.assertGreater(
            total_t_junctions, 0, "final-attempt bend never formed a T-junction"
        )

    def test_correlated_walk_kink_rate_and_sigma(self) -> None:
        """20% sharp kinks; every non-kink step drifts with sigma = 18 degrees."""
        import kintsugi

        kinks = 0
        drifts = 0
        for seed in range(10):
            params = self._params(0.6)
            rng = _RecordingRNG(seed)
            kintsugi.generate_crack_growth_paths(params, rng)
            drifts += sum(
                1
                for loc, scale in rng.normal_calls
                if loc == 0.0 and scale == 18.0
            )
            kinks += sum(
                1
                for low, high in rng.uniform_calls
                if low == -85.0 and high == 85.0
            )

        self.assertGreater(drifts, 0)
        self.assertGreater(kinks, 0)
        ratio = kinks / float(kinks + drifts)
        self.assertGreaterEqual(ratio, 0.15)
        self.assertLessEqual(ratio, 0.25)

    def test_median_tortuosity_and_zero_crossings(self) -> None:
        import kintsugi

        for severity in (0.3, 0.6, 1.0):
            medians = []
            for seed in range(6):
                params = self._params(severity)
                paths = kintsugi.generate_crack_growth_paths(
                    params, np.random.default_rng(seed)
                )
                stats = kintsugi.analyze_growth_paths(paths, params)
                with self.subTest(S=severity, seed=seed):
                    self.assertEqual(stats["crossings"], 0)
                    self.assertEqual(stats["clearance_violations"], 0)
                medians.append(float(stats["tortuosity_median"]))
            with self.subTest(S=severity):
                self.assertGreaterEqual(
                    float(np.median(medians)),
                    1.05,
                    f"S={severity} tortuosity median {np.median(medians):.3f}",
                )


if __name__ == "__main__":
    unittest.main()
