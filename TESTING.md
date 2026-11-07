# Testing workflow: develop on the VPS, test on a workstation

Code changes happen **only on the VPS**. A workstation (currently a MacBook with an Apple M6) pulls, runs the tests and reports back. The suite takes about 38 s there, against about 315 s on the VPS.

`tools/test_report.py` turns each run into a standard report. Agents on the VPS can check exactly which code was tested and what passed or failed, with no guessing from log tails.

## Roles

| Where | Who | Does |
|---|---|---|
| VPS | developer and agents | edit code, commit, push to `origin/main`, read reports with `test_report.py check` |
| Workstation | developer | `git pull`, `test_report.py run`, paste the report block back. **Never edits code.** |

## 1. VPS: publish the change

```bash
git add -A && git commit -m "<what changed>" && git push
```

Commit everything the tests should see. The workstation can only test what has been pushed.

## 2. Workstation: run

One-time setup:

```bash
git clone https://github.com/slowbutfast/kintsugi-fracture.git && cd kintsugi-fracture
python3.11 -m venv .venv && .venv/bin/pip install -r requirements.txt -r requirements-dev.txt
```

Every run:

```bash
git pull
.venv/bin/pip install -r requirements.txt -r requirements-dev.txt   # only if requirements changed
.venv/bin/python tools/test_report.py run                  # quick: unit tests (~40 s)
.venv/bin/python tools/test_report.py run --profile full   # + crack-graph audit, sweep, noise audit
```

Use **`--profile full`** when a change touches crack generation (`generate_crack_paths`, `_make_noise`, `_ridge_segment`, the wall range or truncation), the cutters, CSG, the debris swap or export. Quick is enough for docs, web, CLI and test-only changes. A single suite can also be selected, e.g. `--suites unit sweep`.

The run writes:
- `reports/test-report-<commit>-<host>.json`, the full record;
- `reports/latest.json` and `reports/latest.txt`, copies of the newest JSON and of the block.

It then prints the block. `reports/` is git-ignored, so the clone stays clean.

## 3. Report back

Paste everything from `=== KINTSUGI TEST REPORT v1 ===` through `=== END KINTSUGI TEST REPORT ===` into the VPS session, or `cat reports/latest.txt` and paste that. Surrounding chat text is fine, because `check` finds the block.

The block alone is enough, whether the run passed or failed: failing tests carry their message and the last 15 traceback lines. Send `reports/latest.json` as well only if `check` reports a fingerprint mismatch and you want the differing files listed.

## 4. VPS: check

```bash
.venv/bin/python tools/test_report.py check report.txt     # a saved paste
.venv/bin/python tools/test_report.py check - < report.txt # or stdin
```

| Exit | Verdict line | Meaning |
|---|---|---|
| 0 | `CHECK: APPLIES … overall PASS` | The tested code is byte-identical to the VPS tree, and everything gated passed. |
| 1 | `CHECK: APPLIES … overall FAIL` | Same code, and something failed. The block lists what. |
| 2 | `CHECK: DOES NOT APPLY …` / `UNPARSABLE` | The workstation tested different code (not pulled, VPS edits not pushed, or VPS edited since), or no block was found. **Do not use these results.** |

"Applies" is decided by the **source fingerprint**, not by the commit hash. The fingerprint is a hash of the Git blob SHA-1s of every file that can change a result:
- `kintsugi.py`, `web_app.py`, `sample_models.py`, `generate_sample.py`;
- `requirements*.txt`;
- `tests/*.py`, `tools/*.py`;
- `static/*` and `presets/*.stl`.

The VPS recomputes it from its own working tree, so the check:
- needs no git;
- catches VPS edits that haven't been pushed yet;
- ignores doc-only differences such as `verification.md`.

A dirty workstation clone produces a warning, and the fingerprint decides.

## Rules for agents on the VPS

1. Treat a result as evidence only if `check` exits 0 or 1. On exit 2, ask for a fresh run after pull or push; never reason from a stale report.
2. Quote the verdict line and the `commit:`, `fingerprint:` and `host:` lines when recording results, e.g. in `verification.md`.
3. Gate on the per-test statuses (`failed:` / `error:` lines and the `suite …` lines), never on reading a log by eye.
4. `KNOWN-FAIL(<id>)` means a suite failed for a tracked open finding listed in `KNOWN_OPEN` in `tools/test_report.py` (currently `noise_fold` → F18). It does not fail `overall`. **When that finding is fixed, remove its entry in the same change**, so that a regression shows up as a real `FAIL`.
5. Don't compare output MD5s across hosts. Floating-point rounding can differ between CPUs. Determinism is checked within one machine by `test_determinism`.

## Suites and pass criteria

| Suite | Profile | What runs | Pass when |
|---|---|---|---|
| `unit` | quick, full | `unittest` discovery over `tests/` (35 tests) | every test passes |
| `crack_graph_audit` | full | `tools/crack_graph_audit.py`, tea bowl and vase × S ∈ {0.6, 1.0} × 200 seeds, noise off | phantom = 0, crossing = 0, clamp-line max = 0 in every row |
| `sweep` | full | `tools/sweep_out_of_sample.py`, both presets × R ∈ {0.15, 0.3, 0.45, 0.65, 0.85} × both modes × seeds 500–507 (160 runs) | nonwatertight = 0 and errors = 0. Retries are reported, not gated. |
| `noise_fold` | full | `tools/noise_fold_audit.py`, both presets × S ∈ {0.3, 0.6, 1.0}, crossings over seeds 300–499 with noise on | fold area = 0 and crossings = 0. Currently `KNOWN-FAIL(F18)`. |

Seeds 300–499 are used only by `noise_fold`, whose numbers don't feed back into tuning. Seeds 300–399 and ≥ 600 remain reserved for reviewer hold-out checks of `crack_graph_audit` and the sweeps.

## Report schema (`kintsugi-test-report/1`)

```text
schema, created_utc, profile, overall ("pass" | "fail")
host:   system, release, machine, cpu, python, packages{numpy, scipy, trimesh, manifold3d, fastapi, httpx, rtree}
git:    commit, branch, dirty, dirty_files[]
fingerprint, sources{path: git-blob-sha1}, known_open{suite: finding}
suites.unit:              status, ran, counts{passed, failed, error, skipped, expected_failure, unexpected_success},
                          duration_s, tests[{id, status, duration_s, message?, traceback?}]
suites.crack_graph_audit: status, criteria, duration_s, rows[...]          (tool's JSON rows)
suites.sweep:             status, criteria, duration_s, total, clean, nonwatertight, errors, retries,
                          cutter_attempts, run_time_median_s, run_time_max_s, failures[]
suites.noise_fold:        status, criteria, duration_s, rows[...]
any suite on crash:       status "error", exit_code, log_tail
```

A change to this schema bumps the version in `SCHEMA`, `BEGIN` and this file.
