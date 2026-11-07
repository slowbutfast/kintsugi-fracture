"""Standardised test reports for running the suite off the VPS.

Workstation (after ``git pull``):

    .venv/bin/python tools/test_report.py run                # unit tests only
    .venv/bin/python tools/test_report.py run --profile full # + audits + sweep

writes ``reports/test-report-<commit>-<host>.json`` and prints a fenced
``KINTSUGI TEST REPORT`` block. Paste that block (and, if anything failed, it
already contains the failure details) back to the VPS session.

VPS (agents or humans):

    .venv/bin/python tools/test_report.py check report.txt   # or: ... check - < report.txt

parses a pasted block or a JSON report, recomputes the source fingerprint of the
VPS working tree and states whether the report applies to the code that is
there now. Exit code: 0 = applies and passed, 1 = applies and failed,
2 = does not apply (tested code differs from the VPS tree, or unparsable).

The fingerprint is computed from file contents (Git blob SHA-1s), not from
``git``, so the check works without git and also catches uncommitted VPS edits.
See TESTING.md for the full workflow and the report schema.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import re
import subprocess
import sys
import tempfile
import time
import traceback
import unittest
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCHEMA = "kintsugi-test-report/1"
BEGIN = "=== KINTSUGI TEST REPORT v1 ==="
END = "=== END KINTSUGI TEST REPORT ==="

# Everything whose content can change a test result.
FINGERPRINT_GLOBS = (
    "kintsugi.py", "web_app.py", "sample_models.py", "generate_sample.py",
    "requirements.txt", "requirements-dev.txt",
    "tests/*.py", "tools/*.py", "static/*", "presets/*.stl",
)

# Suites that are allowed to fail because the failure is a tracked, open finding.
# Remove an entry when its finding is fixed, so a regression becomes a real FAIL.
KNOWN_OPEN = {"noise_fold": "F18"}

PROFILES = {
    "quick": ["unit"],
    "full": ["unit", "crack_graph_audit", "sweep", "noise_fold"],
}


# ---------------------------------------------------------------------------
# Fingerprint
# ---------------------------------------------------------------------------
def _blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def source_files() -> dict[str, str]:
    files: dict[str, str] = {}
    for pattern in FINGERPRINT_GLOBS:
        for path in sorted(REPO.glob(pattern)):
            if path.is_file() and "__pycache__" not in path.parts:
                files[path.relative_to(REPO).as_posix()] = _blob_sha(path)
    return dict(sorted(files.items()))


def fingerprint(files: dict[str, str]) -> str:
    text = "\n".join(f"{path} {sha}" for path, sha in sorted(files.items()))
    return hashlib.sha256(text.encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------
def _git(*args: str) -> str | None:
    try:
        out = subprocess.run(
            ["git", *args], cwd=REPO, capture_output=True, text=True, check=True
        )
        return out.stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def _cpu_name() -> str:
    if sys.platform == "darwin":
        try:
            return subprocess.run(
                ["sysctl", "-n", "machdep.cpu.brand_string"],
                capture_output=True, text=True, check=True,
            ).stdout.strip()
        except (OSError, subprocess.CalledProcessError):
            pass
    try:
        for line in Path("/proc/cpuinfo").read_text().splitlines():
            if line.lower().startswith(("model name", "cpu model")):
                return line.split(":", 1)[1].strip()
    except OSError:
        pass
    try:  # ARM Linux has no model name in /proc/cpuinfo
        out = subprocess.run(["lscpu"], capture_output=True, text=True, check=True).stdout
        match = re.search(r"^Model name:\s*(.+)$", out, re.M)
        if match:
            return match.group(1).strip()
    except (OSError, subprocess.CalledProcessError):
        pass
    return platform.processor() or platform.machine()


def environment() -> dict:
    from importlib import metadata

    packages = {}
    for name in ("numpy", "scipy", "trimesh", "manifold3d", "fastapi", "httpx", "rtree"):
        try:
            packages[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            packages[name] = None
    status = _git("status", "--porcelain", "--untracked-files=no")
    return {
        "host": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "cpu": _cpu_name(),
            "python": platform.python_version(),
            "packages": packages,
        },
        "git": {
            "commit": _git("rev-parse", "HEAD"),
            "branch": _git("rev-parse", "--abbrev-ref", "HEAD"),
            "dirty": bool(status) if status is not None else None,
            "dirty_files": status.splitlines() if status else [],
        },
    }


# ---------------------------------------------------------------------------
# Suites
# ---------------------------------------------------------------------------
class _Recorder(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.records: list[dict] = []
        self._started = 0.0

    def startTest(self, test):
        self._started = time.perf_counter()
        super().startTest(test)

    def _add(self, test, status, err=None):
        record = {
            "id": test.id(),
            "status": status,
            "duration_s": round(time.perf_counter() - self._started, 3),
        }
        if err is not None:
            text = self._exc_info_to_string(err, test)
            record["message"] = text.strip().splitlines()[-1] if text.strip() else ""
            record["traceback"] = text
        self.records.append(record)

    def addSuccess(self, test):
        super().addSuccess(test)
        self._add(test, "passed")

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self._add(test, "failed", err)

    def addError(self, test, err):
        super().addError(test, err)
        self._add(test, "error", err)

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self.records.append({"id": test.id(), "status": "skipped", "message": reason,
                             "duration_s": 0.0})

    def addExpectedFailure(self, test, err):
        super().addExpectedFailure(test, err)
        self._add(test, "expected_failure")

    def addUnexpectedSuccess(self, test):
        super().addUnexpectedSuccess(test)
        self._add(test, "unexpected_success")

    def addSubTest(self, test, subtest, err):
        super().addSubTest(test, subtest, err)
        if err is not None:
            status = "failed" if issubclass(err[0], test.failureException) else "error"
            self._add(subtest, status, err)


def run_unit() -> dict:
    sys.path.insert(0, str(REPO / "tests"))
    sys.path.insert(0, str(REPO))
    started = time.perf_counter()
    suite = unittest.defaultTestLoader.discover(str(REPO / "tests"))
    runner = unittest.TextTestRunner(
        stream=sys.stderr, verbosity=2, resultclass=_Recorder
    )
    result = runner.run(suite)
    records = result.records
    counts = {key: sum(1 for r in records if r["status"] == key)
              for key in ("passed", "failed", "error", "skipped",
                          "expected_failure", "unexpected_success")}
    ok = result.wasSuccessful()
    return {
        "status": "pass" if ok else "fail",
        "ran": result.testsRun,
        "counts": counts,
        "duration_s": round(time.perf_counter() - started, 1),
        "tests": records,
    }


def _run_tool(args: list[str], out: Path) -> tuple[int, str]:
    proc = subprocess.run(
        [sys.executable, *args, "--output", str(out)],
        cwd=REPO, capture_output=True, text=True,
    )
    sys.stderr.write(proc.stdout + proc.stderr)
    return proc.returncode, (proc.stdout + proc.stderr)[-4000:]


def run_crack_graph_audit(tmp: Path) -> dict:
    out = tmp / "audit.json"
    started = time.perf_counter()
    code, log = _run_tool(["tools/crack_graph_audit.py", "--presets", "tea_bowl", "vase",
                           "--severities", "0.6", "1.0", "--seeds", "200"], out)
    if code != 0 or not out.exists():
        return {"status": "error", "exit_code": code, "log_tail": log}
    rows = json.loads(out.read_text())
    ok = all(r["phantom_seeds"] == 0 and r["crossing_seeds"] == 0
             and r["clamp_line_fraction_max"] == 0.0 for r in rows)
    return {"status": "pass" if ok else "fail",
            "criteria": "phantom == 0, crossing == 0, clamp-line max == 0 in every row",
            "duration_s": round(time.perf_counter() - started, 1), "rows": rows}


def run_sweep(tmp: Path) -> dict:
    out = tmp / "sweep.json"
    started = time.perf_counter()
    code, log = _run_tool(["tools/sweep_out_of_sample.py", "--presets", "tea_bowl", "vase",
                           "--ratios", "0.15", "0.3", "0.45", "0.65", "0.85",
                           "--modes", "ribbon", "vein",
                           "--seeds", *[str(s) for s in range(500, 508)]], out)
    if not out.exists():
        return {"status": "error", "exit_code": code, "log_tail": log}
    data = json.loads(out.read_text())
    retries = sum(n for k, n in data["cutter_attempts"].items() if str(k) != "1")
    ok = data["nonwatertight"] == 0 and data["errors"] == 0
    return {
        "status": "pass" if ok else "fail",
        "criteria": "nonwatertight == 0 and errors == 0 (retries reported, not gated)",
        "duration_s": round(time.perf_counter() - started, 1),
        "total": data["total"], "clean": data["clean"],
        "nonwatertight": data["nonwatertight"], "errors": data["errors"],
        "retries": retries, "cutter_attempts": data["cutter_attempts"],
        "run_time_median_s": data["run_time_median_s"],
        "run_time_max_s": data.get("run_time_max_s"),
        "failures": [{k: f.get(k) for k in ("preset", "R", "mode", "seed", "status", "error")}
                     for f in data.get("failures", [])],
    }


def run_noise_fold(tmp: Path) -> dict:
    out = tmp / "noise.json"
    started = time.perf_counter()
    code, log = _run_tool(["tools/noise_fold_audit.py", "--presets", "tea_bowl", "vase",
                           "--severities", "0.3", "0.6", "1.0", "--seeds", "300", "500"], out)
    if code != 0 or not out.exists():
        return {"status": "error", "exit_code": code, "log_tail": log}
    rows = json.loads(out.read_text())
    ok = all(r["fold_area_max"] == 0.0 and r["crossing_seeds_with_noise"] == 0 for r in rows)
    return {"status": "pass" if ok else "fail",
            "criteria": "fold area == 0 and crossings with noise == 0 in every row",
            "duration_s": round(time.perf_counter() - started, 1), "rows": rows}


RUNNERS = {
    "unit": lambda tmp: run_unit(),
    "crack_graph_audit": run_crack_graph_audit,
    "sweep": run_sweep,
    "noise_fold": run_noise_fold,
}


# ---------------------------------------------------------------------------
# Summary block
# ---------------------------------------------------------------------------
def _suite_line(name: str, suite: dict) -> str:
    status = suite["status"].upper()
    if suite["status"] == "fail" and name in KNOWN_OPEN:
        status = f"KNOWN-FAIL({KNOWN_OPEN[name]})"
    if suite["status"] == "error":
        return f"suite {name}: ERROR exit={suite.get('exit_code')}"
    if name == "unit":
        c = suite["counts"]
        return (f"suite unit: {status} ran={suite['ran']} passed={c['passed']} "
                f"failed={c['failed']} errors={c['error']} skipped={c['skipped']} "
                f"time={suite['duration_s']}s")
    if name == "crack_graph_audit":
        r = suite["rows"]
        return (f"suite crack_graph_audit: {status} rows={len(r)} "
                f"phantom={sum(x['phantom_seeds'] for x in r)} "
                f"crossing={sum(x['crossing_seeds'] for x in r)} "
                f"clamp_max={max(x['clamp_line_fraction_max'] for x in r):.1%} "
                f"time={suite['duration_s']}s")
    if name == "sweep":
        return (f"suite sweep: {status} total={suite['total']} clean={suite['clean']} "
                f"nonwatertight={suite['nonwatertight']} errors={suite['errors']} "
                f"retries={suite['retries']} median={suite['run_time_median_s']:.2f}s "
                f"time={suite['duration_s']}s")
    if name == "noise_fold":
        r = suite["rows"]
        return (f"suite noise_fold: {status} "
                f"fold_max={max(x['fold_area_max'] for x in r):.1%} "
                f"max_grad={max(x['max_grad'] for x in r):.2f} "
                f"crossing_seeds={sum(x['crossing_seeds_with_noise'] for x in r)}"
                f"/{sum(x['seeds'] for x in r)} time={suite['duration_s']}s")
    return f"suite {name}: {status}"


def summary_block(report: dict, path: Path | None) -> str:
    env, git = report["host"], report["git"]
    commit = (git["commit"] or "unknown")[:12]
    dirty = "DIRTY" if git["dirty"] else ("clean" if git["dirty"] is False else "unknown")
    lines = [
        BEGIN,
        f"overall: {report['overall'].upper()}",
        f"created_utc: {report['created_utc']}",
        f"profile: {report['profile']}",
        f"commit: {commit} {dirty} {git['branch'] or ''}".rstrip(),
        f"fingerprint: {report['fingerprint']}",
        f"host: {env['system']}-{env['release']}-{env['machine']} | {env['cpu']} | "
        f"python {env['python']}",
        "packages: " + " ".join(f"{k}={v}" for k, v in env["packages"].items()),
    ]
    for name, suite in report["suites"].items():
        lines.append(_suite_line(name, suite))
    unit = report["suites"].get("unit")
    for record in (unit or {}).get("tests", []):
        if record["status"] in ("failed", "error", "unexpected_success"):
            lines.append(f"{record['status']}: {record['id']} :: {record.get('message', '')}")
            for tb_line in record.get("traceback", "").strip().splitlines()[-15:]:
                lines.append(f"  | {tb_line}")
    sweep = report["suites"].get("sweep")
    for failure in (sweep or {}).get("failures", [])[:10]:
        lines.append(f"sweep-failure: {failure}")
    for name, suite in report["suites"].items():
        if suite["status"] == "error":
            lines.append(f"suite-error {name}:")
            lines.extend(f"  | {l}" for l in suite.get("log_tail", "").splitlines()[-15:])
    if path is not None:
        lines.append(f"report: {path.relative_to(REPO).as_posix()}")
    lines.append(END)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------
def cmd_run(args) -> int:
    suites = args.suites or PROFILES[args.profile]
    env = environment()
    files = source_files()
    report = {
        "schema": SCHEMA,
        "created_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "profile": "custom" if args.suites else args.profile,
        **env,
        "fingerprint": fingerprint(files),
        "sources": files,
        "known_open": KNOWN_OPEN,
        "suites": {},
    }
    with tempfile.TemporaryDirectory() as tmp:
        for name in suites:
            print(f"--- running {name} ---", file=sys.stderr, flush=True)
            try:
                report["suites"][name] = RUNNERS[name](Path(tmp))
            except Exception:  # a crashed suite is reported, never swallowed
                report["suites"][name] = {"status": "error", "exit_code": None,
                                          "log_tail": traceback.format_exc()}
    gated = [s for n, s in report["suites"].items()
             if not (s["status"] == "fail" and n in KNOWN_OPEN)]
    report["overall"] = "pass" if all(s["status"] == "pass" for s in gated) else "fail"

    out_dir = REPO / "reports"
    out_dir.mkdir(exist_ok=True)
    host = re.sub(r"[^A-Za-z0-9]+", "-", f"{platform.system()}-{platform.machine()}")
    commit = (report["git"]["commit"] or "nocommit")[:12]
    path = out_dir / f"test-report-{commit}-{host}.json"
    path.write_text(json.dumps(report, indent=2))
    (out_dir / "latest.json").write_text(json.dumps(report, indent=2))
    block = summary_block(report, path)
    (out_dir / "latest.txt").write_text(block + "\n")
    print(block)
    return 0 if report["overall"] == "pass" else 1


def _parse(text: str) -> dict:
    text = text.strip()
    if text.startswith("{"):
        data = json.loads(text)
        if data.get("schema") != SCHEMA:
            raise ValueError(f"unknown schema {data.get('schema')!r}")
        return {"overall": data["overall"], "fingerprint": data["fingerprint"],
                "dirty": data["git"]["dirty"], "commit": data["git"]["commit"],
                "sources": data["sources"], "block": summary_block(data, None)}
    if BEGIN not in text or END not in text:
        raise ValueError("no KINTSUGI TEST REPORT block found")
    block = text[text.index(BEGIN): text.index(END) + len(END)]
    fields = dict(re.findall(r"^(overall|fingerprint|commit): (.*)$", block, re.M))
    commit_parts = fields.get("commit", "").split()
    return {"overall": fields["overall"].lower(), "fingerprint": fields["fingerprint"],
            "dirty": "DIRTY" in commit_parts, "commit": commit_parts[0] if commit_parts else None,
            "sources": None, "block": block}


def cmd_check(args) -> int:
    text = sys.stdin.read() if args.report == "-" else Path(args.report).read_text()
    try:
        parsed = _parse(text)
    except (ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"CHECK: UNPARSABLE ({exc})")
        return 2
    files = source_files()
    local = fingerprint(files)
    print(parsed["block"])
    print()
    if parsed["dirty"]:
        # Not fatal on its own: the fingerprint covers every file that can change
        # a result, so a dirty clone only matters if it changed one of those.
        print("WARNING: the tested clone had uncommitted changes (gated by fingerprint below)")
    if parsed["fingerprint"] != local:
        print(f"CHECK: DOES NOT APPLY - tested fingerprint {parsed['fingerprint']} "
              f"!= VPS tree {local}")
        if parsed["sources"]:
            for path in sorted(set(files) | set(parsed["sources"])):
                if files.get(path) != parsed["sources"].get(path):
                    print(f"  differs: {path}")
        else:
            print("  (pass the JSON report to list the differing files)")
        return 2
    verdict = parsed["overall"]
    print(f"CHECK: APPLIES to the current VPS tree (fingerprint {local}); "
          f"overall {verdict.upper()}")
    return 0 if verdict == "pass" else 1


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run", help="run suites on this machine and write a report")
    run.add_argument("--profile", choices=sorted(PROFILES), default="quick")
    run.add_argument("--suites", nargs="+", choices=sorted(RUNNERS))
    run.set_defaults(func=cmd_run)
    check = sub.add_parser("check", help="check a pasted block or JSON report")
    check.add_argument("report", help="file path, or - for stdin")
    check.set_defaults(func=cmd_check)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
