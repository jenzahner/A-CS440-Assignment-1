"""Shared measurements for the autograder and report. DO NOT EDIT.

The autograder uses fixed test seeds; the report uses team-derived seeds.
Both use this module to measure searches and validate paths and trajectories.
"""
from __future__ import annotations

import importlib
import time

from gridworld import core, integrity, report_spec, stats

AGENT_ORDER = ("forward", "backward", "adaptive")


def unpack(result):
    """Read ``(path, g)`` back from a student `astar`, with a usable complaint.

    Returning a bare path instead of the pair is the single most likely way to
    get this wrong, and "cannot unpack non-sequence" would send someone looking
    in entirely the wrong place.
    """
    if isinstance(result, tuple) and len(result) == 2:
        return result
    raise TypeError(
        f"astar must return (path, g); it returned {type(result).__name__}. "
        f"If you have a path, return `path, g` where g is your g-value dict.")


class Impl:
    """One implementation to measure -- normally ``gridworld``.

    Importing is allowed to fail.  A file with a syntax error is a completely
    normal state for a submission to be in, and the grader has to be able to say
    so in a score report rather than fall over with a traceback -- so each
    module is imported on its own and the failures are collected.
    """

    MODULES = ("agents", "heuristics", "search", "heap")

    def __new__(cls, name="gridworld"):
        from gridworld.native import NativeImpl, language
        chosen = language() if name == "gridworld" else name
        if chosen in ("cpp", "java"):
            return NativeImpl(chosen)
        return super().__new__(cls)

    def __init__(self, name="gridworld"):
        self.name = name
        #: module name -> the exception that stopped it importing
        self.errors: dict[str, str] = {}
        if name == "gridworld":
            violations = integrity.guard()
            if violations:
                for mod in self.MODULES:
                    setattr(self, mod, None)
                    self.errors[mod] = "; ".join(violations)
                return
        for mod in self.MODULES:
            try:
                setattr(self, mod, importlib.import_module(f"{name}.{mod}"))
            except Exception as e:                          # noqa: BLE001
                setattr(self, mod, None)
                self.errors[mod] = f"{type(e).__name__}: {e}"

    @property
    def broken(self) -> bool:
        return bool(self.errors)

    def why(self) -> str:
        return "; ".join(f"{name}.py -- {e}" for name, e in self.errors.items())

    def agent(self, key):
        if self.agents is None:
            raise ImportError(f"{self.name}.agents: {self.errors.get('agents')}")
        return self.agents.AGENTS[key]

    def h(self, key):
        if self.heuristics is None:
            raise ImportError(
                f"{self.name}.heuristics: {self.errors.get('heuristics')}")
        return self.heuristics.HEURISTICS[key]


# ---------------------------------------------------------------- timeouts


class Timeout(Exception):
    pass


class _deadline:
    """SIGALRM-based wall-clock cap, so one hung world cannot hang a container."""

    def __init__(self, seconds):
        self.seconds = seconds
        self.ok = False

    def __enter__(self):
        try:
            import signal
            self._old = signal.signal(signal.SIGALRM, self._fire)
            signal.setitimer(signal.ITIMER_REAL, self.seconds)
            self.ok = True
        except (ImportError, ValueError, AttributeError):
            self.ok = False        # Windows, or not the main thread
        return self

    def _fire(self, *a):
        raise Timeout(f"exceeded {self.seconds:g}s on one world")

    def __exit__(self, *a):
        if self.ok:
            import signal
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, self._old)
        return False


# ---------------------------------------------------------------- one world


def run_loop(impl, agent_key, world, h_key, *, tie_break="large_g", weight=1.0,
             timeout=report_spec.PER_WORLD_TIMEOUT) -> dict:
    """Run one replanning agent on one world and read its instruments."""
    rec = {"seed": world.seed, "error": None, "solved": False, "expansions": 0,
           "reexpansions": 0, "probes": 0, "seconds": 0.0, "searches": 0,
           "traj": 0, "tampered": False}
    t0 = time.perf_counter()
    agent = None
    try:
        with _deadline(timeout):
            cls = impl.agent(agent_key)
            agent = cls(world, impl.h(h_key), tie_break=tie_break, weight=weight)
            agent.run()
    except Timeout as e:
        rec["error"] = str(e)
    except NotImplementedError as e:
        rec["error"] = f"not implemented: {e}"
        return rec
    except Exception as e:                                  # noqa: BLE001
        rec["error"] = f"{type(e).__name__}: {e}"
    rec["seconds"] = time.perf_counter() - t0
    if agent is None:
        return rec

    snaps = [p.snapshot() for p in agent.searches]
    rec["expansions"] = sum(s["expansions"] for s in snaps)
    rec["reexpansions"] = sum(s["reexpansions"] for s in snaps)
    rec["probes"] = sum(s["probes"] for s in snaps)
    rec["searches"] = len(snaps)
    rec["traj"] = max(0, len(agent.trajectory) - 1)
    rec["tampered"] = any(not p.intact() for p in agent.searches)
    rec["solved"] = bool(agent.solved)

    if rec["tampered"] and rec["error"] is None:
        rec["error"] = "search instrumentation was replaced"
    if rec["error"] is None:
        bad = _check_trajectory(world, agent)
        if bad:
            rec["error"] = bad
    rec["_agent"] = agent
    return rec


def _check_trajectory(world, agent) -> str | None:
    """Re-walk the trajectory against the true map.  The claim has to survive it."""
    probe = core._true_grid_passable(world)
    traj = agent.trajectory
    if not traj or traj[0] != world.start:
        return "trajectory does not start at the agent's start cell"
    for a, b in zip(traj, traj[1:]):
        if abs(a[0] - b[0]) + abs(a[1] - b[1]) != 1:
            return f"trajectory jumps from {a} to {b}"
        if not probe(*b):
            return f"trajectory walks through the blocked cell {b}"
    reachable = core._optimal_cost(probe, world.w, world.h, world.start, world.goal)
    if agent.solved and traj[-1] != world.goal:
        return "reported success without standing on the target"
    if not agent.solved and reachable is not None:
        return "reported the target unreachable, but it is reachable"
    if agent.solved and reachable is None:
        return "reported reaching a target that is unreachable"
    return None


def run_known(impl, world, h_key, *, weight=1.0, tie_break="large_g",
              timeout=report_spec.PER_WORLD_TIMEOUT) -> dict:
    """One A* search on the fully known map -- the single-search regime."""
    rec = {"seed": world.seed, "error": None, "expansions": 0, "reexpansions": 0,
           "probes": 0, "seconds": 0.0, "cost": None, "optimal": None}
    probe = core._true_grid_passable(world)
    problem = core._make_known_problem(world, {})
    t0 = time.perf_counter()
    path = None
    try:
        with _deadline(timeout):
            if impl.search is None:
                raise ImportError(f"search.py -- {impl.errors.get('search')}")
            path = unpack(impl.search.astar(problem, impl.h(h_key),
                                            tie_break=tie_break, weight=weight))[0]
    except Timeout as e:
        rec["error"] = str(e)
    except NotImplementedError as e:
        rec["error"] = f"not implemented: {e}"
        return rec
    except Exception as e:                                  # noqa: BLE001
        rec["error"] = f"{type(e).__name__}: {e}"
    problem.stop_clock()
    rec["seconds"] = time.perf_counter() - t0
    snap = problem.snapshot()
    rec.update(expansions=snap["expansions"], reexpansions=snap["reexpansions"],
               probes=snap["probes"])
    rec["optimal"] = core._optimal_cost(probe, world.w, world.h,
                                        world.start, world.goal)
    if not problem.intact() and rec["error"] is None:
        rec["error"] = "search instrumentation was replaced"
    if rec["error"] is None and path is None and rec["optimal"] is not None:
        rec["error"] = "returned no path, but the goal is reachable"
    elif rec["error"] is None and path is not None and not path:
        rec["error"] = "returned an empty path; use None for an unreachable goal"
    elif path and rec["error"] is None:
        bad = core._check_path(probe, path, world.start, world.goal)
        if bad:
            rec["error"] = bad
        else:
            rec["cost"] = len(path) - 1
    rec["_problem"] = problem
    rec["_path"] = path
    return rec


# ---------------------------------------------------------------- aggregate


def summarise(records) -> dict:
    """Collapse per-world records into the numbers a report and a score use."""
    good = [r for r in records if r["error"] is None]
    exp = [r["expansions"] for r in good]
    out = {
        "n": len(records),
        "ok": len(good),
        "errors": [r["error"] for r in records if r["error"]][:3],
        "expansions_mean": stats.mean(exp),
        "expansions_median": stats.median(exp),
        "expansions_total": sum(exp),
        "reexpansions": sum(r["reexpansions"] for r in good),
        "probes_mean": stats.mean([r["probes"] for r in good]),
        "seconds_mean": stats.mean([r["seconds"] for r in good]),
        "seconds_total": sum(r["seconds"] for r in records),
        "tampered": any(r.get("tampered") for r in records),
        "per_world": exp,
    }
    if good and "traj" in good[0]:
        out["traj_mean"] = stats.mean([r["traj"] for r in good])
        out["searches_mean"] = stats.mean([r["searches"] for r in good])
        out["solved"] = sum(1 for r in good if r["solved"])
    if good and good[0].get("optimal") is not None:
        ratios = [r["cost"] / r["optimal"] for r in good
                  if r["cost"] and r["optimal"]]
        out["cost_ratio"] = stats.mean(ratios) if ratios else 0.0
        out["cost_mean"] = stats.mean([r["cost"] for r in good if r["cost"]])
    return out


def worlds(family, size, seeds, solvable=True):
    for s in seeds:
        yield core.generate(size, s, family=family, solvable=solvable)


# ---------------------------------------------------------------- the suite


def collect(impl, ruids, *, quick=False, progress=None) -> dict:
    """Run every experiment the report shows.  Returns one nested dict."""
    say = progress or (lambda *a: None)
    rs = report_spec
    scale = 0.3 if quick else 1.0

    def n(k):
        return max(3, int(round(k * scale)))

    data: dict = {"loop": {}, "tie": {}, "known": {}, "weighted": {},
                  "trend": [], "rebuild": [], "stats": {}, "heurloop": {},
                  "meta": {"quick": quick, "impl": impl.name}}

    # -- head to head, in the replanning loop -------------------------
    for family, size in rs.FAMILIES:
        seeds = rs.team_seeds(ruids, n(rs.N_WORLDS), f"{family}{size}")
        ws = list(worlds(family, size, seeds))
        data["loop"][family] = {}
        loop_records = {}
        for key in AGENT_ORDER:
            say(f"  loop {family}{size} {key}")
            recs = [run_loop(impl, key, w, rs.LOOP_HEURISTIC) for w in ws]
            loop_records[key] = recs
            data["loop"][family][key] = summarise(recs)
        pairs = [(a["expansions"], f["expansions"])
                 for a, f in zip(loop_records["adaptive"], loop_records["forward"])
                 if a["error"] is None and f["error"] is None]
        if pairs:
            a, f = zip(*pairs)
            data["stats"][family] = stats.paired_summary(a, f)
        data["meta"].setdefault("sizes", {})[family] = size

    # -- tie-breaking --------------------------------------------------
    for family, size in rs.FAMILIES:
        seeds = rs.team_seeds(ruids, n(rs.N_TIE), f"tie{family}")
        ws = list(worlds(family, size, seeds))
        data["tie"][family] = {}
        for rule in ("small_g", "large_g"):
            say(f"  ties {family}{size} {rule}")
            recs = [run_loop(impl, "forward", w, rs.LOOP_HEURISTIC,
                             tie_break=rule) for w in ws]
            data["tie"][family][rule] = summarise(recs)

    # -- one search on a known map: heuristics, then weights -----------
    for family, _ in rs.FAMILIES:
        seeds = rs.team_seeds(ruids, n(rs.N_KNOWN), f"known{family}")
        ws = list(worlds(family, rs.KNOWN_SIZE, seeds))
        data["known"][family] = {}
        for hk in ("manhattan", "differential", "custom"):
            say(f"  known {family} h={hk}")
            data["known"][family][hk] = summarise(
                [run_known(impl, w, hk) for w in ws])
        data["weighted"][family] = {}
        for wt in rs.WEIGHTS:
            say(f"  known {family} w={wt}")
            s = summarise([run_known(impl, w, "manhattan", weight=wt) for w in ws])
            s["w"] = wt
            data["weighted"][family][wt] = s

    # -- the same heuristics, but inside the loop where they must pay --
    family, size = rs.FAMILIES[1]
    seeds = rs.team_seeds(ruids, n(rs.N_REBUILD), "heurloop")
    ws = list(worlds(family, size, seeds))
    data["heurloop"][family] = {}
    for hk in ("manhattan", "custom"):
        say(f"  loop {family}{size} h={hk}")
        data["heurloop"][family][hk] = summarise(
            [run_loop(impl, "forward", w, hk) for w in ws])

    # -- rebuild-policy sweep -----------------------------------------
    hmod = impl.heuristics          # the module being measured, not ours
    original = getattr(hmod, "REBUILD_EVERY", 16)
    for every in rs.REBUILD_SWEEP:
        hmod.REBUILD_EVERY = (1 << 30) if every is None else every
        say(f"  rebuild every={every}")
        s = summarise([run_loop(impl, "forward", w, "custom") for w in ws])
        s["every"] = every
        data["rebuild"].append(s)
    hmod.REBUILD_EVERY = original

    # -- scaling trend -------------------------------------------------
    for size in rs.TREND_SIZES:
        seeds = rs.team_seeds(ruids, n(rs.N_TREND), f"trend{size}")
        ws = list(worlds("maze", size, seeds))
        row = {"size": size}
        for key in AGENT_ORDER:
            say(f"  trend maze{size} {key}")
            row[key] = summarise([run_loop(impl, key, w, rs.LOOP_HEURISTIC)
                                  for w in ws])
        data["trend"].append(row)

    return data
