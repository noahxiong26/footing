/* Footing Fit Score engine. Runs ON THE PHONE: the person's status and situation never leave the device.
 *
 * Mirrors footing/fit.py line for line (tests/test_fit_parity.py runs both on the same inputs and
 * requires identical output). Method and citations: docs/RATING_FORMULA.md.
 *
 *   component scores (0-100 or null = Unknown)
 *     access          programs this person can likely use here (federal rules by status + state add-ons)
 *     affordability   2-BR Housing Wage / state minimum wage (NLIHC Out of Reach 2026, DOL)
 *     shelter         share of homeless people unsheltered on the Jan 2025 count (HUD AHAR 2025)
 *     safety          state immigration-enforcement laws (ILRC tiers, Sept 2026) - only if status is at risk
 *     criminalization statewide camping law confirmed (Unknown when we have not confirmed either way)
 *     community       Bayesian average of ratings from people who have been there (Unknown until rated)
 *   weights           Rank-Order Centroid of the person's priority order (Barron & Barrett 1996)
 *   fit               weighted mean of KNOWN components (unknowns never count as zero)
 *   confidence        sum of weight x freshness over known components
 *   robustness        rank range across 300 Dirichlet-perturbed weightings (seeded, reproducible)
 */
(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.FootingFit = factory();
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  var COMPONENTS = ["access", "affordability", "shelter", "safety", "criminalization", "community"];
  var FRESHNESS = { access: 0.9, affordability: 0.9, shelter: 0.7, safety: 0.9, criminalization: 0.6 };
  var VALUE = { yes: 1.0, limited: 0.5, varies: 0.5, no: 0.0 };
  var LAWFUL = ["citizen", "lpr5", "lpr", "refugee_asylee", "cuban_haitian", "cofa", "asylum_pending", "tps",
    "daca", "parole", "survivor", "visa"];
  var FULL_HEALTH = ["citizen", "lpr5", "cuban_haitian", "cofa"];
  var HUMANITARIAN = ["refugee_asylee", "tps", "asylum_pending", "parole", "survivor"];
  // State food programs for immigrants SNAP leaves out (NILC table, Aug 18, 2026), as status -> value.
  var STATE_FOOD_BY_STATUS = {
    CA: { lpr: 1.0, refugee_asylee: 1.0, parole: 1.0, survivor: 1.0, cuban_haitian: 1.0 },
    ME: { lpr: 0.75, refugee_asylee: 0.75, asylum_pending: 0.75, tps: 0.75, parole: 0.75, survivor: 0.75 },
    WA: { lpr: 1.0, refugee_asylee: 1.0, parole: 1.0, tps: 1.0, survivor: 1.0, asylum_pending: 0.5 },
    IL: { survivor: 1.0, asylum_pending: 0.5 },
    NM: { refugee_asylee: 0.25, survivor: 0.25, parole: 0.25 }
  };

  function round1(x) { return Math.round(x * 10) / 10; }
  function round3(x) { return Math.round(x * 1000) / 1000; }
  function clamp(x, lo, hi) { return x < lo ? lo : (x > hi ? hi : x); }
  function linear(v, good, bad) { return clamp(100 * (v - bad) / (good - bad), 0, 100); }
  function has(arr, x) { return arr.indexOf(x) !== -1; }

  /** Rank-Order Centroid weights: w_k = (1/n) * sum_{i=k..n} 1/i. */
  function rocWeights(n) {
    var w = [];
    for (var k = 1; k <= n; k++) {
      var s = 0;
      for (var i = k; i <= n; i++) s += 1 / i;
      w.push(s / n);
    }
    return w;
  }

  function statusInfo(elig, status) {
    for (var i = 0; i < elig.statuses.length; i++) if (elig.statuses[i].id === status) return elig.statuses[i];
    return null;
  }

  function programRule(elig, programId, status) {
    for (var i = 0; i < elig.programs.length; i++) {
      var p = elig.programs[i];
      if (p.id !== programId) continue;
      var r = p.rule[status] || p.rule["*"];
      if (!r) return { value: "varies", note: "" };
      return { value: r[0], note: r[1] };
    }
    return { value: "varies", note: "" };
  }

  function safetyApplies(elig, profile) {
    var info = statusInfo(elig, profile.status);
    var risk = info ? info.risk : "unknown";
    if (risk === "high" || risk === "medium") return risk;
    if (profile.household && profile.household.mixed) return "medium";
    return null;
  }

  function foodAccess(elig, st, stCode, profile) {
    var s = profile.status, hh = profile.household || {}, sit = profile.situation || {};
    var snap = VALUE[programRule(elig, "snap", s).value];
    var why = "SNAP: " + programRule(elig, "snap", s).value;
    if (s === "lpr" && (sit.disability)) { snap = 1.0; why = "SNAP: yes (disability exemption from the 5-year wait)"; }
    else if (s === "lpr" && hh.kids) { snap = Math.max(snap, 0.75); why = "SNAP: children can get it now; adults wait 5 years"; }
    if (snap === 0 && hh.mixed && hh.kids) { snap = 0.5; why = "SNAP: U.S.-citizen children in the family can get it"; }
    var stateVal = 0, stateWhy = "";
    var table = STATE_FOOD_BY_STATUS[stCode];
    if (table && table[s] !== undefined) { stateVal = table[s]; stateWhy = st.state_food_immigrants ? st.state_food_immigrants.note : ""; }
    if (stCode === "MN" && (s === "lpr") && (profile.age_band === "50_61" || profile.age_band === "62_plus")) {
      stateVal = 1.0; stateWhy = st.state_food_immigrants ? st.state_food_immigrants.note : "";
    }
    if (stateVal > snap) return { value: stateVal, why: "State food program: " + stateWhy };
    return { value: snap, why: why };
  }

  function healthAccess(elig, st, profile) {
    var s = profile.status, hh = profile.household || {}, sit = profile.situation || {};
    var base = 0.25, baseWhy = "ER care, health centers and emergency Medicaid only";
    var childOrPreg = !!(hh.kids || hh.pregnant);
    if (has(FULL_HEALTH, s)) {
      if (st.medicaid_expansion) return { value: 1.0, why: "Medicaid expansion state: low-income adults qualify" };
      if (childOrPreg || sit.disability) return { value: 0.75, why: "No Medicaid expansion; kids, pregnancy or disability can still qualify" };
      return { value: 0.35, why: "No Medicaid expansion: most adults without kids fall in the coverage gap" };
    }
    if (s === "lpr") {
      if (childOrPreg) return { value: 0.75, why: "Many states cover lawfully residing kids and pregnant people now" };
      return { value: 0.5, why: "5-year Medicaid wait; Marketplace tax credits available" };
    }
    var adults = st.health_adults_all, kids = st.health_children_all;
    var adultVal = adults ? (adults.status === "open" ? 1.0 : (adults.status === "limited" ? 0.6 : base)) : base;
    var adultWhy = adults ? ("State program for adults: " + adults.status + ". " + adults.note) : baseWhy;
    if (has(HUMANITARIAN, s)) {
      if (hh.kids) {
        if (kids) return { value: 1.0, why: "State covers children regardless of status" };
        return { value: 0.6, why: "Many states cover lawfully residing children" };
      }
      if (hh.pregnant) return { value: 0.6, why: "Many states cover lawfully residing pregnant people" };
      if (adultVal > 0.35) return { value: adultVal, why: adultWhy };
      return { value: 0.35, why: "No Medicaid for adults since Oct 1, 2026; limited Marketplace help" };
    }
    // daca, visa, undocumented, unsure
    if (hh.kids && kids) return { value: 1.0, why: "State covers children regardless of status" };
    if (hh.pregnant) return { value: Math.max(0.5, adultVal), why: "Emergency Medicaid covers labor and delivery" };
    return { value: adultVal, why: adultWhy };
  }

  function idAccess(st, profile) {
    var s = profile.status;
    if (s === "asylum_pending") return { value: 0.75, why: "Most states license people with a pending case and work permit" };
    if (has(LAWFUL, s)) return { value: 1.0, why: "Can get a state ID or license with your documents" };
    if (st.drivers_license_all) return { value: 1.0, why: "State issues a " + st.drivers_license_all.form + " regardless of status" };
    return { value: 0.0, why: "State requires proof of lawful presence for a license" };
  }

  function accessComponent(elig, st, stCode, profile) {
    if (profile.status === "undisclosed") return { score: null, reason: "You chose not to say your status, so this part is not scored. Help that is open to everyone is listed below." };
    if (!profile.status) {
      return { score: null, reason: "Add your status (it stays on this phone) to see which programs you can use here." };
    }
    var order = (profile.situation && profile.situation.no_id) ? ["id", "food", "health"] : ["food", "health", "id"];
    var w = rocWeights(3);
    var parts = { food: foodAccess(elig, st, stCode, profile), health: healthAccess(elig, st, profile), id: idAccess(st, profile) };
    var total = 0;
    for (var i = 0; i < 3; i++) total += w[i] * parts[order[i]].value;
    return { score: round1(100 * total), reason: parts.food.why + "; " + parts.health.why + "; " + parts.id.why,
      parts: { food: round3(parts.food.value), health: round3(parts.health.value), id: round3(parts.id.value) } };
  }

  function components(elig, policy, stCode, profile, community) {
    var st = policy.states[stCode];
    var out = {};
    out.access = accessComponent(elig, st, stCode, profile);
    var ratio = st.housing_wage_2br / st.min_wage;
    out.affordability = { score: round1(linear(ratio, 1.5, 5.0)),
      reason: st.oor_hours_at_min_wage + " hours/week at the $" + st.min_wage.toFixed(2) + " minimum wage to afford a 2-bedroom ($" + st.housing_wage_2br.toFixed(2) + "/hr needed)" };
    out.shelter = { score: round1(linear(st.unsheltered_share, 0.05, 0.65)),
      reason: Math.round(100 * st.unsheltered_share) + "% of " + st.pit_total.toLocaleString("en-US") + " people without homes slept outside (Jan 2025 count)" };
    var risk = safetyApplies(elig, profile);
    if (risk) {
      out.safety = { score: round1(100 * (9 - st.enforcement_tier) / 8), reason: "State law: " + st.enforcement_label + " (tier " + st.enforcement_tier + " of 9)" };
    } else if (profile.status === "undisclosed" || !profile.status) {
      out.safety = { score: null, reason: "Shown only if your status could be affected by immigration enforcement." };
    }
    var camp = st.camping_law;
    if (camp && camp.status === "in_effect") out.criminalization = { score: 0, reason: "Statewide camping law: " + camp.note };
    else if (camp && camp.status === "enforcement_mandate") out.criminalization = { score: 25, reason: "State law pushes cities to enforce camping bans: " + camp.note };
    else if (camp && camp.status === "contested") out.criminalization = { score: 50, reason: "Statewide camping law in court: " + camp.note };
    else out.criminalization = { score: null, reason: "Not checked: we have not confirmed a statewide camping law either way." };
    var c = community && community[stCode];
    if (c && c.n > 0) out.community = { score: c.score, reason: c.n + " rating" + (c.n === 1 ? "" : "s") + " from people who have been here", n: c.n, freshness: c.freshness };
    else out.community = { score: null, reason: "No ratings yet. Be the first to rate a place here." };
    return out;
  }

  function defaultPriorities(elig, profile) {
    var order = ["access", "affordability", "shelter", "criminalization", "community"];
    var risk = safetyApplies(elig, profile);
    if (risk === "high") order.unshift("safety");
    else if (risk === "medium") order.splice(2, 0, "safety");
    if (profile.situation && profile.situation.tonight) {
      order.splice(order.indexOf("shelter"), 1);
      order.unshift("shelter");
    }
    return order;
  }

  function priorities(elig, profile, comps) {
    var def = defaultPriorities(elig, profile);
    var chosen = (profile.priorities || []).filter(function (k) { return has(def, k); });
    def.forEach(function (k) { if (!has(chosen, k)) chosen.push(k); });
    return chosen.filter(function (k) { return comps[k] !== undefined; });
  }

  function aggregate(order, weights, comps) {
    var num = 0, den = 0, conf = 0;
    for (var i = 0; i < order.length; i++) {
      var c = comps[order[i]];
      if (c.score === null || c.score === undefined) continue;
      num += weights[i] * c.score;
      den += weights[i];
      var f = order[i] === "community" ? (c.freshness || 0.5) : FRESHNESS[order[i]];
      conf += weights[i] * f;
    }
    return { score: den > 0 ? num / den : null, confidence: conf };
  }

  function fitScore(elig, policy, stCode, profile, community) {
    var comps = components(elig, policy, stCode, profile, community);
    var order = priorities(elig, profile, comps);
    var w = rocWeights(order.length);
    var agg = aggregate(order, w, comps);
    var rows = order.map(function (k, i) {
      return { id: k, weight: round3(w[i]), score: comps[k].score, reason: comps[k].reason, parts: comps[k].parts || null };
    });
    var conf = round3(agg.confidence);
    return { state: stCode, name: policy.states[stCode].name, score: agg.score === null ? null : round1(agg.score),
      confidence: conf, confidence_label: conf >= 0.7 ? "high" : (conf >= 0.45 ? "medium" : "low"), components: rows };
  }

  // ---- seeded randomness (identical in Python) ------------------------------------------------------
  function mulberry32(seed) {
    var a = seed >>> 0;
    return function () {
      a = (a + 0x6D2B79F5) >>> 0;
      var t = a;
      t = Math.imul(t ^ (t >>> 15), t | 1) >>> 0;
      t = (t ^ (t + (Math.imul(t ^ (t >>> 7), t | 61) >>> 0))) >>> 0;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }
  function normal(rand) {
    var u1 = rand(); if (u1 < 1e-12) u1 = 1e-12;
    var u2 = rand();
    return Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * u2);
  }
  function gamma(rand, alpha) {   // Marsaglia & Tsang (2000)
    if (alpha < 1) { var u = rand(); if (u < 1e-12) u = 1e-12; return gamma(rand, alpha + 1) * Math.pow(u, 1 / alpha); }
    var d = alpha - 1 / 3, c = 1 / Math.sqrt(9 * d);
    for (;;) {
      var x = normal(rand), v = 1 + c * x;
      if (v <= 0) continue;
      v = v * v * v;
      var u2 = rand(); if (u2 < 1e-12) u2 = 1e-12;
      if (Math.log(u2) < 0.5 * x * x + d - d * v + d * Math.log(v)) return d * v;
    }
  }

  /** Score and rank every state. With robustness, re-rank under 300 perturbed weightings. */
  function rankStates(elig, policy, profile, community, opts) {
    opts = opts || {};
    var codes = Object.keys(policy.states).sort();
    var results = codes.map(function (c) { return fitScore(elig, policy, c, profile, community); });
    var known = results.filter(function (r) { return r.score !== null; });
    known.sort(function (a, b) { return b.score - a.score || (a.state < b.state ? -1 : 1); });
    known.forEach(function (r, i) { r.rank = i + 1; });
    if (opts.robustness === false || known.length === 0) return results;
    var samples = opts.samples || 300, kappa = opts.kappa || 30, rand = mulberry32(opts.seed || 7);
    var order = known[0].components.map(function (c) { return c.id; });
    var base = rocWeights(order.length);
    var compsByState = {};
    known.forEach(function (r) { var m = {}; r.components.forEach(function (c) { m[c.id] = c; }); compsByState[r.state] = m; });
    var ranks = {}; known.forEach(function (r) { ranks[r.state] = []; });
    for (var s = 0; s < samples; s++) {
      var g = base.map(function (w) { return gamma(rand, Math.max(0.5, kappa * w)); });
      var tot = g.reduce(function (a, b) { return a + b; }, 0);
      var w = g.map(function (x) { return x / tot; });
      var scored = known.map(function (r) { return { st: r.state, v: aggregate(order, w, compsByState[r.state]).score }; });
      scored.sort(function (a, b) { return b.v - a.v || (a.st < b.st ? -1 : 1); });
      scored.forEach(function (x, i) { ranks[x.st].push(i + 1); });
    }
    known.forEach(function (r) {
      var rs = ranks[r.state].slice().sort(function (a, b) { return a - b; });
      r.rank_p10 = rs[Math.floor(0.1 * (rs.length - 1))];
      r.rank_p90 = rs[Math.floor(0.9 * (rs.length - 1))];
      r.p_top5 = round3(rs.filter(function (x) { return x <= 5; }).length / rs.length);
    });
    return results;
  }

  /** Community ratings: time-decayed Bayesian average (prior 3 of 5, weight m = 5). */
  function bayesScore(ratings, nowMs, opts) {
    opts = opts || {};
    var m = opts.m === undefined ? 5 : opts.m, prior = opts.prior === undefined ? 3 : opts.prior;
    var half = (opts.halfLifeDays || 90) * 86400000;
    var sw = 0, sx = 0, fresh = 0;
    ratings.forEach(function (r) {
      var age = Math.max(0, nowMs - r.t);
      var w = Math.pow(0.5, age / half);
      sw += w; sx += w * r.stars;
      fresh += w;
    });
    var avg = (sx + m * prior) / (sw + m);
    return { n: ratings.length, score: round1(100 * (avg - 1) / 4), effective_n: round3(sw),
      freshness: round3(Math.min(1, fresh / 10)) };
  }

  return { COMPONENTS: COMPONENTS, rocWeights: rocWeights, programRule: programRule, fitScore: fitScore,
    rankStates: rankStates, defaultPriorities: defaultPriorities, components: components, bayesScore: bayesScore,
    mulberry32: mulberry32, gamma: gamma, safetyApplies: safetyApplies };
});
