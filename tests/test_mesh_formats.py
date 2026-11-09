"""3MF package input: the dependency-free reader in ``mesh_formats``."""

from __future__ import annotations

import struct
import tempfile
import tracemalloc
import unittest
import zipfile
from pathlib import Path
from unittest import mock

import numpy as np
import trimesh

import kintsugi
from tests import fixtures

try:  # Written after the tests (TDD); import errors are the expected red state.
    import mesh_formats
except ImportError:  # pragma: no cover - only before the reader exists
    mesh_formats = None


UNIT_FACTORS = {
    "micron": 0.001,
    "millimeter": 1.0,
    "centimeter": 10.0,
    "inch": 25.4,
    "foot": 304.8,
    "meter": 1000.0,
}


def _box(extent=(10.0, 10.0, 10.0)) -> trimesh.Trimesh:
    box = trimesh.creation.box(extents=extent)
    return trimesh.Trimesh(
        vertices=np.asarray(box.vertices, dtype=np.float64),
        faces=np.asarray(box.faces),
        process=False,
    )


class MeshFormatsTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory(prefix="kintsugi-3mf-")
        cls.dir = Path(cls._tmp.name)
        cls.bowl = fixtures.manifold_to_trimesh(fixtures.bowl_manifold())

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def setUp(self) -> None:
        if mesh_formats is None:
            self.fail("mesh_formats module does not exist yet")

    # -- helpers -------------------------------------------------------------
    def _path(self, name: str = "model") -> Path:
        MeshFormatsTestCase._n = getattr(MeshFormatsTestCase, "_n", 0) + 1
        return self.dir / f"{name}-{MeshFormatsTestCase._n}.3mf"

    def _load(self, path):
        return mesh_formats.load_3mf(path)

    def assertRejects(self, path, *needles: str) -> None:
        with self.assertRaises(ValueError) as ctx:
            self._load(path)
        message = str(ctx.exception).lower()
        for needle in needles:
            self.assertIn(needle.lower(), message, f"message was: {ctx.exception}")

    # -- core load -------------------------------------------------------------
    def test_single_object_millimetre_load_matches_source(self) -> None:
        path = self._path("core")
        source = fixtures.write_bowl_3mf(path)
        loaded = self._load(path)
        self.assertIsInstance(loaded, trimesh.Trimesh)
        np.testing.assert_array_equal(loaded.vertices, source.vertices)
        np.testing.assert_array_equal(loaded.faces, source.faces)

    def test_missing_unit_attribute_defaults_to_millimetre(self) -> None:
        path = self._path("nounit")
        fixtures.build_3mf(
            path,
            objects=[fixtures.mesh_object(1, self.bowl)],
            build_items=[{"objectid": 1}],
            unit=None,
        )
        np.testing.assert_array_equal(self._load(path).vertices, self.bowl.vertices)

    def test_every_unit_maps_to_its_millimetre_factor(self) -> None:
        for unit, factor in UNIT_FACTORS.items():
            with self.subTest(unit=unit):
                path = self._path(unit)
                fixtures.build_3mf(
                    path,
                    objects=[fixtures.mesh_object(1, _box())],
                    build_items=[{"objectid": 1}],
                    unit=unit,
                )
                np.testing.assert_allclose(
                    self._load(path).vertices, _box().vertices * factor, atol=1e-9
                )

    def test_unknown_unit_rejected(self) -> None:
        path = self._path("badunit")
        fixtures.build_3mf(
            path,
            objects=[fixtures.mesh_object(1, _box())],
            build_items=[{"objectid": 1}],
            unit="parsec",
        )
        self.assertRejects(path, "parsec", "unit")

    # -- units and transforms --------------------------------------------------
    def test_metre_unit_and_composed_transforms(self) -> None:
        metre_bowl = self.bowl.copy()
        metre_bowl.apply_scale(0.001)
        rotation = fixtures.rotation_z_matrix(90.0)
        item_shift = fixtures.translation_matrix(0.010, 0.020, 0.0)
        path = self._path("transforms")
        fixtures.build_3mf(
            path,
            unit="meter",
            objects=[
                fixtures.mesh_object(1, metre_bowl, name="Bowl"),
                fixtures.component_object(
                    2, [{"objectid": 1, "transform": rotation}]
                ),
            ],
            build_items=[{"objectid": 2, "transform": item_shift}],
        )
        expected = fixtures.apply_row_matrix(
            fixtures.apply_row_matrix(metre_bowl.vertices, rotation), item_shift
        ) * 1000.0
        np.testing.assert_allclose(self._load(path).vertices, expected, atol=1e-6)

    def test_object_reused_by_two_components_keeps_both_copies(self) -> None:
        path = self._path("reuse")
        fixtures.build_3mf(
            path,
            objects=[
                fixtures.mesh_object(1, _box()),
                fixtures.component_object(
                    2,
                    [
                        {"objectid": 1},
                        {
                            "objectid": 1,
                            "transform": fixtures.translation_matrix(20.0, 0.0, 0.0),
                        },
                    ],
                ),
            ],
            build_items=[{"objectid": 2}],
        )
        loaded = self._load(path)
        # No-repair contract: process=False, so duplicate vertices are kept.
        self.assertEqual(len(loaded.vertices), 16)
        self.assertEqual(len(loaded.faces), 24)
        self.assertAlmostEqual(float(loaded.vertices[:, 0].max()), 25.0)

    def test_mirrored_transform_keeps_outward_winding(self) -> None:
        mirror = np.eye(4)
        mirror[0, 0] = -1.0
        path = self._path("mirror")
        fixtures.build_3mf(
            path,
            objects=[
                fixtures.mesh_object(1, self.bowl),
                fixtures.component_object(2, [{"objectid": 1, "transform": mirror}]),
            ],
            build_items=[{"objectid": 2}],
        )
        loaded = self._load(path)
        self.assertGreater(loaded.volume, 0.0)
        self.assertAlmostEqual(loaded.volume, self.bowl.volume, delta=1e-6 * self.bowl.volume)

    # -- production extension ----------------------------------------------------
    def test_production_path_resolves_by_path_not_bare_id(self) -> None:
        decoy = _box((3.0, 3.0, 3.0))
        path = self._path("production")
        fixtures.build_3mf(
            path,
            objects=[
                fixtures.mesh_object(1, decoy, name="Decoy"),
                fixtures.component_object(
                    2,
                    [{"objectid": 1, "path": "/3D/Objects/object_1.model"}],
                ),
            ],
            build_items=[{"objectid": 2}],
            extra_parts={
                "3D/Objects/object_1.model": [
                    fixtures.mesh_object(1, self.bowl, name="Bowl")
                ]
            },
        )
        loaded = self._load(path)
        np.testing.assert_array_equal(loaded.vertices, self.bowl.vertices)

    def test_production_path_to_missing_part_rejected(self) -> None:
        path = self._path("missingpart")
        fixtures.build_3mf(
            path,
            objects=[
                fixtures.component_object(
                    2, [{"objectid": 1, "path": "/3D/Objects/missing.model"}]
                )
            ],
            build_items=[{"objectid": 2}],
        )
        self.assertRejects(path, "missing.model")

    def test_production_path_with_parent_segments_rejected(self) -> None:
        for target in ("/../outside.model", "/3D/../3D/Objects/object_1.model"):
            with self.subTest(target=target):
                path = self._path("dotdot")
                fixtures.build_3mf(
                    path,
                    objects=[
                        fixtures.component_object(
                            2, [{"objectid": 1, "path": target}]
                        )
                    ],
                    build_items=[{"objectid": 2}],
                    extra_parts={
                        "3D/Objects/object_1.model": [fixtures.mesh_object(1, _box())]
                    },
                )
                self.assertRejects(path, "path")

    # -- rejections ---------------------------------------------------------------
    def test_two_build_items_rejected(self) -> None:
        path = self._path("twoitems")
        fixtures.build_3mf(
            path,
            objects=[fixtures.mesh_object(1, _box()), fixtures.mesh_object(2, _box())],
            build_items=[{"objectid": 1}, {"objectid": 2}],
        )
        self.assertRejects(path, "single-object", "2")

    def test_zero_build_items_rejected(self) -> None:
        path = self._path("noitems")
        fixtures.build_3mf(
            path, objects=[fixtures.mesh_object(1, _box())], build_items=[]
        )
        self.assertRejects(path, "build item")

    def test_non_model_object_type_rejected(self) -> None:
        for object_type in ("support", "other", "solidsupport", "surface"):
            with self.subTest(type=object_type):
                path = self._path("type")
                fixtures.build_3mf(
                    path,
                    objects=[fixtures.mesh_object(5, _box(), type=object_type)],
                    build_items=[{"objectid": 5}],
                )
                self.assertRejects(path, "5", object_type)

    def test_unreachable_non_model_object_is_ignored(self) -> None:
        path = self._path("unreachable")
        fixtures.build_3mf(
            path,
            objects=[
                fixtures.mesh_object(1, self.bowl),
                fixtures.mesh_object(9, _box(), type="support"),
            ],
            build_items=[{"objectid": 1}],
        )
        np.testing.assert_array_equal(self._load(path).vertices, self.bowl.vertices)

    def test_missing_object_id_rejected(self) -> None:
        path = self._path("missingid")
        fixtures.build_3mf(
            path, objects=[fixtures.mesh_object(1, _box())], build_items=[{"objectid": 99}]
        )
        self.assertRejects(path, "99")

    def test_component_cycle_rejected(self) -> None:
        path = self._path("cycle")
        fixtures.build_3mf(
            path,
            objects=[
                fixtures.component_object(1, [{"objectid": 2}]),
                fixtures.component_object(2, [{"objectid": 1}]),
            ],
            build_items=[{"objectid": 1}],
        )
        self.assertRejects(path, "cycle")

    def test_component_nesting_depth_limit(self) -> None:
        def chain(length: int):
            objects = [
                fixtures.component_object(i, [{"objectid": i + 1}])
                for i in range(1, length)
            ]
            objects.append(fixtures.mesh_object(length, _box()))
            return objects

        shallow = self._path("shallow")
        fixtures.build_3mf(shallow, objects=chain(5), build_items=[{"objectid": 1}])
        self.assertEqual(len(self._load(shallow).faces), 12)

        deep = self._path("deep")
        fixtures.build_3mf(deep, objects=chain(20), build_items=[{"objectid": 1}])
        self.assertRejects(deep, "nesting")

    def test_not_a_zip_rejected(self) -> None:
        path = self._path("notzip")
        path.write_bytes(b"this is definitely not a zip archive")
        self.assertRejects(path, "zip")

    def test_missing_root_model_rejected(self) -> None:
        path = self._path("noroot")
        fixtures.build_3mf(
            path,
            objects=[fixtures.mesh_object(1, _box())],
            build_items=[{"objectid": 1}],
            root_part="3D/other.model",
            with_rels=False,
        )
        self.assertRejects(path, "root model")

    def test_doctype_rejected_before_parsing(self) -> None:
        hostile = (
            b'<?xml version="1.0"?><!DOCTYPE lolz [<!ENTITY a "aaaa">]>'
            b'<model xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">'
            b"<resources/><build/></model>"
        )
        path = self._path("doctype")
        fixtures.build_3mf(
            path,
            objects=[fixtures.mesh_object(1, _box())],
            build_items=[{"objectid": 1}],
            extra_files={"3D/3dmodel.model": hostile},
        )
        self.assertRejects(path, "doctype")

    def test_empty_mesh_rejected(self) -> None:
        empty = trimesh.Trimesh(
            vertices=np.zeros((0, 3)), faces=np.zeros((0, 3), dtype=np.int64), process=False
        )
        path = self._path("empty")
        fixtures.build_3mf(
            path, objects=[fixtures.mesh_object(1, empty)], build_items=[{"objectid": 1}]
        )
        self.assertRejects(path, "triangle")

    def test_out_of_range_triangle_index_rejected(self) -> None:
        raw = (
            '<?xml version="1.0"?>'
            '<model xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02" unit="millimeter">'
            '<resources><object id="1" type="model"><mesh>'
            '<vertices><vertex x="0" y="0" z="0"/><vertex x="1" y="0" z="0"/><vertex x="0" y="1" z="0"/></vertices>'
            '<triangles><triangle v1="0" v2="1" v3="7"/></triangles>'
            "</mesh></object></resources>"
            '<build><item objectid="1"/></build></model>'
        ).encode("utf-8")
        path = self._path("badindex")
        fixtures.build_3mf(
            path,
            objects=[fixtures.mesh_object(1, _box())],
            build_items=[{"objectid": 1}],
            extra_files={"3D/3dmodel.model": raw},
        )
        self.assertRejects(path, "vertex")

    def test_size_caps_are_enforced(self) -> None:
        path = self._path("caps")
        fixtures.write_bowl_3mf(path)
        with mock.patch.object(mesh_formats, "MAX_UNCOMPRESSED_BYTES", 1024):
            self.assertRejects(path, "large")
        with mock.patch.object(mesh_formats, "MAX_TRIANGLES", 10):
            self.assertRejects(path, "triangle")

    # -- hostile or damaged packages (PATCH-01) -----------------------------------
    def _patch_central(self, path, name, *, method=None, crc=None, file_size=None) -> None:
        """Rewrite fields of one zip central-directory entry (headers can lie)."""
        data = bytearray(Path(path).read_bytes())
        position = 0
        while True:
            position = data.find(b"PK\x01\x02", position)
            self.assertGreaterEqual(position, 0, f"central entry {name} not found")
            name_length = struct.unpack_from("<H", data, position + 28)[0]
            if bytes(data[position + 46 : position + 46 + name_length]).decode() == name:
                break
            position += 4
        if method is not None:
            struct.pack_into("<H", data, position + 10, method)
        if crc is not None:
            struct.pack_into("<I", data, position + 16, crc)
        if file_size is not None:
            struct.pack_into("<I", data, position + 24, file_size)
        Path(path).write_bytes(bytes(data))

    def test_understated_size_header_cannot_force_a_large_decompression(self) -> None:
        # ~64 MiB of XML whitespace deflates to tens of KiB; the zip header
        # claims 1,000 bytes.  The declared-size sum cannot be trusted.
        path = self._path("bomb")
        expanded = b"<model>" + b" " * (64 * 1024 * 1024)
        fixtures.build_3mf(
            path,
            objects=[fixtures.mesh_object(1, _box())],
            build_items=[{"objectid": 1}],
            extra_files={"3D/3dmodel.model": expanded},
        )
        self.assertLess(path.stat().st_size, 1024 * 1024)
        self._patch_central(path, "3D/3dmodel.model", file_size=1000)
        tracemalloc.start()
        try:
            with mock.patch.object(mesh_formats, "MAX_UNCOMPRESSED_BYTES", 8 * 1024 * 1024):
                with self.assertRaises(ValueError) as ctx:
                    self._load(path)
            peak = tracemalloc.get_traced_memory()[1]
        finally:
            tracemalloc.stop()
        self.assertIn("corrupt", str(ctx.exception).lower())
        # Inflating the whole entry would peak at 64 MiB or more; the cut-off is
        # the declared size (1,000 bytes) plus one.
        self.assertLess(peak, 2 * 1024 * 1024, f"peak traced memory {peak} bytes")

    def test_honestly_declared_large_part_still_hits_the_budget(self) -> None:
        # No lie here: the declared size is the real size, so the budget decides.
        path = self._path("honestbig")
        fixtures.build_3mf(
            path,
            objects=[fixtures.mesh_object(1, _box())],
            build_items=[{"objectid": 1}],
            extra_files={"3D/3dmodel.model": b"<model>" + b" " * (4 * 1024 * 1024)},
        )
        with mock.patch.object(mesh_formats, "MAX_UNCOMPRESSED_BYTES", 1024 * 1024):
            self.assertRejects(path, "too large")

    def test_corrupt_deflate_stream_is_a_value_error(self) -> None:
        path = self._path("corrupt")
        fixtures.write_bowl_3mf(path)
        info = zipfile.ZipFile(path).getinfo("3D/3dmodel.model")
        data = bytearray(path.read_bytes())
        start = info.header_offset + 30 + len(info.filename.encode()) + len(info.extra)
        middle = start + info.compress_size // 2
        for offset in range(middle, middle + 8):
            data[offset] ^= 0xFF
        path.write_bytes(bytes(data))
        self.assertRejects(path, "corrupt", "3D/3dmodel.model")

    def test_wrong_crc_is_a_value_error(self) -> None:
        path = self._path("badcrc")
        fixtures.write_bowl_3mf(path)
        self._patch_central(path, "3D/3dmodel.model", crc=0xDEADBEEF)
        self.assertRejects(path, "corrupt", "3D/3dmodel.model")

    def test_unsupported_compression_method_is_a_value_error(self) -> None:
        path = self._path("method99")
        fixtures.write_bowl_3mf(path)
        self._patch_central(path, "3D/3dmodel.model", method=99)
        self.assertRejects(path, "3D/3dmodel.model", "unsupported")

    def test_oversized_vendor_config_is_skipped_not_fatal(self) -> None:
        path = self._path("bigconfig")
        fixtures.build_3mf(
            path,
            objects=[fixtures.mesh_object(1, self.bowl)],
            build_items=[{"objectid": 1}],
            extra_files={"Metadata/model_settings.config": b"<config>" + b" " * 4096},
        )
        with mock.patch.object(mesh_formats, "MAX_CONFIG_BYTES", 1024):
            np.testing.assert_array_equal(self._load(path).vertices, self.bowl.vertices)

    # -- Kintsugi assembly ------------------------------------------------------
    def test_kintsugi_assembly_rejected(self) -> None:
        stl = self.dir / "assembly-input.stl"
        fixtures.write_bowl(stl)
        out = self.dir / "assembly-out"
        three_mf = self.dir / "kintsugi_assembly.3mf"
        result = kintsugi.generate_kintsugi_mesh(
            stl, out, R=0.5, mode="vein", seed=1, output_3mf_path=three_mf
        )
        self.assertGreater(result["num_cracks"], 0)
        self.assertTrue(three_mf.exists())
        self.assertRejects(three_mf, "kintsugi")

    # -- fallbacks and discovery --------------------------------------------------
    def test_package_without_rels_falls_back_to_default_part(self) -> None:
        path = self._path("norels")
        fixtures.build_3mf(
            path,
            objects=[fixtures.mesh_object(1, self.bowl)],
            build_items=[{"objectid": 1}],
            with_rels=False,
        )
        np.testing.assert_array_equal(self._load(path).vertices, self.bowl.vertices)

    def test_root_model_found_through_relationship(self) -> None:
        path = self._path("altroot")
        fixtures.build_3mf(
            path,
            objects=[fixtures.mesh_object(1, self.bowl)],
            build_items=[{"objectid": 1}],
            root_part="3D/main.model",
        )
        np.testing.assert_array_equal(self._load(path).vertices, self.bowl.vertices)

    # -- slicer modifier / negative volumes ---------------------------------------
    def test_vendor_config_modifier_volumes_rejected(self) -> None:
        cases = {
            "Metadata/Slic3r_PE_model.config": (
                b'<config><object id="1"><volume firstid="0" lastid="11">'
                b'<metadata type="volume" key="volume_type" value="ParameterModifier"/>'
                b"</volume></object></config>"
            ),
            "Metadata/model_settings.config": (
                b'<config><object id="1"><part id="1" subtype="negative_part">'
                b"</part></object></config>"
            ),
        }
        for name, content in cases.items():
            with self.subTest(config=name):
                path = self._path("modifier")
                fixtures.build_3mf(
                    path,
                    objects=[fixtures.mesh_object(1, self.bowl)],
                    build_items=[{"objectid": 1}],
                    extra_files={name: content},
                )
                self.assertRejects(path, "modifier")

    def test_vendor_config_with_only_model_parts_is_accepted(self) -> None:
        path = self._path("benign")
        fixtures.build_3mf(
            path,
            objects=[fixtures.mesh_object(1, self.bowl)],
            build_items=[{"objectid": 1}],
            extra_files={
                "Metadata/Slic3r_PE_model.config": (
                    b'<config><object id="1"><volume firstid="0" lastid="11">'
                    b'<metadata type="volume" key="volume_type" value="ModelPart"/>'
                    b"</volume></object></config>"
                ),
                "Metadata/model_settings.config": (
                    b'<config><object id="1"><part id="1" subtype="normal_part">'
                    b"</part></object></config>"
                ),
            },
        )
        np.testing.assert_array_equal(self._load(path).vertices, self.bowl.vertices)

    # -- integration with the engine -----------------------------------------------
    def test_validate_and_load_mesh_accepts_3mf_like_the_stl(self) -> None:
        stl = self.dir / "bowl-reference.stl"
        fixtures.write_bowl(stl)
        three_mf = self._path("validate")
        fixtures.write_bowl_3mf(three_mf)
        from_stl = kintsugi.validate_and_load_mesh(stl, 0.0)
        from_3mf = kintsugi.validate_and_load_mesh(three_mf, 0.0)
        self.assertEqual(len(from_3mf.mesh.faces), len(from_stl.mesh.faces))
        np.testing.assert_allclose(from_3mf.mesh.extents, from_stl.mesh.extents)
        # Binary STL stores float32 coordinates and the 3MF float64, so the
        # thickness differs by a few micrometres at most.
        self.assertAlmostEqual(
            from_3mf.probe["wall_thickness_p5"],
            from_stl.probe["wall_thickness_p5"],
            delta=1e-4,
        )

    def test_metre_3mf_validates_where_the_metre_stl_is_rejected(self) -> None:
        metre_stl = self.dir / "metre.stl"
        fixtures.write_metre_bowl(metre_stl)
        with self.assertRaises(ValueError):
            kintsugi.validate_and_load_mesh(metre_stl, 0.0)
        metre_3mf = self._path("metre")
        fixtures.write_bowl_3mf(metre_3mf, unit="meter", scale=0.001)
        validation = kintsugi.validate_and_load_mesh(metre_3mf, 0.0)
        np.testing.assert_allclose(validation.mesh.extents, [90.0, 90.0, 60.0], atol=1e-6)

    def test_reader_uses_only_the_standard_library_for_3mf(self) -> None:
        source = Path(mesh_formats.__file__).read_text(encoding="utf-8")
        for banned in ("lxml", "networkx", "defusedxml"):
            self.assertNotIn(f"import {banned}", source)
            self.assertNotIn(f"from {banned}", source)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
