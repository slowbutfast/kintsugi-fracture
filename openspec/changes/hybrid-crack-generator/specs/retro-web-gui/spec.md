## ADDED Requirements

### Requirement: Hybrid generator controls and API

The web GUI SHALL expose the `hybrid` generator as `Hybrid — macro shards + interior hairlines` (`value="hybrid"`, `data-generator="hybrid"`) in both `#generator-select` and the Mode menu (`#menu-mode`). Selecting it SHALL automatically select `vein` mode, disable the `ribbon` mode option in both the sidebar and the menu, and reveal a collapsible `#hybrid-settings` `<fieldset>` below `#generator-note`.

`#hybrid-settings` SHALL contain exactly six `<select class="xp-select">` controls, all defaulting to `value="auto"`:

- `#hybrid-through-count` (`through_count`, 1–3)
- `#hybrid-through-shape` (`through_shape`, `wedge`/`loop`)
- `#hybrid-tilt-deg` (`tilt_deg`, 5–30)
- `#hybrid-hairline-count` (`hairline_count`, 0–10)
- `#hybrid-hairline-reach` (`hairline_reach`, 0.2–1.0)
- `#hybrid-roughness` (`roughness`)

It SHALL also contain `#hybrid-resolved-note`, which renders the resolved values and `num_fragments` returned in `parameters.hybrid`.

`POST /api/fracture` SHALL accept the six knobs as optional form fields, forward only non-`auto` values to the generator, return `num_fragments` in its JSON payload, and return HTTP 400 when a hybrid knob is sent with a generator other than `hybrid` or when `generator="hybrid"` is combined with `mode="ribbon"`.

#### Scenario: Selecting Hybrid reveals the knob group
- **WHEN** the user selects `Hybrid — macro shards + interior hairlines` in `#generator-select` or `#menu-mode`
- **THEN** the `vein` mode is selected, `ribbon` is disabled in both the sidebar and the menu, `#hybrid-settings` becomes visible, and `#generator-note` describes the hybrid generator

#### Scenario: Sending non-auto hybrid knobs
- **WHEN** the user runs a fracture with `generator="hybrid"` and one or more hybrid knobs set to a non-`auto` value
- **THEN** `viewer.js` appends only those non-`auto` knobs to the `FormData`, and the API resolves the remaining `auto` knobs and echoes every resolved value in `parameters.hybrid`

#### Scenario: Resolved telemetry rendered
- **WHEN** a hybrid fracture response arrives with `parameters.hybrid` and `num_fragments`
- **THEN** `#hybrid-resolved-note` displays the resolved knob values and the fragment count, and the status line reports the fragment count alongside the crack count

#### Scenario: Hybrid knobs with another generator rejected
- **WHEN** a client posts any hybrid knob together with `generator="growth"`, `"shard"` or `"voronoi"`
- **THEN** `POST /api/fracture` returns HTTP 400 with an explanatory detail message

#### Scenario: Hybrid ribbon mode rejected
- **WHEN** a client posts `generator="hybrid"` with `mode="ribbon"`
- **THEN** `POST /api/fracture` returns HTTP 400 with an explanatory detail message

#### Scenario: Solid body rejected by validation endpoint
- **WHEN** a client posts a closed solid body with no interior wall to `POST /api/validate`
- **THEN** the endpoint returns `{"valid": false}` with a detail message stating that the input has no usable wall

#### Scenario: Mobile hybrid controls remain touch-sized
- **WHEN** the application is viewed at `max-width: 900px` with the Hybrid generator active
- **THEN** each `#hybrid-settings` `.xp-select` uses `font-size: 16px` and a touch target of at least 40px above the sticky `⚡ FRACTURE MESH` button
