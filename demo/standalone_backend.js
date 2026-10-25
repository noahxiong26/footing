/* Standalone host for the Footing globe. Same engine as the app (fit.js, globe.js); the server pieces are
   replaced: policy data ships with the page, community ratings live in this page's shared store. */
(function () {
  "use strict";
  var TAGS = ["shelter_full", "shelter_had_beds", "police_moved_people", "welcoming_immigrants", "spanish_spoken",
    "pets_ok", "quiet_place_to_rest", "outlets_wifi", "clean_restrooms", "free_meals_nearby"];
  var TILE = 0.01;                        // same ~1 km tile as footing/geo.py
  var rows = [], db = null, dbState = "connecting";
  function json(u) { return fetch(u).then(function (r) { if (!r.ok) throw new Error(u + " " + r.status); return r.json(); }); }
  function get(k, d) { try { var v = localStorage.getItem(k); return v ? JSON.parse(v) : d; } catch (e) { return d; } }
  function put(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) { /* private window: fine */ } }

  function inRing(x, y, ring) {
    var inside = false;
    for (var i = 0, j = ring.length - 1; i < ring.length; j = i++) {
      var xi = ring[i][0], yi = ring[i][1], xj = ring[j][0], yj = ring[j][1];
      if ((yi > y) !== (yj > y) && x < (xj - xi) * (y - yi) / (yj - yi) + xi) inside = !inside;
    }
    return inside;
  }
  function inPolygon(x, y, poly) {
    if (!inRing(x, y, poly[0])) return false;
    for (var h = 1; h < poly.length; h++) if (inRing(x, y, poly[h])) return false;
    return true;
  }
  function stateAt(lat, lon) {
    var geo = window.FootingGlobe && FootingGlobe._state.statesGeo;
    if (!geo) return null;
    for (var i = 0; i < geo.features.length; i++) {
      var g = geo.features[i].geometry;
      var polys = g.type === "Polygon" ? [g.coordinates] : g.coordinates;
      for (var p = 0; p < polys.length; p++) if (inPolygon(lon, lat, polys[p])) return geo.features[i].properties.code;
    }
    return null;
  }

  function summarize(list, now) {
    var Fit = window.FootingFit;
    var out = Fit.bayesScore(list.map(function (r) { return { t: r.hour_ms, stars: r.overall }; }), now);
    var tags = {};
    list.forEach(function (r) { (r.tags || []).forEach(function (t) { tags[t] = (tags[t] || 0) + 1; }); });
    out.tags = tags;
    return out;
  }
  function heat() {
    var now = Date.now(), byTile = {}, byState = {}, byFips = {};
    rows.forEach(function (r) {
      if (!r || typeof r.overall !== "number" || !r.state) return;
      (byTile[r.tile] = byTile[r.tile] || []).push(r);
      (byState[r.state] = byState[r.state] || []).push(r);
      if (r.fips) (byFips[r.fips] = byFips[r.fips] || []).push(r);
    });
    var localities = {};
    Object.keys(byFips).forEach(function (k) { localities[k] = summarize(byFips[k], now); });
    // Same rule as the server: a tile is only shown once 3 or more ratings are in it.
    var tiles = Object.keys(byTile).filter(function (k) { return byTile[k].length >= 3; }).sort().map(function (k) {
      var s = summarize(byTile[k], now); s.tile = k; s.lat = byTile[k][0].lat; s.lon = byTile[k][0].lon; s.state = byTile[k][0].state; return s;
    });
    var states = {};
    Object.keys(byState).forEach(function (k) { states[k] = summarize(byState[k], now); });
    return Promise.resolve({ tiles: tiles, states: states, localities: localities, total: rows.length,
      method: "time-decayed Bayesian average, prior 3/5 with m=5, half-life 90 days" });
  }

  function rate(body) {
    var lat = +body.lat, lon = +body.lon;
    var i = Math.floor(lat / TILE), j = Math.floor(lon / TILE);
    var clat = Math.round((i + 0.5) * TILE * 1e4) / 1e4, clon = Math.round((j + 0.5) * TILE * 1e4) / 1e4;
    if (!isFinite(lat) || !isFinite(lon)) return Promise.reject(new Error("That location is not a real number."));
    var fips = window.FootingGlobe && FootingGlobe.localityAt(lat, lon);
    if (!fips) return Promise.reject(new Error("Footing covers Virginia only for now."));
    var state = "VA";
    var tile = "t" + i + "_" + j, now = Date.now(), hour = Math.floor(now / 3600000) * 3600000;
    var mine = get("footing.demo.rated", []).filter(function (x) { return now - x.t < 86400000; });
    if (mine.length >= 20) return Promise.reject(new Error("Daily rating limit reached on this device."));
    if (mine.some(function (x) { return x.tile === tile; })) return Promise.reject(new Error("You already rated this place today."));
    // Exactly these fields are stored. No profile, no status, no device id, no text.
    var doc = { tile: tile, lat: clat, lon: clon, state: state, fips: fips, hour_ms: hour, overall: body.overall,
      safe: body.safe || null, respect: body.respect || null, help: body.help || null,
      tags: (body.tags || []).filter(function (t) { return TAGS.indexOf(t) !== -1; }).sort() };
    var done = function (shared) {
      mine.push({ tile: tile, t: now }); put("footing.demo.rated", mine);
      if (!shared) { rows.push(doc); }
      return { ok: true, tile: tile, state: state, fips: fips, shared: shared };
    };
    if (!db) return Promise.resolve(done(false));
    return db.collection("ratings").add(doc).then(function () { return done(true); }, function (e) {
      if (e && e.code === "invalid_argument") dbState = "readonly";
      return done(false);
    });
  }

  window.FootingBackend = {
    standalone: true,
    noImagery: true,
    dataBase: "data/",
    policy: function () { return json("data/policy.json"); },
    va: function () { return json("data/va.json"); },
    towns: function () { return json("data/towns.json"); },
    receipt: function () { return json("data/receipt-christiansburg.json"); },
    heat: heat,
    rate: rate,
    hide: function () {
      try { sessionStorage.clear(); } catch (e) { /* fine */ }
      document.getElementById("globe-root").remove();
      document.getElementById("cover").hidden = false;
    },
  };

  if (window.claude && window.claude.use) {
    window.claude.use("db").then(function (d) {
      if (!d) { dbState = "off"; return; }
      db = d; dbState = "on";
      d.collection("ratings").limit(1000).onSnapshot(function (snap) {
        rows = snap.docs.map(function (x) { return x.data(); });
        if (window.FootingGlobe) FootingGlobe.refreshHeat();
      }, function () { dbState = "off"; });
    });
  }
})();
