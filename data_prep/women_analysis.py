"""
Women-vs-men deep dive: structured survey answers (Data export).

Builds, for three segments (all respondents, current riders, non-riders), a
women-vs-men comparison of every closed-ended question. Output is aggregate-only.

Called from generate_data.py:   women_analysis.structured(df, cols)
"""
import re
import warnings
import numpy as np
import pandas as pd

import women_stats as ws

warnings.filterwarnings("ignore")

MIN_N = 10  # minimum respondents per gender for a binary comparison to be reported

Q2_SHORT = {
    "More routes to new places": "More routes to new places",
    "More frequent service on existing routes": "More frequent service",
    "More reliable services": "More reliable service",
    "Improved trip planning applications": "Better trip-planning apps",
    "Improved fare payment options": "Better fare payment options",
    "Better bus stop amenities - shelters": "Shelters at stops",
    "Better bus stop amenities - lighting at bus stops": "Lighting at stops",
    "Better bus stop amenities - benches": "Benches at stops",
    "Better bus stop amenities - bike racks": "Bike racks at stops",
    "Additional park-and-ride facilities": "Park-and-ride facilities",
}
SCALE = {"not important": 1, "slightly important": 2, "neutral": 3, "important": 4, "very important": 5}


def _first_rating(v):
    """Matches the dashboard's existing convention: first selected value."""
    if pd.isna(v):
        return np.nan
    return SCALE.get(str(v).split(";")[0].strip().lower(), np.nan)


def _mean_rating(v):
    """Sensitivity variant: mean of every value selected."""
    if pd.isna(v):
        return np.nan
    vals = [SCALE.get(p.strip().lower()) for p in str(v).split(";")]
    vals = [x for x in vals if x is not None]
    return float(np.mean(vals)) if vals else np.nan


def _multi_flag(series, option, drop=("Does not apply",)):
    """Boolean per respondent for a ';' multi-select; NaN where the question wasn't answered
    substantively."""
    out = pd.Series(np.nan, index=series.index, dtype="object")
    for idx, v in series.items():
        if pd.isna(v):
            continue
        parts = [p.strip() for p in str(v).split(";")]
        parts = [p for p in parts if p]
        if not parts or all(p in drop for p in parts):
            continue
        out[idx] = option in parts
    return out


def _rank_top(series, item):
    """True if the respondent ranked `item` first, among those who ranked anything."""
    out = pd.Series(np.nan, index=series.index, dtype="object")
    for idx, v in series.items():
        if pd.isna(v):
            continue
        pairs = [p.strip() for p in str(v).split(";") if ":" in p]
        if not pairs:
            continue
        first = None
        for p in pairs:
            r, name = p.split(":", 1)
            if r.strip() == "1":
                first = name.strip()
        out[idx] = (first == item)
    return out


def build_items(df, cols):
    """Return list of item specs: dict(block, id, name, kind, y(Series over df.index), segs)."""
    items = []
    q1 = cols[15]

    def add(block, iid, name, kind, y, segs=("all", "riders", "nonriders")):
        items.append({"block": block, "id": iid, "name": name, "kind": kind, "y": y, "segs": segs})

    # ---- Q1 ridership ------------------------------------------------------
    q1v = df[q1]
    ans = q1v.notna()

    def flag(cond):
        return cond.where(ans).astype(object).where(ans)

    add("q1", "q1_rider", "Currently rides the bus (any frequency)", "binary", flag(q1v.isin(["Daily", "Weekly", "Occasionally"])), ("all",))
    add("q1", "q1_daily", "Rides daily", "binary", flag(q1v == "Daily"), ("all", "riders"))
    add("q1", "q1_weekly", "Rides weekly", "binary", flag(q1v == "Weekly"), ("all", "riders"))
    add("q1", "q1_occ", "Rides occasionally", "binary", flag(q1v == "Occasionally"), ("all", "riders"))
    add("q1", "q1_lapsed", "Used to ride, not in the past 6 months", "binary",
        flag(q1v == "I used to take the bus, but I have not in the past 6 months"), ("all", "nonriders"))
    add("q1", "q1_never", "Does not use the bus", "binary", flag(q1v == "I do not use the bus"), ("all", "nonriders"))

    # ---- Q1a reasons for stopping -----------------------------------------
    reasons = [("Schedule or frequency no longer works for me", "Schedule or frequency no longer works"),
               ("Safety concnerns", "Safety concerns"),
               ("My travel needs changed", "My travel needs changed"),
               ("Gained access to a car or other travel option", "Gained access to a car or other option"),
               ("The switch from free to fare-based service", "Switch from free to fare-based service")]
    for raw, nice in reasons:
        add("q1a", "q1a_" + re.sub(r"\W+", "_", nice.lower())[:24], nice, "binary", _multi_flag(df[cols[16]], raw),
            ("all", "nonriders"))

    # ---- Q2 importance ------------------------------------------------------
    for c in cols[18:29]:
        short = c.split(": ")[-1].split(" [#")[0]
        short = Q2_SHORT.get(short, short)
        if short.startswith("Better sidewalks"):
            short = "Safe sidewalks & crossings to reach stops"
        add("q2", "q2_" + re.sub(r"\W+", "_", short.lower())[:24], short, "ordinal", df[c].apply(_first_rating))

    # ---- Q3 fare ---------------------------------------------------------------
    know = [("Yes, I know how to pay the fare", "Knows how to pay"),
            ("No, but I've ridden other bus systems and assume it is similar", "Doesn't know, assumes it's like other systems"),
            ("No, and I would like to learn how to pay", "Doesn't know, would like to learn"),
            ("No, and I am not currently interested in learning how to pay", "Doesn't know, not interested in learning")]
    kv = df[cols[29]]
    for raw, nice in know:
        add("q3", "q3_" + re.sub(r"\W+", "_", nice.lower())[:24], nice, "binary", (kv == raw).where(kv.notna()).astype(object).where(kv.notna()))
    pay = [("The Umo app", "Pays with the Umo app"), ("A physical GoRaleigh card", "Pays with a GoRaleigh card"), ("Cash", "Pays with cash")]
    for raw, nice in pay:
        add("q3a", "q3a_" + re.sub(r"\W+", "_", nice.lower())[:24], nice, "binary", _multi_flag(df[cols[30]], raw))

    # ---- Q4 stop within a 10 minute walk ------------------------------------
    sv = df[cols[32]]
    for raw, nice in [("Yes", "Has a stop within a 10-minute walk"), ("No", "No stop within a 10-minute walk"), ("Not sure", "Not sure whether a stop is within a 10-minute walk")]:
        add("q4", "q4_" + raw.lower().replace(" ", ""), nice, "binary", (sv == raw).where(sv.notna()).astype(object).where(sv.notna()))

    # ---- Walking / biking ----------------------------------------------------
    cross = ["Whether drivers yield", "Number of safe opportunities to cross", "Enough time to cross",
             "Visibility/awareness of what others are doing", "How predictable the signals or traffic patterns feel",
             "Feeling rushed or stressed"]
    for it in cross:
        add("wb4", "wb4_" + re.sub(r"\W+", "_", it.lower())[:20], "Ranks first: " + it.lower() if it != "Whether drivers yield" else "Ranks first: whether drivers yield",
            "binary", _rank_top(df[cols[44]], it))
    wf = [("Better information in certain areas (example: greenway exits, intersections)", "Better information in key places"),
          ("More consistent visual cues or markings", "More consistent visual cues or markings"),
          ("Understanding rules/expectations fo all road users", "Understanding rules for all road users"),
          ("Clearer signs or maps", "Clearer signs or maps"),
          ("Digital or app-based wayfinding tools", "Digital or app-based wayfinding")]
    for raw, nice in wf:
        add("wb8", "wb8_" + re.sub(r"\W+", "_", nice.lower())[:22], nice, "binary", _multi_flag(df[cols[48]], raw))
    ev = df[cols[51]]
    users = ev.notna() & (ev != "I don't use transit")
    add("wb10", "wb10_easy", "Finds the walk/bike to the stop easy", "binary",
        ev.isin(["Very easy", "Somewhat easy"]).where(users).astype(object).where(users))
    add("wb10", "wb10_hard", "Finds the walk/bike to the stop difficult", "binary",
        ev.isin(["Very Difficult", "Somewhat difficult"]).where(users).astype(object).where(users))
    dv = df[cols[53]]
    dans = dv.isin(["Yes", "No"])
    add("wb12", "wb12_dis", "Disability, mobility or sensory needs affect walking/biking", "binary",
        (dv == "Yes").where(dans).astype(object).where(dans))
    wa = [("A more pleasant environment (shade, trees, art, noise level, etc.)", "A more pleasant environment (shade, trees, art)"),
          ("Better understanding among all road users", "Better understanding among road users"),
          ("More welcoming or social spaces", "More welcoming or social spaces"),
          ("Feeling calmer or less rushed", "Feeling calmer or less rushed")]
    for raw, nice in wa:
        add("wb13", "wb13_" + re.sub(r"\W+", "_", nice.lower())[:22], nice, "binary", _multi_flag(df[cols[55]], raw))
    return items


BLOCKS = [
    ("q1", "How often do you ride?", "Q1"),
    ("q1a", "Why people stopped riding", "Q1a"),
    ("q2", "Importance of improvements (1–5)", "Q2"),
    ("q3", "Knowing how to pay the fare", "Q3"),
    ("q3a", "How riders pay", "Q3a"),
    ("q4", "Bus stop within a 10-minute walk", "Q4"),
    ("wb4", "What matters most when crossing streets", "Walk/bike Q4"),
    ("wb8", "What would make getting around easier to figure out", "Walk/bike Q8"),
    ("wb10", "Walking or biking to the stop", "Walk/bike Q10"),
    ("wb12", "Disability, mobility or sensory needs", "Walk/bike Q12"),
    ("wb13", "What would make walking or biking more appealing", "Walk/bike Q13"),
]


def _adjusted_p(y, kind, df_fm, gcol):
    """p-value for the gender term after adjusting for rider status and age band."""
    import statsmodels.api as sm
    d = pd.DataFrame({
        "y": pd.to_numeric(y, errors="coerce"),
        "female": (df_fm[gcol] == "Female").astype(float),
        "rs": df_fm["rider_status"].fillna("unknown"),
        "age": df_fm["age_band"].fillna("unknown"),
    }).dropna(subset=["y"])
    if d["y"].nunique() < 2:
        return None
    X = pd.get_dummies(d[["rs", "age"]], drop_first=True).astype(float)
    X.insert(0, "female", d["female"])
    X = sm.add_constant(X)
    try:
        if kind == "ordinal":
            res = sm.OLS(d["y"], X).fit(cov_type="HC3")
        else:
            res = sm.Logit(d["y"], X).fit(disp=0, maxiter=200)
            if not res.mle_retvals.get("converged", False):
                return None
        return float(res.pvalues["female"]), float(res.params["female"])
    except Exception:
        return None


def structured(df, cols, gcol):
    """df must already carry 'rider_status'. Returns the per-segment comparison dict."""
    df = df.copy()
    age_col = cols[57]
    age_map = {"15 - 24": "Under 35", "25 - 34": "Under 35", "35 - 44": "35-54", "45 - 54": "35-54",
               "55 - 64": "55+", "Over 65": "55+"}
    df["age_band"] = df[age_col].map(age_map)
    fm = df[df[gcol].isin(["Female", "Male"])].copy()
    is_f = fm[gcol] == "Female"
    segs = {
        "all": fm.index == fm.index,
        "riders": (fm["rider_status"] == "Rider").values,
        "nonriders": fm["rider_status"].isin(["Non-rider (never)", "Non-rider (lapsed)"]).values,
    }
    items = build_items(fm, cols)
    out = {}
    for seg, mask in segs.items():
        sub_idx = fm.index[mask]
        nF = int(is_f[mask].sum())
        nM = int((~is_f[mask]).sum())
        recs = []
        for it in items:
            if seg not in it["segs"]:
                continue
            y = it["y"].loc[sub_idx]
            f = y[is_f.loc[sub_idx]].dropna()
            m = y[~is_f.loc[sub_idx]].dropna()
            if it["kind"] == "ordinal":
                r = ws.compare_ordinal(f.astype(float).values, m.astype(float).values)
            else:
                if len(f) < MIN_N or len(m) < MIN_N:
                    r = None
                else:
                    r = ws.compare_binary(f.astype(bool).values, m.astype(bool).values)
            if r is None:
                continue
            r.update({"block": it["block"], "id": it["id"], "name": it["name"], "kind": it["kind"]})
            if seg == "all":
                adj = _adjusted_p(it["y"], it["kind"], fm, gcol)
                if adj:
                    r["adjP"] = round(adj[0], 4)
                    r["adjSign"] = 1 if adj[1] > 0 else -1
            recs.append(r)
        ws.apply_fdr(recs)
        out[seg] = {"nF": nF, "nM": nM, "items": recs}
    return out


def composition(df, cols, gcol):
    """How the women and men who answered differ on background characteristics, per segment."""
    fm = df[df[gcol].isin(["Female", "Male"])].copy()
    is_f = fm[gcol] == "Female"
    inc_map = {"Less than $10,000": "<$50k", "    $10,000 to $14,999": "<$50k", "$15,000 to $24,999": "<$50k",
               "$25,000 to $34,999": "<$50k", "$35,000 to $49,999": "<$50k", "$50,000 to $74,999": "$50-99k",
               "$75,000 to $99,999": "$50-99k", "$100,000 to $149,999": "$100k+", "$150,000 to $199,999": "$100k+",
               "$200,000 or more": "$100k+"}
    age = fm[cols[57]].map({"15 - 24": "Under 35", "25 - 34": "Under 35", "35 - 44": "35-54", "45 - 54": "35-54",
                            "55 - 64": "55+", "Over 65": "55+"})
    inc = fm[cols[62]].map(inc_map)
    ten = fm[cols[65]]
    edu = fm[cols[69]]
    emp = fm[cols[68]]
    race = fm[cols[58]]
    specs = []

    def flag(cond, base):
        return cond.where(base).astype(object).where(base)

    for lab, s in [("Age under 35", flag(age == "Under 35", age.notna())), ("Age 35–54", flag(age == "35-54", age.notna())),
                   ("Age 55 or older", flag(age == "55+", age.notna())),
                   ("Household income under $50k", flag(inc == "<$50k", inc.notna())),
                   ("Household income $50–99k", flag(inc == "$50-99k", inc.notna())),
                   ("Household income $100k or more", flag(inc == "$100k+", inc.notna())),
                   ("Rents their home", flag(ten == "Rent", ten.notna())), ("Owns their home", flag(ten == "Own", ten.notna())),
                   ("Bachelor's degree or higher", flag(edu.isin(["Bachelor's Degree", "Graduate or Professional Degree"]), edu.notna())),
                   ("Employed full-time", flag(emp.fillna("").str.contains("Employed full-time"), emp.notna())),
                   ("Identifies as White", flag(race.fillna("").str.contains("White"), race.notna())),
                   ("Identifies as a person with a disability", flag(fm[cols[60]] == "Yes", fm[cols[60]].notna()))]:
        specs.append((lab, s))
    segs = {"all": np.ones(len(fm), bool), "riders": (fm["rider_status"] == "Rider").values,
            "nonriders": fm["rider_status"].isin(["Non-rider (never)", "Non-rider (lapsed)"]).values}
    out = {}
    for seg, mask in segs.items():
        recs = []
        for lab, s in specs:
            sub = s[mask]
            f = sub[is_f[mask]].dropna()
            m = sub[~is_f[mask]].dropna()
            if len(f) < MIN_N or len(m) < MIN_N:
                continue
            r = ws.compare_binary(f.astype(bool).values, m.astype(bool).values)
            r["name"] = lab
            recs.append(r)
        ws.apply_fdr(recs)
        out[seg] = recs
    return out


def rating_style(df, cols, gcol):
    """Do women simply rate every improvement higher? Compares each person's average rating
    across the 11 Q2 items, and re-tests each item after centering on that person's own
    average (relative priority), by segment."""
    fm = df[df[gcol].isin(["Female", "Male"])].copy()
    is_f = fm[gcol] == "Female"
    q2c = cols[18:29]
    M = pd.DataFrame({c: fm[c].apply(_first_rating) for c in q2c})
    answered = M.notna().sum(axis=1)
    keep = answered >= 8  # need most items answered for a stable personal baseline
    avg = M.mean(axis=1)
    segs = {"all": np.ones(len(fm), bool), "riders": (fm["rider_status"] == "Rider").values,
            "nonriders": fm["rider_status"].isin(["Non-rider (never)", "Non-rider (lapsed)"]).values}
    out = {}
    for seg, mask in segs.items():
        k = keep.values & mask
        f_avg = avg[k & is_f.values].dropna().values
        m_avg = avg[k & ~is_f.values].dropna().values
        overall = ws.compare_ordinal(f_avg, m_avg, top2_min=4)
        cen = M.sub(avg, axis=0)
        recs = []
        for c in q2c:
            short = c.split(": ")[-1].split(" [#")[0]
            short = Q2_SHORT.get(short, short)
            if short.startswith("Better sidewalks"):
                short = "Safe sidewalks & crossings to reach stops"
            f = cen.loc[k & is_f.values, c].dropna().values
            m = cen.loc[k & ~is_f.values, c].dropna().values
            r = ws.compare_ordinal(f, m, top2_min=0.5)
            if r:
                r["name"] = short
                recs.append(r)
        ws.apply_fdr(recs)
        out[seg] = {"overall": {k2: overall[k2] for k2 in ("nF", "nM", "meanF", "meanM", "diff", "ciLo", "ciHi", "p")} if overall else None,
                    "centered": [{k2: r[k2] for k2 in ("name", "nF", "nM", "meanF", "meanM", "diff", "ciLo", "ciHi", "p", "q", "flag")} for r in recs]}
    return out


def sensitivity_multi_select(df, cols, gcol):
    """Check that the 'first selected value' rule for Q2 does not change the story:
    compares per-item mean differences using mean-of-selected values instead."""
    fm = df[df[gcol].isin(["Female", "Male"])].copy()
    is_f = fm[gcol] == "Female"
    rows = []
    for c in cols[18:29]:
        a = fm[c].apply(_first_rating)
        b = fm[c].apply(_mean_rating)
        rows.append((c.split(": ")[-1][:40], round(a[is_f].mean() - a[~is_f].mean(), 2), round(b[is_f].mean() - b[~is_f].mean(), 2)))
    return rows
