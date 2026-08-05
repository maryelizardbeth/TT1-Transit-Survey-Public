# HN Transit Survey — Public Dashboard

An interactive dashboard summarizing the **How Raleigh Moves: Walking, Biking &amp; Transit Survey**
for the City of Raleigh **TT1 Better Connections to Transit** strategic initiative team.

It is a static web app (HTML / CSS / vanilla JS + [Chart.js](https://www.chartjs.org/)) that mirrors the
design system of the [Housing Landscape dashboard](https://maryelizardbeth.github.io/HN-Housing-Landscape-Public/)
so the two read as siblings, and is structured to have ArcGIS Online layers added later (see below).

## Sections

1. **Overview &amp; Questions** — who responded, plus the single most important takeaway from each question.
2. **Why People Don't Ride** — the reasons, ratings, themes, and verbatim comments behind non-ridership.
3. **Women &amp; Ridership** — the survey's best-powered demographic comparison; where women and men differ.
4. **Key Evidence** — the strongest evidence mapped against the team's draft problem statement.

## Project structure

```
index.html            Markup: header, tab nav, four <section class="view"> panels
styles.css            Design system (Raleigh green / leaf / amber / teal / navy; Calibri stack)
app.js                Tab switching, KPI binding, Chart.js widgets, content injection
data.js               Auto-generated aggregate data (window.SURVEY). Do not edit by hand.
data_prep/
  generate_data.py    Re-builds data.js from the two survey exports
```

## Regenerating the data

`data.js` is produced from the two source exports. The source workbooks contain respondent
names, emails, phone numbers, and IP addresses and are **intentionally not part of this repo**.
`data.js` holds only aggregate statistics and a small set of upvoted, opinion-only verbatim
comments (screened for personal identifiers).

```bash
cd data_prep
python generate_data.py    # writes ../data.js
```

Update the two paths at the top of `generate_data.py` if the source files move.

## Run locally

No build step. Serve the folder with any static server:

```bash
python -m http.server 8000
```

Then open <http://localhost:8000>. (Opening `index.html` directly via `file://` also works, but a
server is closer to how GitHub Pages behaves.)

## Deploy to GitHub Pages

1. Create a new **public** repository named `HN-Transit-Survey-Public` on GitHub.
2. Push this folder to it (see the steps your assistant provided, or the standard `git remote add` /
   `git push` flow).
3. In the repo, go to **Settings → Pages**, set **Source** to `Deploy from a branch`, branch
   `main`, folder `/ (root)`, and save.
4. The site publishes at `https://<your-user>.github.io/HN-Transit-Survey-Public/`.

## ArcGIS Online compatibility

This app is a self-contained static site, so it can be **front-doored on ArcGIS Online** by
registering it as a *Web Mapping Application* item (or embedded via an iframe / Experience Builder).
To add live layers later:

- Include the ArcGIS Maps SDK for JavaScript the same way the Housing Landscape app does
  (`https://js.arcgis.com/5.1/` + the matching `esri/themes/light/main.css`).
- Add a map container alongside the charts and load feature layers by **service name** so the
  references survive a re-publish, consistent with the sibling app's convention.
- The map-pin question (weekly origins/destinations) is a natural first layer; its coordinates were
  exported separately as CSV / GeoJSON during analysis.

## Notes on the data

- Percentages are calculated among respondents who **answered each question**.
- "Non-riders" = residents who never ride **plus** those who stopped within the past six months.
- Demographic breakdowns come from an optional, self-selected subset (roughly a quarter to a third of
  respondents, skewing white, higher-income, and highly educated) and are **directional**.
- Verbatim comments are shown as submitted, with personal identifiers omitted.

This dashboard is a working prototype, not an official public record.
