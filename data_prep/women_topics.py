"""
Women-vs-men focus areas: traveling with children, light / safety / security,
and shade / heat / the walk to the stop.

Quantifies each topic from the comments (share of commenters raising it, overall and
question by question) and ties it back to the survey ratings. Aggregate-only output.

Two separate multiple-comparison families (Benjamini-Hochberg, per segment):
  A. the topic themes, compared across people (one count per person)
  B. the question-by-question rows (exploratory; each person writes at most one
     comment per question, so comments and people coincide)
"""
import numpy as np
import pandas as pd
from scipy import stats

import comment_themes as ct
import women_stats as ws
import women_text as wt
import women_analysis as wa

MIN_Q = 30          # comments per gender needed to report a question row
MIN_HITS = 4        # combined mentions needed to report a question row

TOPIC_THEMES = {
    "kids": ("Traveling with children", wt.THEMES["Traveling with children"]),
    "lighting": ("Lighting & the dark", wt.THEMES["Lighting & the dark"]),
    "security": ("Personal security & harassment", wt.THEMES["Personal security & harassment"]),
    "safety": ("Safety wording (any kind)", r"\bsafe|unsafe|safety|danger|scary|threat|crime|harass"),
    "heat": ("Heat & shade", wt.THEMES["Heat & shade"]),
    "weather": ("Weather (rain, cold, flooding)", wt.THEMES["Weather (rain, cold, flooding)"]),
    "walk": ("Distance & the walk to the stop",
             r"too far|distance|far from|closer|within (?:a )?(?:short )?walk|10.?minute walk|walking distance|long walk"),
    "sidewalks": ("Sidewalks & pedestrian access", wt.THEMES["Sidewalks & pedestrian access"]),
    "amenities": ("Bus stop amenities", wt.THEMES["Bus stop amenities"]),
}
QUESTION_THEMES = ["kids", "lighting", "security", "safety", "heat", "walk"]

# survey rating to compare against comment mentions: theme -> (Q2 column index, label)
VALIDATION = {"lighting": (24, "Lighting at stops"), "heat": (23, "Shelters at stops")}

AGE_35_44 = "35 - 44"

FIELDS = ("nF", "nM", "kF", "kM", "pctF", "pctM", "diff", "ciLo", "ciHi", "p", "q", "flag")


def _slim(r, **extra):
    out = {k: r[k] for k in FIELDS if k in r}
    out.update(extra)
    return out


def _seg_frame(c, seg):
    return c if seg == "all" else c[c.seg == seg]


def _themes(sub):
    ppl = wt._person_level(sub)
    f, m = ppl[ppl.gender == "Female"], ppl[ppl.gender == "Male"]
    rows = []
    for key, (name, pat) in TOPIC_THEMES.items():
        r = ws.compare_binary(f.txt.str.contains(pat, case=False, regex=True).values,
                              m.txt.str.contains(pat, case=False, regex=True).values)
        r["key"], r["name"] = key, name
        rows.append(r)
    ws.apply_fdr(rows)
    return [_slim(r, key=r["key"], name=r["name"]) for r in rows], ppl


def _by_question(sub):
    rows = []
    for qid in ct.ORDER:
        if qid == wt.SPATIAL_QID:
            continue
        s = sub[sub.QuestionId == qid]
        f, m = s[s.gender == "Female"].Comment, s[s.gender == "Male"].Comment
        if len(f) < MIN_Q or len(m) < MIN_Q:
            continue
        for key in QUESTION_THEMES:
            pat = TOPIC_THEMES[key][1]
            ff = f.str.contains(pat, case=False, regex=True).values
            mm = m.str.contains(pat, case=False, regex=True).values
            if ff.sum() + mm.sum() < MIN_HITS:
                continue
            r = ws.compare_binary(ff, mm)
            r.update({"key": key, "qid": qid, "question": ct.QLABEL[qid]})
            rows.append(r)
    ws.apply_fdr(rows)
    return [_slim(r, key=r["key"], qid=r["qid"], question=r["question"]) for r in rows]


def _validation(ppl, ratings):
    """Do people who raise a theme in comments also rate the matching survey item higher?"""
    out = []
    for key, (col_idx, label) in VALIDATION.items():
        pat = TOPIC_THEMES[key][1]
        flag = ppl.txt.str.contains(pat, case=False, regex=True)
        for g, gname in (("Female", "Women"), ("Male", "Men")):
            ids = ppl.index[ppl.gender == g]
            rt = ratings[col_idx].reindex(ids)
            ok = rt.notna()
            yes = rt[ok & flag[ids]]
            no = rt[ok & ~flag[ids]]
            if len(yes) < 8 or len(no) < 8:
                continue
            p = stats.mannwhitneyu(yes, no, alternative="two-sided", method="asymptotic").pvalue
            out.append({"key": key, "rating": label, "group": gname, "nYes": int(len(yes)), "nNo": int(len(no)),
                        "meanYes": round(float(yes.mean()), 2), "meanNo": round(float(no.mean()), 2),
                        "p": round(float(p), 4)})
    return out


def _kids(ppl, df, cols, gcol, seg):
    """Descriptive profile of who raises children; ages from the survey's demographic question."""
    pat = TOPIC_THEMES["kids"][1]
    flag = ppl.txt.str.contains(pat, case=False, regex=True)
    wf = ppl.index[(ppl.gender == "Female") & flag]
    wm = ppl.index[(ppl.gender == "Male") & flag]
    d = df.drop_duplicates("UserId").set_index("UserId")
    rs = d[cols[15]].map({"Daily": "riders", "Weekly": "riders", "Occasionally": "riders",
                          "I do not use the bus": "nonriders",
                          "I used to take the bus, but I have not in the past 6 months": "nonriders"})
    rec = {"nWomen": int(len(wf)), "nMen": int(len(wm)),
           "womenRiders": int((rs.reindex(wf) == "riders").sum()), "womenNonriders": int((rs.reindex(wf) == "nonriders").sum())}
    # age: women raising children vs all other women respondents in this segment
    women = d[d[gcol] == "Female"]
    if seg != "all":
        women = women[rs.reindex(women.index) == seg]
    age = women[cols[57]].dropna()
    in_grp = age.index.isin(wf)
    if in_grp.sum() >= 5:
        k = int((age[in_grp] == AGE_35_44).sum())
        k_all = int((age == AGE_35_44).sum())
        n_all = int(len(age))
        rest_k, rest_n = k_all - k, n_all - int(in_grp.sum())
        p = stats.fisher_exact([[k, int(in_grp.sum()) - k], [rest_k, rest_n - rest_k]])[1] if rest_n > 0 else None
        rec.update({"ageKnown": int(in_grp.sum()), "age3544": k,
                    "womenAge3544Pct": round(k_all / n_all * 100, 1),
                    "pAge": None if p is None else round(float(p), 4)})
    return rec


def topics(df, cols, gcol, cdf):
    c = wt.frame(df, cols, gcol, cdf)
    d = df.drop_duplicates("UserId").set_index("UserId")
    ratings = {i: d[cols[i]].apply(wa._first_rating) for i in (23, 24)}
    out = {}
    for seg in ("all", "riders", "nonriders"):
        sub = _seg_frame(c, seg)
        themes, ppl = _themes(sub)
        out[seg] = {
            "themes": themes,
            "byQuestion": _by_question(sub),
            "validation": _validation(ppl, ratings),
            "kids": _kids(ppl, df, cols, gcol, seg),
        }
    return out
