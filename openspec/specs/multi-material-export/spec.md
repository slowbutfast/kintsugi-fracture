# multi-material-export Specification

## Purpose
TBD - created by archiving change kintsugi-mesh-fracture. Update Purpose after archive.
## Requirements
### Requirement: Sub-nozzle debris reassignment
The system SHALL decompose both the ceramic and the gold results into connected components. A component with volume below $V_{min} = 1.0\text{ mm}^3$ SHALL be moved into the *other* material only when it shares a face region with that destination (unioning it reduces the destination's component count); otherwise it SHALL remain in its original material and be counted. Components are never deleted, so total volume is conserved.

#### Scenario: Floating ceramic crumb
- **WHEN** the difference leaves a ceramic component with volume $< 1.0\text{ mm}^3$
- **THEN** system removes it from the ceramic manifold and unions it into the gold manifold, so the slicer sees no sub-threshold ceramic island

#### Scenario: Gold debris at the rim
- **WHEN** the intersection leaves a gold component with volume $< 1.0\text{ mm}^3$ (e.g. a grazing ribbon exit at the rim)
- **THEN** system removes it from the gold manifold and unions it into the ceramic manifold

#### Scenario: Conservation after reassignment
- **WHEN** reassignment completes
- **THEN** the complementary-volume smoke check still holds within $10^{-6}$ relative tolerance

#### Scenario: Crumbs merge only across a shared face
- **WHEN** a sub-threshold component shares a face region with the other material
- **THEN** it is moved there and the destination's connected-component count decreases by one

#### Scenario: Isolated crumbs stay in place
- **WHEN** a sub-threshold component touches the other material only along an edge or at a point, or is isolated
- **THEN** it remains in its original material and increments `debris_unmoved`; no new kissing edge is introduced

Component volume is a filter for crumbs only. Thin needles attached to larger shards are not separate components, so this filter does not catch them; they are bounded by the printable-thickness test instead.

### Requirement: Paired manifold STL export
The system SHALL export aligned binary STL files in the input coordinate frame, and the files SHALL remain watertight after a disk round-trip.

#### Scenario: Inequality fracture export
- **WHEN** $R < 1.0$
- **THEN** system writes binary STL files for both ceramic body and gold seams, and reloading each from disk with `trimesh.load(..., process=True)` reports `is_watertight == True` and `is_volume == True`

#### Scenario: Wealthy pass-through export
- **WHEN** $R \ge 1.0$
- **THEN** system writes the validated input mesh to `ceramic_body.stl`, does **not** write `gold_seams.stl`, deletes any pre-existing file at the gold output path so that a stale seam from an earlier run cannot be paired with the pristine body, and returns `gold_path: None` in the result dict

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
- **WHEN** `output_3mf_path` is specified and $R < 1.0$
- **THEN** system writes a `.3mf` whose `3D/3dmodel.model` contains exactly one `<build><item>`, referencing an object whose `<components>` reference two mesh objects named `CeramicBody` and `GoldSeams`, with `unit="millimeter"` and identity transforms

#### Scenario: Single-volume wealthy 3MF export
- **WHEN** `output_3mf_path` is specified and $R \ge 1.0$
- **THEN** system writes a `.3mf` with a single build item referencing only the `CeramicBody` mesh object

Extruder or filament assignment requires slicer-specific metadata (`Metadata/Slic3r_PE_model.config`, `Metadata/model_settings.config`). That is out of scope; filaments are assigned per part in the slicer.

