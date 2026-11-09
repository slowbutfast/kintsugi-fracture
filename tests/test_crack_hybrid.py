"""TDD tests for the hybrid shard + growth crack generator.

Run with:  ./.venv/bin/python -m unittest tests.test_crack_hybrid -v
"""

from __future__ import annotations

import hashlib
import math
import tempfile
import unittest
import unittest.mock
from pathlib import Path

import manifold3d as mf
import numpy as np

import kintsugi
from tests import fixtures


def _write_synthetic_cup(path) -> None:
    """A 44 mm cup with a 4.4 mm wall, matching cup_unitree's profile."""
    profile = [
        (0.0, 0.0),
        (22.5, 0.0),
        (22.5, 44.0),
        (18.1, 44.0),
        (18.1, 4.4),
        (0.0, 4.4),
    ]
    cup = mf.Manifold.revolve(
        mf.CrossSection([profile]), circular_segments=96
    )
    fixtures.write_stl(fixtures.manifold_to_trimesh(cup), path)


_REAL_CUP_UNITREE = Path(
    "/tmp/claude-1001/-home-node-global-sandbox-projects-wax-robot/"
    "9bbab440-a7fe-4db6-b307-75b743311db4/scratchpad/demo/cup_unitree.stl"
)


def _paths_digest(paths) -> str:
    digest = hashlib.sha256()
    digest.update(str(len(paths)).encode())
    for path in paths:
        array = np.asarray(path, dtype="<f8")
        digest.update(str(array.shape).encode())
        digest.update(array.tobytes())
    return digest.hexdigest()


# Captured on the unmodified tree before any hybrid code was added.  These
# pin growth and shard byte-identical across the hybrid work.
BASELINE_DIGESTS = {
    'tea_bowl|R=0.2|seed=42|growth': '070a63a8a45fd7c682ca6635f4d514659c3dfeffc9441adfbf7676c911904f9d',
    'tea_bowl|R=0.2|seed=42|shard': 'cd3558dbec0e0ca83ab4a49118889edae2462f8556ab4cc3db91453f0c301961',
    'tea_bowl|R=0.2|seed=43|growth': 'f41fdbdfbe20fe5242ef42ffd7a6a149516e7832e1f399fb9319377a78833dce',
    'tea_bowl|R=0.2|seed=43|shard': '03e5f2152ca3fe056cf8209b4340c9202b4328f29e2d02f83b5886857fa42807',
    'tea_bowl|R=0.2|seed=44|growth': 'e40ffa0e31c96f195ce72ad83f678179c9ae96a9d1c151b84014911939774648',
    'tea_bowl|R=0.2|seed=44|shard': 'cd9b48b3b43490ac93ed6d584ba8854e5ec6ef1ddca44f207cccb263ada1a29f',
    'tea_bowl|R=0.35|seed=42|growth': 'ae6023cc7caf84c9f02820cea91f5eeb03d8d653a2d1508940c11eabc84ebcbb',
    'tea_bowl|R=0.35|seed=42|shard': '55bd54621b4f8a980315a4fb8f10d4451c33b986c64e2d552837c1b87a57f935',
    'tea_bowl|R=0.35|seed=43|growth': '66a0fe89e096c02698069260889972317acdbd41634232dc0deb808c4b6bb2ca',
    'tea_bowl|R=0.35|seed=43|shard': 'a2e25b15c8ae47ffaaaf65611ed45ff644dd708536da06bc0d4fc315c89b738b',
    'tea_bowl|R=0.35|seed=44|growth': 'ce1af6ae473709679d1d2fe24683a6666f11d69a159cabb6d179ca415dda10e3',
    'tea_bowl|R=0.35|seed=44|shard': '499ab8b803b5b05da99bd95297cce289b09c2b76a04a35c63498c162e9263e7f',
    'tea_bowl|R=0.3|seed=42|growth': '0656a5e57075ce7f9f8fb56a8497e1536c196ed0a0e60ecd70d10e634f2063e5',
    'tea_bowl|R=0.3|seed=42|shard': '766984528eb46f3df165d55964538ea258d08574a59c4af6869fb1752e1c34bd',
    'tea_bowl|R=0.3|seed=43|growth': '2258e48e36183c40dd583d39a290b3aa980a8cf651ce945e97802edd9396e507',
    'tea_bowl|R=0.3|seed=43|shard': 'a55e2cf01d14fadc840da2340d3f9c8576cbfcff21e80140c48d58d822d04d39',
    'tea_bowl|R=0.3|seed=44|growth': '5da9bd6f8f6ea9d6c4e153746e6a8c79e98a1cf12d19c04c6828979a4f455fa0',
    'tea_bowl|R=0.3|seed=44|shard': 'f33785e503b5c49aa0ea39cc9122348a9385d2b9a5d7dab877ccd30f7892aecc',
    'tea_bowl|R=0.65|seed=42|growth': '99b098185ca0fe0d98485f317c00542b0a0d47197815b8ded793d44c51840766',
    'tea_bowl|R=0.65|seed=42|shard': 'bf2d398ba5cb41673f22c56d1ad185f16ffadb990c1a2222af7a06f49e8c73ca',
    'tea_bowl|R=0.65|seed=43|growth': '43e4ea11cf69791e39332fe2c4fc86b44a187e7381f2afe4e024a404a9a94dec',
    'tea_bowl|R=0.65|seed=43|shard': 'a6e833cf7d64ed17547d43cc083d31d094d85de58378813150ab0137708deec3',
    'tea_bowl|R=0.65|seed=44|growth': 'c3c3d648f1e4fa308f8bae570bfe1085a5d18d9e71c9d4f7efac080db708602f',
    'tea_bowl|R=0.65|seed=44|shard': '817477666a3d5fdc6d8208e981ece61095d37d08a7614943c4c0a60806b31c37',
    'tea_bowl|R=0.75|seed=42|growth': '8742ccf8e77f5609e42c0dc10feb8fd1bc30f6d8ba61942048ef18507ea6000e',
    'tea_bowl|R=0.75|seed=42|shard': '1b3dcf6e079bf45692c4579cbf0d9f1db37e117b0fc2da2ba59b20208896ad0e',
    'tea_bowl|R=0.75|seed=43|growth': '5140c367e55fc288d7b29b1d7fdf6cbaf8268500a5e0f8c4008a46e6388cae4c',
    'tea_bowl|R=0.75|seed=43|shard': '410479d2eebc0aa6a5f3f4eccb1ea7836da8a3faa95821be43057244ef4696f8',
    'tea_bowl|R=0.75|seed=44|growth': '1d4cc728ba8c3ae14a8ecc4da431969b17aabc15490887a4afbb39880408bac8',
    'tea_bowl|R=0.75|seed=44|shard': 'cce274c512fa3314803c8eb064a0d885acffaca50a71b4cf3480193c6f435a2c',
    'tea_bowl|R=0.8|seed=42|growth': '74320b8cd9857cd2c9025c20346fb27979a4422a863690a93da08e3398a6de82',
    'tea_bowl|R=0.8|seed=42|shard': '5feceb66ffc86f38d952786c6d696c79c2dbc239dd4e91b46729d73a27fb57e9',
    'tea_bowl|R=0.8|seed=43|growth': '2a68d78b8e4cac0bd96c3c7c2a805436a1c311f75ca499223e497172bab522e6',
    'tea_bowl|R=0.8|seed=43|shard': '5feceb66ffc86f38d952786c6d696c79c2dbc239dd4e91b46729d73a27fb57e9',
    'tea_bowl|R=0.8|seed=44|growth': '48d95783dcf1c1fed0546a9fb0e0479ef1057e7754868c548fb0a6fa94290f5e',
    'tea_bowl|R=0.8|seed=44|shard': '5feceb66ffc86f38d952786c6d696c79c2dbc239dd4e91b46729d73a27fb57e9',
    'vase|R=0.2|seed=42|growth': '5b5bc36187a68b5a54ade63b7e8e9b5cd6c04c5013ab8b1ea69a1616a3eb0af0',
    'vase|R=0.2|seed=42|shard': 'b671adf1e38e20e10cacdad7306abef4dd8b11c10bb435f9f55610a9fe6967f6',
    'vase|R=0.2|seed=43|growth': '314cf4542ce2dae41ff68e4ffc6f50f9228a95afb710abc2587c73752a690ce9',
    'vase|R=0.2|seed=43|shard': 'a10e96c8db2b2196160cce8b3b722ec7925b0b159403528e42ab5df154ac6e61',
    'vase|R=0.2|seed=44|growth': '9f655f8cda4c398ff65d9628df71367852da97d09c17d0e6cf4f2a1fb7b6da78',
    'vase|R=0.2|seed=44|shard': 'f4c272df17fb66a7b3477c43911ea91b08945c1e54e86d963a2c77c704bd7ca6',
    'vase|R=0.35|seed=42|growth': '7c038b6caffe2f57d367eacd2a00b5a475750071f545e58790719e1466b074ce',
    'vase|R=0.35|seed=42|shard': '1a05b1678503695d1567271252eef99330b09d104b2e783e31183bedcb43d0fa',
    'vase|R=0.35|seed=43|growth': '5bc7001eeb45915f85d70ca6e00e375b4efd74980d6e546d826a731249fa3156',
    'vase|R=0.35|seed=43|shard': 'd2489a258aa1ef806905f24ea1b175303e94142f586014c6238223fdef344023',
    'vase|R=0.35|seed=44|growth': '21e0fd5840d4e3ad4b31f2bbf2443b734cc19ab553739297deae2eaac5843ac9',
    'vase|R=0.35|seed=44|shard': 'f089efacc25157e3b9fe147b11d1cfee02b11f770529868ba685562584a803d5',
    'vase|R=0.3|seed=42|growth': 'c7d157bc02a4031090eba1b8283d43a77a500b970a5dd8121b9b6831f47f0953',
    'vase|R=0.3|seed=42|shard': 'c68a52c2bbb03f1e7353f8e5ad80e540f1b167e3c57721d13f1bba24eabfbd6b',
    'vase|R=0.3|seed=43|growth': 'd9f7c1d8c946fec9c486a19464f65962c1dde8f79c6f6930b2130a254ae5eaef',
    'vase|R=0.3|seed=43|shard': '598549d9f96ef50f128fe8a4359ef55d814e489c2f8b385eb6408dd44e4531bd',
    'vase|R=0.3|seed=44|growth': '23e982728c384e4666ee9846e1a4304cefaf1e4d9facb21fea3e05d8dbcc538c',
    'vase|R=0.3|seed=44|shard': '1f24698c0f9de5b1afe6abc238750b9bfcbca4d39948e1d7eccd8b86ae008ab7',
    'vase|R=0.65|seed=42|growth': '128d08eff29f797d7fa8fbbac12283aa805ef1219e4f242245901f087fad15ea',
    'vase|R=0.65|seed=42|shard': '66f1720a5b6657fcbd2f289287b2e1c0b5c8cd959f8fb0c436e68edb5160c960',
    'vase|R=0.65|seed=43|growth': '4b4de6e3b46471ff98f299ca8f2d7b2130c4f0dfb3be6bf88affba522477d114',
    'vase|R=0.65|seed=43|shard': 'b9865ba6da13b739b17ba01d0e786623bc009343ea97e46b0a9ed4b8c2808147',
    'vase|R=0.65|seed=44|growth': 'c547e55b460788d95bdd1f8ce267e74e2d2a66db0c8f1ca3b080697b1f0cb65a',
    'vase|R=0.65|seed=44|shard': 'c298f2fcd53a7da8c09fab95815f5e6a3d79344dd1bd7725c8275ca4d7890e77',
    'vase|R=0.75|seed=42|growth': '018bbd86bddb4b3f306cbe217098cdaadd4b4d54d7303e92f460d03932969f21',
    'vase|R=0.75|seed=42|shard': 'd53b39d687bea7beb61750dab366b58db8b377e8a29aac403f05910bbf2df9bc',
    'vase|R=0.75|seed=43|growth': '4d85e3385b36bee4fd2300c063dbb34ce4dfc02ec802fccf20f1d64a3da073e3',
    'vase|R=0.75|seed=43|shard': '7ba0dc2a7a770d6bb09d4aa14aff295d50e4e4978703207755ed1d5df252daab',
    'vase|R=0.75|seed=44|growth': '0fb38bc1b90fb704cc347ae529ce980c277ad9ce50e16bb52b320781d7c0532f',
    'vase|R=0.75|seed=44|shard': '846b3fe35ff5a512c68f0354a4e1b09f6656e9a5106e202976be98b55e01b3ab',
    'vase|R=0.8|seed=42|growth': '7fbbe890da10ea0ec64b6f2bc992035a1cb3a798fdb405a17b72624376095491',
    'vase|R=0.8|seed=42|shard': '5feceb66ffc86f38d952786c6d696c79c2dbc239dd4e91b46729d73a27fb57e9',
    'vase|R=0.8|seed=43|growth': 'bb8870b8436267e8d0c9b99810265d3a48e49920200f781c5d86db1a6c16f598',
    'vase|R=0.8|seed=43|shard': '5feceb66ffc86f38d952786c6d696c79c2dbc239dd4e91b46729d73a27fb57e9',
    'vase|R=0.8|seed=44|growth': 'cb61a1e22957589237c7bdd260ba2320ea7f625e640e3f18777daccb8a927417',
    'vase|R=0.8|seed=44|shard': '5feceb66ffc86f38d952786c6d696c79c2dbc239dd4e91b46729d73a27fb57e9',
}

_RATIOS = (0.2, 0.3, 0.35, 0.65, 0.75, 0.8)
_SEEDS = (42, 43, 44)


class CrackHybridTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory(prefix="kintsugi-hybrid-")
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
        return kintsugi.compute_parameters(
            severity,
            self.validation.mesh,
            manifold=self.validation.manifold,
            probe=self.validation.probe,
        )

    def _hybrid(self, severity: float, seed: int, options=None):
        params = self._params(severity)
        paths = kintsugi.generate_crack_paths(
            params,
            np.random.default_rng(seed),
            generator="hybrid",
            hybrid_options=options,
        )
        return paths, params

    # -- Task 1.1 ----------------------------------------------------------
    def test_growth_and_shard_baseline_digests_unchanged(self) -> None:
        seen = 0
        for label, path in (
            ("tea_bowl", self.tea_bowl_preset),
            ("vase", self.vase_preset),
        ):
            validation = kintsugi.validate_and_load_mesh(path, S=0.0)
            for R in _RATIOS:
                params = kintsugi.compute_parameters(
                    1.0 - R,
                    validation.mesh,
                    manifold=validation.manifold,
                    probe=validation.probe,
                )
                for seed in _SEEDS:
                    for generator in ("growth", "shard"):
                        key = f"{label}|R={R:g}|seed={seed}|{generator}"
                        paths = kintsugi.generate_crack_paths(
                            dict(params),
                            np.random.default_rng(seed),
                            generator=generator,
                        )
                        self.assertEqual(
                            _paths_digest(paths),
                            BASELINE_DIGESTS[key],
                            f"baseline drift: {key}",
                        )
                        seen += 1
        self.assertEqual(seen, len(BASELINE_DIGESTS))

    # -- Task 1.2 ----------------------------------------------------------
    def test_validate_rejects_solid_body_without_wall(self) -> None:
        solid = Path(self._tmp.name) / "solid_cylinder.stl"
        fixtures.write_solid_cylinder(solid)
        with self.assertRaises(ValueError) as ctx:
            kintsugi.validate_and_load_mesh(solid, S=0.0)
        message = str(ctx.exception).lower()
        self.assertIn("wall", message)

    # -- Task 1.3 ----------------------------------------------------------
    def test_hybrid_determinism_and_low_severity(self) -> None:
        first, first_params = self._hybrid(0.5, 42)
        second, second_params = self._hybrid(0.5, 42)
        other, _ = self._hybrid(0.5, 43)
        self.assertEqual(_paths_digest(first), _paths_digest(second))
        self.assertNotEqual(_paths_digest(first), _paths_digest(other))
        self.assertEqual(
            first_params["hybrid"]["num_through_paths"]
            + first_params["hybrid"]["num_hairline_paths"],
            len(first),
        )

        low, low_params = self._hybrid(0.1, 42)
        self.assertEqual(low, [])
        hybrid = low_params["hybrid"]
        self.assertEqual(hybrid["through_count"], 0)
        self.assertEqual(hybrid["hairline_count"], 0)
        self.assertEqual(hybrid["num_fragments"], 1)

        explicit, explicit_params = self._hybrid(
            0.1, 42, {"through_count": 1}
        )
        self.assertGreater(len(explicit), 0)
        explicit_hybrid = explicit_params["hybrid"]
        self.assertEqual(explicit_hybrid["through_shape"], "wedge")
        self.assertGreaterEqual(explicit_hybrid["num_through_fragments"], 2)
        self.assertGreaterEqual(explicit_hybrid["num_fragments"], 2)

    def test_stage1_auto_shape_reaches_rim_via_wedge_fallback(self) -> None:
        import unittest.mock

        with unittest.mock.patch.object(
            kintsugi, "_shard_loop_path", return_value=None
        ):
            paths, params = self._hybrid(
                0.5,
                42,
                {
                    "through_count": 1,
                    "through_shape": "auto",
                    "hairline_count": 0,
                },
            )
        self.assertTrue(paths)
        hybrid = params["hybrid"]
        self.assertEqual(hybrid["through_shape"], "wedge")
        W = float(params["W"])
        wall_z_max = float(params["wall_z_max"])
        wedge = np.asarray(paths[0])
        self.assertFalse(
            kintsugi._is_closed_periodic_path(wedge, params["period"])
        )
        for endpoint in (wedge[0], wedge[-1]):
            self.assertGreaterEqual(
                float(endpoint[1]), wall_z_max - 1e-9
            )
            self.assertLessEqual(
                float(endpoint[1]) - wall_z_max, 0.35 * W + 1e-6
            )

    def test_shard_extra_seam_candidate_targets_any_earlier_seam(self) -> None:
        params = self._params(0.6)
        config = kintsugi._resolve_hybrid_config(
            params, {"through_count": 2}
        )
        stage1, records, shape = kintsugi._hybrid_stage1_paths(
            params, np.random.default_rng(7), config
        )
        self.assertGreaterEqual(len(stage1), 1)
        self.assertEqual(shape, "wedge")

        found = 0
        for seed in range(16):
            candidate = kintsugi._shard_extra_seam_candidate(
                params,
                np.random.default_rng(seed),
                stage1,
                0,
            )
            if candidate is None:
                continue
            found += 1
            target = int(candidate["target_path"])
            self.assertIn(target, range(len(stage1)))
            endpoint = np.asarray(candidate["hit"], dtype=np.float64)
            target_path = np.asarray(stage1[target], dtype=np.float64)
            # The hit is returned as an exact vertex of the accepted seam
            # after truncation, so the matching shared vertex may be inserted
            # in the target copy rather than already present.
            inserted = [
                np.asarray(point, dtype=np.float64).copy()
                for point in target_path
            ]
            kintsugi._subdivide_path(
                inserted, int(candidate["seam_index"]), candidate["local"]
            )
            distances = [
                kintsugi._periodic_distance(point, endpoint, params["period"])
                for point in inserted
            ]
            self.assertLessEqual(min(distances), 1e-6)
        self.assertGreater(found, 0)

        # The plain shard wrapper must produce the same result as the
        # generalized function with a single existing path.
        seam = stage1[0]
        wrapped = kintsugi._shard_second_seam_candidate(
            params, np.random.default_rng(11), seam, 0
        )
        generalized = kintsugi._shard_extra_seam_candidate(
            params, np.random.default_rng(11), [seam], 0
        )
        if wrapped is None:
            self.assertIsNone(generalized)
        else:
            self.assertIsNotNone(generalized)
            assert generalized is not None
            np.testing.assert_allclose(wrapped["path"], generalized["path"])
            self.assertEqual(
                int(wrapped["target_path"]), int(generalized["target_path"])
            )

    def test_fragment_guarantee_across_seeds_42_61(self) -> None:
        for severity in (0.2, 0.6):
            for seed in range(42, 62):
                _, params = self._hybrid(severity, seed)
                hybrid = params["hybrid"]
                self.assertGreaterEqual(
                    hybrid["num_through_paths"],
                    1,
                    f"S={severity} seed={seed}",
                )
                self.assertGreaterEqual(
                    hybrid["num_through_fragments"],
                    2,
                    f"S={severity} seed={seed}",
                )
                self.assertGreaterEqual(
                    hybrid["num_fragments"],
                    2,
                    f"S={severity} seed={seed}",
                )

    def test_cup_unitree_r02_seed1_clearance_regression(self) -> None:
        cup = Path(self._tmp.name) / "synthetic_cup.stl"
        _write_synthetic_cup(cup)
        cases = [("synthetic_cup", cup)]
        if _REAL_CUP_UNITREE.exists():
            cases.append(("real_cup_unitree", _REAL_CUP_UNITREE))
        for label, path in cases:
            with self.subTest(model=label):
                validation = kintsugi.validate_and_load_mesh(path, S=0.0)
                params = kintsugi.compute_parameters(
                    0.8,
                    validation.mesh,
                    manifold=validation.manifold,
                    probe=validation.probe,
                )
                paths = kintsugi.generate_crack_paths(
                    params,
                    np.random.default_rng(1),
                    generator="hybrid",
                )
                stats = kintsugi.analyze_growth_paths(paths, params)
                r_clear = (
                    float(params["W"]) + kintsugi.GROWTH_CLEARANCE_MM
                )
                self.assertEqual(stats["crossings"], 0)
                self.assertEqual(stats["clearance_violations"], 0)
                self.assertIsNotNone(stats["min_clearance"])
                self.assertGreaterEqual(
                    float(stats["min_clearance"]), r_clear - 1e-6
                )
                self.assertGreaterEqual(
                    params["hybrid"]["num_fragments"], 2
                )

    def test_r08_tier_boundary_produces_fracture(self) -> None:
        params = self._params(1.0 - 0.8)
        paths = kintsugi.generate_crack_paths(
            params, np.random.default_rng(42), generator="hybrid"
        )
        hybrid = params["hybrid"]
        self.assertEqual(hybrid["through_count"], 1)
        self.assertGreaterEqual(hybrid["num_through_paths"], 1)
        self.assertGreaterEqual(hybrid["num_fragments"], 2)
        self.assertGreater(len(paths), 0)

    def test_fractional_integer_knobs_rejected(self) -> None:
        params = self._params(0.5)
        for options in (
            {"through_count": 2.5},
            {"through_count": "2.5"},
            {"through_count": "abc"},
            {"through_count": True},
            {"hairline_count": 2.5},
            {"hairline_count": "2.5"},
            {"hairline_count": True},
        ):
            with self.subTest(options=options):
                with self.assertRaises(ValueError):
                    kintsugi.generate_crack_paths(
                        dict(params),
                        np.random.default_rng(42),
                        generator="hybrid",
                        hybrid_options=options,
                    )

    def test_auto_shape_defaults_to_wedge(self) -> None:
        with unittest.mock.patch.object(
            kintsugi,
            "_shard_loop_path",
            side_effect=AssertionError("auto must not try loop"),
        ):
            for seed in range(10):
                paths, params = self._hybrid(
                    0.5,
                    seed,
                    {
                        "through_count": 1,
                        "through_shape": "auto",
                        "hairline_count": 0,
                    },
                )
                self.assertEqual(
                    params["hybrid"]["through_shape"], "wedge"
                )
                self.assertEqual(
                    params["hybrid"]["through_shape_requested"], "auto"
                )
                self.assertFalse(
                    kintsugi._is_closed_periodic_path(
                        np.asarray(paths[0]), params["period"]
                    )
                )

    def test_fail_closed_fragment_guarantee(self) -> None:
        with unittest.mock.patch.object(
            kintsugi, "_count_wall_fragments", return_value=1
        ):
            with self.assertRaises(ValueError):
                self._hybrid(0.5, 42)

    def test_fail_closed_combined_audit(self) -> None:
        bad_stats = {
            "crossings": 1,
            "clearance_violations": 0,
            "min_clearance": 10.0,
        }
        with unittest.mock.patch.object(
            kintsugi, "analyze_growth_paths", return_value=bad_stats
        ):
            with self.assertRaises(ValueError):
                self._hybrid(0.5, 42)

    # -- Task 1.4 ----------------------------------------------------------
    def test_stage2_obstacles_and_rim_exclusion(self) -> None:
        paths, params = self._hybrid(0.5, 42)
        hybrid = params["hybrid"]
        self.assertGreater(hybrid["num_hairline_paths"], 0)
        stats = kintsugi.analyze_growth_paths(paths, params)
        self.assertEqual(stats["crossings"], 0)
        self.assertEqual(stats["clearance_violations"], 0)
        self.assertIsNotNone(stats["min_clearance"])
        r_clear = float(params["W"]) + kintsugi.GROWTH_CLEARANCE_MM
        self.assertGreaterEqual(
            float(stats["min_clearance"]), r_clear - 1e-6
        )

        # Direct Poisson exclusion check: no seed may land in the forbidden
        # zone, whether it comes from rejection sampling or the gap fallback.
        period = 10.0
        excluded = (5.0,)
        for seed in range(50):
            seeds = kintsugi._poisson_rim_seeds(
                4,
                period,
                0.5,
                np.random.default_rng(seed),
                excluded_u=excluded,
                exclusion_radius=1.5,
            )
            for value in seeds:
                self.assertGreaterEqual(
                    kintsugi._circular_distance(value, 5.0, period),
                    1.5 - 1e-9,
                )

        class _PinnedRng:
            def uniform(self, low=0.0, high=1.0, size=None):
                return 5.0

            def integers(self, low, high=None, size=None):
                return 0

        # Every rejection sample is inside the zone, so the deterministic
        # fallback must terminate early rather than place an illegal seed.
        seeds = kintsugi._poisson_rim_seeds(
            2,
            period,
            0.5,
            _PinnedRng(),
            excluded_u=excluded,
            exclusion_radius=1.5,
        )
        self.assertLessEqual(len(seeds), 1)
        for value in seeds:
            self.assertGreaterEqual(
                kintsugi._circular_distance(value, 5.0, period),
                1.5 - 1e-9,
            )

        # When the only fallback site is itself forbidden, return only the
        # legal seed already placed instead of violating the exclusion.
        partial = kintsugi._poisson_rim_seeds(
            2,
            period,
            0.5,
            _PinnedRng(),
            excluded_u=(0.0,),
            exclusion_radius=1.5,
        )
        for value in partial:
            self.assertGreaterEqual(
                kintsugi._circular_distance(value, 0.0, period),
                1.5 - 1e-9,
            )

    def test_macro_seam_anchor_first_step_survives(self) -> None:
        params = self._params(0.5)
        period = float(params["period"])
        W = float(params["W"])
        z_hi = float(params["wall_z_max"]) + 0.35 * W
        z_lo = float(params["wall_z_min"]) + 0.5 * W
        seam = np.column_stack(
            (
                np.full(41, 0.5 * period),
                np.linspace(z_hi, z_lo, 41),
            )
        )
        found = 0
        for seed in range(8):
            local = dict(params)
            paths = kintsugi.generate_crack_growth_paths(
                local,
                np.random.default_rng(seed),
                initial_paths=[seam],
                hairline_count=1,
                seam_anchor_count=1,
            )
            records = local.get("_growth_junctions") or []
            if not paths:
                continue
            found += 1
            path = np.asarray(paths[0])
            self.assertGreaterEqual(len(path), 2)
            anchor_distances = [
                kintsugi._periodic_distance(point, path[0], period)
                for point in seam
            ]
            self.assertLessEqual(min(anchor_distances), 1e-6)
            # The anchor record points at the parent seam and the first
            # growth vertex sits exactly on the parent.
            anchor_records = [
                record
                for record in records
                if record.get("kind") == "Y"
                and int(record.get("parent", -1)) == 0
            ]
            self.assertTrue(anchor_records)
            anchor = np.asarray(anchor_records[0]["point"])
            distances = [
                kintsugi._periodic_distance(point, anchor, period)
                for point in seam
            ]
            self.assertLessEqual(min(distances), 1e-6)
        self.assertGreater(found, 0)

        _, hybrid_params = self._hybrid(
            0.5, 42, {"hairline_count": 6}
        )
        self.assertGreater(
            hybrid_params["hybrid"]["hairline_seam_count"], 0
        )

    def test_combined_audit_invariants(self) -> None:
        for severity in (0.2, 0.5, 0.8):
            for seed in (42, 43, 44, 45):
                paths, params = self._hybrid(severity, seed)
                stats = kintsugi.analyze_growth_paths(paths, params)
                r_clear = (
                    float(params["W"]) + kintsugi.GROWTH_CLEARANCE_MM
                )
                with self.subTest(S=severity, seed=seed):
                    self.assertEqual(stats["crossings"], 0)
                    self.assertEqual(stats["clearance_violations"], 0)
                    self.assertIsNotNone(stats["min_clearance"])
                    self.assertGreaterEqual(
                        float(stats["min_clearance"]), r_clear - 1e-6
                    )
                    if stats["min_incidence_deg"] is not None:
                        self.assertGreaterEqual(
                            float(stats["min_incidence_deg"]),
                            30.0 - 1e-6,
                        )
                    hybrid = params["hybrid"]
                    self.assertEqual(
                        len(paths),
                        hybrid["num_through_paths"]
                        + hybrid["num_hairline_paths"],
                    )

    # -- Task 1.5 ----------------------------------------------------------
    def _digest_with(self, options: dict, seed: int = 42) -> str:
        paths, params = self._hybrid(0.5, seed, options)
        return _paths_digest(paths)

    def test_each_knob_changes_output_and_echoes_telemetry(self) -> None:
        cases = (
            (
                "through_count",
                {"through_count": 1},
                {"through_count": 3},
            ),
            (
                "through_shape",
                {"through_count": 1, "through_shape": "wedge"},
                {"through_count": 1, "through_shape": "loop"},
            ),
            (
                "tilt_deg_wedge",
                {"through_count": 1, "through_shape": "wedge", "tilt_deg": 5},
                {"through_count": 1, "through_shape": "wedge", "tilt_deg": 30},
            ),
            (
                "tilt_deg_loop",
                {"through_count": 1, "through_shape": "loop", "tilt_deg": 5},
                {"through_count": 1, "through_shape": "loop", "tilt_deg": 30},
            ),
            (
                "hairline_count",
                {"hairline_count": 0},
                {"hairline_count": 7},
            ),
            (
                "hairline_reach",
                {"hairline_count": 5, "hairline_reach": 0.2},
                {"hairline_count": 5, "hairline_reach": 1.0},
            ),
            (
                "roughness",
                {"hairline_count": 5, "roughness": 0.5},
                {"hairline_count": 5, "roughness": 2.0},
            ),
        )
        for name, first, second in cases:
            with self.subTest(knob=name):
                distinct = False
                for seed in (42, 43, 44, 45):
                    if self._digest_with(first, seed) != self._digest_with(
                        second, seed
                    ):
                        distinct = True
                        break
                self.assertTrue(distinct, f"{name} did not change output")

        _, auto_params = self._hybrid(0.5, 42)
        auto = auto_params["hybrid"]
        self.assertEqual(auto["through_count"], 2)
        self.assertEqual(auto["hairline_count"], 5)
        self.assertAlmostEqual(auto["hairline_reach"], 0.6, places=9)
        self.assertAlmostEqual(auto["tilt_deg"], 20.0, places=9)
        self.assertAlmostEqual(auto["roughness"], 1.0, places=9)
        self.assertGreaterEqual(auto["num_fragments"], 2)

        _, override_params = self._hybrid(
            0.5,
            42,
            {
                "through_count": 1,
                "through_shape": "loop",
                "tilt_deg": 26,
                "hairline_count": 2,
                "hairline_reach": 0.4,
                "roughness": 1.5,
            },
        )
        override = override_params["hybrid"]
        self.assertEqual(override["through_count"], 1)
        self.assertEqual(override["through_shape"], "loop")
        self.assertAlmostEqual(override["tilt_deg"], 26.0)
        self.assertEqual(override["hairline_count"], 2)
        self.assertAlmostEqual(override["hairline_reach"], 0.4)
        self.assertAlmostEqual(override["roughness"], 1.5)
        self.assertFalse(override["auto_through_count"])
        self.assertFalse(override["auto_hairline_count"])

    def test_generate_kintsugi_mesh_hybrid_watertight(self) -> None:
        import trimesh

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
                        seed=42,
                        generator="hybrid",
                    )
                    self.assertEqual(
                        result["parameters"]["generator"], "hybrid"
                    )
                    self.assertIn("hybrid", result["parameters"])
                    self.assertGreaterEqual(result["num_fragments"], 2)
                    self.assertGreater(result["num_cracks"], 0)
                    for key in ("ceramic_path", "gold_path"):
                        mesh = trimesh.load(result[key], process=True)
                        self.assertTrue(mesh.is_watertight, key)
                        self.assertTrue(mesh.is_volume, key)
                        self.assertGreater(float(mesh.volume), 0.0, key)

    def test_hybrid_rejects_ribbon_and_knobs_on_other_generators(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError) as ctx:
                kintsugi.generate_kintsugi_mesh(
                    self.tea_bowl_preset,
                    tmp,
                    R=0.5,
                    mode="ribbon",
                    generator="hybrid",
                )
            message = str(ctx.exception).lower()
            self.assertIn("hybrid", message)
            self.assertIn("vein", message)

        params = self._params(0.5)
        with self.assertRaises(ValueError):
            kintsugi.generate_crack_paths(
                dict(params),
                np.random.default_rng(42),
                generator="growth",
                hybrid_options={"through_count": 1},
            )
        with self.assertRaises(ValueError):
            kintsugi.generate_crack_paths(
                dict(params),
                np.random.default_rng(42),
                generator="hybrid",
                hybrid_options={"through_count": 9},
            )
        with self.assertRaises(ValueError):
            kintsugi.generate_crack_paths(
                dict(params),
                np.random.default_rng(42),
                generator="hybrid",
                hybrid_options={"tilt_deg": 4.0},
            )
        with self.assertRaises(ValueError):
            kintsugi.generate_crack_paths(
                dict(params),
                np.random.default_rng(42),
                generator="hybrid",
                hybrid_options={"roughness": 3.0},
            )


if __name__ == "__main__":
    unittest.main()
