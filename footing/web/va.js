/* Virginia locality Fit Score and confidence. Runs on the phone; footing/va.py is the Python mirror and
 * tests/test_va.py proves both return identical results. Needs FootingFit (fit.js).
 *
 * State law still decides program access and immigration-enforcement risk; local data replaces the state
 * averages for rent, shelter beds, camping rules and street safety. Every answer carries a confidence score
 * that drops when the point is doubtful or the data is thin or coarse.
 */
(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory(require("./fit.js"));
  else root.FootingVA = factory(root.FootingFit);
})(typeof self !== "undefined" ? self : this, function (Fit) {
  "use strict";
  var VA_BBOX = [36.54, -83.68, 39.47, -75.24];
  var BOUNDARY_KM = 1.5, SNAP_KM = 2.0;
  var LABELS = { access: "Programs you can use", affordability: "Rent", shelter: "Shelter beds",
    safety: "Immigration enforcement", criminalization: "Camping rules", community: "Community ratings",
    crime: "Street safety" };
  var RULE_SCORE = { ban_citywide: 0, ban_partial: 35 };
  var RENT_GOOD = 1.0, RENT_BAD = 3.0;   // housing wage / minimum wage: 1x = one full-time job covers rent
  var FRESHNESS = { access: 0.9, affordability: 0.9, shelter: 0.7, safety: 0.9, criminalization: 0.6 };

  function round1(x) { return Math.round(x * 10) / 10; }
  function round3(x) { return Math.round(x * 1000) / 1000; }
  function clamp(x, lo, hi) { return x < lo ? lo : (x > hi ? hi : x); }
  function linear(v, good, bad) { return clamp(100 * (v - bad) / (good - bad), 0, 100); }
  function fixed(x, d) { var p = Math.pow(10, d); return (Math.round(x * p) / p).toFixed(d); }
  function commas(n) { return Math.round(n).toLocaleString("en-US"); }
  function numStr(x) { return String(Number(x)); }
  function decimals(x) { var s = numStr(x); return s.indexOf(".") >= 0 ? s.split(".")[1].length : 0; }
  function assign(a, b) { var o = {}, k; for (k in a) o[k] = a[k]; for (k in b) o[k] = b[k]; return o; }

  // ---- geometry ----------------------------------------------------------------------------------------------
  function inRing(lon, lat, ring) {
    var inside = false;
    for (var i = 0, j = ring.length - 1; i < ring.length; j = i++) {
      var xi = ring[i][0], yi = ring[i][1], xj = ring[j][0], yj = ring[j][1];
      if ((yi > lat) !== (yj > lat) && lon < (xj - xi) * (lat - yi) / (yj - yi) + xi) inside = !inside;
    }
    return inside;
  }
  function inShape(lon, lat, shape) {
    for (var p = 0; p < shape.length; p++) {
      var poly = shape[p];
      if (!poly.length || !inRing(lon, lat, poly[0])) continue;
      var hole = false;
      for (var h = 1; h < poly.length; h++) if (inRing(lon, lat, poly[h])) { hole = true; break; }
      if (!hole) return true;
    }
    return false;
  }
  function segKm(lat, lon, a, b) {
    var k = Math.cos(lat * Math.PI / 180) * 111.32;
    var px = lon * k, py = lat * 110.574;
    var ax = a[0] * k, ay = a[1] * 110.574, bx = b[0] * k, by = b[1] * 110.574;
    var dx = bx - ax, dy = by - ay, L = dx * dx + dy * dy;
    var t = L === 0 ? 0 : clamp(((px - ax) * dx + (py - ay) * dy) / L, 0, 1);
    var ex = ax + t * dx - px, ey = ay + t * dy - py;
    return Math.sqrt(ex * ex + ey * ey);
  }
  function edgeKm(lat, lon, shape) {
    var best = Infinity;
    shape.forEach(function (poly) {
      poly.forEach(function (ring) {
        for (var i = 0; i < ring.length - 1; i++) { var d = segKm(lat, lon, ring[i], ring[i + 1]); if (d < best) best = d; }
      });
    });
    return best;
  }
  function locate(va, lat, lon) {
    var keys = Object.keys(va.localities).sort();
    for (var i = 0; i < keys.length; i++) {
      var loc = va.localities[keys[i]];
      if (loc.shape.length && inShape(lon, lat, loc.shape)) return keys[i];
    }
    return null;
  }
  function tileOf(lat, lon) { return "t" + Math.floor(lat / 0.01) + "_" + Math.floor(lon / 0.01); }

  function checkPoint(va, lat, lon) {
    var issues = [];
    function add(code, text, factor) { issues.push({ code: code, text: text, factor: factor }); }
    function fail() { return { ok: false, fips: null, name: null, tile: null, validity: 0, boundary_km: null, issues: issues }; }
    lat = (lat === null || lat === undefined || lat === "") ? NaN : Number(lat);
    lon = (lon === null || lon === undefined || lon === "") ? NaN : Number(lon);
    if (!(isFinite(lat) && isFinite(lon) && lat >= -90 && lat <= 90 && lon >= -180 && lon <= 180)) {
      add("invalid", "These coordinates are not a real place (latitude must be -90 to 90, longitude -180 to 180).", 0);
      return fail();
    }
    var fips = locate(va, lat, lon), snapped = false;
    if (fips === null) {
      if (lon >= -90 && lon <= 90 && locate(va, lon, lat)) {
        add("swapped", "These look like latitude and longitude swapped. Did you mean " + numStr(lon) + ", " + numStr(lat) + "?", 0);
        return fail();
      }
      var inBox = lat >= VA_BBOX[0] && lat <= VA_BBOX[2] && lon >= VA_BBOX[1] && lon <= VA_BBOX[3];
      var near = null, nearKm = Infinity;
      if (inBox) {
        Object.keys(va.localities).sort().forEach(function (f) {
          var loc = va.localities[f];
          if (loc.shape.length) { var d = edgeKm(lat, lon, loc.shape); if (d < nearKm) { near = f; nearKm = d; } }
        });
      }
      if (near !== null && nearKm <= SNAP_KM) {
        fips = near; snapped = true;
        add("snapped", "This point is just outside the map outline (water or a border); counted as " +
          va.localities[near].name + ", " + fixed(nearKm, 1) + " km away.", 0.6);
      } else if (inBox) {
        add("no_locality", "This point is in Virginia's box but not inside any county or city (open water, or a neighboring state).", 0);
        return fail();
      } else {
        add("outside_va", "This point is outside Virginia. Local scores cover Virginia only; the state view still works.", 0);
        return fail();
      }
    }
    var loc = va.localities[fips];
    var edge = loc.shape.length ? edgeKm(lat, lon, loc.shape) : 0;
    if (Math.min(decimals(lat), decimals(lon)) <= 1) {
      add("coarse", "The coordinates are rounded (one decimal place is about 11 km), so the local numbers may be for the wrong place.", 0.6);
    }
    if (!snapped && edge < BOUNDARY_KM) {
      add("near_boundary", "About " + fixed(edge, 1) + " km from the " + loc.name + " line on a coarse map; the neighbor's numbers may apply.", 0.85);
    }
    var verts = 0;
    loc.shape.forEach(function (p) { p.forEach(function (r) { verts += r.length; }); });
    if (verts <= 6) add("small_shape", loc.name + " is drawn with only " + verts + " points at this map scale, so its edges are rough.", 0.8);
    var validity = 1;
    issues.forEach(function (i) { validity *= i.factor; });
    return { ok: true, fips: fips, name: loc.name, tile: tileOf(lat, lon), validity: round3(validity),
      boundary_km: isFinite(edge) ? Math.round(edge * 100) / 100 : null, issues: issues };
  }

  // ---- components --------------------------------------------------------------------------------------------
  function nb(va, tile, key) {
    var p = tile.slice(1).split("_"), i = parseInt(p[0], 10), j = parseInt(p[1], 10), s = 0;
    for (var di = -1; di <= 1; di++) for (var dj = -1; dj <= 1; dj++) {
      var t = va.tiles["t" + (i + di) + "_" + (j + dj)];
      if (t) s += t[key];
    }
    return s;
  }

  function crimeComponent(va, fips, tile) {
    var loc = va.localities[fips], cr = loc.crime, sc = va.scales, rate = cr.violent_per_100k, reason;
    if (tile && loc.incident_tiles) {
      var city = va.incident_cities[fips], v = nb(va, tile, "v"), e = nb(va, tile, "e");
      reason = commas(v) + " violent incident" + (v === 1 ? "" : "s") + " reported within about 1.5 km in the last 12 months (" +
        city.name + " police data); " + commas(e) + " trespass, loitering or disorderly calls nearby, which show where police make contact and are not counted as danger.";
      if (rate !== null) reason += " Citywide: " + fixed(rate, 1) + " violent crimes per 100,000 (FBI, 2025).";
      return { score: round1(linear(v, sc.tile_violent_3x3.good, sc.tile_violent_3x3.bad)), reason: reason, level: "block", spec: 1.0, fresh: 0.95 };
    }
    if (rate === null) return { score: null, reason: cr.note, level: "none", spec: 0, fresh: 0 };
    var n = cr.agencies.filter(function (a) { return a.months === 12; }).length, s = sc.violent_per_100k;
    reason = fixed(rate, 1) + " violent crimes per 100,000 people in 2025 (" + n + " police agenc" + (n === 1 ? "y" : "ies") +
      " reporting to the FBI). Virginia localities run from " + fixed(s.good, 1) + " to " + fixed(s.bad, 1) + " (10th to 90th percentile).";
    if (cr.note) reason += " " + cr.note;
    return { score: round1(linear(rate, s.good, s.bad)), reason: reason, level: "locality", spec: 0.75, fresh: 0.8 };
  }

  function localityComponents(elig, policy, va, fips, profile, community, tile) {
    var loc = va.localities[fips], base = Fit.components(elig, policy, "VA", profile, null), out = {};
    ["access", "safety"].forEach(function (k) {
      if (base[k] !== undefined) out[k] = assign(base[k], { level: "state law", spec: 1.0, fresh: FRESHNESS[k] });
    });
    var kids = !!(profile.household && profile.household.kids), br = kids ? "2" : "0";
    var rent = loc.rent, hw = rent.housing_wage[br], mw = va.min_wage;
    out.affordability = { score: round1(linear(hw / mw, RENT_GOOD, RENT_BAD)),
      reason: "Fair Market Rent for a " + (kids ? "2-bedroom" : "studio") + " here is $" + commas(rent.fmr[br]) + "/month: $" +
        fixed(hw, 2) + "/hr full-time to afford it, " + Math.round(40 * hw / mw) + " hours/week at the $" + fixed(mw, 2) +
        " minimum wage (HUD FY2026).", level: "locality", spec: 0.9, fresh: 0.9 };
    var coc = va.cocs[loc.coc], s = va.scales.beds_per_10k;
    out.shelter = { score: round1(linear(coc.beds_per_10k, s.good, s.bad)),
      reason: commas(coc.beds_year_round) + " year-round shelter beds in the " + coc.name + " (" + loc.coc + ") for " +
        commas(coc.residents_2023) + " residents: " + fixed(coc.beds_per_10k, 1) + " per 10,000 (" +
        commas(kids ? coc.beds_for_families : coc.beds_for_adults) + " for " + (kids ? "families with children" : "adults without children") +
        "; Jan 2025 count).", level: "region", spec: 0.7, fresh: 0.7 };
    out.crime = crimeComponent(va, fips, tile);
    var rule = loc.rules;
    if (rule && RULE_SCORE[rule.status] !== undefined) {
      out.criminalization = { score: RULE_SCORE[rule.status], reason: rule.place + ": " + rule.summary + (rule.penalty ? " " + rule.penalty + "." : ""),
        level: "locality", spec: 1.0, fresh: 0.8, source: rule.source_url };
    } else if (rule) {
      out.criminalization = { score: null, reason: rule.place + ": " + rule.summary, level: "locality", spec: 0, fresh: 0, source: rule.source_url };
    } else {
      out.criminalization = { score: null, reason: "Local camping rules not checked for " + loc.name + ". " + va.rules_note.text,
        level: "none", spec: 0, fresh: 0 };
    }
    var c = community && community[fips];
    if (c && c.n > 0) {
      out.community = { score: c.score, n: c.n, reason: c.n + " rating" + (c.n === 1 ? "" : "s") + " from people who have been here",
        level: "locality", spec: 1.0, fresh: c.freshness || 0.5 };
    } else {
      out.community = { score: null, reason: "No ratings yet. Be the first to rate a place here.", level: "none", spec: 0, fresh: 0 };
    }
    return out;
  }

  function localityPriorities(elig, profile, comps) {
    var order = Fit.defaultPriorities(elig, profile);
    order.splice(order.indexOf("shelter") + 1, 0, "crime");
    var chosen = (profile.priorities || []).filter(function (k) { return order.indexOf(k) >= 0; });
    order.forEach(function (k) { if (chosen.indexOf(k) < 0) chosen.push(k); });
    return chosen.filter(function (k) { return comps[k] !== undefined; });
  }

  function confidence(rows, point) {
    var den = 0, num = 0;
    rows.forEach(function (r) { den += r.weight; if (r.score !== null) num += r.weight * r.spec * r.fresh; });
    var quality = den ? num / den : 0, validity = point ? point.validity : 1;
    var value = Math.round(100 * validity * quality);
    var issues = (point ? point.issues : []).map(function (i) { return { code: i.code, text: i.text }; });
    rows.slice().sort(function (a, b) { return b.weight - a.weight; }).forEach(function (r) {
      if (r.score === null) issues.push({ code: "missing_" + r.id, text: LABELS[r.id] + ": no data, so it is left out of the score." });
      else if (r.spec < 0.8) {
        var where = r.level === "region" ? "for the whole region" : "for the whole county or city, not this block";
        issues.push({ code: "coarse_" + r.id, text: LABELS[r.id] + ": the number is " + where + "." });
      }
    });
    return { score: value, label: value >= 70 ? "high" : (value >= 45 ? "medium" : "low"), validity: round3(validity),
      data_quality: round3(quality), issues: issues };
  }

  function localityFit(elig, policy, va, fips, profile, community, point) {
    var tile = point ? point.tile : null;
    var comps = localityComponents(elig, policy, va, fips, profile, community, tile);
    var order = localityPriorities(elig, profile, comps), w = Fit.rocWeights(order.length);
    var num = 0, den = 0;
    var rows = order.map(function (k, i) {
      var c = comps[k];
      if (c.score !== null) { num += w[i] * c.score; den += w[i]; }
      return { id: k, label: LABELS[k], weight: round3(w[i]), score: c.score, reason: c.reason, level: c.level, spec: c.spec,
        fresh: c.fresh, source: c.source || null, parts: c.parts || null };
    });
    return { fips: fips, name: va.localities[fips].name, score: den ? round1(num / den) : null,
      confidence: confidence(rows, point || null), components: rows, point: point || null };
  }

  function fitPoint(elig, policy, va, lat, lon, profile, community) {
    var pt = checkPoint(va, lat, lon);
    if (!pt.ok) {
      return { fips: null, name: null, score: null,
        confidence: { score: 0, label: "low", validity: 0, data_quality: 0, issues: pt.issues.map(function (i) { return { code: i.code, text: i.text }; }) },
        components: [], point: pt };
    }
    return localityFit(elig, policy, va, pt.fips, profile, community, pt);
  }

  function rankLocalities(elig, policy, va, profile, community) {
    var out = Object.keys(va.localities).sort().map(function (f) { return localityFit(elig, policy, va, f, profile, community, null); });
    var known = out.filter(function (r) { return r.score !== null; });
    known.sort(function (a, b) { return b.score - a.score || (a.fips < b.fips ? -1 : 1); });
    known.forEach(function (r, i) { r.rank = i + 1; });
    return out;
  }

  function communityByLocality(va, heatTiles) {
    var groups = {}, order = [];
    heatTiles.forEach(function (t) {
      var f = locate(va, t.lat, t.lon);
      if (f) { if (!groups[f]) { groups[f] = []; order.push(f); } groups[f].push(t); }
    });
    var out = {};
    order.forEach(function (f) {
      var ts = groups[f], n = 0, eff = 0, sx = 0;
      ts.forEach(function (t) { var e = t.effective_n === undefined ? t.n : t.effective_n; n += t.n; eff += e; sx += t.score * e; });
      out[f] = { n: n, score: eff ? round1(sx / eff) : null, freshness: round3(Math.min(1, eff / 10)) };
    });
    return out;
  }

  return { checkPoint: checkPoint, locate: locate, localityFit: localityFit, fitPoint: fitPoint, rankLocalities: rankLocalities,
    communityByLocality: communityByLocality, confidence: confidence, LABELS: LABELS, _fixed: fixed };
});
