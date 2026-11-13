/* ==========================================================================
   TT1 Transit Survey Dashboard — Women deep-dive tabs
   Reads window.SURVEY.women (built by data_prep/women_analysis.py and
   women_text.py) and renders ONE tab, "Women Deep Dive", whose content follows a
   filter at the top (All respondents / Current riders / Non-riders). Self-contained
   so app.js stays untouched.
   ========================================================================== */
(function () {
  "use strict";
  var W = window.SURVEY && window.SURVEY.women;
  if (!W || typeof Chart === "undefined") return;

  var C = { green: "#0D6937", leaf: "#73AB45", chartreuse: "#A8C23E", teal: "#189ABC", navy: "#01426A",
    amber: "#FBAE40", rust: "#A8322D", gray: "#9AA0A6", body: "#414042" };
  var FLAG_COLOR = { clear: C.green, suggestive: C.amber, none: "#C9CCCF" };
  var FLAG_LABEL = { clear: "Significant", suggestive: "Suggestive", none: "Not significant" };

  var SEGS = {
    all: { name: "All respondents", short: "Together" },
    riders: { name: "Current riders", short: "Riders" },
    nonriders: { name: "Non-riders", short: "Non-riders" }
  };

  // ---- helpers ------------------------------------------------------------
  function esc(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  function it(seg, id) {
    var l = W.structured[seg] || [];
    for (var i = 0; i < l.length; i++) if (l[i].id === id) return l[i];
    return null;
  }
  function f0(v) { return v == null ? "—" : Math.round(v).toString(); }
  function f1(v) { return v == null ? "—" : v.toFixed(1); }
  function f2(v) { return v == null ? "—" : v.toFixed(2); }
  function sgn(v, d) { return (v > 0 ? "+" : v < 0 ? "−" : "") + Math.abs(v).toFixed(d); }
  function pTxt(p) { return p == null ? "—" : (p < 0.001 ? "<0.001" : p.toFixed(3)); }
  function badge(flag, r) {
    var tip = r ? "p = " + pTxt(r.p) + "" : "";
    return '<span class="ev ev-' + flag + '" title="' + esc(tip) + '">' + FLAG_LABEL[flag] + "</span>";
  }
  function ciTxt(r, d, unit) { return "[" + sgn(r.ciLo, d) + ", " + sgn(r.ciHi, d) + "]" + (unit ? " " + unit : ""); }
  function pairPct(seg, id) { var r = it(seg, id); return r ? f0(r.pctF) + "% of women vs " + f0(r.pctM) + "% of men" : "—"; }
  function pairMean(seg, id) { var r = it(seg, id); return r ? f2(r.meanF) + " vs " + f2(r.meanM) : "—"; }
  function pairTop2(seg, id) { var r = it(seg, id); return r ? f0(r.top2F) + "% vs " + f0(r.top2M) + "%" : "—"; }
  function countFlags(seg) {
    var l = W.structured[seg] || [], c = 0, s = 0;
    l.forEach(function (r) { if (r.flag === "clear") c++; else if (r.flag === "suggestive") s++; });
    return { clear: c, sugg: s, total: l.length };
  }
  function wrap(str, max) {
    var words = String(str).split(" "), lines = [], cur = "";
    words.forEach(function (w) {
      var t = cur ? cur + " " + w : w;
      if (t.length > max && cur) { lines.push(cur); cur = w; } else cur = t;
    });
    if (cur) lines.push(cur);
    return lines;
  }
  var REF = {};
  W.blocks.forEach(function (b) { REF[b.id] = b; });
  function shortRef(blockId) { return REF[blockId] ? REF[blockId].ref.replace("Walk/bike ", "WB ") : ""; }

  // Draws the 95% CI whisker for each bar on a horizontal bar chart.
  var ciPlugin = {
    id: "ci",
    afterDatasetsDraw: function (chart) {
      var cfg = chart.options.plugins.ci;
      if (!cfg || !cfg.data) return;
      var ctx = chart.ctx, meta = chart.getDatasetMeta(0), xs = chart.scales.x;
      cfg.data.forEach(function (d, i) {
        var bar = meta.data[i]; if (!bar) return;
        var y = bar.y, x1 = xs.getPixelForValue(d.lo), x2 = xs.getPixelForValue(d.hi);
        ctx.save(); ctx.strokeStyle = "#333"; ctx.lineWidth = 1.4; ctx.beginPath();
        ctx.moveTo(x1, y); ctx.lineTo(x2, y);
        ctx.moveTo(x1, y - 4); ctx.lineTo(x1, y + 4); ctx.moveTo(x2, y - 4); ctx.lineTo(x2, y + 4);
        ctx.stroke(); ctx.restore();
      });
    }
  };

  // =========================================================================
  // Segment views (All / Riders / Non-riders)
  // =========================================================================
  var CONSISTENCY = [
    ["q2_lighting_at_stops", "Lighting at stops (importance, 1–5)", "pts", 2],
    ["q2_safe_sidewalks_crossings", "Safe sidewalks & crossings to reach stops (importance)", "pts", 2],
    ["q2_benches_at_stops", "Benches at stops (importance)", "pts", 2],
    ["q2_park_and_ride_facilities", "Park-and-ride facilities (importance)", "pts", 2],
    ["q2_more_frequent_service", "More frequent service (importance)", "pts", 2],
    ["q2_more_reliable_service", "More reliable service (importance)", "pts", 2],
    ["q3_knows_how_to_pay", "Knows how to pay the fare", "pp", 1],
    ["q3_doesn_t_know_would_like_", "Doesn't know and would like to learn how to pay", "pp", 1],
    ["q4_notsure", "Not sure whether a stop is within a 10-minute walk", "pp", 1],
    ["wb12_dis", "Disability, mobility or sensory needs affect walking/biking", "pp", 1]
  ];

  function consistencyTable() {
    var rows = CONSISTENCY.map(function (c) {
      var cells = ["riders", "nonriders", "all"].map(function (seg) {
        var r = it(seg, c[0]);
        if (!r) return '<td class="num na">—</td>';
        return '<td class="num"><span class="dot dot-' + r.flag + '" title="' + FLAG_LABEL[r.flag] + '"></span> ' +
          sgn(r.diff, c[3]) + " " + c[2] + "</td>";
      }).join("");
      return "<tr><th scope=\"row\">" + esc(c[1]) + "</th>" + cells + "</tr>";
    }).join("");
    return '<table class="wtable"><thead><tr><th>Women minus men</th><th class="num">Riders<br><small>n = ' +
      W.sample.seg.riders.nF + " / " + W.sample.seg.riders.nM + '</small></th><th class="num">Non-riders<br><small>n = ' +
      W.sample.seg.nonriders.nF + " / " + W.sample.seg.nonriders.nM + '</small></th><th class="num">Together<br><small>n = ' +
      W.sample.seg.all.nF + " / " + W.sample.seg.all.nM + "</small></th></tr></thead><tbody>" + rows + "</tbody></table>" +
      '<p class="note"><span class="dot dot-clear"></span> significant &nbsp; <span class="dot dot-suggestive"></span> suggestive &nbsp; ' +
      '<span class="dot dot-none"></span> not significant. Positive values mean women scored higher. "pts" = points on the 1–5 scale; "pp" = percentage points.</p>';
  }

  function narrative(seg) {
    var L = [];
    if (seg === "all") {
      var lt = it("all", "q2_lighting_at_stops"), rs = W.ratingStyle.all, cen = null;
      W.ratingStyle.all.centered.forEach(function (r) { if (/Lighting/.test(r.name)) cen = r; });
      L.push("<strong>Ridership is the same.</strong> " + pairPct("all", "q1_rider") + " currently ride at least occasionally, and about " +
        f0(it("all", "q1_never").pctF) + "% of both groups never ride. Differences are in what would make riding work, not in whether they ride.");
      L.push("<strong>Lighting at stops is the one significant difference.</strong> Women rate it " + pairMean("all", "q2_lighting_at_stops") +
        " out of 5 (" + sgn(lt.diff, 2) + "), and " + pairTop2("all", "q2_lighting_at_stops") + " call it important. It shows up separately among riders and non-riders and holds after accounting for age and rider status.");
      L.push("<strong>Women rate almost everything a little higher.</strong> Averaged across all 11 improvements, women score " + f2(rs.overall.meanF) +
        " vs " + f2(rs.overall.meanM) + " for men (" + sgn(rs.overall.diff, 2) + "). Lighting still stands out after each person's own average is removed (" +
        sgn(cen.diff, 2) + ", relative-priority view), so it is a genuine priority and not just a rating habit.");
      L.push("<strong>A pedestrian-environment lead.</strong> Safe sidewalks &amp; crossings (" + pairMean("all", "q2_safe_sidewalks_crossings") + ") and benches (" +
        pairMean("all", "q2_benches_at_stops") + ") are also higher among women (suggestive).");
      L.push("<strong>An information gap.</strong> " + pairPct("all", "q3_doesn_t_know_would_like_") + " say they don't know how to pay and want to learn, and " +
        pairPct("all", "q4_notsure") + " aren't sure whether a stop is within a 10-minute walk (both suggestive).");
      L.push("<strong>Not a \"women left because of safety\" story.</strong> Among people who gave reasons for not riding, " + pairPct("all", "q1a_safety_concerns") +
        " cite safety concerns, which is not significant. Women's emphasis shows up in the conditions around stops and on the walk to them.");
      L.push("<strong>Walking and biking answers look alike.</strong> Both groups put drivers yielding first (" + pairPct("all", "wb4_whether_drivers_yiel") +
        "). One suggestive difference: " + pairPct("all", "wb12_dis") + " say disability, mobility or sensory needs affect how they walk or bike, even though self-identified disability is the same in the sample.");
    } else if (seg === "riders") {
      L.push("<strong>Riders of both genders want the same core service.</strong> More frequent service (" + pairMean("riders", "q2_more_frequent_service") +
        ") and more reliable service (" + pairMean("riders", "q2_more_reliable_service") + ") are near the top for women and men alike; there is no gap.");
      L.push("<strong>Lighting at stops is the standout.</strong> Women riders rate it " + pairMean("riders", "q2_lighting_at_stops") + ", with " +
        pairTop2("riders", "q2_lighting_at_stops") + " calling it important. With only " + W.sample.seg.riders.nF + " women and " + W.sample.seg.riders.nM +
        " men the gap is suggestive, but it matches the non-rider and all-respondent results.");
      L.push("<strong>Park-and-ride is worth watching.</strong> Women riders rate it " + pairMean("riders", "q2_park_and_ride_facilities") + ", a possible difference that is not significant.");
      L.push("<strong>Fare knowledge and payment look alike.</strong> Nearly all riders know how to pay (" + pairPct("riders", "q3_knows_how_to_pay") + "), and " +
        pairPct("riders", "q3a_pays_with_the_umo_app") + " of those who pay use the Umo app. The fare-knowledge gap seen overall is a non-rider issue.");
      L.push("<strong>In their comments,</strong> women riders write less about bike lanes than men riders do (suggestive). Other gaps are not significant. See the Comments &amp; themes section below.");
    } else {
      L.push("<strong>Three pedestrian-environment items lean higher among women non-riders:</strong> lighting at stops (" + pairMean("nonriders", "q2_lighting_at_stops") +
        "), benches (" + pairMean("nonriders", "q2_benches_at_stops") + ") and safe sidewalks &amp; crossings (" + pairMean("nonriders", "q2_safe_sidewalks_crossings") +
        "). Each is suggestive, and the all-respondent view points the same way.");
      L.push("<strong>Women non-riders know less about how to pay.</strong> " + pairPct("nonriders", "q3_knows_how_to_pay") + " know how, " +
        "and " + pairPct("nonriders", "q3_doesn_t_know_would_like_") + " would like to learn. Willingness to learn is a point in favour of outreach and education.");
      L.push("<strong>Uncertainty about stop access.</strong> " + pairPct("nonriders", "q4_notsure") + " aren't sure whether a stop is within a 10-minute walk of home.");
      L.push("<strong>Reasons for stopping are similar.</strong> Safety concerns: " + pairPct("nonriders", "q1a_safety_concerns") +
        "; schedule or frequency: " + pairPct("nonriders", "q1a_schedule_or_frequency_no") + "; switch from free to fare: " +
        pairPct("nonriders", "q1a_switch_from_free_to_fare") + ".");
      L.push("<strong>Priorities for the service itself are similar.</strong> More routes (" + pairMean("nonriders", "q2_more_routes_to_new_places") +
        "), frequency (" + pairMean("nonriders", "q2_more_frequent_service") + ") and reliability (" + pairMean("nonriders", "q2_more_reliable_service") + ") are all high for both groups.");
    }
    return "<ul>" + L.map(function (x) { return "<li>" + x + "</li>"; }).join("") + "</ul>";
  }

  function leadFor(seg) {
    var n = W.sample.seg[seg], f = countFlags(seg);
    if (seg === "all") {
      return "Across all " + n.nF + " women and " + n.nM + " men who gave a gender, women and men answer most questions the same way. " +
        "Of " + f.total + " comparisons, " + f.clear + " is significant (lighting at stops) and " + f.sugg + " more are suggestive.";
    }
    if (seg === "riders") {
      return "Among current riders (" + n.nF + " women, " + n.nM + " men), women and men look far more alike than different. " +
        "With a small group only large gaps show up: " + f.clear + " significant and " + f.sugg + " suggestive across " + f.total + " comparisons.";
    }
    return "Among non-riders (" + n.nF + " women, " + n.nM + " men), women lean toward the conditions around stops and the walk to them, " +
      "and more of them say they don't know how to pay. " + f.clear + " significant and " + f.sugg + " suggestive differences across " + f.total + " comparisons.";
  }

  function segmentHTML(seg) {
    var s = SEGS[seg], n = W.sample.seg[seg], f = countFlags(seg), p = "w-" + seg + "-";
    var html = '<p class="seg-lede"><strong>' + esc(s.name) + ".</strong> " + leadFor(seg) + "</p>";
    html += '<div class="caveat"><strong>How to read this.</strong> Only ' + W.sample.genderAnswered + " of 1,196 respondents gave a gender, and they skew " +
      "white, higher-income and highly educated, so treat results as directional. " + W.sample.nNonbinary + " non-binary respondents are too few to analyze separately. " +
      "<strong>Significant</strong> means the difference holds up after allowing for the many comparisons made; <strong>suggestive</strong> means a possible difference worth following up.</div>";
    html += '<div class="kpi-row">' +
      '<div class="kpi"><span class="num">' + n.nF + '</span><span class="label">Women in this group</span></div>' +
      '<div class="kpi teal"><span class="num">' + n.nM + '</span><span class="label">Men in this group</span></div>' +
      '<div class="kpi amber"><span class="num">' + f.clear + '</span><span class="label">Significant differences (of ' + f.total + ' comparisons)</span></div>' +
      '<div class="kpi navy"><span class="num">' + f.sugg + '</span><span class="label">Suggestive differences</span></div></div>';

    html += '<div class="card wide"><h2>Do riders and non-riders tell the same story?</h2>' +
      '<p class="card-sub">Women minus men, for the items that matter most, in each group and together. The filter above changes the charts and sections below, not this table.</p>' + consistencyTable() + "</div>";

    html += '<div class="card-grid" style="margin-top:16px;">' +
      '<div class="card wide"><h2>Priorities for improvements</h2>' +
      '<p class="card-sub">Question 2 &middot; importance of each improvement in making transit a more likely choice</p>' +
      '<div class="seg-toggle" role="group" aria-label="Rating view" id="' + p + 'q2toggle">' +
      '<button class="on" data-mode="raw">Raw ratings (1–5)</button><button data-mode="rel">Relative priority</button></div>' +
      '<div class="chart-box tall"><canvas id="' + p + 'q2"></canvas></div>' +
      '<p class="note" id="' + p + 'q2note"></p></div>' +
      '<div class="card wide"><h2>Where else did women and men answer differently?</h2>' +
      '<p class="card-sub">Women minus men, in percentage points, showing the largest gaps. Whiskers show the 95% confidence range.</p>' +
      '<div class="chart-box" id="' + p + 'fbox"><canvas id="' + p + 'forest"></canvas></div>' +
      '<p class="note">Green = significant, amber = suggestive, gray = not significant. Bars right of zero mean women were more likely to give the answer.</p></div></div>';

    html += '<details class="info-box" open style="margin-top:16px;"><summary>What stands out</summary><div class="info-body">' + narrative(seg) + "</div></details>";

    html += commentsHTML(seg);

    html += '<details class="info-box" style="margin-top:16px;"><summary>Every question, women vs. men</summary><div class="info-body" id="' + p + 'tables"></div></details>';
    html += '<details class="info-box" style="margin-top:16px;"><summary>Who answered: are the women and men in this group comparable?</summary><div class="info-body" id="' + p + 'comp"></div></details>';
    return html;
  }

  function q2Chart(seg) {
    var p = "w-" + seg + "-", chart = null;
    var raw = (W.structured[seg] || []).filter(function (r) { return r.block === "q2"; });
    var rel = (W.ratingStyle[seg] || { centered: [] }).centered;
    function dataFor(mode) {
      var rows = (mode === "raw" ? raw : rel).slice().sort(function (a, b) { return b.meanF - a.meanF; });
      return {
        rows: rows,
        labels: rows.map(function (r) { return wrap((r.flag === "clear" ? "★ " : r.flag === "suggestive" ? "☆ " : "") + r.name, 30); }),
        f: rows.map(function (r) { return r.meanF; }), m: rows.map(function (r) { return r.meanM; })
      };
    }
    var d = dataFor("raw");
    chart = new Chart(document.getElementById(p + "q2"), {
      type: "bar",
      data: { labels: d.labels, datasets: [
        { label: "Women", data: d.f, backgroundColor: C.green, borderRadius: 3, maxBarThickness: 14 },
        { label: "Men", data: d.m, backgroundColor: C.chartreuse, borderRadius: 3, maxBarThickness: 14 }] },
      options: { indexAxis: "y", responsive: true, maintainAspectRatio: false,
        plugins: { legend: { position: "top", labels: { boxWidth: 12, padding: 8 } },
          tooltip: { callbacks: {
            title: function (items) { return chart._rows[items[0].dataIndex].name; },
            label: function (c) { return c.dataset.label + ": " + c.parsed.x.toFixed(2); },
            afterBody: function (items) { var r = chart._rows[items[0].dataIndex]; return FLAG_LABEL[r.flag] + " (p = " + pTxt(r.p) + ")"; } } } },
        scales: { x: { min: 1, max: 5, grid: { color: "#eee" }, title: { display: true, text: "Mean importance (1–5)" } }, y: { grid: { display: false }, ticks: { autoSkip: false, font: { size: 11 } } } } }
    });
    chart._rows = d.rows;
    var note = document.getElementById(p + "q2note");
    function setNote(mode) {
      note.innerHTML = mode === "raw"
        ? "Sorted by women's score, highest first. ★ significant, ☆ suggestive. Women rate most improvements slightly higher, so the next view removes each person's own average."
        : "Each person's rating minus their own average across all 11 improvements, showing what a group prioritises <em>relative to its other answers</em>. Zero = an average priority. Sorted by women's score, highest first. ★ significant, ☆ suggestive.";
    }
    setNote("raw");
    document.getElementById(p + "q2toggle").addEventListener("click", function (e) {
      var b = e.target.closest("button"); if (!b) return;
      this.querySelectorAll("button").forEach(function (x) { x.classList.remove("on"); });
      b.classList.add("on");
      var nd = dataFor(b.dataset.mode);
      chart._rows = nd.rows;
      chart.data.labels = nd.labels;
      chart.data.datasets[0].data = nd.f; chart.data.datasets[1].data = nd.m;
      chart.options.scales.x.min = b.dataset.mode === "raw" ? 1 : -1;
      chart.options.scales.x.max = b.dataset.mode === "raw" ? 5 : 1;
      chart.options.scales.x.title.text = b.dataset.mode === "raw" ? "Mean importance (1–5)" : "Mean rating minus the person's own average";
      chart.update(); setNote(b.dataset.mode);
    });
  }

  function forestChart(seg) {
    var p = "w-" + seg + "-";
    var bin = (W.structured[seg] || []).filter(function (r) { return r.kind === "binary" && r.block !== "q1" && r.block !== "q4" || r.id === "q4_notsure" || (r.block === "q1" && r.id === "q1_rider"); });
    // Drop mirror-image rows (a "No"/"Not interested" twin adds nothing) and low-information rows.
    bin = bin.filter(function (r) { return !/^wb10_hard$|^q4_no$|^q4_yes$/.test(r.id); });
    var chosen = bin.filter(function (r) { return r.flag !== "none"; });
    var rest = bin.filter(function (r) { return r.flag === "none"; })
      .sort(function (a, b) { return Math.abs(b.diff) - Math.abs(a.diff); });
    chosen = chosen.concat(rest.slice(0, Math.max(0, 14 - chosen.length)));
    chosen.sort(function (a, b) { return b.diff - a.diff; });
    document.getElementById(p + "fbox").style.height = Math.max(260, chosen.length * 30 + 60) + "px";
    var lo = Math.min.apply(null, chosen.map(function (r) { return r.ciLo; })), hi = Math.max.apply(null, chosen.map(function (r) { return r.ciHi; }));
    var span = Math.ceil(Math.max(Math.abs(lo), Math.abs(hi)) / 5) * 5;
    new Chart(document.getElementById(p + "forest"), {
      type: "bar",
      data: { labels: chosen.map(function (r) { return wrap(shortRef(r.block) + " · " + r.name, 40); }),
        datasets: [{ data: chosen.map(function (r) { return r.diff; }), backgroundColor: chosen.map(function (r) { return FLAG_COLOR[r.flag]; }),
          borderRadius: 2, maxBarThickness: 16 }] },
      plugins: [ciPlugin],
      options: { indexAxis: "y", responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false }, ci: { data: chosen.map(function (r) { return { lo: r.ciLo, hi: r.ciHi }; }) },
          tooltip: { callbacks: {
            title: function (items) { return chosen[items[0].dataIndex].name; },
            label: function (c) { var r = chosen[c.dataIndex]; return "Women " + f1(r.pctF) + "% vs men " + f1(r.pctM) + "% (" + sgn(r.diff, 1) + " pp)"; },
            afterBody: function (items) { var r = chosen[items[0].dataIndex]; return ["95% CI " + ciTxt(r, 1, "pp"), FLAG_LABEL[r.flag] + " (p = " + pTxt(r.p) + ")", "n = " + r.nF + " women, " + r.nM + " men"]; } } } },
        scales: { x: { min: -span, max: span, grid: { color: "#eee" }, ticks: { callback: function (v) { return (v > 0 ? "+" : "") + v; } }, title: { display: true, text: "Women minus men (percentage points)" } },
          y: { grid: { display: false }, ticks: { autoSkip: false, font: { size: 11 } } } } }
    });
  }

  function allTables(seg) {
    var host = document.getElementById("w-" + seg + "-tables");
    var by = {};
    (W.structured[seg] || []).forEach(function (r) { (by[r.block] = by[r.block] || []).push(r); });
    host.innerHTML = W.blocks.filter(function (b) { return by[b.id]; }).map(function (b) {
      var rows = by[b.id].map(function (r) {
        if (r.kind === "ordinal") {
          return "<tr><th scope=\"row\">" + esc(r.name) + '</th><td class="num">' + f2(r.meanF) + ' <small>(' + f0(r.top2F) + '% important)</small></td><td class="num">' +
            f2(r.meanM) + ' <small>(' + f0(r.top2M) + '% important)</small></td><td class="num">' + sgn(r.diff, 2) + " " + ciTxt(r, 2) + "</td><td>" + badge(r.flag, r) + "</td></tr>";
        }
        return "<tr><th scope=\"row\">" + esc(r.name) + '</th><td class="num">' + f1(r.pctF) + '% <small>(n=' + r.nF + ')</small></td><td class="num">' + f1(r.pctM) +
          '% <small>(n=' + r.nM + ')</small></td><td class="num">' + sgn(r.diff, 1) + " pp " + ciTxt(r, 1) + "</td><td>" + badge(r.flag, r) + "</td></tr>";
      }).join("");
      return "<h3 class=\"tbl-h\"><span class=\"q-num\">" + esc(b.ref) + "</span> " + esc(b.title) + "</h3>" +
        '<div class="tbl-scroll"><table class="wtable"><thead><tr><th>Answer</th><th class="num">Women</th><th class="num">Men</th><th class="num">Difference (95% CI)</th><th>Evidence</th></tr></thead><tbody>' + rows + "</tbody></table></div>";
    }).join("") + '<p class="note">Percentages are of women or men who answered each question. Hover a label for the p-value.</p>';
  }

  function compositionTable(seg) {
    var host = document.getElementById("w-" + seg + "-comp");
    var rows = (W.composition[seg] || []).map(function (r) {
      return "<tr><th scope=\"row\">" + esc(r.name) + '</th><td class="num">' + f0(r.pctF) + '%</td><td class="num">' + f0(r.pctM) + '%</td><td class="num">' + sgn(r.diff, 0) +
        " pp</td><td>" + (r.flag === "none" ? "Similar" : '<span class="ev ev-suggestive">Differs</span>') + "</td></tr>";
    }).join("");
    host.innerHTML = '<div class="tbl-scroll"><table class="wtable"><thead><tr><th>Background (among those who answered)</th><th class="num">Women</th><th class="num">Men</th><th class="num">Gap</th><th></th></tr></thead><tbody>' + rows + "</tbody></table></div>" +
      '<p class="note">Where backgrounds differ, an answer gap could partly reflect that mix. The lighting, sidewalks and fare-learning results held up after adjusting for rider status and age.</p>';
  }

  function renderBody(seg) {
    var host = document.getElementById("wd-body");
    host.querySelectorAll("canvas").forEach(function (cv) { var c = Chart.getChart(cv); if (c) c.destroy(); });
    voiceState.chart = null; voiceState.seg = seg;
    host.innerHTML = segmentHTML(seg);
    q2Chart(seg); forestChart(seg); allTables(seg); compositionTable(seg); bindComments();
  }

  // =========================================================================
  // Comments & themes tab
  // =========================================================================
  var voiceState = { seg: "all", scope: "any", chart: null };
  var SCOPE_NAME = { any: "All comments", transit: "Transit questions", walkbike: "Walking & biking questions" };

  function themeFor(seg, scope) { var t = W.text.themes[seg]; return t && t[scope]; }

  function drawThemes() {
    var t = themeFor(voiceState.seg, voiceState.scope), cap = document.getElementById("wv-chartcap"), box = document.getElementById("wv-chartbox");
    if (voiceState.chart) { voiceState.chart.destroy(); voiceState.chart = null; }
    if (!t) { box.style.display = "none"; cap.innerHTML = "Too few commenters in this group to compare women and men."; return; }
    box.style.display = "block";
    var rows = t.items.slice().sort(function (a, b) { return b.diff - a.diff; });
    box.style.height = Math.max(300, rows.length * 34 + 70) + "px";
    cap.innerHTML = "Based on <strong>" + t.nF + " women</strong> and <strong>" + t.nM + " men</strong> who left at least one comment (" + SCOPE_NAME[voiceState.scope].toLowerCase() + "). Each person counts once per theme.";
    voiceState.chart = new Chart(document.getElementById("wv-chart"), {
      type: "bar",
      data: { labels: rows.map(function (r) { return wrap((r.flag === "clear" ? "★ " : r.flag === "suggestive" ? "☆ " : "") + r.name, 34); }),
        datasets: [
          { label: "Women", data: rows.map(function (r) { return r.pctF; }), backgroundColor: C.green, borderRadius: 3, maxBarThickness: 13 },
          { label: "Men", data: rows.map(function (r) { return r.pctM; }), backgroundColor: C.chartreuse, borderRadius: 3, maxBarThickness: 13 }] },
      options: { indexAxis: "y", responsive: true, maintainAspectRatio: false, animation: false,
        plugins: { legend: { position: "top", labels: { boxWidth: 12, padding: 8 } },
          tooltip: { callbacks: {
            title: function (items) { return rows[items[0].dataIndex].name; },
            label: function (c) { var r = rows[c.dataIndex]; return c.dataset.label + ": " + c.parsed.x + "% (" + (c.datasetIndex === 0 ? r.kF + " of " + t.nF : r.kM + " of " + t.nM) + ")"; },
            afterBody: function (items) { var r = rows[items[0].dataIndex]; return FLAG_LABEL[r.flag] + " (p = " + pTxt(r.p) + ")"; } } } },
        scales: { x: { beginAtZero: true, grid: { color: "#eee" }, ticks: { callback: function (v) { return v + "%"; } }, title: { display: true, text: "% of commenters raising the theme" } },
          y: { grid: { display: false }, ticks: { autoSkip: false, font: { size: 11 } } } } }
    });
  }

  function quotesHTML() {
    var q = W.text.quotes, out = "";
    var capt = { "Traveling with children": "Caregiving", "Light, safety & feeling secure": "Personal security & lighting", "Shade, heat & the walk to the stop": "Heat & shade", "Not knowing how it works": "Information gap" };
    var TH = themeFor("all", "any"), find = function (n) { var r = null; TH && TH.items.forEach(function (x) { if (x.name.indexOf(n) === 0) r = x; }); return r; };
    var stat = { "Traveling with children": find("Caregiving"), "Light, safety & feeling secure": find("Personal security"), "Shade, heat & the walk to the stop": find("Heat") };
    Object.keys(q).forEach(function (title) {
      var s = stat[title];
      out += '<div class="voice-card"><h3>' + esc(title) + "</h3>" +
        (s ? '<p class="voice-stat">Theme &ldquo;' + esc(s.name) + '&rdquo;: raised by ' + f0(s.pctF) + "% of women commenters vs. " + f0(s.pctM) + "% of men (" + FLAG_LABEL[s.flag].toLowerCase() + ").</p>" : "") +
        q[title].map(function (x) {
          return '<div class="quote">' + (x.upvotes ? '<span class="up">&#9650; ' + x.upvotes + "</span>" : "") + '<span class="txt">&ldquo;' + esc(x.text) + "&rdquo;</span>" +
            '<span class="who">' + esc(x.who) + "</span></div>";
        }).join("") + "</div>";
    });
    return out;
  }

  function commentsHTML(seg) {
    var th = themeFor("all", "any");
    function g(n) { var r = null; th.items.forEach(function (x) { if (x.name.indexOf(n) === 0) r = x; }); return r; }
    var bike = themeFor("all", "walkbike").items.filter(function (x) { return /Biking/.test(x.name); })[0];
    var care = g("Caregiving"), sec = g("Personal security"), amen = g("Bus stop"), heat = g("Heat"), info = g("Apps"), fare = g("Fare");
    var html = '<h2 class="sub-band">Comments &amp; themes</h2><p class="seg-lede">Linking each comment to its author\'s answers gives ' + W.text.engagement[seg].female.commenters + " women and " +
      W.text.engagement[seg].male.commenters + " men in this group who wrote about transit, walking and biking.</p>";
    html += '<div class="caveat"><strong>Exploratory.</strong> Theme counts come from keyword rules applied to each person\'s comments, and the groups are small, so most gaps are <em>suggestive</em> rather than significant. ' +
      "Across all respondents, the one significant result is that men write about bike lanes more than women do in the walking and biking questions. The rest are leads for follow-up.</div>";

    html += '<div class="card wide"><h2>What women and men write about</h2>' +
      '<p class="card-sub">Share of commenters raising each theme at least once. Choose a set of questions; the group follows the filter at the top.</p>' +
      '<div class="toggle-row"><div class="seg-toggle" id="wv-scope"><button class="on" data-v="any">All comments</button><button data-v="transit">Transit questions</button><button data-v="walkbike">Walking &amp; biking questions</button></div></div>' +
      '<p class="note" id="wv-chartcap" style="margin:0 0 8px;"></p><div class="chart-box" id="wv-chartbox"><canvas id="wv-chart"></canvas></div>' +
      '<p class="note">★ significant &nbsp; ☆ suggestive. Themes are keyword-based; "Personal security &amp; harassment" is deliberately narrow (crime, harassment, threatening behavior) and is kept apart from traffic danger.</p></div>';

    html += seg !== "all" ? '<p class="note" style="margin-top:12px;">The written summary of what the comments add and the quotes below cover all respondents. Choose &ldquo;All respondents&rdquo; at the top to read the written summary.</p>' :
      '<details class="info-box" open style="margin-top:16px;"><summary>What the comments add</summary><div class="info-body"><ul>' +
      "<li><strong>Women's attention leans toward the walk and the wait.</strong> Bus stop amenities (" + f0(amen.pctF) + "% of women vs. " + f0(amen.pctM) + "% of men) is suggestive; heat and shade (" + f0(heat.pctF) + "% vs. " + f0(heat.pctM) +
      "%) and crossings and sidewalks lean the same way but are not significant. It echoes the survey result that lighting, benches and sidewalks matter more to women.</li>" +
      "<li><strong>Men's comments are more about cycling.</strong> In the walking and biking questions, " + f0(bike.pctM) + "% of men mention bike lanes or biking vs. " + f0(bike.pctF) + "% of women, the one significant text difference. For women, walking-first improvements may land better than bike-lane framing.</li>" +
      "<li><strong>Travelling with children appears mainly in women's comments</strong> (" + f0(care.pctF) + "% vs. " + f0(care.pctM) + "%, suggestive): strollers and curb ramps, school trips, child-friendly stops, and not feeling able to bring kids onto unprotected streets. The numbers are small, but it points to trip-chaining and care trips as a distinct need worth testing.</li>" +
      "<li><strong>Personal security is a real but minority theme.</strong> " + f0(sec.pctF) + "% of women commenters vs. " + f0(sec.pctM) + "% of men raise crime, harassment or feeling unsafe around other people (not significant). When women raise it, it tends to be specific: being alone, the dark, loitering near stations.</li>" +
      "<li><strong>The information signal is in the survey answers, not the comments.</strong> Comments about apps, information and signage appear at the same rate for women and men (" + f0(info.pctF) + "% vs. " + f0(info.pctM) + "%). The women-specific signal comes from the structured questions: not knowing how to pay and not being sure a stop is nearby.</li>" +
      "<li><strong>Tone and topics.</strong> Women's comments read a little more negative on the platform's automated sentiment score (small difference). Men write somewhat more about fare technology such as tap-to-pay (" + f0(fare.pctM) + "% vs. " + f0(fare.pctF) + "%, not significant).</li></ul></div></details>";


    html += '<div class="card wide" style="margin-top:16px;"><h2>In women\'s own words</h2><p class="card-sub">All respondents &middot; comments written by women, grouped by theme and chosen to show the range of what was said, not to prove a point.</p><div class="voice-grid">' + quotesHTML() + "</div>" +
      '<p class="note">Comments are shown verbatim from a hand-reviewed selection; names and other identifying details are left out. Thumbs-up counts show endorsement by other participants while the survey was open.</p></div>';
    return html;
  }

  function bindComments() {
    document.getElementById("wv-scope").addEventListener("click", function (e) {
      var b = e.target.closest("button"); if (!b) return;
      this.querySelectorAll("button").forEach(function (x) { x.classList.remove("on"); });
      b.classList.add("on"); voiceState.scope = b.dataset.v; drawThemes();
    });
    drawThemes();
  }

  // =========================================================================
  // Single tab: render on first open, re-render when the filter changes
  // =========================================================================
  var current = "all", started = false;
  var tabBtn = document.querySelector('.tab-btn[data-view="wdive"]');
  if (tabBtn) tabBtn.addEventListener("click", function () { if (!started) { started = true; renderBody(current); } });
  var filter = document.getElementById("wd-filter");
  if (filter) {
    filter.addEventListener("click", function (e) {
      var b = e.target.closest("button"); if (!b || b.dataset.seg === current) return;
      filter.querySelectorAll("button").forEach(function (x) { x.classList.remove("on"); x.setAttribute("aria-pressed", "false"); });
      b.classList.add("on"); b.setAttribute("aria-pressed", "true");
      current = b.dataset.seg; started = true;
      var n = W.sample.seg[current];
      var cap = document.getElementById("wd-filter-n");
      if (cap) cap.textContent = n.nF + " women, " + n.nM + " men";
      renderBody(current);
    });
  }
})();
