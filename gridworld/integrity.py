"""Protected-file checks, source checks, and the run log. DO NOT EDIT.

The static source check reports prohibited imports and private map access.
The manifest detects changes to provided files. Gradescope uses staff copies
of the support code. The hash-chained .a1log records local runs for reference
at code review. These checks are not a security boundary or proof of authorship.
"""
from __future__ import annotations

import ast
import hashlib
import json
import platform
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

#: the only files you may change
PYTHON_EDITABLE = ("gridworld/heap.py", "gridworld/search.py",
            "gridworld/heuristics.py", "gridworld/agents.py")

EDITABLE = PYTHON_EDITABLE  # compatibility for staff tools

#: everything whose contents the grader relies on
PROTECTED = ("gridworld/core.py", "gridworld/hlib.py",
             "gridworld/agentbase.py", "gridworld/report_spec.py",
             "gridworld/integrity.py", "gridworld/stats.py",
             "gridworld/viz.py", "gridworld/charts.py", "gridworld/anim.py",
             "gridworld/pdfwriter.py", "gridworld/bench.py",
             "autograder.py", "make_report.py", "submit.py", "demo.py", "gridworld/native.py",
             "native/cpp/SDK.hpp", "native/cpp/Runner.cpp",
             "native/java/SDK.java", "native/java/Runner.java")

#: ready-made priority queues and sorted containers.  Part 2 is the heap.
BANNED_MODULES = {"heapq", "queue", "bisect", "sortedcontainers", "heapdict",
                  "pqdict", "blist", "collections.abc.heap"}

#: private names in `core` that would let a search read the true map or the
#: exact answer instead of computing it
BANNED_NAMES = {"_probe", "_true_grid_passable", "_true_distances",
                "_optimal_cost", "_make_known_problem", "_components",
                "_check_path"}

LOG = ROOT / ".a1log"


# ---------------------------------------------------------------- hashing


def sha256_file(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return ""


def hashes(names) -> dict:
    return {n: sha256_file(ROOT / n) for n in names}


def load_manifest() -> dict | None:
    """Shipped hashes of the protected files, or None if none was shipped."""
    try:
        from gridworld import _manifest
        return dict(_manifest.PROTECTED_SHA256)
    except Exception:
        return None


def verify_protected(root=None, *, package_only=False) -> tuple[list[str], bool]:
    """Returns (list of complaints, whether a manifest was available)."""
    man = load_manifest()
    if man is None:
        return ([], False)
    out = []
    from gridworld.native import language
    selected = language(root)
    for name in PROTECTED:
        if name.startswith("native/") and not name.startswith(f"native/{selected}/"):
            continue
        if package_only and not name.startswith(("gridworld/", "native/")):
            continue
        want = man.get(name)
        if want is None:
            continue
        got = sha256_file((Path(root) if root is not None else ROOT) / name)
        if not got:
            out.append(f"{name} is missing")
        elif got != want:
            out.append(f"{name} has been modified")
    return (out, True)


# ---------------------------------------------------------------- guard


def scan_source(path: Path) -> list[str]:
    """Static check of one student file.  Returns a list of complaints."""
    out: list[str] = []
    try:
        src = path.read_text()
    except OSError:
        return [f"{path.name} is missing"]
    try:
        tree = ast.parse(src, filename=str(path))
    except SyntaxError as e:
        return [f"{path.name}:{e.lineno} does not parse: {e.msg}"]

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                if a.name.split(".")[0] in BANNED_MODULES:
                    out.append(f"{path.name}:{node.lineno} imports {a.name} -- "
                               f"Part 2 is writing your own heap")
        elif isinstance(node, ast.ImportFrom):
            mod = (node.module or "").split(".")[0]
            if mod in BANNED_MODULES:
                out.append(f"{path.name}:{node.lineno} imports from {node.module} "
                           f"-- Part 2 is writing your own heap")
            for a in node.names:
                if a.name in BANNED_NAMES:
                    out.append(f"{path.name}:{node.lineno} imports {a.name}, which "
                               f"reads the true map or the exact answer")
        elif isinstance(node, ast.Call):
            fn = node.func
            name = getattr(fn, "id", None) or getattr(fn, "attr", None)
            if name in ("__import__", "import_module"):
                out.append(f"{path.name}:{node.lineno} imports dynamically; "
                           f"imports must be visible at the top of the file")
        elif isinstance(node, ast.Attribute):
            if node.attr in BANNED_NAMES:
                out.append(f"{path.name}:{node.lineno} reaches for .{node.attr}, "
                           f"which reads the true map or the exact answer")
    return sorted(set(out))


def guard() -> list[str]:
    """Static check of every file you edit.  Empty means clean."""
    out: list[str] = []
    from gridworld.native import language, guard as native_guard
    selected = language()
    if selected != "python":
        return native_guard(lang=selected)
    for name in PYTHON_EDITABLE:
        out.extend(scan_source(ROOT / name))
    return out


# ---------------------------------------------------------------- run log


def _tail_hash() -> str:
    try:
        lines = [l for l in LOG.read_text().splitlines() if l.strip()]
    except OSError:
        return ""
    if not lines:
        return ""
    return hashlib.sha256(lines[-1].encode()).hexdigest()[:16]


def append_log(kind: str, payload: dict) -> None:
    """Append one chained entry.  Never raises: logging must not fail a run."""
    entry = {
        "t": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "kind": kind,
        "prev": _tail_hash(),
        "py": f"{sys.version_info.major}.{sys.version_info.minor}",
        "host": hashlib.sha256(platform.node().encode()).hexdigest()[:8],
        "files": {n.split("/")[-1]: h[:12] for n, h in hashes(editable_files()).items()},
        **payload,
    }
    try:
        with LOG.open("a") as fh:
            fh.write(json.dumps(entry, sort_keys=True) + "\n")
    except OSError:
        pass


def read_log() -> list[dict]:
    try:
        return [json.loads(l) for l in LOG.read_text().splitlines() if l.strip()]
    except (OSError, ValueError):
        return []


def log_summary() -> dict:
    """What the report footer says about the run log."""
    entries = read_log()
    if not entries:
        return {"runs": 0, "days": 0, "first": "", "last": "", "broken": False,
                "versions": 0}
    broken = False
    for prev, cur in zip(entries, entries[1:]):
        want = hashlib.sha256(json.dumps(prev, sort_keys=True).encode()).hexdigest()[:16]
        if cur.get("prev") not in ("", want):
            broken = True
    days = {e["t"][:10] for e in entries}
    versions = len({json.dumps(e.get("files", {}), sort_keys=True) for e in entries})
    return {"runs": len(entries), "days": len(days), "first": entries[0]["t"],
            "last": entries[-1]["t"], "broken": broken, "versions": versions}


# ---------------------------------------------------------------- fingerprint


def fingerprint(results: dict, ruids) -> str:
    """A short digest over the code, the instance set and the measured results.

    The graders recompute this by re-running the submitted code.  It is what
    ties one PDF to one team's code and one team's worlds; a page whose
    fingerprint does not reproduce did not come from the code it was submitted
    with.

    Only *deterministic* quantities go in.  Wall-clock timings differ between
    machines and between runs on one machine, so including them would mean the
    fingerprint never reproduced and the check would be worthless.  Expansion
    counts, path costs and trajectory lengths do not vary, which is exactly why
    those are the numbers you are graded on.
    """
    blob = json.dumps({
        "files": hashes(editable_files()),
        "ruids": sorted(ruids),
        "results": _canonical(results),
    }, sort_keys=True, default=str)
    return hashlib.sha256(blob.encode()).hexdigest()[:16].upper()


#: substrings marking a measurement that legitimately varies between runs
_NONDETERMINISTIC = ("sec", "time", "elapsed", "ci", "_p")


def _canonical(obj):
    """Round floats; drop clock readings and private handles.

    Keys beginning with an underscore hold live objects -- a rendered bitmap, an
    agent, a search problem -- whose `repr` contains a memory address.  Letting
    one into the digest would mean the fingerprint never reproduced, which is
    the one thing it must do.
    """
    if isinstance(obj, dict):
        return {str(k): _canonical(v)
                for k, v in sorted(obj.items(), key=lambda kv: str(kv[0]))
                if not str(k).startswith("_")
                and not any(t in str(k).lower() for t in _NONDETERMINISTIC)}
    if isinstance(obj, (list, tuple)):
        return [_canonical(v) for v in obj]
    if isinstance(obj, float):
        return round(obj, 4)
    if isinstance(obj, (set, frozenset)):
        return sorted(str(v) for v in obj)
    return obj


def editable_files():
    from gridworld.native import editable
    return editable()
