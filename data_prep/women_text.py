"""
Women-vs-men deep dive: open-text comments (Comments export joined to the Data
export on UserId, which is how the comments inherit gender and rider status).

Unit of analysis is the RESPONDENT, not the comment: a theme counts once per
person who raised it anywhere in the comment set being examined. That stops a few
prolific commenters from driving results. Output is aggregate-only; the only
verbatim text that leaves this module is an explicit, hand-reviewed allowlist
(see CURATED_QUOTES). The survey's "Private" flag only meant a comment was hidden
from other participants while the survey was open; the survey is closed, so all
comments are treated as public. Quotes are still screened for identifying details.
"""
import re

import numpy as np
import pandas as pd
from scipy import stats

import comment_themes as ct
import women_stats as ws

SPATIAL_QID = 396333                      # map-pin labels, not discussion
TRANSIT_QIDS = [396191, 396284, 396287, 396289, 396290, 396291, 396511]

# ---------------------------------------------------------------------------
# Theme dictionary for this analysis. Reuses the dashboard's shared definitions
# where they fit and tightens / adds the ones the gender question needs.
# Personal security is deliberately narrow (crime, harassment, threatening
# people) so it is NOT confused with traffic danger, which is its own theme.
# ---------------------------------------------------------------------------
THEMES = {
    "Sidewalks & pedestrian access": r"sidewalk|side walk|pedestrian|curb ?ramp|\bwalkab|on foot",
    "Crosswalks & intersections": ct.THEMES["Crossings & intersections"],
    "Biking & bike lanes": r"bike lane|protected bike|cycl|bikeway|greenway|bike infra|\bbikes?\b|biking|\bbicycl",
    "Heat, shade & weather": r"\bshade|\bheat\b|\bhot\b|summer|\bsun\b|\bsunny|\brain|weather|\btrees?\b|canop",
    "Bus stop amenities": ct.THEMES["Stop amenities (shelter/bench/shade)"],
    "Lighting & the dark": r"\blight(?:ing|s|ed)?\b|\bdark|unlit|well.?lit|after dark|at night",
    "Personal security & harassment": r"crime|criminal|harass|assault|creep|catcall|stalk|mugg|robb|stab|violen|homeless|loiter|sketchy|weirdo|drunk|intoxic|\bdrugs?\b|threatened|feel(?:ing)? (?:un)?safe(?:r)? (?:while|when|at|walking|waiting|on)|\balone\b|by myself",
    "Traffic danger & driver behavior": ct.THEMES["Driver behavior & enforcement"] + r"|run over|hit by|almost ran|not look|don.?t (?:see|look|stop)|attention",
    "Speed & traffic volume": r"\bspeed|fast cars|traffic|high.?speed|\bwide\b",
    "Caregiving: kids, strollers, carrying": r"\bkids?\b|child|children|daughter|\bson\b|stroller|toddler|baby|groceries|daycare|\bparents?\b|my family|school",
    "Confusing or rushed crossings": r"rushed|short (?:time|signal|light)|not enough time|confus|unclear|complicated|navigate|unsure",
    "Frequency & reliability": ct.THEMES["Frequency & reliability"],
    "Routes & coverage": ct.THEMES["Routes, coverage & transfers"],
    "Travel time": ct.THEMES["Travel time & directness"],
    "Fare & payment": ct.THEMES["Fare & payment"],
    "Apps, information & signage": r"\bapp\b|apps\b|information|signage|\bsigns?\b|wayfind|real.?time|\bumo\b",
    "Cost & affordability": ct.THEMES["Cost & affordability"],
    "Cleanliness & conditions": ct.THEMES["Cleanliness & conditions"],
    "Accessibility & mobility": ct.THEMES["Accessibility & mobility"],
}

def frame(df, cols, gcol, cdf):
    """Comments (excluding map-pin labels) joined to each author's gender and rider status."""
    q1 = cols[15]
    rs = df[q1].str.strip().map({
        "Daily": "riders", "Weekly": "riders", "Occasionally": "riders",
        "I do not use the bus": "nonriders",
        "I used to take the bus, but I have not in the past 6 months": "nonriders"})
    info = pd.DataFrame({"gender": df[gcol].values, "seg": rs.values}, index=df["UserId"].values)
    info = info[~info.index.duplicated()]
    c = cdf.join(info, on="UserId")
    c = c[(c["QuestionId"] != SPATIAL_QID) & c["Comment"].notna()].copy()
    c["Comment"] = c["Comment"].astype(str)
    c = c[c["Comment"].str.strip() != ""]
    return c[c["gender"].isin(["Female", "Male"])].copy()


def _person_level(sub):
    return sub.groupby("UserId").agg(gender=("gender", "first"), txt=("Comment", lambda s: " || ".join(s)))


def theme_table(sub):
    ppl = _person_level(sub)
    f = ppl[ppl.gender == "Female"]
    m = ppl[ppl.gender == "Male"]
    if len(f) < 10 or len(m) < 10:
        return None
    rows = []
    for name, pat in THEMES.items():
        ff = f.txt.str.contains(pat, case=False, regex=True).values
        mm = m.txt.str.contains(pat, case=False, regex=True).values
        r = ws.compare_binary(ff, mm)
        r["name"] = name
        rows.append(r)
    ws.apply_fdr(rows)
    rows.sort(key=lambda r: -r["diff"])
    return {"nF": len(f), "nM": len(m), "items": rows}


def themes_by_scope(c):
    scopes = {
        "all": c,
        "riders": c[c.seg == "riders"],
        "nonriders": c[c.seg == "nonriders"],
    }
    groups = {"any": None, "transit": TRANSIT_QIDS, "walkbike": "walkbike"}
    out = {}
    for sname, sub in scopes.items():
        out[sname] = {}
        for gname, q in groups.items():
            if q is None:
                s2 = sub
            elif q == "walkbike":
                s2 = sub[~sub.QuestionId.isin(TRANSIT_QIDS)]
            else:
                s2 = sub[sub.QuestionId.isin(q)]
            out[sname][gname] = theme_table(s2)
    return out


def engagement(c, df, gcol):
    """Participation and tone, at the respondent level."""
    out = {}
    for seg_name, mask in [("all", None), ("riders", "riders"), ("nonriders", "nonriders")]:
        sub = c if mask is None else c[c.seg == mask]
        rec = {}
        per = sub.groupby("UserId").agg(g=("gender", "first"), n=("Comment", "size"),
                                         words=("Comment", lambda s: s.str.split().str.len().mean()),
                                         sent=("SentimentScore", "mean"))
        for g in ["Female", "Male"]:
            p = per[per.g == g]
            rec[g.lower()] = {"commenters": int(len(p)), "commentsPerCommenter": round(float(p.n.mean()), 1),
                              "wordsPerComment": round(float(p.words.mean()), 1),
                              "meanSentiment": round(float(p.sent.mean()), 3)}
        f = per[per.g == "Female"]
        m = per[per.g == "Male"]
        rec["pSentiment"] = round(float(stats.mannwhitneyu(f.sent.dropna(), m.sent.dropna(), alternative="two-sided").pvalue), 4)
        rec["pComments"] = round(float(stats.mannwhitneyu(f.n, m.n, alternative="two-sided").pvalue), 4)
        rec["pWords"] = round(float(stats.mannwhitneyu(f.words.dropna(), m.words.dropna(), alternative="two-sided").pvalue), 4)
        out[seg_name] = rec
    # participation among all F/M survey respondents
    g_all = df[gcol].value_counts()
    for g in ["Female", "Male"]:
        out["all"][g.lower()]["respondents"] = int(g_all.get(g, 0))
    return out


# ---------------------------------------------------------------------------
# Verbatim quotes: ONLY comments from this hand-reviewed allowlist, and only if
# screened for identifying details. Filled in after reviewing candidates.
# ---------------------------------------------------------------------------
NR, RD = "Woman, non-rider", "Woman, current rider"
CURATED_QUOTES = {   # {panel title: [(CommentId, attribution), ...]}  -- all reviewed
    "Traveling with children": [(4464399, NR), (4470057, NR), (4468835, NR), (4468836, NR), (4479200, NR), (4462336, RD)],
    "Light, safety & feeling secure": [(4473679, NR), (4491387, NR), (4473823, NR), (4473446, RD), (4463721, NR), (4462208, NR), (4466281, NR)],
    "Shade, heat & the walk to the stop": [(4466300, NR), (4466307, NR), (4463714, RD), (4487235, NR)],
    "Not knowing how it works": [(4464889, NR), (4489032, NR)],
}


def candidates(cdf, gcol, df, cols, per_theme=6):
    """Women-authored, opinion-only candidates per theme, most-upvoted first
    (used to build the allowlist by hand; never published directly)."""
    c = frame(df, cols, gcol, cdf)
    c = c[c.gender == "Female"]
    c = c[c.Comment.str.len().between(40, 320)]
    pii = re.compile(r"@|\d{3}[-. ]\d{3,4}|\bmy (?:son|daughter|husband|wife|mom|dad)\b.*(?:mugged|hit|killed|attacked)", re.I)
    c = c[~c.Comment.str.contains(pii)]
    out = {}
    for name, pat in THEMES.items():
        s = c[c.Comment.str.contains(pat, case=False, regex=True)].sort_values(["Upvotes", "CommentId"], ascending=[False, True])
        out[name] = s.head(per_theme)[["CommentId", "Upvotes", "seg", "QuestionId", "Comment"]].values.tolist()
    return out


def quotes(cdf):
    """Resolve the curated allowlist to text."""
    by_id = cdf.set_index("CommentId")
    res = {}
    for theme, ids in CURATED_QUOTES.items():
        rows = []
        for cid, tag in ids:
            r = by_id.loc[cid]
            rows.append({"text": " ".join(str(r["Comment"]).split()), "upvotes": int(r["Upvotes"]), "who": tag})
        res[theme] = rows
    return res
