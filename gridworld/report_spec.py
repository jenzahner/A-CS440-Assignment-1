"""Experiment settings, report parsing, and measurement macros. DO NOT EDIT.

Students write answers in report.txt and cite results with {{macro.name}}.
Run python3 autograder.py --macros to list available names.
"""
from __future__ import annotations

import hashlib
import re

# ---------------------------------------------------------------- experiments

#: (family, grid size) for the two standard instance sets.  `scatter` is the
#: handout's own generator at the handout's own size; `maze` is smaller because
#: corridor worlds take far longer to solve and the effect there is large enough
#: to see at 51.
FAMILIES = (("scatter", 101), ("maze", 51))

#: worlds per family for the head-to-head comparison -- the handout's 50
N_WORLDS = 50
#: worlds for the tie-breaking comparison (smaller-g is expensive)
N_TIE = 20
#: worlds for the single-search benchmarks, which are cheap
N_KNOWN = 20
#: grid size for the single-search benchmarks: one long search, both families
KNOWN_SIZE = 101
#: worlds per size for the scaling trend
N_TREND = 6
#: sizes for the scaling trend, on the maze family
TREND_SIZES = (31, 41, 51, 61, 71)
#: weights swept for the bounded-suboptimality trade-off
WEIGHTS = (1.0, 1.25, 1.5, 2.0, 3.0, 5.0)
#: landmark-table staleness thresholds swept in Part 6(c); None means "never"
REBUILD_SWEEP = (1, 4, 16, 64, None)
#: worlds for the rebuild sweep
N_REBUILD = 8

#: the heuristic the head-to-head comparison uses, so that Parts 3, 4 and 5 are
#: about the algorithms rather than about whose heuristic is better
LOOP_HEURISTIC = "manhattan"

#: a run that takes longer than this on one world is abandoned and reported as
#: a failure, so one pathological bug cannot hang a grading container
PER_WORLD_TIMEOUT = 25.0


def team_seeds(ruids, n: int, salt: str = "") -> list[int]:
    """The instance set for one team, derived from its RUIDs.

    Every team gets a different 50 worlds.  This is not to make the assignment
    harder -- the worlds are drawn from the same distribution and are no easier
    or harder -- but so that a set of results belongs to exactly one team.  A
    report whose numbers do not match the submitting team's seeds was not
    produced by the submitting team's run.
    """
    key = hashlib.sha256(("|".join(sorted(ruids)) + "#" + salt).encode()).hexdigest()
    base = int(key[:12], 16) % 1_000_000
    return [base + i for i in range(n)]


# ---------------------------------------------------------------- the report

ANSWER_KEYS = ("Q1", "Q2", "Q3", "Q4", "Q5", "Q6", "Q7")

QUESTION_TITLES = {
    "Q1": "Q1  Why east, and why Manhattan is consistent",
    "Q2": "Q2  Termination, and the bound on the number of moves",
    "Q3": "Q3  Tie-breaking: what you measured and why it happens",
    "Q4": "Q4  Forward vs. backward: where the asymmetry comes from",
    "Q5": "Q5  Adaptive A*, and whether the difference is real",
    "Q6": "Q6  Your differential heuristic, and when it fails to pay",
    "Q7": "Q7  Weighted A*: the bound, and why the loop erases the gain",
}

MAX_CHARS = 520
MIN_CHARS = 1
PLACEHOLDER = "REPLACE THIS TEXT WITH YOUR ANSWER"
PLACEHOLDER_NAME = "YOUR NAME HERE"
PLACEHOLDER_RUID = "000000000"
MAX_TEAM = 4

PLEDGE = ("I did not use generative AI to write any code or any answer in "
          "this submission, and every member of this team can explain every "
          "line of it.")

#: Names you may cite in an answer, and where each one comes from in the
#: measured data.  Anything not in this table cannot be put on the page.
MACROS: dict[str, tuple] = {
    # head-to-head, replanning loop, h = manhattan, large-g tie-breaking
    "scatter.fwd.exp": ("loop", "scatter", "forward", "expansions_mean"),
    "scatter.bwd.exp": ("loop", "scatter", "backward", "expansions_mean"),
    "scatter.ada.exp": ("loop", "scatter", "adaptive", "expansions_mean"),
    "maze.fwd.exp": ("loop", "maze", "forward", "expansions_mean"),
    "maze.bwd.exp": ("loop", "maze", "backward", "expansions_mean"),
    "maze.ada.exp": ("loop", "maze", "adaptive", "expansions_mean"),
    "scatter.fwd.traj": ("loop", "scatter", "forward", "traj_mean"),
    "maze.fwd.traj": ("loop", "maze", "forward", "traj_mean"),
    "scatter.fwd.searches": ("loop", "scatter", "forward", "searches_mean"),
    "maze.fwd.searches": ("loop", "maze", "forward", "searches_mean"),
    # ratios
    "scatter.bwd_over_fwd": ("ratio", "scatter", "backward"),
    "maze.bwd_over_fwd": ("ratio", "maze", "backward"),
    "scatter.ada_over_fwd": ("ratio", "scatter", "adaptive"),
    "maze.ada_over_fwd": ("ratio", "maze", "adaptive"),
    # tie-breaking
    "scatter.tie.small": ("tie", "scatter", "small_g", "expansions_mean"),
    "scatter.tie.large": ("tie", "scatter", "large_g", "expansions_mean"),
    "maze.tie.small": ("tie", "maze", "small_g", "expansions_mean"),
    "maze.tie.large": ("tie", "maze", "large_g", "expansions_mean"),
    "scatter.tie.ratio": ("tieratio", "scatter"),
    "maze.tie.ratio": ("tieratio", "maze"),
    # the paired test on Adaptive vs Repeated Forward
    "scatter.ada.p": ("stats", "scatter", "p"),
    "maze.ada.p": ("stats", "maze", "p"),
    "scatter.ada.wins": ("stats", "scatter", "wins"),
    "maze.ada.wins": ("stats", "maze", "wins"),
    "scatter.ada.n": ("stats", "scatter", "n"),
    "maze.ada.n": ("stats", "maze", "n"),
    # single search on a fully known map
    "known.scatter.man": ("known", "scatter", "manhattan", "expansions_mean"),
    "known.scatter.diff": ("known", "scatter", "differential", "expansions_mean"),
    "known.scatter.custom": ("known", "scatter", "custom", "expansions_mean"),
    "known.maze.man": ("known", "maze", "manhattan", "expansions_mean"),
    "known.maze.diff": ("known", "maze", "differential", "expansions_mean"),
    "known.maze.custom": ("known", "maze", "custom", "expansions_mean"),
    "known.scatter.speedup": ("speedup", "scatter"),
    "known.maze.speedup": ("speedup", "maze"),
    # the heuristic inside the loop, where it has to pay for itself
    "loop.maze.man.exp": ("heurloop", "maze", "manhattan", "expansions_mean"),
    "loop.maze.custom.exp": ("heurloop", "maze", "custom", "expansions_mean"),
    "loop.maze.man.sec": ("heurloop", "maze", "manhattan", "seconds_mean"),
    "loop.maze.custom.sec": ("heurloop", "maze", "custom", "seconds_mean"),
    # weighted A*
    "w15.exp": ("weighted", "scatter", 1.5, "expansions_mean"),
    "w15.cost": ("weighted", "scatter", 1.5, "cost_ratio"),
    "w50.exp": ("weighted", "scatter", 5.0, "expansions_mean"),
    "w50.cost": ("weighted", "scatter", 5.0, "cost_ratio"),
    "w1.exp": ("weighted", "scatter", 1.0, "expansions_mean"),
}

#: characters that make a token look like a reported result rather than prose
_RESULT_NUMBER = re.compile(
    r"""(?<![\w.])(
        \d+\.\d+          # a decimal: 1.5, 0.42
      | \d{2,}            # two or more digits: 15, 4122
      | \d\s*[%×]         # a percentage or a times sign
      | \d\s*[xX](?![\w]) # "3x fewer"
    )""", re.VERBOSE)

_MACRO = re.compile(r"\{\{\s*([A-Za-z0-9_.]+)\s*\}\}")


def parse_report(text: str) -> dict:
    """Parse the ``=== KEY ===`` block format.  Returns ``{key: body}``."""
    out: dict = {}
    key, buf = None, []
    for line in text.splitlines():
        m = re.match(r"^\s*===\s*([A-Za-z0-9_]+)\s*===\s*$", line)
        if m:
            if key is not None:
                out[key] = "\n".join(buf).strip()
            key, buf = m.group(1).upper(), []
            continue
        if line.lstrip().startswith("#"):
            continue
        if key is not None:
            buf.append(line)
    if key is not None:
        out[key] = "\n".join(buf).strip()
    return out


def parse_members(block: str) -> list[tuple[str, str]]:
    members = []
    for line in (block or "").splitlines():
        line = line.strip()
        if not line:
            continue
        name, _, ruid = line.partition(",")
        members.append((name.strip(), ruid.strip()))
    return members


def macro_value(name: str, data: dict):
    """Resolve one macro against measured data.  Returns None if unavailable."""
    path = MACROS.get(name)
    if path is None or not data:
        return None
    kind, rest = path[0], path[1:]
    try:
        if kind == "ratio":
            fam, alg = rest
            base = data["loop"][fam]["forward"]["expansions_mean"]
            return data["loop"][fam][alg]["expansions_mean"] / base
        if kind == "tieratio":
            fam = rest[0]
            return (data["tie"][fam]["small_g"]["expansions_mean"]
                    / data["tie"][fam]["large_g"]["expansions_mean"])
        if kind == "speedup":
            fam = rest[0]
            return (data["known"][fam]["manhattan"]["expansions_mean"]
                    / data["known"][fam]["custom"]["expansions_mean"])
        node = data[kind]
        for step in rest:
            node = node[step]
        return node
    except (KeyError, TypeError, ZeroDivisionError):
        return None


def format_value(v) -> str:
    if v is None:
        return "??"
    if isinstance(v, float):
        if v >= 1000:
            return f"{v:,.0f}"
        if v >= 100:
            return f"{v:.0f}"
        if v >= 10:
            return f"{v:.1f}"
        if v >= 0.01:
            return f"{v:.2f}"
        return f"{v:.3g}"
    return f"{v:,}" if isinstance(v, int) and abs(v) >= 1000 else str(v)


def substitute(body: str, data: dict) -> tuple[str, list[str], list[str]]:
    """Replace every ``{{macro}}`` with its measured value.

    Returns the rendered text, the macro names that are not citable at all, and
    the ones that are citable but have no measurement yet.  The two are
    different problems: the first is a typo in an answer, the second only means
    nothing has been run.
    """
    unknown: list[str] = []
    unmeasured: list[str] = []

    def sub(m):
        name = m.group(1)
        if name not in MACROS:
            unknown.append(name)
            return f"[unknown macro {name}]"
        v = macro_value(name, data)
        if v is None:
            unmeasured.append(name)
            return "[not measured]"
        return format_value(v)

    return _MACRO.sub(sub, body), unknown, unmeasured


#: one team check, one pledge check, one per answer
N_CHECKS = 2 + len(ANSWER_KEYS)


def check_report(parsed: dict, data: dict | None = None) -> list[str]:
    """Every problem with a report.  An empty list means it is well-formed."""
    problems: list[str] = []

    members = parse_members(parsed.get("MEMBERS", ""))
    if not members:
        problems.append("MEMBERS is empty -- list every member as 'Name, RUID'")
    elif len(members) > MAX_TEAM:
        problems.append(f"{len(members)} members listed; the maximum team size "
                        f"is {MAX_TEAM}")
    else:
        for name, ruid in members:
            if not name or PLACEHOLDER_NAME.lower() in name.lower():
                problems.append("MEMBERS still holds the template placeholder")
            elif ruid == PLACEHOLDER_RUID:
                problems.append(f"'{name}' still has the placeholder RUID")
            elif not re.fullmatch(r"\d{6,12}", ruid or ""):
                problems.append(f"'{name}' has a missing or malformed RUID ({ruid!r})")

    pledge = " ".join((parsed.get("PLEDGE") or "").split())
    if pledge != PLEDGE:
        problems.append("PLEDGE is missing or altered -- it must be typed exactly "
                        "as it appears in report.txt")

    for k in ANSWER_KEYS:
        body = " ".join((parsed.get(k) or "").split())
        if not body:
            problems.append(f"{k} is missing")
            continue
        if PLACEHOLDER.lower() in body.lower():
            problems.append(f"{k} still contains the placeholder text")
            continue
        rendered, unknown, unmeasured = substitute(body, data or {})
        for name in unknown:
            problems.append(f"{k} cites {{{{{name}}}}}, which is not a name you "
                            f"may cite (see MACROS in report_spec.py, or run "
                            f"`python3 autograder.py --macros`)")
        if data:
            for name in unmeasured:
                problems.append(f"{k} cites {{{{{name}}}}}, which this run did not "
                                f"measure -- the part it comes from failed")
        stripped = _MACRO.sub("", body)
        for m in _RESULT_NUMBER.finditer(stripped):
            problems.append(
                f"{k} contains the typed number '{m.group(0).strip()}'. Results "
                f"are never typed: cite one with a macro such as "
                f"{{{{scatter.tie.ratio}}}} instead")
            break
        if len(rendered) < MIN_CHARS:
            problems.append(f"{k} is {len(rendered)} characters; at least "
                            f"{MIN_CHARS} expected")
        elif (data is not None or not _MACRO.search(body)) and len(rendered) > MAX_CHARS:
            problems.append(f"{k} is {len(rendered)} characters; the page fits "
                            f"{MAX_CHARS} and the rest is cut off")
    return problems
