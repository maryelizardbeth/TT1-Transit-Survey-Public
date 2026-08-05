/* ==========================================================================
   TT1 Transit Survey Dashboard — app logic
   Reads window.SURVEY (data.js), renders Chart.js widgets, fills KPIs, and
   injects the per-question takeaways, quotes, and evidence blocks.
   ========================================================================== */
(function () {
  "use strict";
  var S = window.SURVEY;

  // ---- Brand palette (mirrors the Housing Landscape app) ------------------
  var C = {
    green: "#0D6937", leaf: "#73AB45", mid: "#4C8C40", chartreuse: "#A8C23E",
    teal: "#189ABC", navy: "#01426A", amber: "#FBAE40", rust: "#A8322D",
    border: "#BFBFBF", body: "#414042", tint: "#DAEFD3"
  };
  Chart.defaults.font.family = "Calibri, 'Segoe UI', Candara, 'Trebuchet MS', sans-serif";
  Chart.defaults.font.size = 12;
  Chart.defaults.color = C.body;

  var pct = function (n, d) { return d ? Math.round((n / d) * 1000) / 10 : 0; };
  var fmt = function (n) { return n.toLocaleString("en-US"); };

  // =========================================================================
  // Tab switching
  // =========================================================================
  var tabs = document.querySelectorAll(".tab-btn");
  var views = document.querySelectorAll(".view");
  var rendered = {};
  tabs.forEach(function (btn) {
    btn.addEventListener("click", function () {
      var v = btn.dataset.view;
      tabs.forEach(function (b) { b.classList.remove("active"); b.setAttribute("aria-selected", "false"); });
      btn.classList.add("active"); btn.setAttribute("aria-selected", "true");
      views.forEach(function (view) { view.classList.remove("active"); });
      document.getElementById("view-" + v).classList.add("active");
      window.scrollTo({ top: 0, behavior: "smooth" });
      if (!rendered[v]) { renderView(v); rendered[v] = true; }
    });
  });

  // =========================================================================
  // KPI + inline number binding
  // =========================================================================
  function setText(id, val) { var el = document.getElementById(id); if (el) el.textContent = val; }

  var m = S.meta;
  var nonriderKnowYes = S.fareKnowledge.nonriders["Yes, I know how"];
  var nonriderKnowTotal = Object.values(S.fareKnowledge.nonriders).reduce(function (a, b) { return a + b; }, 0);
  var pctKnow = pct(nonriderKnowYes, nonriderKnowTotal);
  var stopN = S.stopProximity.nonriders;
  var stopTotal = stopN.Yes + stopN.No + stopN["Not sure"];
  var pctNoStop = pct(stopN.No, stopTotal);

  // Overview
  setText("kf-total", fmt(m.total));
  setText("kf-comments", fmt(S.comments.aggregate.totalComments));
  setText("kpi-total", fmt(m.total));
  setText("kpi-nonrider", m.pctNonrider + "%");
  setText("kpi-nonrider-sub", fmt(m.nNonrider) + " people");
  setText("kpi-rider", fmt(m.nRider));
  setText("kpi-comments", fmt(S.comments.aggregate.totalComments));
  setText("kpi-upvotes", fmt(S.comments.aggregate.totalUpvotes));

  // Why not
  setText("wn-nonrider", fmt(m.nNonrider));
  setText("wn-kpi-pct", m.pctNonrider + "%");
  setText("wn-kpi-stop", pctNoStop + "%");
  setText("wn-kpi-know", pctKnow + "%");

  // Women
  var g = S.gender;
  var lightRow = g.importance.find(function (r) { return /lighting/i.test(r.improvement); });
  var learnF = g.fareKnowledge.female["No, would like to learn"];
  var learnM = g.fareKnowledge.male["No, would like to learn"];
  setText("wm-female", fmt(g.nFemale));
  setText("wm-male", fmt(g.nMale));
  setText("wm-kpi-female", fmt(g.nFemale));
  setText("wm-kpi-male", fmt(g.nMale));
  setText("wm-kpi-light", "+" + (lightRow ? lightRow.gap.toFixed(1) : "—"));
  setText("wm-kpi-learn", "≈" + (learnM ? (learnF / learnM).toFixed(1) : "—") + "×");

  // Evidence
  var reliableRow = S.importance.nonriders.find(function (r) { return /reliable/i.test(r.name); });
  var freqRow = S.importance.nonriders.find(function (r) { return /frequent/i.test(r.name); });
  var sidewalkRow = S.importance.nonriders.find(function (r) { return /sidewalk/i.test(r.name); });
  setText("ev-nonrider-pct", m.pctNonrider + "%");
  setText("ev-nonrider", fmt(m.nNonrider));
  setText("ev-never", fmt(m.nNever));
  setText("ev-lapsed", fmt(m.nLapsed));
  setText("ev-freq-theme", (freqRow ? freqRow.pctImportant : "—") + "%");
  setText("ev-reliable", (reliableRow ? reliableRow.pctImportant : "—") + "%");
  setText("ev-sidewalk", (sidewalkRow ? sidewalkRow.pctImportant : "—") + "%");
  setText("ev-nostop", pctNoStop + "%");

  // =========================================================================
  // Chart helpers
  // =========================================================================
  function hBar(id, labels, data, color, opts) {
    opts = opts || {};
    return new Chart(document.getElementById(id), {
      type: "bar",
      data: { labels: labels, datasets: [{ data: data, backgroundColor: color, borderRadius: 3, maxBarThickness: 34 }] },
      options: Object.assign({
        indexAxis: "y", responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false }, tooltip: { callbacks: opts.tip } },
        scales: {
          x: { beginAtZero: true, grid: { color: "#eee" }, ticks: { callback: opts.xfmt } },
          y: { grid: { display: false } }
        }
      }, opts.extra || {})
    });
  }

  // Compact chart builders used inside the per-question accordion.
  function smallHBar(canvas, labels, data, colors, o) {
    o = o || {};
    return new Chart(canvas, {
      type: "bar",
      data: { labels: labels, datasets: [{ data: data, backgroundColor: colors, borderRadius: 3, maxBarThickness: 26 }] },
      options: {
        indexAxis: "y", responsive: true, maintainAspectRatio: false, animation: false,
        plugins: { legend: { display: false }, tooltip: { callbacks: {
          title: o.titles ? function (items) { return o.titles[items[0].dataIndex]; } : undefined,
          label: o.tipLabel || function (c) { return c.parsed.x; } } } },
        scales: { x: { beginAtZero: true, grid: { color: "#eee" }, ticks: { callback: o.xfmt } },
          y: { grid: { display: false }, ticks: { font: { size: 11 } } } }
      }
    });
  }
  function smallDoughnut(canvas, labels, data, colors, o) {
    o = o || {};
    return new Chart(canvas, {
      type: "doughnut",
      data: { labels: labels, datasets: [{ data: data, backgroundColor: colors, borderWidth: 2, borderColor: "#fff" }] },
      options: {
        responsive: true, maintainAspectRatio: false, cutout: "55%", animation: false,
        plugins: { legend: { position: "right", labels: { boxWidth: 12, padding: 6, font: { size: 11 } } },
          tooltip: { callbacks: { label: o.tipLabel || function (c) { return c.label + ": " + fmt(c.parsed); } } } }
      }
    });
  }
  // Horizontal bar of a question's top upvoted comments (label = truncated text).
  function quoteBars(canvas, qid, color) {
    var qs = (S.comments.topQuotes[qid] || []).slice(0, 4);
    var full = qs.map(function (q) { return q.text; });
    var trunc = qs.map(function (q) { var t = q.text.replace(/\s+/g, " "); return t.length > 30 ? t.slice(0, 30) + "…" : t; });
    return smallHBar(canvas, trunc, qs.map(function (q) { return q.upvotes; }), color,
      { titles: full, tipLabel: function (c) { return c.parsed.x + " upvotes"; } });
  }

  // =========================================================================
  // Per-question takeaways (Section 1)
  // =========================================================================
  var themeNames = ["Payment / app", "Safety / crime", "Frequency / reliability", "Car dependence", "Routes / coverage"];

  var QUESTIONS = [
    { num: "Q1", tag: "survey", title: "How often do you ride the bus?",
      body: "About three in four respondents are non-riders: " + m.pctNever + "% never use the bus and another " +
        pct(m.nLapsed, m.q1Answered) + "% stopped within the last six months. Only " + m.pctRider +
        "% currently ride daily, weekly, or occasionally.",
      take: "The sample is overwhelmingly people the system is <strong>not</strong> currently reaching — exactly the audience for a &ldquo;why not&rdquo; study.",
      viz: function (cv) {
        smallHBar(cv, S.q1.labels, S.q1.counts, [C.rust, C.amber, C.chartreuse, C.leaf, C.green],
          { tipLabel: function (c) { return fmt(c.parsed.x) + " (" + pct(c.parsed.x, m.q1Answered) + "% of answered)"; } });
      } },
    { num: "Q1a", tag: "survey", title: "What made you stop or never start riding?",
      body: "Among non-riders, schedule/frequency and safety lead, followed closely by changed travel needs, gaining access to a car, and the return of fares. No single reason dominates.",
      take: "Non-ridership is <strong>multi-causal</strong>. Among people who stopped in just the last six months, the switch from free to paid fares jumps to the second-most-cited reason.",
      viz: function (cv) {
        smallHBar(cv, S.reasons.nonriders.labels, S.reasons.nonriders.counts, C.green,
          { tipLabel: function (c) { return fmt(c.parsed.x) + " selections"; } });
      } },
    { num: "Q2", tag: "survey", title: "Which improvements would make you more likely to ride?",
      body: "Ranked by importance, non-riders put <strong>sidewalks and safe crossings to reach the stop</strong> first (" +
        (sidewalkRow ? sidewalkRow.pctImportant : "—") + "% important), then lighting, reliability, shelters, and routes. Fare payment options rank 10th of 11.",
      take: "Getting to the stop safely and having reliable service beat every on-board or payment feature.",
      viz: function (cv) {
        var imp = S.importance.nonriders.slice(0, 6);
        smallHBar(cv, imp.map(function (x) { return x.name.replace("Better bus stop amenities - ", "").replace("Better ", ""); }),
          imp.map(function (x) { return x.pctImportant; }),
          imp.map(function (x) { return /sidewalk/i.test(x.name) ? C.green : C.leaf; }),
          { xfmt: function (v) { return v + "%"; }, tipLabel: function (c) { return c.parsed.x + "% important / very important"; } });
      } },
    { num: "Q3", tag: "survey", title: "Do you know how to pay the fare?",
      body: "Only " + pctKnow + "% of non-riders know how to pay, versus the large majority of current riders. A third simply assume it works like other cities' systems.",
      take: "A real <strong>knowledge and outreach gap</strong> — most non-riders have never learned how payment works.",
      viz: function (cv) {
        var k = S.fareKnowledge.nonriders;
        smallDoughnut(cv, Object.keys(k), Object.values(k), [C.green, C.teal, C.amber, C.rust],
          { tipLabel: function (c) { return c.label + ": " + fmt(c.parsed); } });
      } },
    { num: "Q3b", tag: "comments", title: "Improvements to the fare system",
      body: "This question drew the highest comment engagement of any question — about half of public comments earned an upvote. The repeated, specific ask is <strong>tap-to-pay</strong> (contactless card or phone) instead of the Umo app.",
      take: "Payment isn't a top reason people avoid the bus, but among those who comment it is the most concrete, high-agreement fix.",
      viz: function (cv) { quoteBars(cv, "396284", C.teal); } },
    { num: "Q4", tag: "survey", title: "Is there a stop within a 10-minute walk?",
      body: "Roughly " + pctNoStop + "% of non-riders who answered don't have a stop within a ten-minute walk (versus far fewer current riders).",
      take: "For a meaningful share of non-riders, the nearest stop is simply <strong>too far to reach on foot</strong>.",
      viz: function (cv) {
        var s = S.stopProximity.nonriders, tot = s.Yes + s.No + s["Not sure"];
        smallDoughnut(cv, ["Yes", "No", "Not sure"], [s.Yes, s.No, s["Not sure"]], [C.green, C.rust, C.amber],
          { tipLabel: function (c) { return c.label + ": " + fmt(c.parsed) + " (" + pct(c.parsed, tot) + "%)"; } });
      } },
    { num: "Q6–Q9", tag: "survey", title: "Open-ended: what would change your mind?",
      body: "In their own words, non-riders most raise car dependence, frequency/reliability, safety, and route coverage. Payment stays minor — until people compare GoRaleigh to another city's system, where tap-to-pay spikes to the second-most-mentioned theme.",
      take: "Unprompted priorities match the ratings: <strong>time, reliability, safety, and coverage</strong> lead.",
      viz: function (cv) {
        var avg = themeNames.map(function (t) {
          var vals = S.openThemes.map(function (r) { return r[t]; });
          return Math.round(vals.reduce(function (a, b) { return a + b; }, 0) / vals.length * 10) / 10;
        });
        smallHBar(cv, themeNames, avg, [C.amber, C.rust, C.teal, C.navy, C.mid],
          { xfmt: function (v) { return v + "%"; }, tipLabel: function (c) { return c.parsed.x + "% of comments (avg across Q6–Q9)"; } });
      } },
    { num: "WB1", tag: "comments", title: "Crossing streets while walking or biking",
      body: "The top-upvoted answers are &ldquo;drivers do not respect pedestrians&rdquo; (81 upvotes) and &ldquo;lack of sidewalks&rdquo; (61).",
      take: "Driver behavior and missing sidewalks are the dominant pedestrian-safety complaints citywide.",
      viz: function (cv) { quoteBars(cv, "396292", C.leaf); } },
    { num: "WB2", tag: "comments", title: "Where crossing feels hardest",
      body: "Residents named specific danger spots repeatedly: Atlantic Avenue at Whitaker Mill (Ironworks), Glenwood Avenue outside downtown, and New Bern Avenue.",
      take: "This is concrete, <strong>location-specific</strong> intelligence that can be routed straight to traffic engineering.",
      viz: function (cv) { quoteBars(cv, "396293", C.leaf); } },
    { num: "WB11", tag: "comments", title: "Improving the walk or bike to transit stops",
      body: "The single top answer is simply &ldquo;Sidewalks&rdquo; (48 upvotes), followed by greenway connections, lighting, and mid-block crossings.",
      take: "The question most directly tied to TT1's charter <strong>validates the sidewalk-and-lighting focus</strong> unprompted.",
      viz: function (cv) { quoteBars(cv, "396511", C.green); } },
    { num: "Demo", tag: "survey", title: "Who answered the demographic questions?",
      body: "Only about a quarter to a third of respondents answered the optional demographic items, and those who did skew white, higher-income, and highly educated.",
      take: "Read demographic breakdowns as <strong>directional</strong>. Gender has the largest usable samples and is explored on its own tab.",
      viz: function (cv) {
        smallHBar(cv, S.demoCoverage.map(function (d) { return d.field; }), S.demoCoverage.map(function (d) { return d.pct; }), C.navy,
          { xfmt: function (v) { return v + "%"; }, tipLabel: function (c) { return c.parsed.x + "% answered (n=" + fmt(S.demoCoverage[c.dataIndex].n) + ")"; } });
      } }
  ];

  function renderQuestions() {
    var host = document.getElementById("question-list");
    if (!host) return;
    host.innerHTML = QUESTIONS.map(function (q) {
      return '<details class="q-item"><summary>' +
        '<span class="q-num">' + q.num + '</span>' +
        '<span class="q-title">' + q.title + '</span>' +
        '<span class="q-tag ' + q.tag + '">' + (q.tag === "survey" ? "Responses" : "Comments") + '</span>' +
        '<span class="q-chevron">&#9656;</span>' +
        '</summary><div class="q-body"><p>' + q.body + '</p>' +
        '<div class="q-chart"><canvas></canvas></div>' +
        '<div class="takeaway">' + q.take + '</div></div></details>';
    }).join("");
    // Lazy-render each question's chart the first time its section is opened
    // (a canvas has no size while the <details> is collapsed).
    var items = host.querySelectorAll(".q-item");
    items.forEach(function (el, i) {
      el.addEventListener("toggle", function () {
        var q = QUESTIONS[i];
        if (el.open && !q._rendered && q.viz) {
          q._rendered = true;
          q.viz(el.querySelector("canvas"));
        }
      });
    });
  }

  // =========================================================================
  // Quote injection
  // =========================================================================
  function quoteHTML(q, showUp) {
    var up = showUp && q.upvotes != null ? '<span class="up">&#9650; ' + q.upvotes + '</span>' : "";
    return '<div class="quote">' + up + '<span class="txt">&ldquo;' + q.text + '&rdquo;</span></div>';
  }
  function fillQuotes(id, list, showUp) {
    var host = document.getElementById(id);
    if (host) host.innerHTML = list.map(function (q) { return quoteHTML(q, showUp); }).join("");
  }

  var tq = S.comments.topQuotes;
  function topFrom(qid, n) { return (tq[qid] || []).slice(0, n); }

  // Real, verbatim women-focused comments pulled from the survey open text
  var WOMEN_QUOTES = [
    { text: "If bus service was safer for women and minorities and it didn't take 30 minutes to 4 hours to get anywhere, I would primarily take the bus." },
    { text: "Poor lighting, especially as a woman who might have to walk alone." },
    { text: "It does not feel safe for a woman to use buses in this condition. We need a shift in culture where the system becomes so good that regular workers start using it — that is the only way young women won't be afraid." },
    { text: "No sidewalks, or feeling like I will have to walk in an isolated or unsafe area, as a single female." }
  ];

  // =========================================================================
  // Per-view rendering
  // =========================================================================
  function renderView(v) {
    if (v === "overview") {
      // Q1 doughnut
      new Chart(document.getElementById("chart-q1"), {
        type: "doughnut",
        data: {
          labels: S.q1.labels,
          datasets: [{ data: S.q1.counts,
            backgroundColor: [C.rust, C.amber, C.chartreuse, C.leaf, C.green], borderWidth: 2, borderColor: "#fff" }]
        },
        options: { responsive: true, maintainAspectRatio: false, cutout: "58%",
          plugins: { legend: { position: "right", labels: { boxWidth: 12, padding: 8 } },
            tooltip: { callbacks: { label: function (c) { return c.label + ": " + fmt(c.parsed) + " (" + pct(c.parsed, m.q1Answered) + "%)"; } } } } }
      });
    }

    if (v === "whynot") {
      var r = S.reasons.nonriders;
      hBar("chart-reasons", r.labels, r.counts, C.green,
        { tip: { label: function (c) { return fmt(c.parsed.x) + " selections"; } } });

      var imp = S.importance.nonriders;
      hBar("chart-importance", imp.map(function (x) { return x.name.replace("Better bus stop amenities - ", "").replace("Better ", ""); }),
        imp.map(function (x) { return x.pctImportant; }),
        imp.map(function (x) { return /sidewalk/i.test(x.name) ? C.green : C.leaf; }),
        { xfmt: function (v) { return v + "%"; }, tip: { label: function (c) { return c.parsed.x + "% rate important / very important"; } } });

      // Themes grouped bar
      var th = S.openThemes;
      var themeNames = ["Payment / app", "Safety / crime", "Frequency / reliability", "Car dependence", "Routes / coverage"];
      var series = th.map(function (row, i) {
        var cols = [C.amber, C.rust, C.teal, C.navy];
        return { label: row.question.split(":")[0], data: themeNames.map(function (t) { return row[t]; }),
          backgroundColor: cols[i], borderRadius: 2, maxBarThickness: 16 };
      });
      new Chart(document.getElementById("chart-themes"), {
        type: "bar",
        data: { labels: themeNames, datasets: series },
        options: { responsive: true, maintainAspectRatio: false,
          plugins: { legend: { position: "top", labels: { boxWidth: 10, padding: 6, font: { size: 10 } } },
            tooltip: { callbacks: { label: function (c) { return c.dataset.label + ": " + c.parsed.y + "%"; } } } },
          scales: { y: { beginAtZero: true, ticks: { callback: function (v) { return v + "%"; } }, grid: { color: "#eee" } },
            x: { grid: { display: false } } } }
      });

      // Fare knowledge grouped (non-riders vs riders), as % within group
      var kLabels = Object.keys(S.fareKnowledge.nonriders);
      var nrTot = Object.values(S.fareKnowledge.nonriders).reduce(function (a, b) { return a + b; }, 0);
      var rTot = Object.values(S.fareKnowledge.riders).reduce(function (a, b) { return a + b; }, 0);
      new Chart(document.getElementById("chart-fareknow"), {
        type: "bar",
        data: { labels: kLabels, datasets: [
          { label: "Non-riders", data: kLabels.map(function (k) { return pct(S.fareKnowledge.nonriders[k], nrTot); }), backgroundColor: C.amber, borderRadius: 3, maxBarThickness: 22 },
          { label: "Current riders", data: kLabels.map(function (k) { return pct(S.fareKnowledge.riders[k], rTot); }), backgroundColor: C.green, borderRadius: 3, maxBarThickness: 22 }
        ] },
        options: { indexAxis: "y", responsive: true, maintainAspectRatio: false,
          plugins: { legend: { position: "top", labels: { boxWidth: 12, padding: 8 } },
            tooltip: { callbacks: { label: function (c) { return c.dataset.label + ": " + c.parsed.x + "%"; } } } },
          scales: { x: { beginAtZero: true, ticks: { callback: function (v) { return v + "%"; } }, grid: { color: "#eee" } }, y: { grid: { display: false } } } }
      });

      fillQuotes("quotes-whynot", topFrom("396287", 3).concat(topFrom("396289", 2)), true);
    }

    if (v === "women") {
      // Importance gap grouped horizontal
      var gi = S.gender.importance;
      new Chart(document.getElementById("chart-gender-importance"), {
        type: "bar",
        data: { labels: gi.map(function (x) { return x.improvement.replace("Better bus stop amenities - ", "").replace("Better ", ""); }),
          datasets: [
            { label: "Women", data: gi.map(function (x) { return x.female; }), backgroundColor: C.green, borderRadius: 3, maxBarThickness: 14 },
            { label: "Men", data: gi.map(function (x) { return x.male; }), backgroundColor: C.chartreuse, borderRadius: 3, maxBarThickness: 14 }
          ] },
        options: { indexAxis: "y", responsive: true, maintainAspectRatio: false,
          plugins: { legend: { position: "top", labels: { boxWidth: 12, padding: 8 } },
            tooltip: { callbacks: { label: function (c) { return c.dataset.label + ": " + c.parsed.x.toFixed(2) + " / 5"; } } } },
          scales: { x: { beginAtZero: true, suggestedMax: 5, grid: { color: "#eee" }, title: { display: true, text: "Mean importance (1–5)" } }, y: { grid: { display: false } } } }
      });

      // Rider rate by gender
      new Chart(document.getElementById("chart-gender-rider"), {
        type: "bar",
        data: { labels: ["Women", "Men"], datasets: [{ data: [S.gender.riderStatus.female.Rider, S.gender.riderStatus.male.Rider],
          backgroundColor: [C.green, C.chartreuse], borderRadius: 4, maxBarThickness: 60 }] },
        options: { responsive: true, maintainAspectRatio: false,
          plugins: { legend: { display: false }, tooltip: { callbacks: { label: function (c) { return c.parsed.y + "% currently ride"; } } } },
          scales: { y: { beginAtZero: true, ticks: { callback: function (v) { return v + "%"; } }, grid: { color: "#eee" } }, x: { grid: { display: false } } } }
      });

      // Fare knowledge by gender
      var gk = Object.keys(S.gender.fareKnowledge.female);
      new Chart(document.getElementById("chart-gender-fare"), {
        type: "bar",
        data: { labels: gk, datasets: [
          { label: "Women", data: gk.map(function (k) { return S.gender.fareKnowledge.female[k]; }), backgroundColor: C.green, borderRadius: 3, maxBarThickness: 22 },
          { label: "Men", data: gk.map(function (k) { return S.gender.fareKnowledge.male[k]; }), backgroundColor: C.chartreuse, borderRadius: 3, maxBarThickness: 22 }
        ] },
        options: { indexAxis: "y", responsive: true, maintainAspectRatio: false,
          plugins: { legend: { position: "top", labels: { boxWidth: 12, padding: 8 } },
            tooltip: { callbacks: { label: function (c) { return c.dataset.label + ": " + c.parsed.x + "%"; } } } },
          scales: { x: { beginAtZero: true, ticks: { callback: function (v) { return v + "%"; } }, grid: { color: "#eee" } }, y: { grid: { display: false } } } }
      });

      fillQuotes("quotes-women", WOMEN_QUOTES, false);
    }

    if (v === "evidence") {
      fillQuotes("quotes-evidence", topFrom("396287", 1).concat(topFrom("396511", 1)).concat(topFrom("396291", 1)), true);
    }
  }

  // ---- Initial render -----------------------------------------------------
  renderQuestions();
  renderView("whynot");
  rendered.whynot = true;
})();
