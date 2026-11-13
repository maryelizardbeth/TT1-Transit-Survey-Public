"""
Statistical helpers for the women-vs-men deep dive.

Kept separate from generate_data.py so the method is easy to audit. Everything
returned here is aggregate-only (counts, percentages, test statistics).

Design choices
--------------
* Compare women (Female) with men (Male). Non-binary respondents (n=17) are too
  few to analyze separately, and cells that small risk identifying people, so
  they are excluded from comparisons (they are disclosed in the sample counts).
* Ordinal importance ratings: Mann-Whitney U (p), bootstrap CI on the mean
  difference, Cliff's delta as the effect size.
* Categorical / multi-select shares: Fisher's exact test (p) and a Newcombe
  hybrid-score 95% CI on the difference in percentage points.
* Many items are tested, so Benjamini-Hochberg false-discovery-rate q-values are
  computed per segment. Labels: "clear" = q < .10, "suggestive" = raw p < .05
  but q >= .10, otherwise "none".
"""
import math
import numpy as np
from scipy import stats

RNG_SEED = 20260813
N_BOOT = 3000


def bh_qvalues(pvals):
    """Benjamini-Hochberg adjusted p-values (q-values); NaNs are passed through."""
    p = np.array(pvals, dtype=float)
    q = np.full_like(p, np.nan)
    ok = ~np.isnan(p)
    if not ok.any():
        return q.tolist()
    pv = p[ok]
    order = np.argsort(pv)
    ranked = pv[order]
    m = len(pv)
    adj = ranked * m / (np.arange(m) + 1)
    adj = np.minimum.accumulate(adj[::-1])[::-1]
    adj = np.minimum(adj, 1.0)
    out = np.empty(m)
    out[order] = adj
    q[ok] = out
    return q.tolist()


def label_for(p, q):
    if p is None or (isinstance(p, float) and math.isnan(p)):
        return "none"
    if q is not None and not (isinstance(q, float) and math.isnan(q)) and q < 0.10:
        return "clear"
    if p < 0.05:
        return "suggestive"
    return "none"


def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (c - h, c + h)


def newcombe_diff(k1, n1, k2, n2):
    """95% CI for p1 - p2 (Newcombe hybrid score), in proportion units."""
    p1, p2 = k1 / n1, k2 / n2
    l1, u1 = wilson(k1, n1)
    l2, u2 = wilson(k2, n2)
    d = p1 - p2
    lo = d - math.sqrt((p1 - l1) ** 2 + (u2 - p2) ** 2)
    hi = d + math.sqrt((u1 - p1) ** 2 + (p2 - l2) ** 2)
    return lo, hi


def compare_binary(f_flags, m_flags):
    """f_flags / m_flags: boolean sequences (one entry per respondent who was asked)."""
    f = np.asarray(f_flags, dtype=bool)
    m = np.asarray(m_flags, dtype=bool)
    nf, nm = len(f), len(m)
    if nf == 0 or nm == 0:
        return None
    kf, km = int(f.sum()), int(m.sum())
    lo, hi = newcombe_diff(kf, nf, km, nm)
    try:
        p = float(stats.fisher_exact([[kf, nf - kf], [km, nm - km]])[1])
    except Exception:
        p = float("nan")
    return {
        "nF": nf, "nM": nm, "kF": kf, "kM": km,
        "pctF": round(kf / nf * 100, 1), "pctM": round(km / nm * 100, 1),
        "diff": round((kf / nf - km / nm) * 100, 1),
        "ciLo": round(lo * 100, 1), "ciHi": round(hi * 100, 1),
        "p": p,
    }


def compare_ordinal(f_vals, m_vals, top2_min=4, seed=RNG_SEED):
    """1-5 importance ratings. Returns means, top-2-box %, bootstrap CI, MWU p, Cliff's delta."""
    f = np.asarray(f_vals, dtype=float)
    m = np.asarray(m_vals, dtype=float)
    nf, nm = len(f), len(m)
    if nf < 5 or nm < 5:
        return None
    rng = np.random.default_rng(seed)
    bf = rng.choice(f, size=(N_BOOT, nf), replace=True).mean(axis=1)
    bm = rng.choice(m, size=(N_BOOT, nm), replace=True).mean(axis=1)
    d = bf - bm
    lo, hi = np.percentile(d, [2.5, 97.5])
    u, p = stats.mannwhitneyu(f, m, alternative="two-sided", method="asymptotic")
    delta = 2 * u / (nf * nm) - 1  # >0 means women tend to rate higher
    top_f = float((f >= top2_min).mean() * 100)
    top_m = float((m >= top2_min).mean() * 100)
    return {
        "nF": nf, "nM": nm,
        "meanF": round(float(f.mean()), 2), "meanM": round(float(m.mean()), 2),
        "diff": round(float(f.mean() - m.mean()), 2),
        "ciLo": round(float(lo), 2), "ciHi": round(float(hi), 2),
        "top2F": round(top_f, 1), "top2M": round(top_m, 1),
        "delta": round(float(delta), 2),
        "p": float(p),
    }


def apply_fdr(records, key="p"):
    """Attach q and a 'flag' (clear / suggestive / none) to every record in-place."""
    qs = bh_qvalues([r.get(key, float("nan")) if r else float("nan") for r in records])
    for r, q in zip(records, qs):
        if not r:
            continue
        r["q"] = None if (q is None or math.isnan(q)) else round(float(q), 4)
        r["flag"] = label_for(r.get(key), q)
        r["p"] = None if (r.get(key) is None or math.isnan(r[key])) else round(float(r[key]), 4)
    return records
