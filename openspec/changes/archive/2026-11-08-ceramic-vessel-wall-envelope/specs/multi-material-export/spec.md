## MODIFIED Requirements

### Requirement: Paired manifold STL export
The system SHALL export aligned binary STL files in the input coordinate frame, and the files SHALL remain watertight after a disk round-trip.

#### Scenario: Inequality fracture export
- **WHEN** $R < 1.0$ and the gold solid is non-empty
- **THEN** system writes binary STL files for both ceramic body and gold seams, and reloading each from disk with `trimesh.load(..., process=True)` reports `is_watertight == True` and `is_volume == True`

#### Scenario: Empty gold solid fallback when R < 1.0
- **WHEN** $R < 1.0$ and the complementary gold boolean has zero triangles or volume
- **THEN** system writes `ceramic_body.stl`, does **not** write `gold_seams.stl`, unlinks any stale file at `gold_seams.stl`, returns `gold_path: None`, `seams_omitted: True`, and sets `triangle_counts.gold: 0` and `volumes.gold: 0.0`

#### Scenario: Wealthy pass-through export
- **WHEN** $R \ge 1.0$
- **THEN** system writes the validated input mesh to `ceramic_body.stl`, does **not** write `gold_seams.stl`, deletes any pre-existing file at the gold output path so that a stale seam from an earlier run cannot be paired with the pristine body, and returns `gold_path: None` and `seams_omitted: False` in the result dict

#### Scenario: Export sliver repair
- **WHEN** a CSG output contains a sub-`10 nm` sliver edge that binary-STL float32 would turn into a four-face edge
- **THEN** the exporter collapses only such tiny edges, and only when the mesh remains watertight, positive-volume and within `10^-6` relative volume; printable faces are not deleted. The repaired mesh is computed once per material per guard evaluation and the same mesh is reused for the STL, the 3MF and the triangle counts

#### Scenario: Round-trip guard
- **WHEN** both outputs have been computed, debris has been reassigned and export slivers repaired
- **THEN** system serialises each manifold to binary STL in memory and reloads it with position merging; both outputs must have zero edges used by other than two faces. If either fails, the cutter alone is rebuilt with up to 3 deterministic sub-seeds (vein mode may first try two deterministic union orders within one attempt) and the guard re-runs; if all attempts fail, a `RuntimeError` is raised and no output files are written

#### Scenario: Seed robustness
- **WHEN** the tea bowl is run over the 144-run tuning sweep and the independent 160-run out-of-sample sweep, in both modes
- **THEN** every completed run produces two watertight, volume-valid STLs with zero bad edges, no valid bowl is falsely rejected, and no run needs a cutter retry

### Requirement: Unified multi-material 3MF export
The system SHALL optionally export a single 3MF Core-spec package in which one build item references one parent object whose `<components>` list the named mesh objects `CeramicBody` and `GoldSeams`, so slicers load it as one object with two parts. The package SHALL be written directly with `zipfile` and `xml.etree`, because `trimesh`'s scene exporter writes each geometry as a separate build item (verified with trimesh 5.2.0).

#### Scenario: Multi-material 3MF export
- **WHEN** `output_3mf_path` is specified, $R < 1.0$, and the gold solid is non-empty
- **THEN** system writes a `.3mf` whose `3D/3dmodel.model` contains exactly one `<build><item>`, referencing an object whose `<components>` reference two mesh objects named `CeramicBody` and `GoldSeams`, with `unit="millimeter"` and identity transforms

#### Scenario: Single-volume fallback 3MF export
- **WHEN** `output_3mf_path` is specified, and either $R \ge 1.0$ or the gold solid is omitted
- **THEN** system writes a `.3mf` with a single build item referencing only the `CeramicBody` mesh object
