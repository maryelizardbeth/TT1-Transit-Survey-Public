"""
Shared comment-analysis logic for the transit survey dashboard and the Excel
findings workbook, so both tell the same story.

Approach: summarize EVERY comment on a question first (common themes over all
comments, public and private), then layer upvote-based endorsement on top.
Questions whose comments were all private still get a full thematic summary.
"""
import re

# One shared theme dictionary applied to every question's full comment set.
# Non-capturing groups (?:...) keep pandas from emitting match-group warnings.
THEMES = {
    "Sidewalks & gaps": r"sidewalk|side walk",
    "Bike lanes & greenways": r"bike lane|protected bike|cycl|bikeway|greenway|bike infra",
    "Driver behavior & enforcement": r"driver|speeding|\bspeed\b|yield|turn on red|distracted|aggressive|enforce|penalt|run(?:ning)? (?:the )?red|reckless",
    "Crossings & intersections": r"crosswalk|cross(?:ing)? the|intersection|signal|mid.?block|pedestrian signal|no turn on red|light timing",
    "Lighting": r"\blight(?:ing|s|ed)?\b|\bdark|unlit|well.?lit",
    "Personal safety & security": r"\bsafe|unsafe|crime|scary|threat|stab|harass|assault|creep|danger|homeless",
    "Cleanliness & conditions": r"clean|dirty|trash|smell|drug|needle|marijuana|urine|filth|conditions?",
    "Frequency & reliability": r"frequen|reliab|on.?time|\bwait\b|\blate\b|schedule|headway|come more",
    "Travel time & directness": r"too long|takes? too long|faster|time.?consuming|(?:4|four) times|\bdirect\b|quicker|hours to get",
    "Routes, coverage & transfers": r"\broute|coverage|connect|transfer|downtown|does.?n.?t go|more stops|express|no bus (?:to|near)|airport",
    "Fare & payment": r"tap.?to.?pay|\bumo\b|\bfare|payment|apple pay|\bdebit|credit card|\bcash\b|free fare",
    "Cars & driving": r"\bcar\b|\bcars\b|\bdrive|driving|convenien|\buber|\blyft",
    "Stop amenities (shelter/bench/shade)": r"shelter|bench|shade|\btree|canopy|seating|restroom|bathroom|awning",
    "Weather": r"weather|\brain|\bheat\b|\bhot\b|summer|\bsun\b|\bcold",
    "Cost & affordability": r"\bcost|afford|cheap|expensive|\bprice|\bfree\b",
    "Distance to stop": r"too far|distance|far from|closer|within (?:a )?(?:short )?walk|10.?minute walk|near my",
    "Accessibility & mobility": r"disab|wheelchair|mobility|\bada\b|\bramp|blind|\bdeaf|sensory|stroller|walker|\bcane\b",
    "Connectivity & infrastructure": r"connectivity|connected|infrastructure|network|\bgaps\b|separated|separation|complete street",
}

QLABEL = {
    396191: "1a. Reasons for stopping riding",
    396284: "3b. Improvements to the fare system",
    396287: "6. Circumstances more likely to ride",
    396289: "7. Change to ride one more day/week",
    396290: "8. First word or phrase about the bus",
    396291: "9. Versus bus systems elsewhere",
    396292: "Walk/bike 1. Crossing-street experience",
    396293: "Walk/bike 2. Easier/harder crossing spots",
    396294: "Walk/bike 3. Confusing intersections",
    396306: "Walk/bike 5. What feels comfortable",
    396506: "Walk/bike 6. What feels stressful",
    396307: "Walk/bike 7. Safety concerns changing routes",
    396310: "Walk/bike 8. What would make navigating easier",
    396507: "Walk/bike 9. Why not walk or bike",
    396511: "11. Improve walk/bike to transit stops",
    396516: "12a. Disability / mobility / sensory needs",
    396518: "Walk/bike 13. Make walking/biking more appealing",
    396333: "5. Map pins of weekly trips",
}

# Survey order used for display.
ORDER = [396284, 396287, 396289, 396290, 396291, 396191, 396292, 396293, 396294,
         396306, 396506, 396307, 396310, 396507, 396511, 396516, 396518, 396333]

# Questions whose "comments" are really map-pin location labels, not discussion.
SPATIAL = {396333}


def analyze(cdf, top_themes=6, top_quotes=3, examples=3):
    """Return {qid: analysis dict} summarizing every comment per question."""
    out = {}
    for qid in ORDER:
        sub = cdf[cdf["QuestionId"] == qid]
        comments = sub["Comment"].dropna().astype(str)
        comments = comments[comments.str.strip() != ""]
        n_all = int(len(comments))
        n_public = int((sub["Private"] == False).sum())
        n_private = int((sub["Private"] == True).sum())
        upvotes = int(sub["Upvotes"].sum())
        pub = sub[sub["Private"] == False]
        pct_upvoted = round(float((pub["Upvotes"] > 0).mean() * 100), 1) if len(pub) else None

        themes = []
        if n_all:
            for name, pat in THEMES.items():
                h = int(comments.str.contains(pat, case=False, regex=True).sum())
                if h:
                    themes.append({"name": name, "count": h, "pct": round(h / n_all * 100, 1)})
            themes.sort(key=lambda x: -x["count"])
        themes = themes[:top_themes]

        # Upvote layer: top endorsed public comments.
        quotes = []
        for _, r in pub.sort_values("Upvotes", ascending=False).head(top_quotes).iterrows():
            if r["Upvotes"] > 0 and str(r["Comment"]).strip():
                quotes.append({"upvotes": int(r["Upvotes"]), "text": str(r["Comment"]).strip()[:400]})

        # Representative examples (used when there is little/no upvote signal).
        ex = []
        for c in comments:
            t = " ".join(str(c).split())
            if 40 <= len(t) <= 240:
                ex.append({"text": t[:300]})
            if len(ex) >= examples:
                break

        out[qid] = {
            "id": qid, "label": QLABEL[qid],
            "nAll": n_all, "nPublic": n_public, "nPrivate": n_private,
            "upvotes": upvotes, "pctUpvoted": pct_upvoted,
            "spatial": qid in SPATIAL,
            "themes": themes, "topQuotes": quotes, "examples": ex,
        }
    return out
