/* Footing globe: from space down to a Virginia city or county.
 *
 * Virginia first (session 4): each of Virginia's 133 cities and counties is colored by a Fit Score computed ON THIS
 * PHONE (vafit.js) from public data shipped with the app. "All states (beta)" keeps the earlier state-level view
 * (fit.js). The person's status, household and priorities stay in localStorage and are never sent anywhere; the only
 * thing this screen sends is a community rating (stars + fixed tags + a ~1 km tile) when the person chooses to rate.
 *
 * Works offline: shapes are bundled (Census TIGER for Virginia, us-atlas / world-atlas). When online, Sentinel-2
 * cloudless imagery (EOX) and CARTO labels fade in as you zoom toward the ground.
 */
(function () {
  "use strict";
  var Fit = window.FootingFit, VaFit = window.FootingVaFit, I = window.FootingI18n, VaPoint = window.FootingVaPoint;
  var API = "api";
  // Optional host adapter (the standalone demo page sets one; the app uses the Footing API).
  // {policy(), va(), heat(), rate(body), towns(), receipt(town), hide(), dataBase, standalone, noImagery}
  var B = window.FootingBackend || {};
  var RAMP = ["#1b2440", "#2d4a6b", "#3f7c85", "#9cb07a", "#f2c14e", "#fff1c9"];
  var LAYERS_US = ["fit", "community", "shelter", "affordability", "safety"];
  var IMAGERY = "https://tiles.maps.eox.at/wmts/1.0.0/s2cloudless-2020_3857/default/g/{z}/{y}/{x}.jpg";
  var LABELS = ["a", "b", "c", "d"].map(function (s) { return "https://" + s + ".basemaps.cartocdn.com/dark_only_labels/{z}/{x}/{y}.png"; });
  var US_BOUNDS = [[-124.8, 24.4], [-66.9, 49.4]];   // contiguous U.S.
  var VA_BOUNDS = [[-83.68, 36.54], [-75.24, 39.47]];
  var KINDS = { snap_retailer: "#f2c14e", library: "#8fd6a8", clinic: "#ff9e8a", health_center: "#ff9e8a", pharmacy: "#ff9e8a",
    post_office: "#a7b1c6", toilets: "#7fc6e8", drinking_water: "#7fc6e8", food_bank: "#f2c14e", soup_kitchen: "#f2c14e",
    shelter: "#fff1c9", day_center: "#fff1c9", laundry: "#a7b1c6", employment_agency: "#a7b1c6", school: "#9cb07a" };
  // Which published sources stand behind each Virginia component (keys into va_localities.json "sources").
  var COMP_SOURCES = { shelter: ["hud_pit", "hud_hic", "hud_coc_areas"], rent: ["hud_fmr"], services: ["usda_snap", "osm", "apta_fare_free"],
    laws: ["hb1394_2026"], safety: ["ice_287g", "va_ed1_2026"], crime: ["fbi_cde"], community: [] };

  var store = {
    get: function (k, d) { try { var v = localStorage.getItem(k); return v ? JSON.parse(v) : d; } catch (e) { return d; } },
    set: function (k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) { /* private mode: fine */ } },
  };
  var reduced = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function guessLang() {
    var n = (navigator.language || "en").slice(0, 2);
    return (I.LANGS || ["en", "es"]).indexOf(n) !== -1 ? n : "en";
  }

  var S = {
    lang: store.get("footing.lang", guessLang()),
    profile: store.get("footing.globe.profile", null),
    scope: store.get("footing.globe.scope", "va"),
    view: "intro", layer: "fit", selected: null, selectedPoint: null, prevView: "top",
    policy: null, elig: null, va: null, community: {}, heat: null, ranked: [], byCode: {}, vaRanked: [], byFips: {},
    map: null, mapOk: false, statesGeo: null, vaGeo: null, recorded: [], ratingPoint: null, rating: { tags: [] },
    lit: 999, spinning: false, markers: [], ratingMarker: null, receiptTile: null, placePopup: null,
  };
  if ((I.LANGS || ["en", "es"]).indexOf(S.lang) === -1) S.lang = "en";
  function t(k, v) { return I.t(S.lang, k, v); }
  function esc(s) {
    return String(s === null || s === undefined ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  function $(sel) { return document.querySelector(sel); }
  function hexToRgb(h) { return [parseInt(h.slice(1, 3), 16), parseInt(h.slice(3, 5), 16), parseInt(h.slice(5, 7), 16)]; }
  function rampColor(v) {
    if (v === null || v === undefined) return null;
    var x = Math.max(0, Math.min(100, v)) / 20, i = Math.min(4, Math.floor(x)), f = x - i;
    var a = hexToRgb(RAMP[i]), b = hexToRgb(RAMP[i + 1]);
    return "rgb(" + a.map(function (c, k) { return Math.round(c + (b[k] - c) * f); }).join(",") + ")";
  }
  function inkOn(v) { return v !== null && v !== undefined && v < 45 ? "#e8ecf4" : "#10131c"; }
  function fillExpr() {
    return ["interpolate", ["linear"], ["get", "v"], 0, RAMP[0], 20, RAMP[1], 40, RAMP[2], 60, RAMP[3], 80, RAMP[4], 100, RAMP[5]];
  }
  function defaultProfile() {
    return { status: "undisclosed", household: {}, situation: {}, age_band: null, priorities: [] };
  }
  function num(n) {
    try { return Number(n).toLocaleString(S.lang === "en" ? "en-US" : S.lang); } catch (e) { return String(n); }
  }
  function money(n) { return "$" + num(Math.round(n)); }
  function isVa() { return S.scope === "va"; }
  function statusLabel(s) {
    if (S.lang === "en") return s.label;
    if (S.lang === "es") return s.label_es || s.label;
    var k = "st_" + s.id, v = t(k);
    return v === k ? s.label : v;
  }
  function programLabel(g) {
    if (S.lang === "en") return g.label;
    if (S.lang === "es") return g.label_es || g.label;
    var k = "p_" + g.id, v = t(k);
    return v === k ? g.label : v;
  }

  // ---------------- data ----------------
  function getJSON(url) {
    return fetch(url).then(function (r) { if (!r.ok) throw new Error(url + " " + r.status); return r.json(); });
  }
  function loadHeat() {
    return (B.heat ? B.heat() : getJSON(API + "/ratings/heat")).then(function (h) { S.heat = h; })
      .catch(function () { S.heat = null; });
  }
  function profileFor(scope) {
    var p = JSON.parse(JSON.stringify(S.profile || defaultProfile()));
    if (scope === "us") p.priorities = p.priorities_us || [];
    return p;
  }

  function compute() {
    var h = S.heat || {};
    if (isVa()) {
      S.vaRanked = VaFit.rankLocalities(S.elig, S.va, profileFor("va"), h.localities || {}, { samples: 200 });
      S.byFips = {};
      S.vaRanked.forEach(function (r) { S.byFips[r.fips] = r; });
    } else {
      S.ranked = Fit.rankStates(S.elig, S.policy, profileFor("us"), h.states || {}, { samples: 200 });
      S.byCode = {};
      S.ranked.forEach(function (r) { S.byCode[r.state] = r; });
    }
    paint();
  }

  function layers() {
    if (!isVa()) return LAYERS_US;
    var out = ["fit", "shelter", "rent", "services", "laws", "safety", "community"];
    if ((S.profile || {}).show_crime) out.push("crime");
    return out;
  }

  /** What the map shows for one Virginia locality under the chosen layer (null = no data, hatched). */
  function vaLayerValue(r) {
    if (!r) return null;
    if (S.layer === "fit") return r.score;
    var c = comp(r, S.layer);
    if (c) return c.score;
    var loc = S.va.localities[r.fips];
    if (S.layer === "safety") {     // not part of this person's score, but they asked to see it on the map
      var g = loc.enforcement_287g || [];
      return g.some(function (x) { return x.model === "Task Force Model"; }) ? 10 : (g.length ? 40 : 80);
    }
    return null;
  }
  function comp(r, id) { for (var i = 0; i < r.components.length; i++) if (r.components[i].id === id) return r.components[i]; return null; }

  function usLayerValue(r) {
    if (!r) return null;
    if (S.layer === "fit") return r.score;
    var c = comp(r, S.layer);
    if (S.layer === "safety" && !c) {
      var st = S.policy.states[r.state];
      return Math.round(1000 * (9 - st.enforcement_tier) / 8) / 10;
    }
    return c ? c.score : null;
  }

  function paint() {
    if (S.statesGeo) {
      S.statesGeo.features.forEach(function (f) {
        var r = S.byCode[f.properties.code], v = isVa() ? null : usLayerValue(r);
        var lit = r && r.rank ? r.rank <= S.lit : true;
        f.properties.v = v === null ? -1 : (lit ? v : 0);
        f.properties.known = v !== null;
      });
    }
    if (S.vaGeo) {
      S.vaGeo.features.forEach(function (f) {
        var r = S.byFips[f.id], v = vaLayerValue(r);
        var lit = r && r.rank ? r.rank <= S.lit : true;
        f.properties.v = v === null ? -1 : (lit ? v : 0);
        f.properties.known = v !== null;
      });
    }
    if (!S.mapOk) return;
    S.map.getSource("states").setData(S.statesGeo);
    S.map.getSource("va").setData(S.vaGeo);
    var va = isVa();
    ["states-known", "states-unknown"].forEach(function (id) { S.map.setLayoutProperty(id, "visibility", va ? "none" : "visible"); });
    ["states-dim"].forEach(function (id) { S.map.setLayoutProperty(id, "visibility", va ? "visible" : "none"); });
    ["va-known", "va-unknown", "va-line", "va-selected", "help-dots"].forEach(function (id) { S.map.setLayoutProperty(id, "visibility", va ? "visible" : "none"); });
  }

  function lightUp() {
    if (reduced) { S.lit = 999; paint(); return; }
    S.lit = 0;
    var max = isVa() ? 140 : 52, step = isVa() ? 6 : 2;
    var tick = function () {
      S.lit += step;
      paint();
      if (S.lit < max) setTimeout(tick, 40);
    };
    tick();
  }

  // ---------------- geometry helpers ----------------
  function inRing(x, y, ring) {
    var inside = false;
    for (var i = 0, j = ring.length - 1; i < ring.length; j = i++) {
      var xi = ring[i][0], yi = ring[i][1], xj = ring[j][0], yj = ring[j][1];
      if ((yi > y) !== (yj > y) && x < (xj - xi) * (y - yi) / (yj - yi) + xi) inside = !inside;
    }
    return inside;
  }
  function inFeature(lon, lat, f) {
    var g = f.geometry, polys = g.type === "Polygon" ? [g.coordinates] : g.coordinates;
    for (var p = 0; p < polys.length; p++) {
      if (!inRing(lon, lat, polys[p][0])) continue;
      var hole = false;
      for (var h = 1; h < polys[p].length; h++) if (inRing(lon, lat, polys[p][h])) hole = true;
      if (!hole) return true;
    }
    return false;
  }
  function localityAt(lat, lon) {
    if (!S.vaGeo || !isFinite(lat) || !isFinite(lon)) return null;
    for (var i = 0; i < S.vaGeo.features.length; i++) {
      var f = S.vaGeo.features[i], b = f.properties.bbox;
      if (lon < b[0] || lon > b[2] || lat < b[1] || lat > b[3]) continue;
      if (inFeature(lon, lat, f)) return f.id;
    }
    return null;
  }
  function bboxOf(f) {
    var b = [180, 90, -180, -90];
    var walk = function (c) {
      if (typeof c[0] === "number") {
        if (c[0] < b[0]) b[0] = c[0]; if (c[1] < b[1]) b[1] = c[1];
        if (c[0] > b[2]) b[2] = c[0]; if (c[1] > b[3]) b[3] = c[1];
      } else c.forEach(walk);
    };
    walk(f.geometry.coordinates);
    if (f.properties.code === "AK") b = [-170, 51, -130, 71.5];   // skip the Aleutians crossing 180
    return b;
  }

  // ---------------- map ----------------
  function webglOk() {
    try { var c = document.createElement("canvas"); return !!(c.getContext("webgl2") || c.getContext("webgl")); }
    catch (e) { return false; }
  }

  function drawStars() {
    var c = $("#stars");
    if (!c) return;
    var dpr = Math.min(2, window.devicePixelRatio || 1);
    c.width = c.clientWidth * dpr; c.height = c.clientHeight * dpr;
    var g = c.getContext("2d");
    g.fillStyle = "#05070f"; g.fillRect(0, 0, c.width, c.height);
    var rand = Fit.mulberry32(20261024), n = Math.round(c.width * c.height / (2600 * dpr));
    for (var i = 0; i < n; i++) {
      var x = rand() * c.width, y = rand() * c.height, r = rand() < 0.93 ? 0.5 * dpr : 1.1 * dpr, a = 0.25 + 0.75 * rand();
      g.fillStyle = "rgba(232,236,244," + a.toFixed(2) + ")";
      g.beginPath(); g.arc(x, y, r, 0, 6.2832); g.fill();
    }
  }

  function hatchImage() {
    var c = document.createElement("canvas"); c.width = c.height = 16;
    var g = c.getContext("2d");
    g.fillStyle = "rgba(27,36,64,0.85)"; g.fillRect(0, 0, 16, 16);
    g.strokeStyle = "rgba(167,177,198,0.75)"; g.lineWidth = 1.5;
    g.beginPath(); g.moveTo(-4, 4); g.lineTo(4, -4); g.moveTo(0, 16); g.lineTo(16, 0); g.moveTo(12, 20); g.lineTo(20, 12); g.stroke();
    return g.getImageData(0, 0, 16, 16);
  }

  // Computer layout (>= 1100 px, Virginia): a persistent list of all places on one side, the map in the middle,
  // the detail panel on the other side. Phones and small windows keep the bottom sheet.
  var DESK = window.matchMedia ? window.matchMedia("(min-width: 1100px)") : { matches: false };
  function desk() { return !!DESK.matches && isVa() && S.vaRanked.length > 0; }
  /** Apply the layout switch before anything measures it, so the camera never frames for the wrong layout. */
  function syncDesk() {
    var root = $("#globe-root"), rail = $(".g-rail"), on = desk();
    if (!rail && root) { rail = document.createElement("aside"); rail.className = "g-rail"; root.appendChild(rail); }
    document.documentElement.classList.toggle("g-desk", on);
    if (rail) rail.hidden = !on;
    return on && !!rail;
  }

  function sheetPad() {
    if (syncDesk()) {
      // Frame the map inside the space the two panels leave open, whatever the language direction.
      var a = $(".g-rail").getBoundingClientRect(), b = $(".g-sheet").getBoundingClientRect(), W = window.innerWidth;
      var lo = Math.min(a.left, b.left) === a.left ? a : b, hi = lo === a ? b : a;
      return { top: 90, bottom: 70, left: Math.round(lo.right) + 24, right: Math.round(W - hi.left) + 24 };
    }
    var wide = window.innerWidth >= 900, sh = $(".g-sheet");
    var h = sh ? sh.offsetHeight : 200, rtl = document.documentElement.dir === "rtl";
    if (wide) return rtl ? { top: 90, bottom: 40, left: 40, right: 440 } : { top: 90, bottom: 40, left: 440, right: 40 };
    return { top: 70, bottom: Math.min(h, window.innerHeight * 0.6) + 20, left: 20, right: 20 };
  }

  function helpGeo() {
    var feats = [];
    Object.keys(S.va.localities).forEach(function (f) {
      (S.va.localities[f].help_points || []).forEach(function (p, i) {
        feats.push({ type: "Feature", geometry: { type: "Point", coordinates: [p.lon, p.lat] },
          properties: { fips: f, i: i, kind: p.kind, color: KINDS[p.kind] || "#a7b1c6" } });
      });
    });
    return { type: "FeatureCollection", features: feats };
  }

  function buildMap(states, countries, vaTopo) {
    var topo = window.topojson;
    S.statesGeo = topo.feature(states, states.objects.states);
    var fips = {};
    Object.keys(S.policy.states).forEach(function (code) { fips[S.policy.states[code].fips] = code; });
    S.statesGeo.features = S.statesGeo.features.filter(function (f) { return fips[f.id]; });
    S.statesGeo.features.forEach(function (f) { f.properties.code = fips[f.id]; f.properties.v = -1; f.properties.known = false; });
    var land = topo.feature(countries, countries.objects.countries);
    paint();
    var map = new maplibregl.Map({
      container: "globe-map",
      style: {
        version: 8,
        projection: { type: "globe" },
        sources: {
          land: { type: "geojson", data: land },
          states: { type: "geojson", data: S.statesGeo },
          va: { type: "geojson", data: S.vaGeo, promoteId: "fips" },
          help: { type: "geojson", data: helpGeo() },
          heat: { type: "geojson", data: { type: "FeatureCollection", features: [] } },
          imagery: { type: "raster", tiles: [IMAGERY], tileSize: 256, maxzoom: 15,
            attribution: '<a href="https://s2maps.eu">Sentinel-2 cloudless</a> by EOX (Copernicus Sentinel data 2020)' },
          labels: { type: "raster", tiles: LABELS, tileSize: 256, maxzoom: 18,
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>' },
        },
        sky: { "sky-color": "#05070f", "horizon-color": "#1d3b6e", "fog-color": "#0b1a33",
          "atmosphere-blend": ["interpolate", ["linear"], ["zoom"], 0, 1, 5, 1, 7, 0] },
        layers: [
          { id: "ocean", type: "background", paint: { "background-color": "#081429" } },
          { id: "land", type: "fill", source: "land", paint: { "fill-color": "#121c33",
            "fill-opacity": ["interpolate", ["linear"], ["zoom"], 5, 1, 8, 0.4] } },
          { id: "imagery", type: "raster", source: "imagery", minzoom: 4.5, paint: { "raster-saturation": -0.35, "raster-brightness-max": 0.85,
            "raster-opacity": ["interpolate", ["linear"], ["zoom"], 4.5, 0, 7.5, 0.9] } },
          { id: "land-line", type: "line", source: "land", paint: { "line-color": "rgba(232,236,244,0.18)", "line-width": 0.6 } },
          { id: "states-known", type: "fill", source: "states", filter: ["==", ["get", "known"], true],
            paint: { "fill-color": fillExpr(), "fill-opacity": ["interpolate", ["linear"], ["zoom"], 3, 0.92, 7, 0.55, 10, 0.12, 12, 0] } },
          { id: "states-unknown", type: "fill", source: "states", filter: ["==", ["get", "known"], false],
            paint: { "fill-pattern": "hatch", "fill-opacity": ["interpolate", ["linear"], ["zoom"], 3, 0.9, 10, 0.2, 12, 0] } },
          // Virginia scope: every other state is quiet, so the eye goes to the lit Virginia map
          { id: "states-dim", type: "fill", source: "states", filter: ["!=", ["get", "code"], "VA"],
            paint: { "fill-color": "#0d1528", "fill-opacity": ["interpolate", ["linear"], ["zoom"], 3, 0.85, 9, 0.5] } },
          { id: "states-line", type: "line", source: "states", paint: { "line-color": "rgba(232,236,244,0.22)",
            "line-width": ["interpolate", ["linear"], ["zoom"], 2, 0.5, 7, 1.2] } },
          { id: "va-known", type: "fill", source: "va", filter: ["==", ["get", "known"], true],
            paint: { "fill-color": fillExpr(), "fill-opacity": ["interpolate", ["linear"], ["zoom"], 4, 0.95, 8, 0.8, 11, 0.35, 13, 0.12] } },
          { id: "va-unknown", type: "fill", source: "va", filter: ["==", ["get", "known"], false],
            paint: { "fill-pattern": "hatch", "fill-opacity": ["interpolate", ["linear"], ["zoom"], 4, 0.9, 11, 0.3, 13, 0.1] } },
          { id: "va-line", type: "line", source: "va", paint: { "line-color": "rgba(5,7,15,0.85)",
            "line-width": ["interpolate", ["linear"], ["zoom"], 5, 0.4, 8, 1, 11, 1.6] } },
          { id: "va-selected", type: "line", source: "va", filter: ["==", ["id"], ""],
            paint: { "line-color": "#fff1c9", "line-width": ["interpolate", ["linear"], ["zoom"], 5, 2, 10, 4] } },
          { id: "states-selected", type: "line", source: "states", filter: ["==", ["get", "code"], ""],
            paint: { "line-color": "#fff1c9", "line-width": ["interpolate", ["linear"], ["zoom"], 2, 2, 8, 4] } },
          { id: "labels", type: "raster", source: "labels", minzoom: 6.5, paint: { "raster-opacity": ["interpolate", ["linear"], ["zoom"], 6.5, 0, 8, 0.9] } },
          { id: "heat", type: "heatmap", source: "heat", maxzoom: 10, paint: {
            "heatmap-weight": ["/", ["get", "score"], 100], "heatmap-radius": ["interpolate", ["linear"], ["zoom"], 2, 14, 9, 40],
            "heatmap-opacity": 0.85,
            "heatmap-color": ["interpolate", ["linear"], ["heatmap-density"], 0, "rgba(0,0,0,0)", 0.2, RAMP[1], 0.45, RAMP[2],
              0.65, RAMP[3], 0.85, RAMP[4], 1, RAMP[5]] } },
          { id: "heat-points", type: "circle", source: "heat", minzoom: 8, paint: {
            "circle-color": ["interpolate", ["linear"], ["get", "score"], 0, RAMP[0], 20, RAMP[1], 40, RAMP[2], 60, RAMP[3], 80, RAMP[4], 100, RAMP[5]],
            "circle-radius": ["interpolate", ["linear"], ["zoom"], 8, 10, 14, 60], "circle-blur": 0.6, "circle-opacity": 0.75,
            "circle-stroke-color": "#fff1c9", "circle-stroke-width": 1 } },
          { id: "help-dots", type: "circle", source: "help", minzoom: 8.5, paint: {
            "circle-color": ["get", "color"], "circle-radius": ["interpolate", ["linear"], ["zoom"], 8.5, 3.5, 13, 8],
            "circle-stroke-color": "#05070f", "circle-stroke-width": 1.5 } },
        ],
      },
      center: [-40, 25], zoom: 0.4, minZoom: 0.3, maxZoom: 17,
      attributionControl: { compact: true },
      renderWorldCopies: false,
    });
    S.map = map;
    map.on("styleimagemissing", function (e) { if (e.id === "hatch" && !map.hasImage("hatch")) map.addImage("hatch", hatchImage()); });
    map.on("load", function () {
      if (!map.hasImage("hatch")) map.addImage("hatch", hatchImage());
      if (B.noImagery) {                       // host can't load outside tiles: keep the vector map readable when zoomed in
        ["labels", "imagery"].forEach(function (id) { map.removeLayer(id); map.removeSource(id); });
        map.setPaintProperty("land", "fill-opacity", 1);
        map.setPaintProperty("states-known", "fill-opacity", ["interpolate", ["linear"], ["zoom"], 3, 0.92, 7, 0.6, 12, 0.35]);
        map.setPaintProperty("states-unknown", "fill-opacity", ["interpolate", ["linear"], ["zoom"], 3, 0.9, 12, 0.3]);
        map.setPaintProperty("va-known", "fill-opacity", ["interpolate", ["linear"], ["zoom"], 4, 0.95, 10, 0.75, 13, 0.5]);
        map.setPaintProperty("va-unknown", "fill-opacity", ["interpolate", ["linear"], ["zoom"], 4, 0.9, 13, 0.4]);
      }
      S.mapOk = true;
      paint();
      paintHeat();
      if (S.selected && isVa()) map.setFilter("va-selected", ["==", ["id"], S.selected]);
      $(".g-loading") && $(".g-loading").remove();
      if (S.view === "rate") return;
      if (S.profile) flyHome(true); else { frameIntro(); startSpin(); }
    });
    map.on("error", function () { /* imagery tiles fail offline; bundled layers keep working */ });
    map.on("click", function (e) {
      if (S.view === "rate") { rateTap(e.lngLat.lat, e.lngLat.lng); return; }
      var hits = map.queryRenderedFeatures(e.point, { layers: isVa() ? ["help-dots", "va-known", "va-unknown", "states-dim"] : ["states-known", "states-unknown"] });
      if (!hits.length) return;
      var f = hits[0];
      if (f.layer.id === "help-dots") { helpPopup(f); return; }
      if (f.layer.id === "states-dim") { toast(t("vaOnly")); return; }
      if (isVa()) selectLocality(String(f.id || f.properties.fips), true, checkPoint(e.lngLat.lat, e.lngLat.lng));
      else selectState(f.properties.code, true);
    });
    ["mousedown", "touchstart", "wheel"].forEach(function (ev) { map.on(ev, stopSpin); });
    ["va-known", "va-unknown", "states-known", "states-unknown", "help-dots"].forEach(function (id) {
      map.on("mouseenter", id, function () { map.getCanvas().style.cursor = "pointer"; });
      map.on("mouseleave", id, function () { map.getCanvas().style.cursor = ""; });
    });
    map.on("zoomend", function () { if (map.getZoom() >= 10.5) showTownPlaces(); });
    map.on("resize", function () {
      if (S.placePopup) requestAnimationFrame(function () { if (S.placePopup) keepPopupVisible(S.placePopup); });
    });
  }

  function helpPopup(f) {
    var p = S.va.localities[f.properties.fips].help_points[f.properties.i];
    var html = '<div class="g-pop"><strong>' + esc(p.name || t("k_" + p.kind)) + "</strong><br>" + esc(t("k_" + p.kind)) +
      (p.hours ? "<br>" + esc(t("hours")) + ": " + esc(p.hours) : "") +
      (p.phone ? '<br><a href="tel:' + esc(p.phone.replace(/[^+\d]/g, "")) + '">' + esc(p.phone) + "</a>" : "") + "</div>";
    if (S.placePopup) S.placePopup.remove();
    var popup = new maplibregl.Popup({ offset: 10, anchor: "bottom", closeButton: true })
      .setLngLat([p.lon, p.lat]).setHTML(html).addTo(S.map);
    S.placePopup = popup;
    popup.on("close", function () { if (S.placePopup === popup) S.placePopup = null; });
    requestAnimationFrame(function () { keepPopupVisible(popup); });
  }

  // MapLibre knows the canvas edges, but not the controls covering it. Fit inside the exposed map.
  function keepPopupVisible(popup) {
    if (S.placePopup !== popup) return;
    var el = popup.getElement(), sh = $(".g-sheet").getBoundingClientRect();
    var top = $(".g-top").getBoundingClientRect().bottom + 8;
    var left = 8, right = window.innerWidth - 8, bottom = window.innerHeight - 8;
    if (window.innerWidth < 900) bottom = Math.min(bottom, sh.top - 8);
    else if (sh.left < window.innerWidth / 2) left = sh.right + 8;
    else right = sh.left - 8;
    var legend = $(".g-legend");
    if (!legend.hidden) bottom = Math.min(bottom, legend.getBoundingClientRect().top - 8);
    popup.setMaxWidth(Math.max(80, right - left) + "px");
    var content = el.querySelector(".maplibregl-popup-content");
    content.style.maxHeight = Math.max(40, bottom - top - 20) + "px";
    content.style.overflowY = "auto";
    var r = el.getBoundingClientRect();
    var dx = r.left < left ? left - r.left : (r.right > right ? right - r.right : 0);
    var dy = r.top < top ? top - r.top : (r.bottom > bottom ? bottom - r.bottom : 0);
    if (dx || dy) S.map.panBy([-dx, -dy], { duration: 0 });
  }

  function frameIntro() {
    var pad = sheetPad(), h = window.innerHeight - pad.top - pad.bottom, w = window.innerWidth - pad.left - pad.right;
    var px = Math.max(160, Math.min(h, w) * 0.86);
    var zoom = Math.log2(px / (512 / Math.PI));
    S.map.jumpTo({ center: [-60, 28], zoom: Math.max(0.3, zoom), padding: pad });
  }

  function startSpin() {
    if (reduced || S.spinning) return;
    S.spinning = true;
    var started = performance.now();
    var step = function (now) {
      if (!S.spinning || !S.map) return;
      if (now - started > 25000) { S.spinning = false; return; }
      var c = S.map.getCenter();
      S.map.setCenter([c.lng + 0.12, c.lat]);
      requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  }
  function stopSpin() { S.spinning = false; }

  function flyHome(quick) {
    stopSpin();
    if (!S.mapOk) return;
    S.map.setPadding(sheetPad());
    var cam = S.map.cameraForBounds(isVa() ? VA_BOUNDS : US_BOUNDS, { padding: 16 });
    if (!cam) { lightUp(); return; }
    var opts = { center: cam.center, zoom: cam.zoom, bearing: 0, essential: true };
    if (reduced || quick) { S.map.jumpTo(opts); lightUp(); return; }
    opts.duration = 3400; opts.curve = 1.6;
    S.map.once("moveend", lightUp);
    S.map.flyTo(opts);
  }

  function fitTo(b, maxZoom) {
    S.map.setPadding(sheetPad());
    S.map.fitBounds([[b[0], b[1]], [b[2], b[3]]], { padding: 24, duration: reduced ? 0 : 1800, maxZoom: maxZoom, essential: true });
  }

  function flyToState(code) {
    if (!S.mapOk) return;
    var f = S.statesGeo.features.filter(function (x) { return x.properties.code === code; })[0];
    if (!f) return;
    S.map.setFilter("states-selected", ["==", ["get", "code"], code]);
    fitTo(bboxOf(f), 7.5);
  }

  function flyToLocality(fips) {
    if (!S.mapOk) return;
    var f = S.vaGeo.features.filter(function (x) { return x.id === fips; })[0];
    if (!f) return;
    S.map.setFilter("va-selected", ["==", ["id"], fips]);
    fitTo(f.properties.bbox, 9.2);
  }

  function paintHeat() {
    if (!S.mapOk || !S.map.getSource("heat")) return;
    var feats = (S.heat && S.heat.tiles || []).map(function (x) {
      return { type: "Feature", geometry: { type: "Point", coordinates: [x.lon, x.lat] }, properties: { score: x.score, n: x.n } };
    });
    S.map.getSource("heat").setData({ type: "FeatureCollection", features: feats });
    var vis = S.layer === "community" || S.layer === "fit" ? "visible" : "none";
    S.map.setLayoutProperty("heat", "visibility", vis);
    S.map.setLayoutProperty("heat-points", "visibility", vis);
  }

  function showTownPlaces() {
    var c = S.map.getCenter();
    var town = S.recorded.filter(function (r) { return Math.abs(r.lat - c.lat) < 0.08 && Math.abs(r.lon - c.lng) < 0.08; })[0];
    if (!town || S.receiptTile === town.set) return;
    S.receiptTile = town.set;
    (B.receipt ? B.receipt(town) : getJSON(API + "/receipt?" + new URLSearchParams({ lat: town.lat, lon: town.lon }))).then(function (r) {
      S.markers.forEach(function (m) { m.remove(); });
      S.markers = [];
      Object.keys(r.nearest || {}).forEach(function (kind) {
        (r.nearest[kind] || []).slice(0, 3).forEach(function (p) {
          var el = document.createElement("button");
          el.className = "g-place"; el.type = "button";
          el.style.background = KINDS[kind] || "#a7b1c6";
          el.setAttribute("aria-label", p.name + " (" + kind.replace(/_/g, " ") + ")");
          el.title = p.name;
          var pop = new maplibregl.Popup({ offset: 12, closeButton: false }).setHTML(
            '<div class="g-pop"><strong>' + esc(p.name) + "</strong><br>" + esc(kind.replace(/_/g, " ")) +
            (p.walk_min != null ? ", " + Math.round(p.walk_min) + " min walk" : "") +
            (p.open_now === true ? "<br>Open now" : p.open_now === false ? "<br>Closed now" : "") + "</div>");
          S.markers.push(new maplibregl.Marker({ element: el }).setLngLat([p.lon, p.lat]).setPopup(pop).addTo(S.map));
        });
      });
    }).catch(function () { S.receiptTile = null; });
  }

  // ---------------- sheet views ----------------
  function render() {
    var sh = $(".g-sheet");
    if (!sh) return;
    if (S.placePopup && S.view !== "locality") S.placePopup.remove();
    var views = { intro: introView, profile: profileView, top: isVa() ? vaTopView : topView, list: isVa() ? vaListView : listView,
      state: stateView, locality: localityView, rate: rateView };
    var html = (views[S.view] || views.intro)();
    var tall = S.view === "profile" || S.view === "list" || (S.view === "rate" && S.ratingPoint);
    sh.className = "g-sheet" + (tall ? " tall" : "") + (S.view === "rate" && !S.ratingPoint ? " short" : "");
    sh.innerHTML = '<button class="g-grip" aria-label="Resize panel" type="button"></button>' + html;
    bindView();
    renderRail();
    renderChrome();
    var h = sh.querySelector("h1, h2");
    if (h) { h.setAttribute("tabindex", "-1"); }
    updatePeek();
  }

  /** The computer layout's list of all 133 places. Re-rendered with the sheet; keeps its search and scroll. */
  function renderRail() {
    if (!syncDesk()) return;
    var rail = $(".g-rail");
    var oldQ = rail.querySelector("#g-rail-q"), oldList = rail.querySelector(".g-list");
    var q = oldQ ? oldQ.value : "", scroll = oldList ? oldList.scrollTop : 0, hadFocus = oldQ && document.activeElement === oldQ;
    rail.setAttribute("aria-label", t("allPlaces"));
    rail.innerHTML = "<h2>" + esc(t("allPlaces")) + '</h2><p class="g-small">' + esc(t("l_" + S.layer)) + "</p>" +
      '<label class="g-search"><span class="sr-only">' + esc(t("search")) + '</span><input type="search" id="g-rail-q" placeholder="' +
      esc(t("search")) + '" autocomplete="off"></label><p class="g-nomatch" hidden>' + esc(t("noMatch")) + "</p>" +
      '<ul class="g-list">' + vaSorted().map(vaRowHTML).join("") + "</ul>";
    var cur = S.view === "locality" && rail.querySelector('[data-fips="' + S.selected + '"]');
    if (cur) cur.setAttribute("aria-current", "true");
    rail.querySelectorAll("[data-fips]").forEach(function (b) {
      b.addEventListener("click", function () { selectLocality(b.dataset.fips, true); });
    });
    var input = rail.querySelector("#g-rail-q");
    input.value = q;
    filterList(rail, input);
    input.addEventListener("input", function () { filterList(rail, input); });
    rail.querySelector(".g-list").scrollTop = scroll;
    if (hadFocus) input.focus();
  }

  function filterList(box, input) {
    var v = input.value.trim().toLowerCase(), shown = 0;
    box.querySelectorAll(".g-list li").forEach(function (li) {
      var hit = !v || li.dataset.name.indexOf(v) !== -1;
      li.hidden = !hit; if (hit) shown++;
    });
    box.querySelector(".g-nomatch").hidden = shown > 0;
  }

  function updatePeek() {
    var sh = $(".g-sheet");
    if (sh) document.documentElement.style.setProperty("--sheet-peek", Math.min(sh.offsetHeight, window.innerHeight * 0.86) + "px");
  }

  function renderChrome() {
    $(".g-legend").hidden = S.view === "intro" || S.view === "profile" || S.view === "rate";
    var lang = $("#g-lang");
    if (lang.tagName === "SELECT") {
      lang.setAttribute("aria-label", "Language / " + t("lang"));
      lang.innerHTML = (I.LANGS || ["en", "es"]).map(function (l) {
        return '<option value="' + l + '"' + (l === S.lang ? " selected" : "") + ">" + esc(I.t(l, "langName")) + "</option>";
      }).join("");
    } else lang.textContent = S.lang === "es" ? "English" : "Español";
    // On a computer there is room to say what the quick exit does; "Hide" alone reads like "hide this panel".
    // Only languages that have the long label use it; the others keep their translated short one.
    var longHide = document.documentElement.classList.contains("g-desk") && (I.strings[S.lang] || {}).hide;
    $("#g-hide").textContent = longHide || t("hideShort");
    $("#g-hide").title = t("hideLong");
    $("#g-hide").setAttribute("aria-label", t("hideLong"));
    $("#g-listbtn").textContent = S.view === "list" ? t("map") : t("list");
    var sel = $("#g-layer");
    sel.setAttribute("aria-label", t("layer"));
    if (layers().indexOf(S.layer) === -1) S.layer = "fit";
    sel.innerHTML = layers().map(function (l) { return '<option value="' + l + '"' + (l === S.layer ? " selected" : "") + ">" + esc(t("l_" + l)) + "</option>"; }).join("");
    $("#g-low").textContent = S.layer === "fit" ? t("legendLow") : t("lo_" + S.layer);
    $("#g-high").textContent = S.layer === "fit" ? t("legendHigh") : t("hi_" + S.layer);
    $("#g-unk").textContent = t("legendUnknown");
    document.documentElement.lang = S.lang;
    document.documentElement.dir = (I.RTL || []).indexOf(S.lang) !== -1 ? "rtl" : "ltr";
    var map = $("#globe-map");
    if (map) map.setAttribute("aria-label", isVa() ? "Map of Virginia's cities and counties, colored by how well each fits you. The List button shows the same information as a list."
      : "Globe. States are colored by how well they fit you. Use the List button for the same information as a list.");
  }

  function machineNote() {
    return (I.MACHINE || []).indexOf(S.lang) !== -1 ? '<p class="g-machine" lang="' + S.lang + '">' + esc(t("machine")) + "</p>" : "";
  }

  var LOCK = '<svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true"><rect x="3" y="7" width="10" height="8" rx="2" fill="currentColor"/><path d="M5 7V5a3 3 0 0 1 6 0v2" stroke="currentColor" stroke-width="1.6" fill="none"/></svg>';

  function introView() {
    return "<h1>" + esc(isVa() ? t("title_va") : t("title")) + "</h1><p>" + esc(isVa() ? t("lede_va") : t("lede")) + "</p>" + machineNote() +
      '<div class="g-lock">' + LOCK + "<span>" + esc(t("privacy")) + "</span></div>" +
      '<div class="g-actions"><button class="g-primary" data-go="profile" type="button">' + esc(t("start")) + "</button>" +
      '<button class="g-secondary" data-go="skip" type="button">' + esc(t("skip")) + "</button>" +
      (B.standalone ? "" : '<a class="g-secondary" href="#/start">' + esc(t("nearMe")) + "</a>") +
      '<a class="g-secondary" href="tel:211">' + esc(t("call211short")) + "</a></div>";
  }

  function profileView() {
    var p = draft(), hh = p.household || {}, sit = p.situation || {};
    var statuses = S.elig.statuses.map(function (s) {
      return '<label><input type="radio" name="status" value="' + s.id + '"' + (p.status === s.id ? " checked" : "") + "> " + esc(statusLabel(s)) + "</label>";
    }).join("");
    var chip = function (group, key) {
      var on = group === "household" ? !!hh[key] : !!sit[key];
      return '<button type="button" class="g-chip" data-chip="' + group + "." + key + '" aria-pressed="' + on + '">' + esc(t(key)) + "</button>";
    };
    var ages = [["18_24", "age18"], ["25_49", "age25"], ["50_61", "age50"], ["62_plus", "age62"]].map(function (a) {
      return '<button type="button" class="g-chip" data-age="' + a[0] + '" aria-pressed="' + (p.age_band === a[0]) + '">' + esc(t(a[1])) + "</button>";
    }).join("");
    var beds = [["auto", "bedAuto"], [0, "bed0"], [1, "bed1"], [2, "bed2"], [3, "bed3"], [4, "bed4"]].map(function (b) {
      var on = b[0] === "auto" ? (hh.bedrooms === undefined || hh.bedrooms === null) : hh.bedrooms === b[0];
      return '<button type="button" class="g-chip" data-bed="' + b[0] + '" aria-pressed="' + on + '">' + esc(t(b[1])) + "</button>";
    }).join("");
    var crime = isVa() ? "<h3>" + esc(t("crimeQ")) + "</h3><p>" + esc(t("crimeHelp")) + '</p><div class="g-chips">' +
      '<button type="button" class="g-chip" data-crime="0" aria-pressed="' + !p.show_crime + '">' + esc(t("crimeOff")) + "</button>" +
      '<button type="button" class="g-chip" data-crime="1" aria-pressed="' + !!p.show_crime + '">' + esc(t("crimeOn")) + "</button></div>" : "";
    return "<h2>" + esc(t("aboutYou")) + '</h2><div class="g-lock">' + LOCK + "<span>" + esc(t("privacy")) + "</span></div>" + machineNote() +
      '<fieldset class="g-fs"><legend><h3>' + esc(t("statusQ")) + "</h3></legend>" +
      "<p>" + esc(t("statusHelp")) + '</p><div class="g-status">' + statuses + "</div></fieldset>" +
      "<h3>" + esc(t("whoQ")) + '</h3><div class="g-chips">' + ["kids", "pregnant", "partner", "pets", "mixed"].map(function (k) { return chip("household", k); }).join("") + "</div>" +
      (isVa() ? "<h3>" + esc(t("bedroomsQ")) + '</h3><div class="g-chips g-beds">' + beds + "</div>" : "") +
      "<h3>" + esc(t("situationQ")) + '</h3><div class="g-chips">' + ["tonight", "car", "no_id", "veteran", "disability"].map(function (k) { return chip("situation", k); }).join("") + "</div>" +
      "<h3>" + esc(t("ageQ")) + '</h3><div class="g-chips">' + ages + "</div>" +
      crime + priorityBlock(p) +
      '<div class="g-actions"><button class="g-primary g-wide" data-go="save" type="button">' + esc(t("showMap")) + "</button>" +
      '<button class="g-secondary g-wide" data-go="forget" type="button">' + esc(t("forget")) + "</button></div>";
  }

  function currentOrder(p) {
    var prof = JSON.parse(JSON.stringify(p || S.profile || defaultProfile()));
    if (isVa()) {
      var comps = VaFit.components(S.va, "51121", prof, {}, S.elig);
      comps.community = comps.community || {};
      var def = VaFit.defaultPriorities(S.elig, prof);
      var chosen = (prof.priorities || []).filter(function (k) { return def.indexOf(k) !== -1; });
      def.forEach(function (k) { if (chosen.indexOf(k) === -1) chosen.push(k); });
      return chosen.filter(function (k) { return comps[k] !== undefined; });
    }
    prof.priorities = prof.priorities_us || [];
    var sample = Fit.components(S.elig, S.policy, "VA", prof, {});
    var d2 = Fit.defaultPriorities(S.elig, prof);
    var ch2 = (prof.priorities || []).filter(function (k) { return d2.indexOf(k) !== -1; });
    d2.forEach(function (k) { if (ch2.indexOf(k) === -1) ch2.push(k); });
    return ch2.filter(function (k) { return sample[k] !== undefined; });
  }

  function priorityBlock(p) {
    var order = currentOrder(p), w = Fit.rocWeights(order.length);
    return "<h3>" + esc(t("priQ")) + "</h3><p>" + esc(t("priHelp")) + '</p><ol class="g-pri">' + order.map(function (k, i) {
      return "<li><span>" + esc(t("c_" + k)) + '</span><span class="w">' + Math.round(100 * w[i]) + "%</span>" +
        '<button type="button" data-pri="' + k + '" data-dir="-1" aria-label="' + esc(t("up") + ": " + t("c_" + k)) + '"' + (i === 0 ? " disabled" : "") + ">&uarr;</button>" +
        '<button type="button" data-pri="' + k + '" data-dir="1" aria-label="' + esc(t("down") + ": " + t("c_" + k)) + '"' + (i === order.length - 1 ? " disabled" : "") + ">&darr;</button>" +
        '<span class="wbar" style="width:' + (100 * w[i] / w[0]).toFixed(1) + '%"></span></li>';
    }).join("") + "</ol>";
  }

  function scoreBadge(score) {
    if (score === null || score === undefined) return '<div class="g-badge unknown">?<small>' + esc(t("unknownWhy")) + "</small></div>";
    return '<div class="g-badge" style="background:' + rampColor(score) + ";color:" + inkOn(score) + '">' + Math.round(score) + "<small>/ 100</small></div>";
  }

  function rangeText(r, short) {
    if (!r.rank_p10) return "";
    if (short) return r.rank_p10 === r.rank_p90 ? t("fixedShort", { a: r.rank_p10 }) : t("rangeShort", { a: r.rank_p10, b: r.rank_p90 });
    return r.rank_p10 === r.rank_p90 ? t("rankFixed", { a: r.rank_p10 }) : t("rankRange", { a: r.rank_p10, b: r.rank_p90 });
  }

  // ---- Virginia views ----
  function vaRowHTML(r) {
    var v = vaLayerValue(r), unk = v === null;
    var sub = S.layer === "fit" ? rangeText(r, true) : "";
    var sig = S.layer === "fit" ? '<span class="sig ' + r.confidence_label + '" role="img" aria-label="' + esc(t("confidence") + ": " + t("conf_" + r.confidence_label)) + '"><i></i><i></i><i></i></span>' : "";
    return '<li data-name="' + esc(r.name.toLowerCase()) + '"><button type="button" class="g-row" data-fips="' + r.fips + '"><span class="r">' + (r.rank && S.layer === "fit" ? "#" + r.rank : "") + "</span>" +
      "<span>" + esc(r.name) + (sub ? '<span class="sub">' + sig + esc(sub) + "</span>" : "") + "</span>" +
      '<span class="s' + (unk ? " unknown" : "") + '" style="' + (unk ? "" : "background:" + rampColor(v) + ";color:" + inkOn(v)) + '">' + (unk ? "?" : Math.round(v)) + "</span></button></li>";
  }

  function vaSorted() {
    if (S.layer === "fit") return S.vaRanked.slice().sort(function (a, b) { return (a.rank || 999) - (b.rank || 999) || (a.name < b.name ? -1 : 1); });
    return S.vaRanked.slice().sort(function (a, b) {
      var x = vaLayerValue(a), y = vaLayerValue(b);
      if (x === null && y === null) return a.name < b.name ? -1 : 1;
      if (x === null) return 1;
      if (y === null) return -1;
      return y - x || (a.name < b.name ? -1 : 1);
    });
  }

  function whoLine() {
    var p = S.profile;
    if (!p) return "";
    var who = S.elig.statuses.filter(function (s) { return s.id === p.status; })[0];
    var bits = [];
    if (who && p.status !== "undisclosed") bits.push(statusLabel(who));
    if ((p.household || {}).kids) bits.push(t("kids"));
    bits.push(t("sz" + VaFit.bedrooms(p)));
    return "<p>" + esc(bits.join(", ")) + "</p>";
  }

  function vaTopView() {
    return "<h2>" + esc(t("topVa")) + "</h2>" + whoLine() + machineNote() +
      '<ul class="g-list">' + vaSorted().slice(0, 5).map(vaRowHTML).join("") + "</ul>" +
      '<div class="g-actions"><button class="g-secondary" data-go="list" type="button">' + esc(t("seeAll")) + "</button>" +
      '<button class="g-secondary" data-go="profile" type="button">' + esc(S.profile ? t("editAboutYou") : t("start")) + "</button>" +
      '<button class="g-link g-wide" data-go="scope-us" type="button">' + esc(t("scope_us")) + "</button></div>";
  }

  function vaListView() {
    return "<h2>" + esc(t("allPlaces")) + "</h2><p>" + esc(t("l_" + S.layer)) + "</p>" +
      '<label class="g-search"><span class="sr-only">' + esc(t("search")) + '</span><input type="search" id="g-q" placeholder="' + esc(t("search")) + '" autocomplete="off"></label>' +
      '<p class="g-nomatch" hidden>' + esc(t("noMatch")) + "</p>" +
      '<ul class="g-list">' + vaSorted().map(vaRowHTML).join("") + "</ul>";
  }

  /** Details runs in the person's language. Recorded evidence quotes stay English and are marked so.
   *  A missing template must never show a wrong sentence: it falls back to the engine's English reason,
   *  labelled "Details (in English)", and logs once so the gap is visible in the smoke tests. */
  function reasonRuns(c) {
    if (S.lang !== "en" && I.vaReasonParts && c.reason_data) {
      try { return { runs: I.vaReasonParts(S.lang, c), translated: true }; }
      catch (e) { if (window.console) console.warn("Footing: no " + S.lang + " reason for " + c.id + ": " + e.message); }
    }
    return { runs: [{ text: c.reason, lang: "en", kind: "translation" }], translated: S.lang === "en" };
  }
  function reasonHTML(runs) {
    return runs.map(function (p) {
      return '<span lang="' + esc(p.lang) + '"' + (p.lang === "en" ? ' dir="ltr"' : "") +
        (p.kind === "quote" ? ' class="g-quote"' : "") + ">" + esc(p.text) + "</span>";
    }).join(" ");
  }
  /** The short line uses only the translated runs; the English evidence quote stays in Details. */
  function reasonLine(c) {
    var rr = reasonRuns(c);
    var own = rr.runs.filter(function (p) { return p.kind === "translation"; });
    return (own.length ? own : rr.runs).map(function (p) { return p.text; }).join(" ");
  }

  /** One short line per component in the person's language, built from the numbers. */
  function localLine(c, loc) {
    var kids = !!((S.profile || {}).household || {}).kids;
    if (c.id === "rent" && c.parts) return t("line_rent", { rent: money(c.parts.rent), size: t("sz" + c.parts.bedrooms), hours: Math.round(c.parts.hours) });
    if (c.id === "shelter" && c.parts) return t(kids ? "line_shelter_kids" : "line_shelter", { pct: Math.round(100 * c.parts.outside_share), beds: num(c.parts.beds), people: num(c.parts.people) });
    if (c.id === "services") {
      var s = loc.services, osm = s.osm || {}, help = 0;
      ["food_bank", "soup_kitchen", "shelter", "day_center", "clinic", "library", "toilets", "shower", "drinking_water", "laundry"].forEach(function (k) { help += osm[k] || 0; });
      return t("line_services", { groc: num(s.snap.full_grocery), help: num(help) }) + (s.fare_free_transit ? " " + t("line_transit") : "");
    }
    if (c.id === "laws") return c.score === null ? (loc.local_rule ? reasonLine(c) : t("law_null")) : t("law_" + c.score);
    if (c.id === "safety") return t("safe_" + c.score);
    if (c.id === "crime") {
      if (c.parts && c.parts.level === "block") return t("line_crime_block", {
        v: num(c.parts.violent), e: num(c.parts.enforcement), from: c.parts.window_start, to: c.parts.window_end
      });
      return c.score === null ? t("crime_null") : t("line_crime", { x: num(loc.crime.violent_per_1k) });
    }
    if (c.id === "community") return c.score === null ? t("community_null") : t("line_community", { n: num(((S.heat && S.heat.localities) || {})[loc.fips] ? S.heat.localities[loc.fips].n : 0) });
    return reasonLine(c);
  }

  function sourceLinks(c) {
    var keys = (COMP_SOURCES[c.id] || []).slice();
    if (c.id === "laws" && c.source) keys = [c.source];
    if (c.id === "crime" && c.source) keys.unshift(c.source);
    if (c.id === "services" && !S.va.localities[S.selected].services.fare_free_transit) keys = keys.filter(function (k) { return k !== "apta_fare_free"; });
    var src = S.va.sources;
    return keys.filter(function (k) { return src[k]; }).map(function (k) {
      var s = src[k];
      if (k === "city_incidents") {
        var city = S.va.incident_cities[S.selected];
        s = { title: city.agency, url: city.source_url, publisher: city.name,
          as_of: city.window_start + " – " + city.latest_date };
      }
      return '<li><a href="' + esc(s.url) + '" target="_blank" rel="noopener">' + esc(s.title) + "</a>, " + esc(s.publisher) + " (" + esc(t("asOf")) + " " + esc(s.as_of) + ")</li>";
    }).join("");
  }

  /** The score as area: each column is as wide as the part's weight and filled as high as its score.
   *  Filled area over the counted area is exactly the score. Unknown parts are striped and sit at the end. */
  function mosaic(r) {
    var known = r.components.filter(function (c) { return c.score !== null; });
    var unknown = r.components.filter(function (c) { return c.score === null; });
    var cols = known.concat(unknown).map(function (c) {
      var w = (100 * c.weight).toFixed(2), unk = c.score === null;
      return '<div class="col' + (unk ? " unk" : "") + '" style="flex-grow:' + w + '" title="' + esc(t("c_" + c.id) + ": " + (unk ? t("unknownWhy") : Math.round(c.score))) + '">' +
        (unk ? "" : '<div class="fill" style="height:' + c.score + "%;background:" + rampColor(c.score) + '"></div>') +
        '<span class="lbl" style="color:' + (unk ? "var(--g-ink-2)" : (c.score > 60 ? "#10131c" : "var(--g-ink)")) + '">' + (unk ? "?" : Math.round(c.score)) + "</span></div>";
    }).join("");
    var names = known.concat(unknown).map(function (c) {
      return '<span style="flex-grow:' + (100 * c.weight).toFixed(2) + '" title="' + esc(t("c_" + c.id)) + '">' + esc(t("c_" + c.id)) + "</span>";
    }).join("");
    var sum = known.map(function (c) { return esc(t("c_" + c.id)) + " " + Math.round(c.score) + " × " + Math.round(100 * c.share) + "%"; }).join(" + ");
    return '<figure class="g-mosaic"><div class="cols" aria-hidden="true">' + cols + '</div><div class="names" aria-hidden="true">' + names + "</div>" +
      '<figcaption><span class="sr-only">' + sum + " = " + Math.round(r.score) + ". </span>" + esc(t("mosaicHelp")) + "</figcaption></figure>";
  }

  function confMeter(r) {
    var known = r.components.filter(function (c) { return c.score !== null; }).length;
    return '<div class="g-conf" role="img" aria-label="' + esc(t("confidence") + ": " + t("conf_" + r.confidence_label)) + '">' +
      '<span class="bar"><span class="v" style="width:' + Math.round(100 * r.confidence) + '%"></span><i style="left:45%"></i><i style="left:70%"></i></span></div>' +
      '<p class="g-small">' + esc(t("confLine", { k: known, n: r.components.length })) + "</p>";
  }

  function helpList(loc) {
    var pts = loc.help_points || [];
    if (!pts.length) return "<p>" + esc(t("helpNone")) + "</p>";
    return '<ul class="g-help">' + pts.slice(0, 12).map(function (p) {
      return '<li><i style="background:' + (KINDS[p.kind] || "#a7b1c6") + '" aria-hidden="true"></i><span><strong>' + esc(p.name || t("k_" + p.kind)) + "</strong> " +
        '<span class="k">' + esc(t("k_" + p.kind)) + "</span>" + (p.hours ? '<span class="h">' + esc(p.hours) + "</span>" : "") + "</span>" +
        (p.phone ? '<a href="tel:' + esc(p.phone.replace(/[^+\d]/g, "")) + '" aria-label="' + esc(t("phone") + " " + (p.name || "")) + '">' + esc(p.phone) + "</a>" : "") + "</li>";
    }).join("") + "</ul>";
  }

  function localityView() {
    var r = S.byFips[S.selected];
    if (!r) return "";
    var pt = S.selectedPoint;
    if (pt && pt.fips === S.selected) {
      r = VaFit.fitScore(S.elig, S.va, S.selected, profileFor("va"), (S.heat || {}).localities || {}, pt.tile);
      r.confidence = Math.round(r.confidence * pt.validity * 1000) / 1000;
      r.confidence_label = r.confidence >= 0.7 ? "high" : (r.confidence >= 0.45 ? "medium" : "low");
    }
    var loc = S.va.localities[r.fips];
    var n = S.vaRanked.filter(function (x) { return x.rank; }).length;
    var town = S.recorded.filter(function (x) { return localityAt(x.lat, x.lon) === r.fips; })[0];
    var known = r.components.filter(function (c) { return c.score !== null; });
    var unknown = r.components.filter(function (c) { return c.score === null; });
    var card = function (c) {
      var unk = c.score === null, rr = reasonRuns(c);
      return '<li data-component="' + c.id + '" class="g-c2' + (unk ? " unk" : "") + '"><div class="hd"><span class="name">' + esc(t("c_" + c.id)) + "</span>" +
        '<span class="num" style="' + (unk ? "" : "background:" + rampColor(c.score) + ";color:" + inkOn(c.score)) + '">' + (unk ? "?" : Math.round(c.score)) + "</span></div>" +
        (unk ? "" : '<span class="w">' + esc(t("weightOf", { w: Math.round(100 * c.share) })) + "</span>") +
        '<p class="line">' + esc(localLine(c, loc)) + "</p>" +
        '<details><summary>' + esc(rr.translated ? t("details") : t("detailsEn")) + '</summary><p class="g-reason">' + reasonHTML(rr.runs) + "</p>" +
        (sourceLinks(c) ? '<ul class="g-srcs">' + sourceLinks(c) + "</ul>" : "") + "</details></li>";
    };
    return '<h2 id="g-loc-title">' + esc(r.name) + '</h2><p class="g-kind">' + esc(loc.kind === "city" ? t("city") : t("county")) + "</p>" +
      (pt ? '<p class="g-small g-point-note">' + esc(t("pointScore")) + '</p><button class="g-link" data-go="locality-wide" type="button">' + esc(t("wholeLocality")) + "</button>" : "") +
      '<div class="g-score">' + scoreBadge(r.score) + '<div class="g-meta">' + esc(t("fit")) +
      (r.rank ? "<br><strong>" + esc(t("rankOf", { r: r.rank, n: n })) + "</strong>" : "") +
      "<br>" + esc(t("confidence")) + ": <strong>" + esc(t("conf_" + r.confidence_label)) + "</strong></div></div>" +
      confMeter(r) +
      (r.rank_p10 ? '<p class="g-small">' + esc(rangeText(r)) + "</p>" : "") +
      '<div class="g-actions"><button class="g-secondary" data-go="rate" type="button">' + esc(t("rateHere")) + "</button>" +
      '<a class="g-secondary" href="tel:211">' + esc(t("call211short")) + "</a>" +
      (town && !B.standalone ? '<a class="g-primary g-wide" href="#/receipt?' + new URLSearchParams({ lat: town.lat, lon: town.lon, profile: legacyProfile() }) + '">' + esc(t("openReceipt", { town: town.label })) + "</a>" : "") +
      "</div><h3>" + esc(t("howBuilt")) + "</h3>" + mosaic(r) +
      '<ul class="g-c2s">' + known.map(card).join("") + "</ul>" +
      (unknown.length ? "<h3>" + esc(t("unknownParts")) + '</h3><ul class="g-c2s">' + unknown.map(card).join("") + "</ul>" : "") +
      "<h3>" + esc(t("helpHere")) + "</h3>" + helpList(loc) +
      "<h3>" + esc(t("programsVa")) + '</h3><p class="g-small">' + esc(t("statewide")) + "</p>" + programsHTML("VA") +
      '<p><a href="tel:211" class="g-ink">' + esc(t("call211")) + "</a></p>" + vaSourcesHTML();
  }

  function vaSourcesHTML() {
    var srcs = S.va.sources;
    return '<details class="g-src"><summary>' + esc(t("sources")) + "</summary><ul>" + Object.keys(srcs).map(function (k) {
      var s = srcs[k];
      return '<li><a href="' + esc(s.url) + '" target="_blank" rel="noopener">' + esc(s.title) + "</a>, " + esc(s.publisher) + " (" + esc(t("asOf")) + " " + esc(s.as_of) + ")</li>";
    }).join("") + "</ul></details>";
  }

  // ---- U.S. (beta) views, unchanged from session 3 apart from naming ----
  function rowHTML(r) {
    var v = usLayerValue(r), unk = v === null;
    return '<li><button type="button" class="g-row" data-state="' + r.state + '"><span class="r">' + (r.rank ? "#" + r.rank : "") + "</span>" +
      "<span>" + esc(r.name) + (S.layer === "fit" && r.rank_p10 ? '<span class="sub">' + esc(rangeText(r, true)) + "</span>" : "") + "</span>" +
      '<span class="s' + (unk ? " unknown" : "") + '" style="' + (unk ? "" : "background:" + rampColor(v) + ";color:" + inkOn(v)) + '">' + (unk ? "?" : Math.round(v)) + "</span></button></li>";
  }
  function sortedForLayer() {
    return S.ranked.slice().sort(function (a, b) {
      var x = usLayerValue(a), y = usLayerValue(b);
      if (x === null && y === null) return a.name < b.name ? -1 : 1;
      if (x === null) return 1;
      if (y === null) return -1;
      return y - x || (a.name < b.name ? -1 : 1);
    });
  }
  function topView() {
    return "<h2>" + esc(t("top")) + "</h2>" + whoLine() +
      '<ul class="g-list">' + sortedForLayer().slice(0, 5).map(rowHTML).join("") + "</ul>" +
      '<div class="g-actions"><button class="g-secondary" data-go="list" type="button">' + esc(t("allStates")) + "</button>" +
      '<button class="g-secondary" data-go="profile" type="button">' + esc(S.profile ? t("editAboutYou") : t("start")) + "</button>" +
      '<button class="g-link g-wide" data-go="scope-va" type="button">' + esc(t("scope_va")) + "</button></div>";
  }
  function listView() {
    return "<h2>" + esc(t("allStates")) + "</h2><p>" + esc(t("l_" + S.layer)) + '</p><ul class="g-list">' + sortedForLayer().map(rowHTML).join("") + "</ul>";
  }

  function programsHTML(code) {
    var p = S.profile || defaultProfile(), st = S.policy.states[code];
    var undisclosed = !p.status || p.status === "undisclosed";
    var rows = S.elig.programs.filter(function (g) { return g.id !== "public_charge" && (!undisclosed || g.rule["*"]); }).map(function (g) {
      var rule = Fit.programRule(S.elig, g.id, p.status);
      var note = rule.note;
      if (g.id === "snap" && st.state_food_immigrants && rule.value !== "yes") note = (note ? note + " " : "") + "State: " + st.state_food_immigrants.note;
      if (g.id === "medicaid" && p.status && ["citizen", "lpr5", "cuban_haitian", "cofa"].indexOf(p.status) !== -1)
        note = st.medicaid_expansion ? "This state expanded Medicaid." : "This state did not expand Medicaid. " + note;
      if (g.id === "medicaid" && rule.value !== "yes") {
        if (st.health_children_all) note += " State covers children regardless of status" + (st.health_children_all.note ? " (" + st.health_children_all.note + ")" : "") + ".";
        if (st.health_adults_all) note += " State adult program: " + st.health_adults_all.status + ". " + st.health_adults_all.note;
      }
      return "<li><span>" + esc(programLabel(g)) + '</span><span class="v ' + rule.value + '">' + esc(t(rule.value)) + "</span>" +
        (note ? '<span class="note" lang="en">' + esc(note) + "</span>" : "") + "</li>";
    });
    if (!undisclosed) {
      var dl = st.drivers_license_all;
      var lawful = ["undocumented", "unsure"].indexOf(p.status) === -1;
      var val = lawful ? "yes" : (dl ? "yes" : "no");
      rows.push("<li><span>" + esc(S.lang === "es" ? "Licencia o identificación estatal" : "Driver's license or state ID") + '</span><span class="v ' + val + '">' + esc(t(val)) + "</span>" +
        '<span class="note" lang="en">' + esc(lawful ? "With your documents." : (dl ? "This state issues a " + dl.form + " regardless of status (since " + dl.year + ")." : "This state requires proof of lawful presence.")) + "</span></li>");
    }
    var pc = Fit.programRule(S.elig, "public_charge", p.status);
    var caution = (!undisclosed && pc.value === "limited") ? '<div class="g-caution"><strong>' + esc(t("caution")) + ":</strong> <span lang=\"en\">" + esc(pc.note) +
      '</span><br><a href="https://www.immigrationadvocates.org/legaldirectory/" target="_blank" rel="noopener">' + esc(t("legal")) + "</a></div>" : "";
    return caution + '<ul class="g-progs">' + rows.join("") + "</ul>";
  }

  function sourcesHTML() {
    var srcs = S.policy.sources;
    return '<details class="g-src"><summary>' + esc(t("sources")) + "</summary><ul>" + Object.keys(srcs).map(function (k) {
      var s = srcs[k];
      return '<li><a href="' + esc(s.url) + '" target="_blank" rel="noopener">' + esc(s.title) + "</a>, " + esc(s.publisher) + " (" + esc(t("asOf")) + " " + esc(s.as_of) + ")</li>";
    }).join("") + "</ul></details>";
  }

  function whySpan(reason) {
    var out = I.reason ? I.reason(S.lang, reason) : reason;
    // Mark it as English only when it really is, so screen readers and the "machine translation" note stay honest.
    return '<span class="why"' + (out === reason && S.lang !== "en" ? ' lang="en"' : "") + ">" + esc(out) + "</span>";
  }

  function stateView() {
    var r = S.byCode[S.selected];
    if (!r) return "";
    var comps = r.components.map(function (c) {
      var unk = c.score === null;
      return '<div class="g-comp"><span class="name">' + esc(t("c_" + c.id)) + "<em>" + Math.round(100 * c.weight) + "%</em></span>" +
        '<span class="num">' + (unk ? "?" : Math.round(c.score)) + "</span>" +
        '<span class="track' + (unk ? " unknown" : "") + '">' + (unk ? "" : '<span class="fill" style="display:block;width:' + c.score + "%;background:" + rampColor(c.score) + '"></span>') + "</span>" +
        // fit.js builds its reasons in English so it matches fit.py exactly; i18n.reason translates them at
        // display time (tests/js/check_reasons.js). Anything it cannot translate stays English and says so.
        whySpan(c.reason) + "</div>";
    }).join("");
    var rankLine = r.rank ? "<strong>" + esc(t("rank")) + " #" + r.rank + "</strong> " + esc(t("of")) + " " + S.ranked.filter(function (x) { return x.rank; }).length : "";
    return '<h2 id="g-state-title">' + esc(r.name) + "</h2>" +
      '<div class="g-score">' + scoreBadge(r.score) + '<div class="g-meta">' + esc(t("fit")) + "<br>" + rankLine +
      "<br>" + esc(t("confidence")) + ": <strong>" + esc(t("conf_" + r.confidence_label)) + "</strong>" +
      (r.rank_p10 ? "<br><span>" + esc(rangeText(r)) + "</span>" : "") + "</div></div>" +
      '<div class="g-actions">' + (r.state === "VA" ? '<button class="g-primary g-wide" data-go="scope-va" type="button">' + esc(t("scope_va")) + "</button>" : "") +
      '<button class="g-secondary" data-go="fly" type="button">' + esc(t("flyIn")) + "</button>" +
      '<a class="g-secondary" href="tel:211">' + esc(t("call211short")) + "</a>" +
      "</div><h3>" + esc(t("why")) + '</h3><div class="g-comps">' + comps + "</div>" +
      "<h3>" + esc(t("programs")) + "</h3>" + programsHTML(r.state) +
      '<p><a href="tel:211" class="g-ink">' + esc(t("call211")) + "</a></p>" + sourcesHTML();
  }

  function legacyProfile() {
    var p = S.profile || {}, out = [];
    if ((p.situation || {}).car) out.push("car");
    if ((p.household || {}).kids) out.push("kids");
    return out.join(",");
  }

  function rateView() {
    var r = S.rating, pt = S.ratingPoint;
    var back = '<button class="g-back" data-go="back" type="button">&larr; ' + esc(t("back")) + "</button>";
    if (!pt) return back + "<h2>" + esc(t("rateTitle")) + "</h2><p>" + esc(t("rateHelpVa")) + "</p>";
    var stars = function (dim) {
      return '<div class="g-dim"><span id="dim-' + dim + '">' + esc(t(dim)) + '</span><div class="g-stars" role="group" aria-labelledby="dim-' + dim + '">' +
        [1, 2, 3, 4, 5].map(function (n) {
          return '<button type="button" data-star="' + dim + '" data-n="' + n + '" aria-pressed="' + (r[dim] === n) + '" aria-label="' + n + ' / 5">' + (r[dim] >= n ? "&#9733;" : "&#9734;") + "</button>";
        }).join("") + "</div></div>";
    };
    var tags = ["shelter_full", "shelter_had_beds", "police_moved_people", "welcoming_immigrants", "spanish_spoken", "pets_ok",
      "quiet_place_to_rest", "outlets_wifi", "clean_restrooms", "free_meals_nearby"].map(function (k) {
      return '<button type="button" class="g-chip" data-tag="' + k + '" aria-pressed="' + (r.tags.indexOf(k) !== -1) + '">' + esc(t("tag_" + k)) + "</button>";
    }).join("");
    var place = pt.fips && S.va ? S.va.localities[pt.fips].name : pt.lat.toFixed(2) + ", " + pt.lon.toFixed(2);
    return back + "<h2>" + esc(t("rateTitle")) + '</h2><p class="g-spot"><strong>' + esc(place) + "</strong><br>" + esc(t("changeSpot")) + "</p>" +
      stars("overall") + stars("safe") + stars("respect") + stars("help") +
      "<h3>" + esc(t("tags")) + '</h3><div class="g-chips">' + tags + "</div>" +
      '<div class="g-actions"><button class="g-primary g-wide" data-go="send" type="button"' + (r.overall ? "" : " disabled") + ">" + esc(t("send")) + "</button></div>";
  }

  // ---------------- interactions ----------------
  function bindView() {
    var sh = $(".g-sheet");
    sh.querySelectorAll("[data-go]").forEach(function (b) { b.addEventListener("click", function () { go(b.dataset.go); }); });
    sh.querySelectorAll("[data-state]").forEach(function (b) { b.addEventListener("click", function () { selectState(b.dataset.state, true); }); });
    sh.querySelectorAll("[data-fips]").forEach(function (b) { b.addEventListener("click", function () { selectLocality(b.dataset.fips, true); }); });
    sh.querySelectorAll("input[name=status]").forEach(function (i) {
      i.addEventListener("change", function () { draft().status = i.value; rerenderPriorities(); });
    });
    sh.querySelectorAll("[data-chip]").forEach(function (b) {
      b.addEventListener("click", function () {
        var parts = b.dataset.chip.split("."), d = draft();
        d[parts[0]] = d[parts[0]] || {};
        d[parts[0]][parts[1]] = !d[parts[0]][parts[1]];
        b.setAttribute("aria-pressed", d[parts[0]][parts[1]]);
        rerenderPriorities();
      });
    });
    sh.querySelectorAll("[data-age]").forEach(function (b) {
      b.addEventListener("click", function () {
        var d = draft();
        d.age_band = d.age_band === b.dataset.age ? null : b.dataset.age;
        sh.querySelectorAll("[data-age]").forEach(function (x) { x.setAttribute("aria-pressed", x.dataset.age === d.age_band); });
      });
    });
    sh.querySelectorAll("[data-bed]").forEach(function (b) {
      b.addEventListener("click", function () {
        var d = draft(); d.household = d.household || {};
        if (b.dataset.bed === "auto") delete d.household.bedrooms; else d.household.bedrooms = +b.dataset.bed;
        sh.querySelectorAll("[data-bed]").forEach(function (x) { x.setAttribute("aria-pressed", x === b); });
      });
    });
    sh.querySelectorAll("[data-crime]").forEach(function (b) {
      b.addEventListener("click", function () {
        draft().show_crime = b.dataset.crime === "1";
        sh.querySelectorAll("[data-crime]").forEach(function (x) { x.setAttribute("aria-pressed", x === b); });
        rerenderPriorities();
      });
    });
    bindPriorities(sh);
    sh.querySelectorAll("[data-star]").forEach(function (b) {
      b.addEventListener("click", function () {
        S.rating[b.dataset.star] = +b.dataset.n; render();
        var again = $('.g-sheet [data-star="' + b.dataset.star + '"][data-n="' + b.dataset.n + '"]');
        if (again) again.focus({ preventScroll: true });
      });
    });
    sh.querySelectorAll("[data-tag]").forEach(function (b) {
      b.addEventListener("click", function () {
        var i = S.rating.tags.indexOf(b.dataset.tag);
        if (i === -1) S.rating.tags.push(b.dataset.tag); else S.rating.tags.splice(i, 1);
        b.setAttribute("aria-pressed", i === -1);
      });
    });
    var q = sh.querySelector("#g-q");
    if (q) q.addEventListener("input", function () { filterList(sh, q); });
    var grip = sh.querySelector(".g-grip");
    if (grip) grip.addEventListener("click", function () {
      sh.classList.toggle("tall"); updatePeek();
      if (S.mapOk) S.map.easeTo({ padding: sheetPad(), duration: reduced ? 0 : 250 });
    });
  }

  var _draft = null;
  function draft() { if (!_draft) _draft = JSON.parse(JSON.stringify(S.profile || defaultProfile())); return _draft; }

  function rerenderPriorities() {
    var ol = $(".g-pri");
    if (!ol) return;
    var tmp = document.createElement("div");
    tmp.innerHTML = priorityBlock(draft());
    ol.replaceWith(tmp.querySelector(".g-pri"));
    bindPriorities($(".g-sheet"));
  }

  function bindPriorities(sh) {
    sh.querySelectorAll("[data-pri]").forEach(function (b) {
      b.addEventListener("click", function () {
        var d = draft(), order = currentOrder(d), k = b.dataset.pri, i = order.indexOf(k), j = i + (+b.dataset.dir);
        if (j < 0 || j >= order.length) return;
        order.splice(i, 1); order.splice(j, 0, k);
        if (isVa()) d.priorities = order; else d.priorities_us = order;
        rerenderPriorities();
        var again = $('.g-pri [data-pri="' + k + '"][data-dir="' + b.dataset.dir + '"]');
        if (again && !again.disabled) again.focus();
      });
    });
  }

  function setScope(scope) {
    S.scope = scope; store.set("footing.globe.scope", scope);
    S.selected = null; S.selectedPoint = null; S.layer = "fit";
    if (S.mapOk) { S.map.setFilter("va-selected", ["==", ["id"], ""]); S.map.setFilter("states-selected", ["==", ["get", "code"], ""]); }
    S.view = "top"; compute(); render(); flyHome(false); focusHeading();
  }

  function go(what) {
    if (what === "profile") { _draft = null; S.view = "profile"; render(); focusHeading(); return; }
    if (what === "skip") { S.view = "top"; compute(); render(); flyHome(false); return; }
    if (what === "save") {
      S.profile = draft(); _draft = null;
      store.set("footing.globe.profile", S.profile);
      S.view = "top"; compute(); render(); flyHome(false); focusHeading(); return;
    }
    if (what === "forget") {
      try {
        Object.keys(localStorage).filter(function (k) { return k.indexOf("footing.") === 0 && k !== "footing.lang"; })
          .forEach(function (k) { localStorage.removeItem(k); });
      } catch (e) { /* fine */ }
      S.profile = null; S.selectedPoint = null; S.ratingPoint = null;
      if (S.ratingMarker) { S.ratingMarker.remove(); S.ratingMarker = null; }
      _draft = null; S.view = "intro"; compute(); render(); toast(t("forgot")); return;
    }
    if (what === "list") { S.view = "list"; render(); return; }
    if (what === "locality-wide") { S.selectedPoint = null; render(); return; }
    if (what === "scope-us") { setScope("us"); return; }
    if (what === "scope-va") { setScope("va"); return; }
    if (what === "fly") {
      if (S.selected && S.mapOk && !isVa()) {
        var f = S.statesGeo.features.filter(function (x) { return x.properties.code === S.selected; })[0];
        fitTo(bboxOf(f), 9);
      }
      return;
    }
    if (what === "rate") {
      S.prevView = S.view; S.rating = { tags: [] }; S.ratingPoint = null; S.view = "rate"; render();
      if (S.mapOk) S.map.easeTo({ padding: sheetPad(), duration: reduced ? 0 : 250 });
      return;
    }
    if (what === "back") {
      if (S.ratingMarker) { S.ratingMarker.remove(); S.ratingMarker = null; }
      S.ratingPoint = null; S.view = S.prevView && S.prevView !== "rate" ? S.prevView : "top"; render(); focusHeading(); return;
    }
    if (what === "send") { sendRating(); return; }
  }

  function focusHeading() { var h = $(".g-sheet h1, .g-sheet h2"); if (h) h.focus({ preventScroll: true }); }

  function selectState(code, fly) {
    S.selected = code; S.view = "state"; render();
    if (fly) flyToState(code);
    focusHeading();
  }

  function selectLocality(fips, fly, pt) {
    if (!S.byFips[fips]) return;
    S.selectedPoint = pt && pt.ok && pt.fips === fips ?
      { fips: fips, tile: pt.tile, validity: pt.validity } : null;
    S.selected = fips; S.view = "locality"; render();
    if (S.mapOk) S.map.setFilter("va-selected", ["==", ["id"], fips]);
    if (fly) flyToLocality(fips);
    focusHeading();
  }

  /** Check a point the same way footing/va.py does, so the phone and the server agree on what is usable.
   *  The shoreline file is not loaded on the phone (it is large and only the open-water case needs it);
   *  footing/ratings.py re-checks with it before storing, so a water tap is still refused, just later. */
  function checkPoint(lat, lon) {
    if (!VaPoint || !S.vaGeo) return { ok: !!localityAt(lat, lon), fips: localityAt(lat, lon),
      tile: VaFit.tileOf(lat, lon), code: "ok", issues: [], validity: 1 };
    var pt = VaPoint.checkPoint(S.vaGeo, lat, lon, {
      stateAt: function (la, lo) { return stateCodeAt(la, lo); },
      stateName: S.policy && S.policy.states ? stateNames() : null,
    });
    if (pt.ok) pt.tile = VaFit.tileOf(lat, lon);
    return pt;
  }

  function stateNames() {
    if (!S._stateNames) {
      S._stateNames = {};
      Object.keys(S.policy.states).forEach(function (c) { S._stateNames[c] = S.policy.states[c].name; });
    }
    return S._stateNames;
  }

  function stateCodeAt(lat, lon) {
    if (!S.statesGeo) return null;
    for (var i = 0; i < S.statesGeo.features.length; i++) {
      var f = S.statesGeo.features[i], b = f.properties.bbox;
      if (b && (lon < b[0] || lon > b[2] || lat < b[1] || lat > b[3])) continue;
      if (inFeature(lon, lat, f)) return f.properties.code || null;
    }
    return null;
  }

  /** A tap while rating: far out, zoom in on the tap first; close in, check it is in Virginia and drop the pin. */
  function rateTap(lat, lon) {
    var pt = checkPoint(lat, lon);
    // Say what is actually wrong with the spot ("that is in Maryland", "that is on open water") instead of
    // one catch-all message. The engine writes these in English; t() covers the ones we have translated.
    // A tap can only be outside Virginia or on water (swapped or non-numeric coordinates need typing); both are
    // translated. Anything else falls back to the engine's English reason rather than a wrong sentence.
    var TAP = { outside_virginia: "outsideTap", open_water: "waterTap" };
    if (!pt.ok) { toast(TAP[pt.code] ? t(TAP[pt.code]) : pt.reason || t("outsideTap")); return; }
    if (S.map.getZoom() < 10) {
      S.map.flyTo({ center: [lon, lat], zoom: 12, duration: reduced ? 0 : 1600, essential: true });
      toast(t("tapZoom"));
      return;
    }
    setRatingPoint(lat, lon, pt.fips, pt);
  }

  function setRatingPoint(lat, lon, fips, pt) {
    pt = pt || checkPoint(lat, lon);
    S.ratingPoint = { lat: lat, lon: lon, fips: fips || localityAt(lat, lon), issues: pt.ok ? pt.issues : [] };
    if (S.ratingMarker) S.ratingMarker.remove();
    var el = document.createElement("div"); el.className = "g-pin";
    if (S.map) S.ratingMarker = new maplibregl.Marker({ element: el }).setLngLat([lon, lat]).addTo(S.map);
    render();
  }

  function deviceToken() {
    var d = store.get("footing.device", null);
    if (!d) {
      var a = new Uint8Array(16); (window.crypto || {}).getRandomValues ? crypto.getRandomValues(a) : a.forEach(function (_, i) { a[i] = Math.random() * 256; });
      d = Array.prototype.map.call(a, function (x) { return ("0" + x.toString(16)).slice(-2); }).join("");
      store.set("footing.device", d);
    }
    return d;
  }

  function sendRating() {
    var r = S.rating, pt = S.ratingPoint;
    if (!pt || !r.overall) return;
    // Only these fields leave the phone. No status, no profile, no free text.
    var body = { lat: pt.lat, lon: pt.lon, device: deviceToken(), overall: r.overall, tags: r.tags };
    ["safe", "respect", "help"].forEach(function (d) { if (r[d]) body[d] = r[d]; });
    (B.rate ? B.rate(body) : fetch(API + "/ratings", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) })
      .then(function (res) { return res.json().then(function (j) { if (!res.ok) throw new Error(j.detail || "error"); return j; }); }))
      .then(function (j) {
        if (S.ratingMarker) { S.ratingMarker.remove(); S.ratingMarker = null; }
        var fips = j.fips || pt.fips;
        toast(j.shared === false ? t("sentLocal") : t("ratedThanks", { place: fips ? S.va.localities[fips].name : "" }));
        S.ratingPoint = null;
        return loadHeat().then(function () {
          compute(); paintHeat();
          if (isVa() && fips) selectLocality(fips, false, checkPoint(pt.lat, pt.lon)); else { S.view = S.prevView || "top"; render(); }
        });
      })
      .catch(function (e) { toast(navigator.onLine === false ? t("rateNeedsServer") : e.message); });
  }

  function toast(msg) {
    var old = $(".g-toast"); if (old) old.remove();
    var d = document.createElement("div"); d.className = "g-toast"; d.setAttribute("role", "status"); d.textContent = msg;
    $("#globe-root").appendChild(d);
    setTimeout(function () { d.remove(); }, 4200);
  }

  function bindChrome() {
    var lang = $("#g-lang");
    if (lang.tagName === "SELECT") lang.addEventListener("change", function () { S.lang = lang.value; store.set("footing.lang", S.lang); render(); if (S.mapOk) S.map.easeTo({ padding: sheetPad(), duration: 0 }); });
    else lang.addEventListener("click", function () { S.lang = S.lang === "es" ? "en" : "es"; store.set("footing.lang", S.lang); render(); });
    $("#g-hide").addEventListener("click", function () {
      try { sessionStorage.clear(); } catch (e) { /* fine */ }
      if (B.hide) B.hide(); else location.replace("https://www.weather.gov/");
    });
    $("#g-listbtn").addEventListener("click", function () {
      S.view = S.view === "list" ? (S.selected ? (isVa() ? "locality" : "state") : "top") : "list"; render();
    });
    $("#g-layer").addEventListener("change", function (e) {
      S.layer = e.target.value; paint(); paintHeat(); render();
      if (S.layer === "community" && !(S.heat && S.heat.total)) toast(t("noRatings"));
    });
    window.addEventListener("resize", function () { drawStars(); updatePeek(); });
    if (DESK.addEventListener) DESK.addEventListener("change", function () {
      if (!S.va) return;
      render();
      if (S.view === "locality" && S.selected) flyToLocality(S.selected); else flyHome(true);
    });
    window.addEventListener("online", function () { S.map && S.map.triggerRepaint(); });
  }

  // ---------------- lifecycle ----------------
  var started = false;
  function start() {
    started = true;
    drawStars();
    bindChrome();
    renderChrome();
    var base = B.dataBase || "data/";
    var loads = [B.policy ? B.policy() : getJSON(API + "/policy"), getJSON(base + "states-10m.json"), getJSON(base + "countries-110m.json"),
      B.va ? B.va() : getJSON(API + "/va"), getJSON(base + "va-localities.json")];
    Promise.all(loads).then(function (res) {
      S.policy = res[0].states; S.elig = res[0].eligibility; S.va = res[3];
      var vt = res[4];
      S.vaGeo = window.topojson.feature(vt, vt.objects.localities);
      S.vaGeo.features.forEach(function (f) { f.properties.fips = f.id; f.properties.bbox = bboxOf(f); f.properties.v = -1; f.properties.known = false; });
      Object.keys(S.va.localities).forEach(function (f) { S.va.localities[f].fips = f; });
      return Promise.all([loadHeat(), (B.towns ? B.towns() : getJSON(API + "/healthz")).then(function (h) {
        S.recorded = (h.recorded || []).map(function (r) {
          var m = /,\s*([A-Z]{2})$/.exec(r.label);
          return { label: r.label.replace(/^Downtown /, ""), lat: r.lat, lon: r.lon, set: r.set, state: m ? m[1] : null };
        });
      }).catch(function () { S.recorded = []; })]).then(function () { return res; });
    }).then(function (res) {
      compute();
      if (S.profile) S.view = "top";
      if (webglOk() && window.maplibregl) {
        buildMap(res[1], res[2]);
      } else {
        $(".g-loading") && $(".g-loading").remove();
        S.view = "list"; toast(t("noWebgl"));
      }
      if (pendingRate) { var pr = pendingRate; pendingRate = null; openRateAt(pr.lat, pr.lon); }
      render();
    }).catch(function (e) {
      $(".g-loading").textContent = e.message;
    });
  }

  var pendingRate = null;
  function openRateAt(lat, lon) {
    S.prevView = S.view === "rate" ? "top" : S.view;
    S.rating = { tags: [] }; S.view = "rate";
    var fips = localityAt(lat, lon);
    var go2 = function () { S.map.jumpTo({ center: [lon, lat], zoom: 12 }); if (fips) setRatingPoint(lat, lon, fips); else toast(t("outsideTap")); };
    if (S.mapOk) go2(); else if (S.map) S.map.once("load", go2); else if (fips) S.ratingPoint = { lat: lat, lon: lon, fips: fips };
    render();
  }

  window.FootingGlobe = {
    show: function (opts) {
      opts = opts || {};
      $("#globe-root").hidden = false;
      document.body.classList.add("on-globe");
      if (!started) { if (opts.rate) pendingRate = opts.rate; start(); return; }
      if (opts.rate) openRateAt(opts.rate.lat, opts.rate.lon);
      if (S.map) S.map.resize();
      render();
    },
    hide: function () {
      var root = $("#globe-root");
      if (root) root.hidden = true;
      document.body.classList.remove("on-globe");
      stopSpin();
    },
    /** Re-read ratings (the standalone page calls this when its shared store changes). */
    refreshHeat: function () {
      return loadHeat().then(function () { if (!S.policy) return; compute(); if (S.mapOk) paintHeat(); render(); });
    },
    localityAt: localityAt,
    _state: S,
  };
})();
