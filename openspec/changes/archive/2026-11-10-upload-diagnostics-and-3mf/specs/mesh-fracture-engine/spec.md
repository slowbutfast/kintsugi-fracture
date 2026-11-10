## ADDED Requirements

### Requirement: 3MF package input
The system SHALL load a `.3mf` input into one flattened millimetre mesh before the supported input envelope is checked. It SHALL use only the Python standard library (`zipfile`, `xml.etree`) plus the existing numpy/trimesh dependencies. The reader SHALL:

1. Locate the root model through the package relationship in `_rels/.rels` (`http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel`), falling back to `3D/3dmodel.model` when that relationship is absent.
2. Require exactly one `<build><item>`.
3. Resolve objects recursively from that item:
   - mesh objects contribute their `<vertices>` and `<triangles>`;
   - component objects contribute their referenced objects, each under its own `transform`;
   - a component with a Production-extension `p:path` SHALL resolve its `objectid` inside that package part, not by bare id across parts.
4. Compose transforms (component transforms nested inside the build-item transform). Each transform is a 3MF row-major 4×3 affine, with the translation in the last three values.
5. Convert coordinates to millimetres from the root model's `unit` attribute (`micron` 0.001, `millimeter` 1, `centimeter` 10, `inch` 25.4, `foot` 304.8, `meter` 1000; default `millimeter`).
6. Ignore materials, colours, textures, thumbnails and metadata.
7. Return a single `trimesh.Trimesh` with `process=False`, so no merging or repair happens before `_clean_mesh` runs inside validation.

The existing input envelope (closed solid, millimetre extents within [20, 300], vessel, wall thickness) SHALL then apply unchanged.

The reader SHALL treat the package as untrusted. It SHALL read each entry through a bounded read that stops at the entry's declared size (an honest entry never decompresses to more) and at the remaining decompressed-size budget of 512 MiB for the package, and SHALL NOT decompress an entry in full before checking its size. Any error the zip layer raises for a damaged or unsupported entry SHALL surface as a `ValueError`, never as another exception type, so that callers report an invalid model and not a server error.

The reader SHALL raise a `ValueError` naming the problem when:
- the file is not a ZIP;
- an entry is damaged: it fails its CRC, its compressed stream is corrupt, its header understates its real size, or it uses an unsupported compression method;
- the decompressed package exceeds the 512 MiB budget;
- no root model can be found;
- the build has zero or more than one item;
- a referenced object, part or `p:path` target is missing or points outside the package;
- any reachable object has a `type` other than `model`;
- the `unit` value is unknown;
- component nesting exceeds 16 levels or contains a cycle;
- no triangles are reachable;
- the package is our own Kintsugi assembly, meaning the reachable mesh objects are exactly those named `CeramicBody` and `GoldSeams`.

#### Scenario: Single-object core 3MF loads in millimetres
- **WHEN** a 3MF whose root model has `unit="millimeter"`, one build item, and one mesh object containing a closed bowl is passed to `validate_and_load_mesh`
- **THEN** the loaded mesh has the same vertex positions and face count as the source object, and validation proceeds exactly as for the equivalent STL

#### Scenario: Metre unit and transforms are applied
- **WHEN** a 3MF with `unit="meter"` places the bowl through a build-item transform (translation) and a component transform (rotation)
- **THEN** the flattened mesh equals the bowl with both transforms composed and coordinates multiplied by 1000, within 1e-6 mm

#### Scenario: Production-extension part resolved by path
- **WHEN** the root model's single object is a component with `p:path="/3D/Objects/object_1.model"` and `objectid="1"`, while the root model also defines an unrelated object with id `1`
- **THEN** the reader loads the mesh from `/3D/Objects/object_1.model`, not the root object with the same id

#### Scenario: Multiple build items rejected
- **WHEN** a 3MF has two build items
- **THEN** a `ValueError` states that only single-object 3MF files are supported and reports the item count

#### Scenario: Non-model object type rejected
- **WHEN** a reachable object has `type="support"` or `type="other"`
- **THEN** a `ValueError` names the object id and its type

#### Scenario: Kintsugi assembly rejected
- **WHEN** the input is a `kintsugi_assembly.3mf` produced by `export_kintsugi_3mf`
- **THEN** a `ValueError` states that the file is already a Kintsugi output and asks for the original model

#### Scenario: Malformed package rejected
- **WHEN** the input is not a ZIP, has no root model, references a missing object, uses an unknown unit, or contains a component cycle
- **THEN** a `ValueError` names the specific problem, and no partial mesh is returned

#### Scenario: Entry whose header understates its size
- **WHEN** a package of about 200 KB declares a 1,000-byte model part in its zip header but the part's compressed stream expands to 200 MiB
- **THEN** a `ValueError` states that the part is corrupt, and the reader decompresses only about the declared size (peak memory does not grow by the real size)

#### Scenario: Damaged or unsupported entry rejected as an invalid model
- **WHEN** a model part has a corrupt deflate stream, a wrong CRC, or an unsupported compression method
- **THEN** a `ValueError` names the part and says it is corrupt or unsupported, and `POST /api/validate` answers `valid: false` with that detail instead of an HTTP 500

#### Scenario: Honest oversized package rejected
- **WHEN** a package's parts really decompress to more than the 512 MiB budget
- **THEN** a `ValueError` states that the package is too large when uncompressed
