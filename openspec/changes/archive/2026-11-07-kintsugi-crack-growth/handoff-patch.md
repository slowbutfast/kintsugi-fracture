# Surgical Patch Handoff: OpenSpec Change 'kintsugi-crack-growth' [PATCH-02]

## 1. Executive Objective & Diagnostic Feedback
- **Change Name**: `kintsugi-crack-growth`
- **Patch ID**: `PATCH-02`
- **Objective**: Fix misleading "Pristine / Wealthy" UI status on thin-wall omitted seams, expose `seams_omitted` top-level in web API, reduce crack stopping-short rate by bending near-misses onto target segments on final attempt, lower kink rate to 15–20% for true correlated walk, and update planning artifacts and sign-off labels.
- **Feedback & Diagnostic Trace**:
  ```
  Warning 1 (UI & API Status on Thin Walls):
  - On thin_cylinder at R=0.62, num_cracks is 0, causing viewer.js:405 to display "Pristine / Wealthy (0 cracks)".
  - This is misleading: the vessel is not wealthy (R < 1.0); its wall is too thin (< 1.05 mm) for printable vein grooves.
  - web_app.py does not expose seams_omitted as a top-level response field.
  
  Warning 2 (Artifact Text Alignment & Task 2.4 Sign-off):
  - Task 2.4 was marked [x] by the agent rather than reserved for human review.
  - architecture.md and design.md still describe ±60° bounds and 80% T-ratio gate, while code uses ±85° and informational T-ratio.
  - verification.md agent notes should be explicitly labeled as agent notes, not human sign-off.
  
  Morphology Feedback (Stopping Short & Kink Rate):
  - Stopping short remains high (34–38% of crack ends) because cracks die 3 mm short when straight-line forward extension misses.
  - Heading walk has 50% uniform kink probability, producing staircase lightning instead of an organic correlated fracture walk.
  - num_cracks still counts uncarved cracks when only some cracks are carved.
  ```
- **Root Cause Analysis**:
  1. `viewer.js` tested only `body.num_cracks === 0`; `web_app.py` didn't bubble `seams_omitted` to top-level JSON response.
  2. In `kintsugi.py`, when a candidate segment enters clearance distance but its straight extension misses the target, after 4 attempts it dies 3 mm away.
  3. Kink rate was hardcoded at `rng.random() < 0.50`.
  4. Task 2.4 was ticked during automated apply rather than left open for human evaluation.

## 2. Strict Target Context Map
| File Path (relative to repo root) | Target Lines | Modification Summary |
|---|---|---|
| `web_app.py` | L206–L220 | In `/api/fracture` response, add top-level `"seams_omitted": bool` and `"seams_omitted_reason": str | None`. |
| `static/viewer.js` | L405–L412 | In `setStatus(label)`, check `body.seams_omitted`: if true, display `"Seams Omitted (wall thickness < 1.05 mm)"`. |
| `tests/test_web_api.py` | L70–L100 | Add test `test_api_fracture_thin_wall_seams_omitted` asserting top-level `seams_omitted: True` and `num_cracks: 0` on `thin_cylinder` at $R=0.62$. |
| `kintsugi.py` | L1265–L1320 | In `generate_crack_growth_paths`: when `attempt == 3` (final attempt) and a segment is within clearance $R_{\text{clear}}$ at arrival angle $\ge 30^\circ$, bend the final step to snap directly onto the nearest point on that segment, forming a shared T-junction instead of dying short. |
| `kintsugi.py` | L1215–L1230 | Reduce sharp kink rate from 50% to 15% (`rng.random() < 0.15`), letting remaining 85% follow Gaussian step ($\sigma = \text{radians}(12^\circ)$). |
| `kintsugi.py` | L2845–L2860 | Ensure `num_cracks` counts only paths that retained at least one valid carved cutter point. |
| `openspec/changes/kintsugi-crack-growth/tasks.md` | L14, L26, L42–L55 | Un-tick Task 2.4, update Task 4.2 text, and append Patch 02 checklist. |
| `openspec/changes/kintsugi-crack-growth/architecture.md` | L19, L55–L75 | Update heading limits from $\pm 60^\circ$ to $\pm 85^\circ$, and update branching description. |
| `openspec/changes/kintsugi-crack-growth/design.md` | L96–L110 | Update visual morphology text to reflect $\pm 85^\circ$ lateral links. |
| `openspec/changes/kintsugi-crack-growth/verification.md` | L20–L40 | Relabel agent inspection notes to make clear human sign-off is pending. |

## 3. Blast Radius & Invariant Guardrails
- **STRICT BLAST RADIUS**: Modify ONLY the lines and files specified in the Target Context Map.
- **FORBIDDEN**:
  - Do NOT modify the core CSG boolean kernel or binary STL exporter.
  - Do NOT allow tangent cutter contacts ($d \to 0$); preserve the $d < 0.25\text{ mm}$ omission cutoff.
  - Do NOT introduce crossing cracks.
- **INVARIANTS TO PRESERVE**: All 43 existing unit tests MUST continue to pass, plus the new API assertion.

## 4. Visual & UI Impact
- When thin vessels (e.g. `thin_cylinder` at $R=0.62$) omit gold seams, status bar displays `Seams Omitted (wall thickness < 1.05 mm)` instead of the misleading `Pristine / Wealthy (0 cracks)`.
- Reduced stopping-short gaps: cracks connect into closed networks enclosing shards rather than stopping 3 mm apart.
- Organic wandering fractures instead of 50% staircase zigzags.

## 5. Reproduction & Verification Protocol
1. **Reproduce First**:
   ```bash
   .venv/bin/python -m unittest tests/test_web_api.py -v
   ```
   Confirm that currently `/api/fracture` does not return top-level `seams_omitted`.
2. **Apply Minimal Fix**: Implement edits in `web_app.py`, `static/viewer.js`, `kintsugi.py`, and planning docs.
3. **Verify Fix**: Confirm new API test passes and UI status logic works.
4. **Full Regression Suite**:
   ```bash
   .venv/bin/python -m unittest discover -s tests -v
   ```

## 6. Surgical Patch Checklist
- [ ] P02.1 Expose `seams_omitted` and `seams_omitted_reason` in `web_app.py` and add API test assertion for R=0.62 thin_cylinder.
- [ ] P02.2 Update `static/viewer.js` to display "Seams Omitted (wall thickness < 1.05 mm)" when `seams_omitted` is true.
- [ ] P02.3 In `kintsugi.py`, ensure `num_cracks` counts only paths with carved cutter points, and bend final step onto nearest valid point within clearance at >= 30° instead of dying short.
- [ ] P02.4 Reduce sharp kink rate to 15-20% for true correlated random walk in `kintsugi.py`.
- [ ] P02.5 Update `architecture.md`, `design.md`, and `verification.md` to match ±85° headings, informational T-ratio, and relabeled agent notes.
- [ ] P02.6 Run full test suite (`.venv/bin/python -m unittest discover -s tests -v`) verifying 100% clean passes.
- [ ] P02.7 Update `verification.md` and mark PATCH-02 resolved in `patch.md`.
