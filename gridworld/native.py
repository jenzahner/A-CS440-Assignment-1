"""C++/Java adapter for the common experiments. Provided; DO NOT EDIT."""
from __future__ import annotations
import atexit
import hashlib
import json
import math
import os
from pathlib import Path
import random
import shutil
import subprocess
import tempfile
import threading
import queue
from types import SimpleNamespace
from gridworld import core, integrity
from gridworld.agentbase import ReplanningAgent

SOURCES = {
    "cpp": tuple(f"native/cpp/{n}.hpp" for n in ("Heap", "Search", "Heuristics", "Agents")),
    "java": tuple(f"native/java/{n}.java" for n in ("Heap", "Search", "Heuristics", "Agents")),
}
SUPPORT = ("native/cpp/SDK.hpp", "native/cpp/Runner.cpp", "native/java/SDK.java", "native/java/Runner.java")


def language(root=None):
    root = Path(root or integrity.ROOT)
    found = [lang for lang, files in SOURCES.items() if any((root / f).exists() for f in files)]
    if all((root / f).exists() for f in integrity.PYTHON_EDITABLE):
        found.append("python")
    marker = root / "language.txt"
    if marker.exists():
        chosen = marker.read_text().strip().lower()
        if chosen not in ("python", "cpp", "java"):
            raise ValueError("language.txt must contain python, cpp, or java")
        # The staff tree has all languages; release/submission trees have one.
        if len(found) > 1 and not (root / "staff/make_starter.py").is_file():
            raise ValueError("Mixed-language submission: submit exactly one starter folder")
        return chosen
    if len(found) == 1:
        return found[0]
    if len(found) > 1 and (root / "staff/make_starter.py").is_file():
        return "python"
    raise ValueError("Cannot identify one language; include language.txt and one complete starter")


def editable(root=None):
    lang = language(root)
    return integrity.PYTHON_EDITABLE if lang == "python" else SOURCES[lang]


def guard(root=None, lang=None):
    import re
    root = Path(root or integrity.ROOT)
    lang = lang or language(root)
    out = []
    for name in SOURCES[lang]:
        p = root / name
        if not p.is_file():
            out.append(f"{name} is missing")
            continue
        src = p.read_text(errors="replace")
        # Ignore comments so a note about a prohibited container is harmless.
        src = re.sub(r'/\*.*?\*/|//[^\n]*', '', src, flags=re.S)
        banned = (r'\b(priority_queue|make_heap|push_heap|pop_heap|sort_heap|multiset|multimap)\b'
                  if lang == "cpp" else r'\b(PriorityQueue|PriorityBlockingQueue|TreeSet|TreeMap)\b')
        if re.search(banned, src):
            out.append(f"{name}: write your own heap; library priority queues are prohibited")
        if name.endswith(("Heap.hpp", "Heap.java")) and re.search(r'\b(sort|stable_sort|sorted)\s*\(', src):
            out.append(f"{name}: sorting is not a binary heap implementation")
        if re.search(r'\b(terrain_|belief_|order_|closed_|probes_|re_|terrain|belief)\b', src):
            out.append(f"{name}: use the public sensing/search API, not support internals")
        if lang == "cpp" and re.search(r'#\s*define\s+(private|protected|class)\b', src):
            out.append(f"{name}: changing support access controls is prohibited")
        if lang == "java" and ('java.lang.reflect' in src or 'setAccessible' in src):
            out.append(f"{name}: reflection into support code is prohibited")
    return out


class Worker:
    def __init__(self, lang, root):
        self.lang, self.root, self.process = lang, Path(root), None
        self.temp = tempfile.TemporaryDirectory(prefix="a1-native-")
        self.build = Path(self.temp.name)
        # Build from only named source files. Never run submitted build scripts.
        files = SOURCES[lang] + tuple(n for n in SUPPORT if f"/{lang}/" in n)
        for name in files:
            shutil.copy2(self.root / name, self.build / Path(name).name)
        if lang == "cpp":
            compiler = shutil.which("g++") or shutil.which("clang++")
            if not compiler:
                raise RuntimeError("C++17 compiler missing: install g++ or clang++")
            cmd = [compiler, "-std=c++17", "-O2", "Runner.cpp", "-o", "worker"]
            self.command = [str(self.build / "worker")]
        else:
            compiler = shutil.which("javac")
            if not compiler:
                raise RuntimeError("Java compiler missing: install JDK 17 or newer (javac and java)")
            cmd = [compiler, "--release", "17", "-d", "."] + [Path(n).name for n in files]
            self.command = [shutil.which("java") or "java", "-Xmx512m", "-cp", str(self.build), "Runner"]
        with tempfile.TemporaryFile() as log:
            try:
                r = subprocess.run(cmd, cwd=self.build, stdout=log, stderr=log, timeout=60)
            except subprocess.TimeoutExpired as e:
                raise RuntimeError("Compilation exceeded 60 seconds") from e
            if r.returncode:
                log.seek(0)
                raise RuntimeError("Compilation failed:\n" + log.read(12000).decode(errors="replace"))
        atexit.register(self.close)

    def close(self):
        if self.process is not None:
            self.process.kill()
            self.process.wait()
            self.process.stdin.close()
            self.process.stdout.close()
            self.process = None
        self.temp.cleanup()

    def _start(self):
        self.process = subprocess.Popen(self.command, cwd=self.build, stdin=subprocess.PIPE,
                                        stdout=subprocess.PIPE, stderr=None)
        self.responses = queue.Queue(maxsize=2)
        proc, responses = self.process, self.responses
        def read():
            try:
                while True:
                    line = proc.stdout.readline(32 * 1024 * 1024)
                    try:
                        responses.put(line, timeout=1)
                    except queue.Full:
                        break
                    if not line or not line.endswith(b"\n"):
                        break
            except (ValueError, OSError):
                pass
        threading.Thread(target=read, daemon=True).start()

    def ask(self, request, timeout=25):
        if self.process is None:
            self._start()
        try:
            proc, responses = self.process, self.responses
            def write():
                try:
                    proc.stdin.write((request + "\n").encode())
                    proc.stdin.flush()
                except (BrokenPipeError, OSError, ValueError):
                    pass
            threading.Thread(target=write, daemon=True).start()
            try:
                raw = responses.get(timeout=timeout)
            except queue.Empty as e:
                raise TimeoutError(f"Native program exceeded {timeout}s on one check") from e
            if not raw or not raw.endswith(b"\n"):
                raise RuntimeError("Native program exited or exceeded the response limit")
            result = json.loads(raw)
            if "error" in result:
                message = result["error"]
                if "TODO:" in message:
                    raise NotImplementedError(message)
                raise RuntimeError(message)
            return result
        except BaseException:
            # A timeout or crash must not leave a stale response for the next world.
            if self.process is not None:
                self.process.kill()
                self.process.wait()
                self.process.stdin.close()
                self.process.stdout.close()
                self.process = None
            raise


def cell(s, w, height):
    if not isinstance(s, int) or not 0 <= s < w * height:
        raise ValueError(f"invalid native cell ID {s!r}")
    return (s % w, s // w)


def snapshot(record, w, height):
    order = [cell(s, w, height) for s in record.get("order", [])]
    vals = {key: record[key] for key in ("expansions", "reexpansions", "probes")}
    if any(not isinstance(v, int) or v < 0 for v in vals.values()):
        raise ValueError("invalid native counters")
    return {**vals, "distinct": vals["expansions"] - vals["reexpansions"],
            "closed": set(order), "order": list(dict.fromkeys(order)), "elapsed": 0.0}


class NativeImpl:
    def __init__(self, lang, root=None):
        self.name, self.errors = lang, {}
        self.root = Path(root or integrity.ROOT)
        self.heuristics = SimpleNamespace(REBUILD_EVERY=16)
        self.heap = None
        self.search = SimpleNamespace(astar=self.astar)
        try:
            violations = guard(self.root, lang)
            if violations:
                raise ValueError("; ".join(violations))
            self.worker = Worker(lang, self.root)
        except Exception as e:
            self.errors[lang] = str(e)

    @property
    def broken(self):
        return bool(self.errors)

    def why(self):
        return "; ".join(self.errors.values())

    def request(self, op, w, height, start, goal, probe, hk, key="forward", tie="large_g", weight=1, max_steps=200000):
        if self.broken:
            raise RuntimeError(self.why())
        bits = ''.join('1' if probe(x, y) else '0' for y in range(height) for x in range(w))
        return self.worker.ask(f"{op} {w} {height} {start[1]*w+start[0]} {goal[1]*w+goal[0]} {hk} {key} {tie} {weight} {self.heuristics.REBUILD_EVERY} {max_steps} {bits}")

    def h(self, key):
        if key not in ("manhattan", "zero", "differential", "custom"):
            raise KeyError(key)
        last = [None, None]
        def h(s, p):
            if last[0] is not p:
                r = self.request("HVALUES", p.w, p.h, p.start, p.goal, p.passable, key)
                last[:] = [p, r["values"]]
            v = last[1][s[1]*p.w+s[0]]
            return float('nan') if v is None else v
        h.key = key
        return h

    def astar(self, p, h, *, tie_break="large_g", weight=1, learned=None):
        r = self.request("SEARCH", p.w, p.h, p.start, p.goal, p.passable, h.key, tie=tie_break, weight=weight)
        snap = snapshot(r["snapshot"], p.w, p.h)
        p._snapshot = lambda: snap  # authoritative counters from the supplied native SDK
        path = [cell(s, p.w, p.h) for s in r["path"]] or None
        return path, {cell(s, p.w, p.h): d for s, d in r["g"]}

    def agent(self, key):
        impl = self
        class Agent(ReplanningAgent):
            def run(self, max_steps=200000):
                w = self.world
                r = impl.request("LOOP", w.w, w.h, w.start, w.goal, core._true_grid_passable(w),
                                 self.h.key, key, self.tie_break, self.weight, max_steps)
                trajectory = [cell(s, w.w, w.h) for s in r["trajectory"]]
                if not trajectory or trajectory[0] != w.start:
                    raise ValueError("trajectory does not start at the initial cell")
                self.sense()
                for s in trajectory[1:]:
                    self.move_to(s)  # independently enforce sensing and legal movement
                for rec in r["searches"]:
                    snap = snapshot(rec, w.w, w.h)
                    p = SimpleNamespace(start=cell(rec["start"], w.w, w.h),
                                        goal=cell(rec["goal"], w.w, w.h),
                                        snapshot=lambda snap=snap: snap, intact=lambda: True, **snap)
                    self.searches.append(p)
                self.learned_h = {cell(s, w.w, w.h): float('nan') if v is None else v for s,v in r["learned"]}
                if any(not math.isfinite(v) or v < 0 for v in self.learned_h.values()):
                    raise ValueError("learned heuristics must be finite and nonnegative")
                self.solved = r["solved"]
                return self.solved
        return Agent

    def check_heap(self, say):
        rng = random.Random(7)
        ops, flat, ref, nxt = [], [], {}, 0
        # Generate the same priority distribution and operation count as Python.
        for _ in range(4000):
            if ref and rng.random() < .45:
                ops.append(None);flat.append('1')
                del ref[min(ref, key=ref.get)]
            else:
                pri = (rng.randrange(500), rng.randrange(500))
                ops.append((nxt, pri));flat.extend(map(str, (0, *pri, nxt)))
                ref[nxt] = pri;nxt += 1
        n = 60000
        flat += [str(n)] + [str(rng.randrange(1 << 30)) for _ in range(n)]
        r = self.worker.ask("HEAP 4000 " + " ".join(flat))
        if not r['invariant'] or not r['sorted']:
            say(2, "FAIL heap invariant or sorted removal order")
            return 0.0
        ref = {};popped = iter(r['popped'])
        if len(r['sizes']) != len(ops) or len(r['popped']) != sum(op is None for op in ops):
            raise ValueError("incomplete heap results")
        for op, size in zip(ops, r['sizes']):
            if op is None:
                item = next(popped)
                if item not in ref or ref[item] != min(ref.values()):
                    say(2, "FAIL heap popped an item without minimum priority")
                    return 0.0
                del ref[item]
            else:
                ref[op[0]] = op[1]
            if size != len(ref):
                say(2, "FAIL heap size is incorrect")
                return 0.0
        if not r['empty']:
            say(2, "FAIL empty heap must throw the documented exception")
            return 1.5
        if r['comparisons'] > 6*n*math.log2(n):
            say(2, "Heap correct but exceeded the comparison budget")
            return 2.0
        say(2, f"Heap passed 4,000 mixed operations and 60,000-item comparison test ({r['comparisons']:,} comparisons)")
        return 3.0
