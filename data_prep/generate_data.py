"""
Generate data.js for the TT1 Transit Survey dashboard.

Reads the two survey exports and writes ../data.js containing a single global
SURVEY object consumed by app.js. Re-run this whenever the source files change.

Usage (from data_prep/):
    python generate_data.py
"""
import pandas as pd
import json
import os

# ---------------------------------------------------------------------------
# Source files. Update these paths if the exports move.
# ---------------------------------------------------------------------------
DATA_PATH = r"C:\Users\smithmy\OneDrive - City Of Raleigh\TT1\How Raleigh Moves_ Walking, Biking and Transit Survey_Data.xlsx"
COMMENTS_PATH = r"C:\Users\smithmy\OneDrive - City Of Raleigh\TT1\How Raleigh Moves_ Walking, Biking and Transit Survey_Comments.xlsx"
OUT_PATH = os.path.join(os.path.dirname(__file__), "..", "data.js")

df = pd.read_excel(DATA_PATH, sheet_name="Response Data")
cdf = pd.read_excel(COMMENTS_PATH, sheet_name="Response Data")
cols = df.columns.tolist()

# ---------------------------------------------------------------------------
# Column references (verified indices)
# ---------------------------------------------------------------------------
q1 = cols[15]
# The Q1 export has a stray trailing space on "Daily " that breaks exact matching.
df[q1] = df[q1].str.strip()
q1a = cols[16]
q2_cols = cols[18:29]
q3_know = cols[29]
q3a_method = cols[30]
q4 = cols[32]
gender_col = cols[63]
income_col = cols[62]
disability_col = cols[60]
rentown_col = cols[65]
age_col = cols[57]

# ---------------------------------------------------------------------------
# Rider segmentation
# ---------------------------------------------------------------------------
df['rider_status'] = df[q1].map({
    'Daily': 'Rider', 'Weekly': 'Rider', 'Occasionally': 'Rider',
    'I do not use the bus': 'Non-rider (never)',
    'I used to take the bus, but I have not in the past 6 months': 'Non-rider (lapsed)'
})
nonrider_mask = df['rider_status'].isin(['Non-rider (never)', 'Non-rider (lapsed)'])
rider_mask = df['rider_status'] == 'Rider'
lapsed_mask = df['rider_status'] == 'Non-rider (lapsed)'
never_mask = df['rider_status'] == 'Non-rider (never)'

total = len(df)
q1_answered = df[q1].notna().sum()
n_never = int(never_mask.sum())
n_lapsed = int(lapsed_mask.sum())
n_nonrider = int(nonrider_mask.sum())
n_rider = int(rider_mask.sum())

q1_counts = df[q1].value_counts()
q1_order = ['I do not use the bus', 'I used to take the bus, but I have not in the past 6 months',
            'Occasionally', 'Weekly', 'Daily']
q1_labels_display = {
    'I do not use the bus': 'Do not use the bus',
    'I used to take the bus, but I have not in the past 6 months': 'Used to, not in past 6 months',
    'Occasionally': 'Occasionally', 'Weekly': 'Weekly', 'Daily': 'Daily'
}


def explode_reasons(series):
    e = series.dropna().str.split(';').explode().str.strip()
    e = e[~e.isin(['Does not apply'])]
    return e.value_counts()


reasons_nonriders = explode_reasons(df.loc[nonrider_mask, q1a])
reasons_lapsed = explode_reasons(df.loc[lapsed_mask, q1a])

# Fix the source typo "Safety concnerns" for display
reason_fix = {'Safety concnerns': 'Safety concerns'}


def reasons_to_obj(vc):
    labels = [reason_fix.get(k, k) for k in vc.index.tolist()]
    return {"labels": labels, "counts": [int(v) for v in vc.values.tolist()]}


# ---------------------------------------------------------------------------
# Q2 importance
# ---------------------------------------------------------------------------
scale = {"Not important": 1, "Slightly important": 2, "Neutral": 3, "Important": 4, "Very Important": 5}


def clean_single(val):
    if pd.isna(val):
        return None
    return scale.get(str(val).split(';')[0].strip(), None)


def importance_list(mask):
    out = []
    sub = df.loc[mask]
    for c in q2_cols:
        vals = sub[c].dropna().apply(lambda v: str(v).split(';')[0].strip())
        n = len(vals)
        pct = (vals.isin(['Important', 'Very Important'])).sum() / n * 100 if n else 0
        numeric = sub[c].apply(clean_single).dropna()
        short = c.split(': ')[-1].split(' [#')[0]
        out.append({"name": short, "n": int(n), "mean": round(float(numeric.mean()), 2),
                    "pctImportant": round(float(pct), 1)})
    out.sort(key=lambda x: x['mean'], reverse=True)
    return out


imp_nonriders = importance_list(nonrider_mask)
imp_riders = importance_list(rider_mask)

# ---------------------------------------------------------------------------
# Q3 fare knowledge
# ---------------------------------------------------------------------------
know_order = ['Yes, I know how to pay the fare',
              "No, but I've ridden other bus systems and assume it is similar",
              'No, and I would like to learn how to pay',
              'No, and I am not currently interested in learning how to pay']
know_display = {
    'Yes, I know how to pay the fare': 'Yes, I know how',
    "No, but I've ridden other bus systems and assume it is similar": 'No, but assume it is similar',
    'No, and I would like to learn how to pay': 'No, would like to learn',
    'No, and I am not currently interested in learning how to pay': 'No, not interested'
}


def know_obj(mask):
    vc = df.loc[mask, q3_know].value_counts()
    return {know_display[k]: int(vc.get(k, 0)) for k in know_order}


fare_know_nonriders = know_obj(nonrider_mask)
fare_know_riders = know_obj(rider_mask)


def explode_simple(series):
    return series.dropna().str.split(';').explode().str.strip().value_counts()


def payment_obj(mask):
    vc = explode_simple(df.loc[mask, q3a_method])
    vc = vc[~vc.index.isin(['Does not apply'])]
    return {"labels": vc.index.tolist(), "counts": [int(v) for v in vc.values.tolist()]}


payment_nonriders = payment_obj(nonrider_mask)
payment_riders = payment_obj(rider_mask)

# ---------------------------------------------------------------------------
# Q4 stop proximity
# ---------------------------------------------------------------------------
def q4_obj(mask):
    vc = df.loc[mask, q4].value_counts()
    return {"Yes": int(vc.get('Yes', 0)), "No": int(vc.get('No', 0)),
            "Not sure": int(vc.get('Not sure', 0))}


stop_nonriders = q4_obj(nonrider_mask)
stop_riders = q4_obj(rider_mask)

# ---------------------------------------------------------------------------
# Open-text themes (Q6-Q9), non-riders
# ---------------------------------------------------------------------------
text_idx = {37: 'Q6: Circumstances to ride', 38: 'Q7: Change for +1 day/week',
            39: 'Q8: First word or phrase', 40: 'Q9: Versus other systems'}
themes = {
    'Payment / app': r'tap.?to.?pay|umo|payment|pay the fare|pay fare|apple pay|debit card|credit card',
    'Safety / crime': r'safe|unsafe|crime|scary|threat|stab|harass|assault|creep',
    'Frequency / reliability': r'frequen|on.?time|reliab|late|\bwait\b',
    'Car dependence': r'\bcar\b|drive|driving|convenien',
    'Routes / coverage': r'route|coverage',
}
theme_rows = []
for idx, label in text_idx.items():
    c = cols[idx]
    series = df.loc[nonrider_mask, c].dropna().astype(str)
    n = len(series)
    row = {"question": label, "n": int(n)}
    for tname, pattern in themes.items():
        hits = series.str.contains(pattern, case=False, regex=True).sum()
        row[tname] = round(hits / n * 100, 1) if n else 0
    theme_rows.append(row)

# ---------------------------------------------------------------------------
# Demographic coverage
# ---------------------------------------------------------------------------
demo_idx = {'Age': 57, 'Race': 58, 'Disability': 60, 'Income': 62, 'Gender': 63,
            'Rent/own': 65, 'Employment': 68, 'Education': 69}
demo_coverage = [{"field": lbl, "n": int(df[cols[i]].notna().sum()),
                  "pct": round(df[cols[i]].notna().sum() / total * 100, 1)}
                 for lbl, i in demo_idx.items()]

# ---------------------------------------------------------------------------
# GENDER deep dive (best-powered demographic split)
# ---------------------------------------------------------------------------
fm = df[df[gender_col].isin(['Female', 'Male'])].copy()
n_female = int((fm[gender_col] == 'Female').sum())
n_male = int((fm[gender_col] == 'Male').sum())

gender_importance = []
for c in q2_cols:
    short = c.split(': ')[-1].split(' [#')[0]
    rowd = {"improvement": short}
    for g in ['Female', 'Male']:
        numeric = fm[fm[gender_col] == g][c].apply(clean_single).dropna()
        rowd[g.lower()] = round(float(numeric.mean()), 2)
    rowd["gap"] = round(rowd["female"] - rowd["male"], 2)
    gender_importance.append(rowd)
gender_importance.sort(key=lambda x: abs(x["gap"]), reverse=True)


def know_pct_by_gender(g):
    sub = fm[fm[gender_col] == g]
    vc = sub[q3_know].value_counts(normalize=True) * 100
    return {know_display[k]: round(float(vc.get(k, 0)), 1) for k in know_order}


gender_fare_know = {"female": know_pct_by_gender('Female'), "male": know_pct_by_gender('Male')}


def rider_status_by_gender(g):
    sub = fm[fm[gender_col] == g]
    vc = sub['rider_status'].value_counts(normalize=True) * 100
    return {
        "Rider": round(float(vc.get('Rider', 0)), 1),
        "Non-rider (lapsed)": round(float(vc.get('Non-rider (lapsed)', 0)), 1),
        "Non-rider (never)": round(float(vc.get('Non-rider (never)', 0)), 1),
    }


gender_rider_status = {"female": rider_status_by_gender('Female'), "male": rider_status_by_gender('Male')}

# Safety mentions in open text, by gender
q6, q7, q8, q9 = cols[37], cols[38], cols[39], cols[40]
fm_text = fm[[q6, q7, q8, q9, gender_col]].copy()
combined = fm_text[[q6, q7, q8, q9]].fillna('').astype(str).agg(' | '.join, axis=1)
fm_text = fm_text.assign(combined=combined)
fm_text = fm_text[fm_text['combined'].str.replace('|', '', regex=False).str.strip() != '']
safety_pat = r'safe|unsafe|crime|scary|threat|stab|harass|assault|creep'
fm_text['safety'] = fm_text['combined'].str.contains(safety_pat, case=False, regex=True)
gender_safety = {}
for g in ['Female', 'Male']:
    sub = fm_text[fm_text[gender_col] == g]
    gender_safety[g.lower()] = {"n": int(len(sub)),
                                "mentions": int(sub['safety'].sum()),
                                "pct": round(float(sub['safety'].mean() * 100), 1)}

# Reasons for stopping, by gender (% of substantive answers)
def reasons_pct_by_gender(g):
    sub = fm[fm[gender_col] == g]
    e = explode_reasons(sub[q1a])
    n_sub = sub[q1a].notna().sum() - (sub[q1a] == 'Does not apply').sum()
    return {reason_fix.get(k, k): round(float(v / n_sub * 100), 1) for k, v in e.items()} if n_sub else {}


gender_reasons = {"female": reasons_pct_by_gender('Female'), "male": reasons_pct_by_gender('Male'),
                  "n_female_answers": int(fm[fm[gender_col] == 'Female'][q1a].notna().sum() -
                                          (fm[fm[gender_col] == 'Female'][q1a] == 'Does not apply').sum()),
                  "n_male_answers": int(fm[fm[gender_col] == 'Male'][q1a].notna().sum() -
                                        (fm[fm[gender_col] == 'Male'][q1a] == 'Does not apply').sum())}

# ---------------------------------------------------------------------------
# Income: fare-switch reason by income bucket
# ---------------------------------------------------------------------------
income_bucket_map = {
    'Less than $10,000': 'Under $50k', '    $10,000 to $14,999': 'Under $50k', '$15,000 to $24,999': 'Under $50k',
    '$25,000 to $34,999': 'Under $50k', '$35,000 to $49,999': 'Under $50k',
    '$50,000 to $74,999': '$50k-$99k', '$75,000 to $99,999': '$50k-$99k',
    '$100,000 to $149,999': '$100k+', '$150,000 to $199,999': '$100k+', '$200,000 or more': '$100k+',
}
df['income_bucket'] = df[income_col].map(income_bucket_map)
sub_income = df.dropna(subset=['income_bucket'])
fare_switch_income = []
for bucket in ['Under $50k', '$50k-$99k', '$100k+']:
    g = sub_income[sub_income['income_bucket'] == bucket]
    pct = g[q1a].fillna('').str.contains('switch from free to fare', case=False, regex=False).mean() * 100
    fare_switch_income.append({"bucket": bucket, "n": int(len(g)), "pct": round(float(pct), 1)})

# Rent/own ever-ridden
def ever_ridden_pct(val):
    sub = df[df[rentown_col] == val]
    ever = sub['rider_status'].isin(['Rider', 'Non-rider (lapsed)']).mean() * 100
    return round(float(ever), 1), int(len(sub))


own_pct, own_n = ever_ridden_pct('Own')
rent_pct, rent_n = ever_ridden_pct('Rent')

# ---------------------------------------------------------------------------
# COMMENTS file
# ---------------------------------------------------------------------------
question_labels = {
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
    396310: "Walk/bike 8. Easier to figure out",
    396507: "Walk/bike 9. Why not walk or bike",
    396511: "11. Improve walk/bike to transit stops",
    396516: "12a. Disability / mobility / sensory needs",
    396518: "13. Make walking/biking more appealing",
    396333: "5. Map pins of weekly trips",
}
order = [396284, 396287, 396289, 396290, 396291, 396292, 396293, 396294, 396306,
         396506, 396507, 396511, 396516, 396191, 396307, 396310, 396518, 396333]

comment_summary = []
top_quotes = {}
for qid in order:
    sub = cdf[cdf['QuestionId'] == qid]
    pub = sub[sub['Private'] == False]
    n_public = int(len(pub))
    total_up = int(sub['Upvotes'].sum())
    pct_up = round(float((pub['Upvotes'] > 0).mean() * 100), 1) if n_public else None
    comment_summary.append({"id": qid, "label": question_labels[qid], "total": int(len(sub)),
                            "public": n_public, "upvotes": total_up, "pctUpvoted": pct_up})
    quotes = []
    for _, r in pub.sort_values('Upvotes', ascending=False).head(4).iterrows():
        if pd.notna(r['Comment']):
            quotes.append({"upvotes": int(r['Upvotes']), "text": str(r['Comment']).strip()[:400]})
    top_quotes[str(qid)] = quotes

comments_agg = {
    "totalComments": int(len(cdf)),
    "publicComments": int((cdf['Private'] == False).sum()),
    "privateComments": int((cdf['Private'] == True).sum()),
    "totalUpvotes": int(cdf['Upvotes'].sum()),
    "meanSentiment": round(float(cdf['SentimentScore'].mean()), 3),
    "profanity": int((cdf['ContainsProfanity'] == True).sum()),
    "tags": {c.replace('Tag_', ''): int((cdf[c] == True).sum()) for c in cdf.columns if c.startswith('Tag_')},
    "maxUpvote": int(cdf['Upvotes'].max()),
}

# ---------------------------------------------------------------------------
# Assemble
# ---------------------------------------------------------------------------
SURVEY = {
    "meta": {
        "total": int(total),
        "q1Answered": int(q1_answered),
        "nNever": n_never, "nLapsed": n_lapsed, "nNonrider": n_nonrider, "nRider": n_rider,
        "pctNonrider": round(n_nonrider / q1_answered * 100, 1),
        "pctNever": round(n_never / q1_answered * 100, 1),
        "pctRider": round(n_rider / q1_answered * 100, 1),
    },
    "q1": {"labels": [q1_labels_display[k] for k in q1_order],
           "counts": [int(q1_counts.get(k, 0)) for k in q1_order]},
    "reasons": {"nonriders": reasons_to_obj(reasons_nonriders),
                "lapsed": reasons_to_obj(reasons_lapsed)},
    "importance": {"nonriders": imp_nonriders, "riders": imp_riders},
    "fareKnowledge": {"nonriders": fare_know_nonriders, "riders": fare_know_riders},
    "payment": {"nonriders": payment_nonriders, "riders": payment_riders},
    "stopProximity": {"nonriders": stop_nonriders, "riders": stop_riders},
    "openThemes": theme_rows,
    "demoCoverage": demo_coverage,
    "gender": {
        "nFemale": n_female, "nMale": n_male,
        "importance": gender_importance,
        "fareKnowledge": gender_fare_know,
        "riderStatus": gender_rider_status,
        "safety": gender_safety,
        "reasons": gender_reasons,
    },
    "income": {"fareSwitch": fare_switch_income},
    "tenure": {"ownPct": own_pct, "ownN": own_n, "rentPct": rent_pct, "rentN": rent_n},
    "comments": {"summary": comment_summary, "topQuotes": top_quotes, "aggregate": comments_agg},
}

with open(OUT_PATH, "w", encoding="utf-8") as f:
    f.write("// Auto-generated by data_prep/generate_data.py -- do not edit by hand.\n")
    f.write("// Source: How Raleigh Moves Walking, Biking and Transit Survey (Data + Comments exports).\n")
    f.write("window.SURVEY = ")
    json.dump(SURVEY, f, indent=2, ensure_ascii=False)
    f.write(";\n")

print("Wrote", os.path.abspath(OUT_PATH))
print("Key figures:")
print("  Total responses:", total, "| Non-riders:", n_nonrider, f"({SURVEY['meta']['pctNonrider']}% of answered)")
print("  Women:", n_female, "| Men:", n_male)
print("  Comments:", comments_agg['totalComments'], "| Max upvote:", comments_agg['maxUpvote'])
