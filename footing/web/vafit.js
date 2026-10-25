/* Footing Virginia Fit: scores each of Virginia's 133 localities (95 counties + 38 independent cities) for one person.
 * Runs ON THE PHONE, like fit.js: the person's status, household and priorities never leave the device.
 * Mirrors footing/vafit.py line for line (tests/test_vafit.py runs both on the same inputs and requires equal output).
 *
 *   components (0-100, or null = Unknown and NOT counted)
 *     shelter    share of people outside + shelter beds per person, for the local Continuum of Care (HUD, Jan 2025);
 *                with kids it uses family beds per person in families
 *     rent       hours of minimum-wage work per week for HUD's fair market rent at the size you need (FY2026)
 *     services   full-service SNAP grocers per 10k people, hot-meal (Restaurant Meals) SNAP stores, help places
 *                mapped in OpenStreetMap per 10k, how many places there are to go at all (log scale), fare-free buses
 *     laws       this city's or county's rules on sleeping/camping outside (only rules we confirmed; else Unknown)
 *     safety     287(g) agreements with ICE that cover this place (only shown when the person's status is at risk)
 *     crime      violent crime reported to the FBI per 1,000 people, 2025 (OFF unless the person turns it on)
 *     community  ratings from people who have been here (time-decayed Bayesian average)
 *   weights      Rank-Order Centroid of the person's priority order; Unknown parts drop out and the rest renormalize
 *   confidence   sum of weight x freshness over known parts (crime freshness also scales with reporting coverage;
 *                shelter is 0.7 where the count covers only this place, 0.6 for 2-10 places, 0.5 for the Balance of State)
 *   small places per-capita counts are shrunk toward the Virginia rate as if 25,000 more people lived there
 */
(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory(require("./fit.js"));
  else root.FootingVaFit = factory(root.FootingFit);
})(typeof self !== "undefined" ? self : this, function (Fit) {
  "use strict";

  var COMPONENTS = ["shelter", "rent", "services", "laws", "safety", "crime", "community"];
  var FRESHNESS = { shelter: 0.7, rent: 0.95, services: 0.6, laws: 0.6, safety: 0.9, crime: 0.7 };
  var BEDROOM_WORD = ["studio", "1-bedroom", "2-bedroom", "3-bedroom", "4-bedroom"];
  var SERVICE_WEIGHTS = { grocery: 0.3, help: 0.2, choice: 0.2, transit: 0.2, meals: 0.1 };
  var HELP_KINDS = ["food_bank", "soup_kitchen", "shelter", "day_center", "clinic", "library", "toilets", "shower", "drinking_water", "laundry"];

  var SHRINK_POP = 25000;  // small places: per-capita rates are pulled toward the Virginia rate as if 25,000 more people lived there
  var BIG_COC = 10;        // a Continuum of Care covering more localities than this says little about any one town

  /** Statewide sums (summed in FIPS order so both engines get the same floats). */
  function stateTotals(va) {
    var t = { pop: 0, grocery: 0, help: 0, cocSize: {} };
    Object.keys(va.localities).sort().forEach(function (f) {
      var l = va.localities[f], osm = l.services.osm || {};
      t.pop += l.pop_2025; t.grocery += l.services.snap.full_grocery;
      HELP_KINDS.forEach(function (k) { t.help += osm[k] || 0; });
      t.cocSize[l.coc.code] = (t.cocSize[l.coc.code] || 0) + 1;
    });
    return t;
  }

  /** Per-10k rate with small-place shrinkage toward the state rate (empirical-Bayes style). */
  function shrunkRate(count, pop, stateCount, statePop) {
    return (count + stateCount / statePop * SHRINK_POP) / (pop + SHRINK_POP) * 10000;
  }

  function round1(x) { return Math.round(x * 10) / 10; }
  function round3(x) { return Math.round(x * 1000) / 1000; }
  function clamp(x, lo, hi) { return x < lo ? lo : (x > hi ? hi : x); }
  function linear(v, good, bad) { return clamp(100 * (v - bad) / (good - bad), 0, 100); }
  function plural(n, one, many) { return n + " " + (n === 1 ? one : many); }
  function num(x) { return String(x); }                       // integers print without ".0" in both engines
  function money(x) { return "$" + Math.round(x).toLocaleString("en-US"); }
  function commas(n) { return Math.round(n).toLocaleString("en-US"); }

  /** Bedrooms the person needs: their own choice (0-4), else 2 with kids, else 1. */
  function bedrooms(profile) {
    var hh = profile.household || {};
    var b = hh.bedrooms;
    if (typeof b === "number" && b >= 0 && b <= 4 && Math.floor(b) === b) return b;
    return hh.kids ? 2 : 1;
  }

  function rentComponent(loc, wage, profile) {
    var b = bedrooms(profile), rent = loc.fmr.by_bedrooms[b];
    var hours = rent * 12 / (0.30 * 52 * wage);
    return { score: round1(linear(hours, 40, 140)),
      reason: money(rent) + "/month for a " + BEDROOM_WORD[b] + " (HUD fair market rent, FY2026, " + loc.fmr.area + "). At Virginia's $" +
        wage.toFixed(2) + " minimum wage that takes " + Math.round(hours) + " hours of work a week to keep rent at 30% of pay.",
      parts: { rent: rent, bedrooms: b, hours: round1(hours) } };
  }

  function shelterComponent(loc, profile, tot) {
    var c = loc.coc, size = tot.cocSize[c.code], kids = !!(profile.household || {}).kids;
    var share = c.unsheltered / c.pit_total;
    var parts = [round1(linear(share, 0.05, 0.65))];
    var beds = kids ? c.beds_family : c.beds_year_round, people = kids ? c.people_in_families : c.pit_total;
    var bedLine;
    if (people > 0) {
      parts.push(round1(linear(beds / people, 1.0, 0.3)));
      bedLine = commas(beds) + " year-round " + (kids ? "family " : "") + "shelter beds for " + commas(people) + (kids ? " people in families" : " people");
    } else {
      bedLine = commas(beds) + " year-round " + (kids ? "family " : "") + "shelter beds; no " + (kids ? "families were" : "one was") + " counted without a home";
    }
    var sum = 0; parts.forEach(function (p) { sum += p; });
    return { score: round1(sum / parts.length),
      reason: c.name + " (Jan 2025 count): " + Math.round(100 * share) + "% of " + commas(c.pit_total) + " people without homes slept outside; " +
        bedLine + "." + (c.unsheltered_carried_from_2024 ? " The outside count is from Jan 2024 (this area counted shelters only in 2025)." : "") +
        (size > BIG_COC ? " This count covers " + size + " cities and counties together, so it says little about this one." :
          (size > 1 ? " This count covers " + size + " cities and counties; the beds may be in a neighboring one." : "")),
      precision: size > BIG_COC ? 0.5 / 0.7 : (size > 1 ? 0.6 / 0.7 : 1),
      parts: { outside_share: round3(share), beds: beds, people: people } };
  }

  function servicesComponent(loc, tot) {
    var s = loc.services, pop = loc.pop_2025, parts = {}, why = [];
    var groc = s.snap.full_grocery / pop * 10000;
    parts.grocery = round1(linear(shrunkRate(s.snap.full_grocery, pop, tot.grocery, tot.pop), 3.0, 0.5));
    why.push(plural(s.snap.full_grocery, "full grocery store takes", "full grocery stores take") + " EBT (" + num(round1(groc)) + " per 10,000 people)");
    var rm = s.snap.restaurant_meals;
    parts.meals = rm > 0 ? 100 : 0;
    why.push(rm > 0 ? plural(rm, "restaurant takes", "restaurants take") + " SNAP for hot meals" : "no restaurants take SNAP for hot meals");
    var osm = s.osm || {}, help = 0;
    HELP_KINDS.forEach(function (k) { help += osm[k] || 0; });
    if (help > 0) {
      parts.help = round1(linear(shrunkRate(help, pop, tot.help, tot.pop), 8, 0.5));
      why.push(plural(help, "help place", "help places") + " mapped (food, clinics, restrooms, libraries, laundry...)");
    } else {
      why.push("no help places mapped in OpenStreetMap (that usually means not mapped, so it is not counted)");
    }
    var options = s.snap.full_grocery + rm + help;
    parts.choice = round1(linear(Math.log10(options + 1), Math.log10(151), Math.log10(4)));
    if (s.fare_free_transit) { parts.transit = 100; why.push("free buses: " + s.fare_free_transit.system); }
    var num_ = 0, den = 0;
    ["grocery", "help", "choice", "transit", "meals"].forEach(function (k) {
      if (parts[k] !== undefined) { num_ += SERVICE_WEIGHTS[k] * parts[k]; den += SERVICE_WEIGHTS[k]; }
    });
    var small = pop < SHRINK_POP ? " With " + commas(pop) + " people, these counts are pulled toward the Virginia average so one store does not swing the score." : "";
    return { score: round1(num_ / den), reason: why.join("; ") + "." + small, parts: parts };
  }

  function lawsComponent(loc, state) {
    var r = loc.local_rule;
    if (r && r.score !== null && r.score !== undefined) return { score: r.score, reason: r.note, source: r.source };
    if (r) return { score: null, reason: r.note + " Not scored: " + (r.status === "proposed" ? "not adopted." : "not an ordinance."), source: r.source };
    return { score: null, reason: state.camping_law.note + " We have not checked " + loc.name + "'s own code yet, so this part is not counted." };
  }

  function safetyComponent(loc, state) {
    var g = loc.enforcement_287g || [];
    var tfm = g.filter(function (x) { return x.model === "Task Force Model"; });
    var stateNote = " " + state.state_287g.note;
    if (tfm.length) return { score: 10, reason: tfm[0].agency + " has a 287(g) task force agreement with ICE (signed " + tfm[0].signed +
      "): local officers can question and arrest people about immigration status during regular work." + stateNote };
    if (g.length) return { score: 40, reason: g[0].agency + " has a 287(g) " + g[0].model.toLowerCase() + " agreement with ICE (signed " + g[0].signed +
      "): people booked into jail can be held for ICE." + stateNote };
    return { score: 80, reason: "No local 287(g) agreement with ICE is listed for " + loc.name + " (ICE list, Oct 2026). Federal agents can still act anywhere." + stateNote };
  }

  function tileOf(lat, lon) {
    return "t" + Math.floor(lat * 100) + "_" + Math.floor(lon * 100);
  }

  // Sum one incident class over the 3x3 tiles around `tile`, about 3 km across.
  function neighbourhood(va, tile, key) {
    var parts = tile.slice(1).split("_");
    var i = parseInt(parts[0], 10), j = parseInt(parts[1], 10), total = 0;
    for (var di = -1; di <= 1; di++) {
      for (var dj = -1; dj <= 1; dj++) {
        var t = va.incident_tiles["t" + (i + di) + "_" + (j + dj)];
        if (t) total += t[key];
      }
    }
    return total;
  }

  /* Reported crime, as local as the data allows. Norfolk and Charlottesville publish incident-level
   * reports, so a point in either is scored on the violent incidents in the 3x3 tiles around it over 12
   * months; everywhere else it is the FBI's yearly figure for the whole city or county.
   * Trespass, loitering and drunkenness calls are counted separately and never as danger: they show where
   * police make contact, which is where unhoused people already are. */
  function crimeComponent(va, loc, fips, tile) {
    var c = loc.crime;
    if (tile && va.incident_cities && va.incident_cities[fips] && va.incident_tiles[tile]) {
      var city = va.incident_cities[fips], sc = va.incident_scale;
      var v = neighbourhood(va, tile, "v"), e = neighbourhood(va, tile, "e");
      var reason = commas(v) + " violent incident" + (v === 1 ? "" : "s") + " reported within about 1.5 km in the " +
        "last 12 months (" + city.name + " police data); " + commas(e) + " trespass, loitering or disorderly calls " +
        "nearby, which show where police make contact and are not counted as danger.";
      if (c && c.violent_per_1k !== null && c.violent_per_1k !== undefined) {
        reason += " Citywide: " + num(c.violent_per_1k) + " violent crimes per 1,000 people (FBI, 2025).";
      }
      return { score: round1(linear(v, sc.good, sc.bad)), coverage: 1.0, level: "block", freshness: 0.95, reason: reason };
    }
    if (!c || c.violent_per_1k === null || c.violent_per_1k === undefined)
      return { score: null, coverage: 0, level: "none", reason: "Not counted: " + (c && c.unknown_reason ? c.unknown_reason : "no FBI data for this place.") };
    return { score: round1(linear(c.violent_per_1k, 1.0, 8.0)), coverage: c.coverage === null ? 0 : c.coverage,
      level: "locality",
      reason: num(c.violent_per_1k) + " violent crimes reported to the FBI per 1,000 people in 2025 (" + commas(c.violent_2025) +
        " reports). Reports reflect policing as well as danger; people without homes are more often victims than offenders." };
  }

  function components(va, fips, profile, community, tile) {
    var loc = va.localities[fips], state = va.state, out = {}, tot = stateTotals(va);
    out.shelter = shelterComponent(loc, profile, tot);
    out.rent = rentComponent(loc, state.min_wage, profile);
    out.services = servicesComponent(loc, tot);
    out.laws = lawsComponent(loc, state);
    if (Fit.safetyApplies(profile._elig, profile)) out.safety = safetyComponent(loc, state);
    if (profile.show_crime) out.crime = crimeComponent(va, loc, fips, tile);
    var c = community && community[fips];
    if (c && c.n > 0) out.community = { score: c.score, n: c.n, freshness: c.freshness, reason: c.n + " rating" + (c.n === 1 ? "" : "s") + " from people who have been here" };
    else out.community = { score: null, reason: "No ratings yet. Be the first to rate a place here." };
    return out;
  }

  function defaultPriorities(elig, profile) {
    var order = ["shelter", "rent", "services", "laws", "community"];
    var risk = Fit.safetyApplies(elig, profile);
    if (risk === "high") order.unshift("safety");
    else if (risk === "medium") order.splice(2, 0, "safety");
    if (profile.situation && profile.situation.tonight && order[0] !== "shelter") {
      order.splice(order.indexOf("shelter"), 1); order.unshift("shelter");
    }
    if (profile.show_crime) order.push("crime");
    return order;
  }

  function priorities(elig, profile, comps) {
    var def = defaultPriorities(elig, profile);
    var chosen = (profile.priorities || []).filter(function (k) { return def.indexOf(k) !== -1; });
    def.forEach(function (k) { if (chosen.indexOf(k) === -1) chosen.push(k); });
    return chosen.filter(function (k) { return comps[k] !== undefined; });
  }

  function freshness(k, c) {
    // block-level crime carries its own; it is fresher than a yearly total
    if (c.freshness !== undefined && c.freshness !== null && k !== "community") return c.freshness;
    if (k === "community") return c.freshness || 0.5;
    if (k === "crime") return FRESHNESS.crime * (c.coverage || 0);
    if (k === "shelter") return FRESHNESS.shelter * (c.precision === undefined ? 1 : c.precision);
    return FRESHNESS[k];
  }

  function aggregate(order, weights, comps) {
    var num_ = 0, den = 0, conf = 0;
    for (var i = 0; i < order.length; i++) {
      var c = comps[order[i]];
      if (c.score === null || c.score === undefined) continue;
      num_ += weights[i] * c.score; den += weights[i];
      conf += weights[i] * freshness(order[i], c);
    }
    return { score: den > 0 ? num_ / den : null, confidence: conf };
  }

  function fitScore(elig, va, fips, profile, community, tile) {
    var p = withElig(profile, elig);
    var comps = components(va, fips, p, community, tile);
    var order = priorities(elig, p, comps);
    var w = Fit.rocWeights(order.length);
    var agg = aggregate(order, w, comps);
    var known = 0; order.forEach(function (k, i) { if (comps[k].score !== null && comps[k].score !== undefined) known += w[i]; });
    var rows = order.map(function (k, i) {
      var c = comps[k], has = c.score !== null && c.score !== undefined;
      return { id: k, weight: round3(w[i]), share: has && known > 0 ? round3(w[i] / known) : 0,
        contribution: has && known > 0 ? round1(w[i] / known * c.score) : 0, score: has ? c.score : null,
        reason: c.reason, parts: c.parts || null, source: c.source || null };
    });
    var conf = round3(agg.confidence);
    return { fips: fips, name: va.localities[fips].name, score: agg.score === null ? null : round1(agg.score), confidence: conf,
      confidence_label: conf >= 0.7 ? "high" : (conf >= 0.45 ? "medium" : "low"), components: rows };
  }

  function withElig(profile, elig) {
    var p = {}; Object.keys(profile || {}).forEach(function (k) { p[k] = profile[k]; });
    p._elig = elig;
    return p;
  }

  /** Score and rank all localities; with robustness, re-rank under perturbed weights (same method as fit.js). */
  function rankLocalities(elig, va, profile, community, opts) {
    opts = opts || {};
    var codes = Object.keys(va.localities).sort();
    var results = codes.map(function (f) { return fitScore(elig, va, f, profile, community); });
    var known = results.filter(function (r) { return r.score !== null; });
    known.sort(function (a, b) { return b.score - a.score || (a.fips < b.fips ? -1 : 1); });
    known.forEach(function (r, i) { r.rank = i + 1; });
    if (opts.robustness === false || known.length === 0) return results;
    var samples = opts.samples || 200, kappa = opts.kappa || 30, rand = Fit.mulberry32(opts.seed || 11);
    var order = known[0].components.map(function (c) { return c.id; });
    var base = Fit.rocWeights(order.length);
    var compsBy = {};
    known.forEach(function (r) { var m = {}; r.components.forEach(function (c) { m[c.id] = c; }); compsBy[r.fips] = m; });
    var ranks = {}; known.forEach(function (r) { ranks[r.fips] = []; });
    for (var s = 0; s < samples; s++) {
      var g = base.map(function (w) { return Fit.gamma(rand, Math.max(0.5, kappa * w)); });
      var tot = g.reduce(function (a, b) { return a + b; }, 0);
      var w = g.map(function (x) { return x / tot; });
      var scored = known.map(function (r) { return { f: r.fips, v: aggregate(order, w, compsBy[r.fips]).score }; });
      scored.sort(function (a, b) { return b.v - a.v || (a.f < b.f ? -1 : 1); });
      scored.forEach(function (x, i) { ranks[x.f].push(i + 1); });
    }
    known.forEach(function (r) {
      var rs = ranks[r.fips].slice().sort(function (a, b) { return a - b; });
      r.rank_p10 = rs[Math.floor(0.1 * (rs.length - 1))];
      r.rank_p90 = rs[Math.floor(0.9 * (rs.length - 1))];
    });
    return results;
  }

  return { COMPONENTS: COMPONENTS, bedrooms: bedrooms, components: function (va, f, p, c, elig, tile) { return components(va, f, withElig(p, elig), c, tile); },
    tileOf: tileOf,
    defaultPriorities: defaultPriorities, fitScore: fitScore, rankLocalities: rankLocalities };
});
