"""Paired statistics for Part 5. DO NOT EDIT.

Compare expansion counts on the same worlds using paired differences.
The signed-rank null is symmetry about zero; a location interpretation assumes
symmetric differences and independent worlds. Skewed raw counts alone do not
establish whether a paired t-test is appropriate. Interpret p-values alongside
effect sizes. See the staff key for references and grading guidance.
"""
from __future__ import annotations

import math
import random


def mean(xs):
    xs = list(xs)
    return sum(xs) / len(xs) if xs else 0.0


def median(xs):
    xs = sorted(xs)
    n = len(xs)
    if not n:
        return 0.0
    return xs[n // 2] if n % 2 else 0.5 * (xs[n // 2 - 1] + xs[n // 2])


def stdev(xs):
    xs = list(xs)
    if len(xs) < 2:
        return 0.0
    m = mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))


def _phi(z):
    """Standard normal CDF."""
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def _ranks(values):
    """Ranks 1..n with ties given their average rank."""
    order = sorted(range(len(values)), key=lambda i: values[i])
    out = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        avg = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            out[order[k]] = avg
        i = j + 1
    return out


def _exact_p(doubled_ranks, w2):
    """Exact two-sided p for the signed-rank statistic, by DP over subset sums.

    ``doubled_ranks`` are the ranks times two, so that average ranks from ties
    stay integers.  ``w2`` is the observed statistic, likewise doubled.
    """
    total = sum(doubled_ranks)
    counts = {0: 1}
    for r in doubled_ranks:
        nxt = dict(counts)
        for s, c in counts.items():
            nxt[s + r] = nxt.get(s + r, 0) + c
        counts = nxt
    n = len(doubled_ranks)
    space = 2 ** n
    lo = sum(c for s, c in counts.items() if s <= w2)
    hi = sum(c for s, c in counts.items() if s >= total - w2)
    p = (lo + hi) / space
    return min(1.0, p)


def wilcoxon(a, b) -> dict:
    """Paired Wilcoxon signed-rank test on ``a`` versus ``b``.

    Returns ``n`` (non-zero pairs), the statistic ``W``, a two-sided ``p``, how
    the method was computed, and how often ``a`` beat ``b``.
    """
    a, b = list(a), list(b)
    if len(a) != len(b):
        raise ValueError("paired samples must have equal lengths")
    diffs = [x - y for x, y in zip(a, b)]
    nz = [d for d in diffs if d != 0]
    wins = sum(1 for d in diffs if d < 0)       # a smaller = a wins
    losses = sum(1 for d in diffs if d > 0)
    ties = len(diffs) - wins - losses
    n = len(nz)
    if n == 0:
        return {"n": 0, "W": 0.0, "p": 1.0, "method": "no non-zero pairs",
                "wins": wins, "losses": losses, "ties": ties}

    rk = _ranks([abs(d) for d in nz])
    w_pos = sum(r for d, r in zip(nz, rk) if d > 0)
    w_neg = sum(r for d, r in zip(nz, rk) if d < 0)
    W = min(w_pos, w_neg)

    if n <= 22:
        p = _exact_p([int(round(2 * r)) for r in rk], int(round(2 * W)))
        method = "exact"
    else:
        mu = n * (n + 1) / 4.0
        # Conditional on the observed absolute ranks, independent random signs
        # give variance sum(rank**2)/4. This includes the correction for ties.
        sigma = math.sqrt(sum(r * r for r in rk) / 4.0)
        z = (W - mu + 0.5) / sigma if sigma else 0.0
        p = min(1.0, 2.0 * _phi(z))
        method = "normal approximation"
    return {"n": n, "W": W, "p": p, "method": method,
            "wins": wins, "losses": losses, "ties": ties}


def bootstrap_ci(xs, statistic=median, reps: int = 2000, alpha: float = 0.05,
                 seed: int = 12345):
    """Percentile bootstrap interval for a statistic of ``xs``."""
    xs = list(xs)
    if len(xs) < 2:
        return (0.0, 0.0)
    rng = random.Random(seed)
    n = len(xs)
    vals = []
    for _ in range(reps):
        vals.append(statistic([xs[rng.randrange(n)] for _ in range(n)]))
    vals.sort()
    lo = vals[int(alpha / 2 * reps)]
    hi = vals[min(reps - 1, int((1 - alpha / 2) * reps))]
    return (lo, hi)


def paired_summary(a, b) -> dict:
    """Everything the report needs about one paired comparison of ``a`` vs ``b``."""
    ratios = [x / y for x, y in zip(a, b) if y]
    out = wilcoxon(a, b)
    out["median_ratio"] = median(ratios)
    out["ci"] = bootstrap_ci(ratios)
    out["mean_a"], out["mean_b"] = mean(a), mean(b)
    return out
