"""The viewer's JavaScript modules, run under Node against the Python reader.

``static/threemf.js`` must preview the geometry ``mesh_formats.load_3mf``
validates, and reject the same inputs.  ``static/upload.js`` decides, before
any request is sent, whether a file is within the deployment's limits.  Skipped
when Node is not installed (it is not a runtime dependency of the app).
"""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path

import numpy as np
import trimesh

import mesh_formats
from tests import fixtures

ROOT = Path(__file__).resolve().parent.parent
RUNNER = ROOT / "tests" / "js" / "runner.mjs"
STATIC_PRESETS = ROOT / "static" / "presets" / "index.json"
MIB = 1024 * 1024


def _box(extent=(10.0, 10.0, 10.0)) -> trimesh.Trimesh:
    box = trimesh.creation.box(extents=extent)
    return trimesh.Trimesh(
        vertices=np.asarray(box.vertices, dtype=np.float64),
        faces=np.asarray(box.faces),
        process=False,
    )


def _soup(mesh: trimesh.Trimesh) -> np.ndarray:
    return np.asarray(mesh.vertices)[np.asarray(mesh.faces)].reshape(-1)


@unittest.skipUnless(shutil.which("node"), "node is not installed")
class ViewerJsTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory(prefix="kintsugi-viewer-js-")
        cls.dir = Path(cls._tmp.name)
        cls.bowl = fixtures.manifold_to_trimesh(fixtures.bowl_manifold())
        cls.ok_cases: dict[str, Path] = {}
        cls.reject_cases: dict[str, tuple[Path, tuple[str, ...]]] = {}
        cls._build_fixtures()
        cls.results = cls._run_node()

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    # -- fixtures -------------------------------------------------------------
    @classmethod
    def _ok(cls, name, **kwargs) -> None:
        path = cls.dir / f"{name}.3mf"
        fixtures.build_3mf(path, **kwargs)
        cls.ok_cases[name] = path

    @classmethod
    def _reject(cls, name, needles, **kwargs) -> None:
        path = cls.dir / f"{name}.3mf"
        extra = kwargs.pop("raw_bytes", None)
        if extra is not None:
            path.write_bytes(extra)
        else:
            fixtures.build_3mf(path, **kwargs)
        cls.reject_cases[name] = (path, needles)

    @classmethod
    def _build_fixtures(cls) -> None:
        bowl = cls.bowl
        metre = bowl.copy()
        metre.apply_scale(0.001)
        rotation = fixtures.rotation_z_matrix(90.0)
        shift = fixtures.translation_matrix(0.010, 0.020, 0.0)
        mirror = np.eye(4)
        mirror[0, 0] = -1.0

        cls._ok("core", objects=[fixtures.mesh_object(1, bowl)], build_items=[{"objectid": 1}])
        cls._ok(
            "named_with_entities",
            objects=[fixtures.mesh_object(1, _box(), name="Bowl & <Co> \"x\"")],
            build_items=[{"objectid": 1}],
        )
        cls._ok(
            "metre_transforms",
            unit="meter",
            objects=[
                fixtures.mesh_object(1, metre),
                fixtures.component_object(2, [{"objectid": 1, "transform": rotation}]),
            ],
            build_items=[{"objectid": 2, "transform": shift}],
        )
        cls._ok(
            "production_path",
            objects=[
                fixtures.mesh_object(1, _box((3.0, 3.0, 3.0)), name="Decoy"),
                fixtures.component_object(
                    2, [{"objectid": 1, "path": "/3D/Objects/object_1.model"}]
                ),
            ],
            build_items=[{"objectid": 2}],
            extra_parts={"3D/Objects/object_1.model": [fixtures.mesh_object(1, bowl)]},
        )
        cls._ok(
            "reuse",
            objects=[
                fixtures.mesh_object(1, _box()),
                fixtures.component_object(
                    2,
                    [
                        {"objectid": 1},
                        {"objectid": 1, "transform": fixtures.translation_matrix(20.0, 0.0, 0.0)},
                    ],
                ),
            ],
            build_items=[{"objectid": 2}],
        )
        cls._ok(
            "mirrored",
            objects=[
                fixtures.mesh_object(1, bowl),
                fixtures.component_object(2, [{"objectid": 1, "transform": mirror}]),
            ],
            build_items=[{"objectid": 2}],
        )
        cls._ok(
            "inch_unit",
            unit="inch",
            objects=[fixtures.mesh_object(1, _box())],
            build_items=[{"objectid": 1}],
        )
        cls._ok(
            "stored_entries_and_a_thumbnail",
            objects=[fixtures.mesh_object(1, bowl)],
            build_items=[{"objectid": 1}],
            compression=zipfile.ZIP_STORED,
            extra_files={"Metadata/thumbnail.png": b"\x89PNG" + bytes(2048)},
        )
        cls._ok(
            "no_rels_default_part",
            objects=[fixtures.mesh_object(1, _box())],
            build_items=[{"objectid": 1}],
            with_rels=False,
        )

        cls._reject(
            "two_items",
            ("single-object", "2"),
            objects=[fixtures.mesh_object(1, _box()), fixtures.mesh_object(2, _box())],
            build_items=[{"objectid": 1}, {"objectid": 2}],
        )
        cls._reject(
            "no_items", ("build item",), objects=[fixtures.mesh_object(1, _box())], build_items=[]
        )
        cls._reject(
            "support_type",
            ("5", "support"),
            objects=[fixtures.mesh_object(5, _box(), type="support")],
            build_items=[{"objectid": 5}],
        )
        cls._reject(
            "cycle",
            ("cycle",),
            objects=[
                fixtures.component_object(1, [{"objectid": 2}]),
                fixtures.component_object(2, [{"objectid": 1}]),
            ],
            build_items=[{"objectid": 1}],
        )
        deep = [fixtures.component_object(i, [{"objectid": i + 1}]) for i in range(1, 20)]
        deep.append(fixtures.mesh_object(20, _box()))
        cls._reject("too_deep", ("nesting",), objects=deep, build_items=[{"objectid": 1}])
        cls._reject(
            "missing_part",
            ("missing.model",),
            objects=[
                fixtures.component_object(
                    2, [{"objectid": 1, "path": "/3D/Objects/missing.model"}]
                )
            ],
            build_items=[{"objectid": 2}],
        )
        cls._reject(
            "dotdot",
            ("path",),
            objects=[fixtures.component_object(2, [{"objectid": 1, "path": "/../outside.model"}])],
            build_items=[{"objectid": 2}],
        )
        cls._reject(
            "missing_object",
            ("99",),
            objects=[fixtures.mesh_object(1, _box())],
            build_items=[{"objectid": 99}],
        )
        cls._reject(
            "unknown_unit",
            ("parsec", "unit"),
            unit="parsec",
            objects=[fixtures.mesh_object(1, _box())],
            build_items=[{"objectid": 1}],
        )
        cls._reject(
            "doctype",
            ("doctype",),
            objects=[fixtures.mesh_object(1, _box())],
            build_items=[{"objectid": 1}],
            extra_files={
                "3D/3dmodel.model": (
                    b'<?xml version="1.0"?><!DOCTYPE x [<!ENTITY a "b">]>'
                    b'<model xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">'
                    b"<resources/><build/></model>"
                )
            },
        )
        cls._reject(
            "kintsugi_assembly",
            ("kintsugi",),
            objects=[
                fixtures.component_object(1, [{"objectid": 2}, {"objectid": 3}]),
                fixtures.mesh_object(2, _box(), name="CeramicBody"),
                fixtures.mesh_object(3, _box((2.0, 2.0, 2.0)), name="GoldSeams"),
            ],
            build_items=[{"objectid": 1}],
        )
        cls._reject(
            "modifier_prusa",
            ("modifier",),
            objects=[fixtures.mesh_object(1, _box())],
            build_items=[{"objectid": 1}],
            extra_files={
                "Metadata/Slic3r_PE_model.config": (
                    b'<config><object id="1"><volume firstid="0" lastid="11">'
                    b'<metadata type="volume" key="volume_type" value="ParameterModifier"/>'
                    b"</volume></object></config>"
                )
            },
        )
        cls._reject(
            "modifier_bambu",
            ("modifier",),
            objects=[fixtures.mesh_object(1, _box())],
            build_items=[{"objectid": 1}],
            extra_files={
                "Metadata/model_settings.config": (
                    b'<config><object id="1"><part id="1" subtype="negative_part"></part></object></config>'
                )
            },
        )
        cls._reject("not_a_zip", ("zip",), raw_bytes=b"this is definitely not a zip archive")
        core_bytes = cls.ok_cases["core"].read_bytes()
        cls._reject("truncated_zip", ("zip",), raw_bytes=core_bytes[: len(core_bytes) // 2])

    @classmethod
    def _run_node(cls) -> dict:
        health = {"max_upload_bytes": 4 * MIB, "accepted_formats": [".stl", ".obj", ".3mf"]}
        job = {
            "threemf": [
                {"name": name, "file": str(path)}
                for name, path in {
                    **cls.ok_cases,
                    **{n: p for n, (p, _) in cls.reject_cases.items()},
                }.items()
            ]
            + [
                # The preview applies its own uncompressed-size cap from the zip headers.
                {
                    "name": "size_cap",
                    "file": str(cls.ok_cases["core"]),
                    "limits": {"maxUncompressedBytes": 1024},
                }
            ],
            "upload": [
                {"name": "within", "file_name": "bowl.stl", "size": 3 * MIB, "health": health},
                {"name": "over", "file_name": "big.stl", "size": 6 * MIB, "health": health},
                {"name": "exact", "file_name": "edge.3mf", "size": 4 * MIB, "health": health},
                {"name": "one_byte_over", "file_name": "edge.stl", "size": 4 * MIB + 1, "health": health},
                {"name": "bad_suffix", "file_name": "model.ply", "size": 10, "health": health},
                {"name": "upper_case", "file_name": "MODEL.STL", "size": 10, "health": health},
                {"name": "no_health", "file_name": "huge.stl", "size": 51 * MIB},
                {"name": "bad_health", "file_name": "x.stl", "size": 5 * MIB,
                 "health": {"max_upload_bytes": "lots", "accepted_formats": "stl"}},
            ],
            "subtitle": [
                {"name": "hosted", "health": health},
                {"name": "unknown"},
                {"name": "local", "health": {"max_upload_bytes": 50 * MIB,
                                             "accepted_formats": [".stl", ".obj", ".3mf"]}},
            ],
            "engine": {
                "resolve": [
                    {"name": "same_origin", "path": "/api/health", "base": ""},
                    {"name": "companion_api", "path": "/api/health",
                     "base": "http://127.0.0.1:8000"},
                    {"name": "companion_outputs", "path": "/outputs/job/ceramic_body.stl",
                     "base": "http://127.0.0.1:8000/"},
                    {"name": "no_leading_slash", "path": "outputs/gold_seams.stl",
                     "base": "http://127.0.0.1:8001"},
                    {"name": "absolute", "path": "https://cdn.example/x.stl",
                     "base": "http://127.0.0.1:8000"},
                ],
                "static_presets": [
                    {"name": "disconnected", "indexFile": str(STATIC_PRESETS), "base": ""},
                    {"name": "companion", "indexFile": str(STATIC_PRESETS),
                     "base": "http://127.0.0.1:8001"},
                ],
                "probes": [
                    {"name": "first_port", "ports": list(range(8000, 8010)),
                     "responses": {"8000": {"status": 200, "body": {
                         "service": "kintsugi-studio", "api_version": "1.0"}}}},
                    {"name": "fallback_port", "ports": list(range(8000, 8010)),
                     "responses": {"8001": {"status": 200, "body": {
                         "service": "kintsugi-studio", "api_version": "1.0"}}}},
                    {"name": "wrong_service", "ports": [8000, 8001],
                     "responses": {
                         "8000": {"status": 200, "body": {"service": "other"}},
                         "8001": {"status": 200, "body": {
                             "service": "kintsugi-studio", "api_version": "1.0"}}}},
                    {"name": "unreachable",
                     "responses": {}},
                ],
                "versions": [
                    {"name": "match", "version": "1.0"},
                    {"name": "minor", "version": "1.7"},
                    {"name": "major_mismatch", "version": "2.0"},
                    {"name": "missing", "version": None},
                ],
            },
        }
        job_path = cls.dir / "job.json"
        job_path.write_text(json.dumps(job), encoding="utf-8")
        completed = subprocess.run(
            ["node", str(RUNNER), str(job_path)],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(cls.dir),
        )
        if completed.returncode != 0:
            raise RuntimeError(f"node runner failed:\n{completed.stderr}")
        return json.loads(completed.stdout)

    def _threemf(self, name: str) -> dict:
        return next(item for item in self.results["threemf"] if item["name"] == name)

    # -- 3MF parity -------------------------------------------------------------
    def test_preview_geometry_matches_the_server_reader(self) -> None:
        for name, path in self.ok_cases.items():
            with self.subTest(case=name):
                js = self._threemf(name)
                self.assertTrue(js["ok"], js)
                expected = mesh_formats.load_3mf(path)
                self.assertEqual(js["triangles"], len(expected.faces))
                np.testing.assert_allclose(
                    np.asarray(js["positions"]), _soup(expected), atol=1e-3, rtol=1e-6
                )

    def test_preview_rejects_what_the_server_rejects_with_the_same_reason(self) -> None:
        for name, (path, needles) in self.reject_cases.items():
            with self.subTest(case=name):
                with self.assertRaises(ValueError) as server:
                    mesh_formats.load_3mf(path)
                js = self._threemf(name)
                self.assertFalse(js["ok"], f"preview accepted {name}")
                for needle in needles:
                    self.assertIn(needle.lower(), str(server.exception).lower())
                    self.assertIn(needle.lower(), js["error"].lower())

    def test_preview_enforces_the_uncompressed_size_cap_from_zip_headers(self) -> None:
        js = self._threemf("size_cap")
        self.assertFalse(js["ok"], js)
        self.assertIn("too large", js["error"].lower())

    def test_mirrored_preview_keeps_outward_winding(self) -> None:
        js = self._threemf("mirrored")
        soup = np.asarray(js["positions"]).reshape(-1, 3, 3)
        # Signed volume of a closed outward-oriented mesh is positive.
        volume = np.einsum("ij,ij->i", soup[:, 0], np.cross(soup[:, 1], soup[:, 2])).sum() / 6.0
        self.assertGreater(volume, 0.0)

    # -- upload pre-flight ------------------------------------------------------
    def _upload(self, name: str) -> dict:
        return next(item for item in self.results["upload"] if item["name"] == name)

    def test_files_within_the_limit_are_allowed(self) -> None:
        for name in ("within", "exact", "upper_case"):
            with self.subTest(case=name):
                self.assertIsNone(self._upload(name)["message"])

    def test_over_limit_message_names_size_and_limit(self) -> None:
        message = self._upload("over")["message"]
        self.assertIn("big.stl is 6.0 MB", message)
        self.assertIn("up to 4.0 MB", message)
        self.assertIn("binary STL or 3MF", message)
        self.assertIsNotNone(self._upload("one_byte_over")["message"])

    def test_unsupported_suffix_message_lists_formats(self) -> None:
        message = self._upload("bad_suffix")["message"]
        self.assertEqual(message, "model.ply: unsupported format. Use .stl, .obj or .3mf.")

    def test_missing_or_malformed_health_falls_back_to_defaults(self) -> None:
        no_health = self._upload("no_health")
        self.assertFalse(no_health["limits"]["known"])
        self.assertEqual(no_health["limits"]["maxUploadBytes"], 50 * MIB)
        self.assertIn("51.0 MB", no_health["message"])
        bad = self._upload("bad_health")
        self.assertEqual(bad["limits"]["maxUploadBytes"], 50 * MIB)
        self.assertEqual(bad["limits"]["acceptedFormats"], [".stl", ".obj", ".3mf"])
        self.assertIsNone(bad["message"])

    def test_upload_zone_subtitle(self) -> None:
        texts = {item["name"]: item["text"] for item in self.results["subtitle"]}
        self.assertEqual(texts["hosted"], ".stl, .obj or .3mf · watertight only · up to 4.0 MB")
        self.assertEqual(texts["local"], ".stl, .obj or .3mf · watertight only · up to 50.0 MB")
        self.assertEqual(texts["unknown"], ".stl, .obj or .3mf · watertight only")

    # -- companion engine helpers ----------------------------------------------
    def _engine(self, section: str, name: str) -> dict:
        return next(
            item for item in self.results["engine"][section] if item["name"] == name
        )

    def test_resolve_engine_url_keeps_same_origin_paths_relative(self) -> None:
        self.assertEqual(
            self._engine("resolve", "same_origin")["url"], "/api/health"
        )

    def test_resolve_engine_url_prefixes_companion_api_and_outputs(self) -> None:
        self.assertEqual(
            self._engine("resolve", "companion_api")["url"],
            "http://127.0.0.1:8000/api/health",
        )
        self.assertEqual(
            self._engine("resolve", "companion_outputs")["url"],
            "http://127.0.0.1:8000/outputs/job/ceramic_body.stl",
        )
        self.assertEqual(
            self._engine("resolve", "no_leading_slash")["url"],
            "http://127.0.0.1:8001/outputs/gold_seams.stl",
        )

    def test_resolve_engine_url_does_not_rewrite_absolute_urls(self) -> None:
        self.assertEqual(
            self._engine("resolve", "absolute")["url"],
            "https://cdn.example/x.stl",
        )

    def test_static_preset_manifest_populates_all_bundled_presets(self) -> None:
        self.assertTrue(STATIC_PRESETS.exists(), STATIC_PRESETS)
        static = self._engine("static_presets", "disconnected")
        self.assertEqual(static["ids"], ["tea_bowl", "benchy", "vase"])
        for preset in static["presets"]:
            self.assertTrue(preset["name"])
            self.assertTrue(preset["description"])
            self.assertTrue(preset["mesh_url"].startswith("/presets/"))
            self.assertTrue(preset["mesh_url"].endswith(".stl"))

    def test_static_preset_manifest_qualifies_mesh_urls_for_a_companion(self) -> None:
        companion = self._engine("static_presets", "companion")
        for url in companion["meshUrls"]:
            self.assertTrue(url.startswith("http://127.0.0.1:8001/presets/"), url)

    def test_probe_engine_reuses_a_running_engine_on_the_first_port(self) -> None:
        probe = self._engine("probes", "first_port")
        self.assertTrue(probe["ok"], probe)
        self.assertEqual(probe["port"], 8000)
        self.assertEqual(probe["baseUrl"], "http://127.0.0.1:8000")
        self.assertEqual(probe["attempts"], [8000])
        self.assertEqual(probe["apiVersion"], "1.0")
        self.assertTrue(probe["compatible"])

    def test_probe_engine_falls_forward_across_the_port_range(self) -> None:
        probe = self._engine("probes", "fallback_port")
        self.assertTrue(probe["ok"], probe)
        self.assertEqual(probe["port"], 8001)
        self.assertEqual(probe["attempts"], [8000, 8001])

    def test_probe_engine_skips_a_non_kintsugi_service(self) -> None:
        probe = self._engine("probes", "wrong_service")
        self.assertTrue(probe["ok"], probe)
        self.assertEqual(probe["port"], 8001)
        self.assertEqual(probe["attempts"], [8000, 8001])

    def test_probe_engine_reports_unreachable_ports(self) -> None:
        probe = self._engine("probes", "unreachable")
        self.assertFalse(probe["ok"], probe)
        self.assertIn("8000-8009", probe["error"])

    def test_api_version_requires_a_matching_major(self) -> None:
        self.assertTrue(self._engine("versions", "match")["compatible"])
        self.assertTrue(self._engine("versions", "minor")["compatible"])
        self.assertFalse(self._engine("versions", "major_mismatch")["compatible"])
        self.assertFalse(self._engine("versions", "missing")["compatible"])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
