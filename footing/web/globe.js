/* Footing globe: from space down to your town.
 *
 * Every state is colored by a Fit Score computed ON THIS PHONE from public policy data (fit.js). The person's
 * status and situation are kept in localStorage and never sent to the server; the only things this screen
 * sends are a community rating (1-5 stars + fixed tags + a ~1 km tile) when the person chooses to rate a place.
 *
 * Works offline: states, countries and counties are bundled (us-atlas / world-atlas, public domain data).
 * When online, Sentinel-2 cloudless imagery (EOX) and CARTO labels fade in as you zoom toward the ground.
 */
(function () {
  "use strict";
  var Fit = window.FootingFit, I = window.FootingI18n;
  var API = "api";
  // Optional host adapter (the standalone demo page sets one; the app uses the Footing API).
  // {policy(), heat(), rate(body), towns(), receipt(town), hide(), dataBase, standalone, noImagery}
  var B = window.FootingBackend || {};
  var RAMP = ["#1b2440", "#2d4a6b", "#3f7c85", "#9cb07a", "#f2c14e", "#fff1c9"];
  var COMP_IDS = ["access", "affordability", "shelter", "safety", "criminalization", "community"];
  var LAYERS = ["fit", "community", "shelter", "affordability", "safety"];
  var IMAGERY = "https://tiles.maps.eox.at/wmts/1.0.0/s2cloudless-2020_3857/default/g/{z}/{y}/{x}.jpg";
  var LABELS = ["a", "b", "c", "d"].map(function (s) { return "https://" + s + ".basemaps.cartocdn.com/dark_only_labels/{z}/{x}/{y}.png"; });
  var US_BOUNDS = [[-124.8, 24.4], [-66.9, 49.4]];   // contiguous U.S.
  var KINDS = { snap_retailer: "#f2c14e", library: "#8fd6a8", clinic: "#ff9e8a", health_center: "#ff9e8a", pharmacy: "#ff9e8a",
    post_office: "#a7b1c6", toilets: "#7fc6e8", drinking_water: "#7fc6e8", food_bank: "#f2c14e", soup_kitchen: "#f2c14e",
    shelter: "#fff1c9", day_center: "#fff1c9", laundry: "#a7b1c6", employment_agency: "#a7b1c6", school: "#9cb07a" };

  var store = {
    get: function (k, d) { try { var v = localStorage.getItem(k); return v ? JSON.parse(v) : d; } catch (e) { return d; } },
    set: function (k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) { /* private mode: fine */ } },
    del: function (k) { try { localStorage.removeItem(k); } catch (e) { /* fine */ } },
  };
  var reduced = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  var S = {
    lang: store.get("footing.lang", ((navigator.language || "en").slice(0, 2) === "es") ? "es" : "en"),
    profile: store.get("footing.globe.profile", null),
    view: "intro", layer: "fit", selected: null, listMode: false,
    policy: null, elig: null, community: {}, heat: null, ranked: [], byCode: {},
    map: null, mapOk: false, statesGeo: null, recorded: [], ratingPoint: null, rating: { tags: [] },
    lit: 99, spinning: false, markers: [], ratingMarker: null, receiptTile: null,
  };
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
  function fillExpr() {
    return ["interpolate", ["linear"], ["get", "v"], 0, RAMP[0], 20, RAMP[1], 40, RAMP[2], 60, RAMP[3], 80, RAMP[4], 100, RAMP[5]];
  }
  function defaultProfile() {
    return { status: "undisclosed", household: {}, situation: {}, age_band: null, priorities: [] };
  }

  // ---------------- data ----------------
  function getJSON(url) {
    return fetch(url).then(function (r) { if (!r.ok) throw new Error(url + " " + r.status); return r.json(); });
  }
  function loadHeat() {
    return (B.heat ? B.heat() : getJSON(API + "/ratings/heat")).then(function (h) {
      S.heat = h;
      S.community = {};
      Object.keys(h.states || {}).forEach(function (st) { S.community[st] = h.states[st]; });
    }).catch(function () { S.heat = null; });
  }

  function compute() {
    var profile = S.profile || defaultProfile();
    S.ranked = Fit.rankStates(S.elig, S.policy, profile, S.community, { samples: 200 });
    S.byCode = {};
    S.ranked.forEach(function (r) { S.byCode[r.state] = r; });
    paintStates();
  }

  function layerValue(r) {
    if (!r) return null;
    if (S.layer === "fit") return r.score;
    var c = null;
    r.components.forEach(function (x) { if (x.id === S.layer) c = x; });
    if (S.layer === "safety" && !c) {   // citizens: show the law anyway when they ask for this layer
      var st = S.policy.states[r.state];
      return Math.round(1000 * (9 - st.enforcement_tier) / 8) / 10;
    }
    return c ? c.score : null;
  }

  function paintStates() {
    if (!S.statesGeo) return;
    S.statesGeo.features.forEach(function (f) {
      var r = S.byCode[f.properties.code];
      var v = layerValue(r);
      var lit = r && r.rank ? r.rank <= S.lit : true;
      f.properties.v = v === null ? -1 : (lit ? v : 0);
      f.properties.known = v !== null;
      f.properties.rank = r && r.rank ? r.rank : 0;
    });
    if (S.mapOk && S.map.getSource("states")) S.map.getSource("states").setData(S.statesGeo);
  }

  function lightUp() {
    if (reduced) { S.lit = 99; paintStates(); return; }
    S.lit = 0;
    var tick = function () {
      S.lit += 2;
      paintStates();
      if (S.lit < 52) setTimeout(tick, 45);
    };
    tick();
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

  function sheetPad() {
    var wide = window.innerWidth >= 900, sh = $(".g-sheet");
    var h = sh ? sh.offsetHeight : 200;
    return wide ? { top: 90, bottom: 40, left: 440, right: 40 } : { top: 70, bottom: Math.min(h, window.innerHeight * 0.6) + 20, left: 20, right: 20 };
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
    return [[b[0], b[1]], [b[2], b[3]]];
  }

  function buildMap(states, countries) {
    var topo = window.topojson;
    S.statesGeo = topo.feature(states, states.objects.states);
    var fips = {};
    Object.keys(S.policy.states).forEach(function (code) { fips[S.policy.states[code].fips] = code; });
    S.statesGeo.features = S.statesGeo.features.filter(function (f) { return fips[f.id]; });
    S.statesGeo.features.forEach(function (f) { f.properties.code = fips[f.id]; f.properties.v = -1; f.properties.known = false; });
    var land = topo.feature(countries, countries.objects.countries);
    var map = new maplibregl.Map({
      container: "globe-map",
      style: {
        version: 8,
        projection: { type: "globe" },
        sources: {
          land: { type: "geojson", data: land },
          states: { type: "geojson", data: S.statesGeo },
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
          { id: "states-line", type: "line", source: "states", paint: { "line-color": "rgba(5,7,15,0.9)",
            "line-width": ["interpolate", ["linear"], ["zoom"], 2, 0.6, 7, 1.6] } },
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
      }
      S.mapOk = true;
      paintStates();
      paintHeat();
      $(".g-loading") && $(".g-loading").remove();
      if (S.profile) flyUS(true); else { frameIntro(); startSpin(); }
    });
    map.on("error", function () { /* imagery tiles fail offline; bundled layers keep working */ });
    map.on("click", "states-known", onStateClick);
    map.on("click", "states-unknown", onStateClick);
    map.on("click", function (e) {
      if (S.view !== "rate") return;
      // A tap at country or state zoom is tens of km off, so zoom in first and ask for a second, exact tap.
      if (map.getZoom() < 8) { map.flyTo({ center: e.lngLat, zoom: 11, duration: reduced ? 0 : 1200, essential: true }); toast(t("tapCloser")); return; }
      setRatingPoint(e.lngLat.lat, e.lngLat.lng);
    });
    ["mousedown", "touchstart", "wheel"].forEach(function (ev) { map.on(ev, stopSpin); });
    map.on("mouseenter", "states-known", function () { map.getCanvas().style.cursor = "pointer"; });
    map.on("mouseleave", "states-known", function () { map.getCanvas().style.cursor = ""; });
    map.on("zoomend", function () { if (map.getZoom() >= 10.5) showTownPlaces(); });
  }

  function onStateClick(e) {
    if (S.view === "rate" && S.map.getZoom() >= 8) return;
    var f = e.features && e.features[0];
    if (f) selectState(f.properties.code, true);
  }

  function frameIntro() {
    // Whole Earth, centered in the space above the sheet.
    var pad = sheetPad(), h = window.innerHeight - pad.top - pad.bottom, w = window.innerWidth - pad.left - pad.right;
    var px = Math.max(160, Math.min(h, w) * 0.86);           // globe diameter we want on screen
    var zoom = Math.log2(px / (512 / Math.PI)) ;              // globe diameter ~ 512/pi * 2^zoom px at zoom z
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

  function flyUS(quick) {
    stopSpin();
    if (!S.mapOk) return;
    S.map.setPadding(sheetPad());                         // the sheet's space lives in the map padding
    var cam = S.map.cameraForBounds(US_BOUNDS, { padding: 16 });
    if (!cam) { lightUp(); return; }
    var opts = { center: cam.center, zoom: cam.zoom, bearing: 0, essential: true };
    if (reduced || quick) { S.map.jumpTo(opts); lightUp(); return; }
    opts.duration = 3200; opts.curve = 1.6;
    S.map.once("moveend", lightUp);
    S.map.flyTo(opts);
  }

  function flyToState(code) {
    if (!S.mapOk) return;
    var f = S.statesGeo.features.filter(function (x) { return x.properties.code === code; })[0];
    if (!f) return;
    S.map.setFilter("states-selected", ["==", ["get", "code"], code]);
    S.map.setPadding(sheetPad());
    S.map.fitBounds(bboxOf(f), { padding: 16, duration: reduced ? 0 : 1800, maxZoom: 7.5, essential: true });
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
          el.style.cssText = "width:16px;height:16px;border-radius:50%;border:2px solid #05070f;padding:0;cursor:pointer;background:" + (KINDS[kind] || "#a7b1c6");
          el.setAttribute("aria-label", p.name + " (" + kind.replace(/_/g, " ") + ")");
          el.title = p.name;
          var pop = new maplibregl.Popup({ offset: 12, closeButton: false }).setHTML(
            '<div style="color:#10131c;font:13px var(--sans)"><strong>' + esc(p.name) + "</strong><br>" + esc(kind.replace(/_/g, " ")) +
            (p.walk_min != null ? " · " + Math.round(p.walk_min) + " min walk" : "") +
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
    var html = { intro: introView, profile: profileView, top: topView, list: listView, state: stateView, rate: rateView }[S.view]();
    // The rating form stays short until a spot is picked, so the map is big enough to tap on a phone.
    var tall = S.view === "profile" || S.view === "list" || (S.view === "rate" && S.ratingPoint);
    sh.className = "g-sheet" + (tall ? " tall" : "");
    sh.innerHTML = '<button class="g-grip" aria-label="Resize panel" type="button"></button>' + html;
    if (S.lastView !== S.view || S.lastSelected !== S.selected) sh.scrollTop = 0;   // a new view starts at its title
    S.lastView = S.view; S.lastSelected = S.selected;
    bindView();
    renderChrome();
    var h = sh.querySelector("h1, h2");
    if (h) { h.setAttribute("tabindex", "-1"); }
    updatePeek();
  }

  function updatePeek() {
    var sh = $(".g-sheet");
    if (sh) document.documentElement.style.setProperty("--sheet-peek", Math.min(sh.offsetHeight, window.innerHeight * 0.86) + "px");
  }

  function renderChrome() {
    $(".g-legend").hidden = S.view === "intro" || S.view === "profile" || S.view === "rate";
    $("#g-lang").textContent = t("lang");
    $("#g-hide").textContent = t("hideShort");
    $("#g-hide").setAttribute("aria-label", t("hideLong"));
    $("#g-listbtn").textContent = S.view === "list" ? t("map") : t("list");
    var sel = $("#g-layer");
    sel.setAttribute("aria-label", t("layer"));
    sel.innerHTML = LAYERS.map(function (l) { return '<option value="' + l + '"' + (l === S.layer ? " selected" : "") + ">" + esc(t("l_" + l)) + "</option>"; }).join("");
    $("#g-low").textContent = S.layer === "fit" ? t("legendLow") : t("lo_" + S.layer);
    $("#g-high").textContent = S.layer === "fit" ? t("legendHigh") : t("hi_" + S.layer);
    $("#g-unk").textContent = t("legendUnknown");
    document.documentElement.lang = S.lang;
  }

  var LOCK = '<svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true"><rect x="3" y="7" width="10" height="8" rx="2" fill="currentColor"/><path d="M5 7V5a3 3 0 0 1 6 0v2" stroke="currentColor" stroke-width="1.6" fill="none"/></svg>';

  function introView() {
    return "<h1>" + esc(t("title")) + "</h1><p>" + esc(t("lede")) + "</p>" +
      '<div class="g-lock">' + LOCK + "<span>" + esc(t("privacy")) + "</span></div>" +
      '<div class="g-actions"><button class="g-primary" data-go="profile" type="button">' + esc(t("start")) + "</button>" +
      '<button class="g-secondary" data-go="skip" type="button">' + esc(t("skip")) + "</button>" +
      (B.standalone ? "" : '<a class="g-secondary" href="#/start">' + esc(t("nearMe")) + "</a>") +
      '<a class="g-secondary" href="tel:211">' + esc(t("call211short")) + "</a></div>";
  }

  function profileView() {
    var p = S.profile || defaultProfile(), hh = p.household || {}, sit = p.situation || {};
    var statuses = S.elig.statuses.map(function (s) {
      return '<label><input type="radio" name="status" value="' + s.id + '"' + (p.status === s.id ? " checked" : "") + "> " +
        esc(S.lang === "es" ? s.label_es : s.label) + "</label>";
    }).join("");
    var chip = function (group, key) {
      var on = group === "household" ? !!hh[key] : !!sit[key];
      return '<button type="button" class="g-chip" data-chip="' + group + "." + key + '" aria-pressed="' + on + '">' + esc(t(key)) + "</button>";
    };
    var ages = [["18_24", "age18"], ["25_49", "age25"], ["50_61", "age50"], ["62_plus", "age62"]].map(function (a) {
      return '<button type="button" class="g-chip" data-age="' + a[0] + '" aria-pressed="' + (p.age_band === a[0]) + '">' + esc(t(a[1])) + "</button>";
    }).join("");
    return "<h2>" + esc(t("aboutYou")) + '</h2><div class="g-lock">' + LOCK + "<span>" + esc(t("privacy")) + "</span></div>" +
      '<fieldset style="border:0;padding:0;margin:0"><legend><h3 style="margin-top:6px">' + esc(t("statusQ")) + "</h3></legend>" +
      "<p>" + esc(t("statusHelp")) + '</p><div class="g-status">' + statuses + "</div></fieldset>" +
      "<h3>" + esc(t("whoQ")) + '</h3><div class="g-chips">' + ["kids", "pregnant", "partner", "pets", "mixed"].map(function (k) { return chip("household", k); }).join("") + "</div>" +
      "<h3>" + esc(t("situationQ")) + '</h3><div class="g-chips">' + ["tonight", "car", "no_id", "veteran", "disability"].map(function (k) { return chip("situation", k); }).join("") + "</div>" +
      "<h3>" + esc(t("ageQ")) + '</h3><div class="g-chips">' + ages + "</div>" +
      priorityBlock(p) +
      '<div class="g-actions"><button class="g-primary g-wide" data-go="save" type="button">' + esc(t("showMap")) + "</button>" +
      '<button class="g-secondary g-wide" data-go="forget" type="button">' + esc(t("forget")) + "</button></div>";
  }

  function currentOrder(p) {
    var comps = {}, prof = p || S.profile || defaultProfile();
    var sample = Fit.components(S.elig, S.policy, "VA", prof, S.community);
    Object.keys(sample).forEach(function (k) { comps[k] = sample[k]; });
    var def = Fit.defaultPriorities(S.elig, prof);
    var chosen = (prof.priorities || []).filter(function (k) { return def.indexOf(k) !== -1; });
    def.forEach(function (k) { if (chosen.indexOf(k) === -1) chosen.push(k); });
    return chosen.filter(function (k) { return comps[k] !== undefined; });
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

  function scoreBadge(score, small) {
    if (score === null || score === undefined) return '<div class="g-badge unknown">?<small>' + esc(t("unknownWhy")) + "</small></div>";
    return '<div class="g-badge" style="background:' + rampColor(score) + '">' + Math.round(score) + (small ? "" : "<small>/ 100</small>") + "</div>";
  }

  function rowHTML(r) {
    var v = layerValue(r);
    var unk = v === null;
    return '<li><button type="button" class="g-row" data-state="' + r.state + '"><span class="r">' + (r.rank ? "#" + r.rank : "") + "</span>" +
      "<span>" + esc(r.name) + (S.layer === "fit" && r.rank_p10 ? '<span class="sub">' + esc(r.rank_p10 === r.rank_p90 ? t("fixedShort", { a: r.rank_p10 }) : t("rangeShort", { a: r.rank_p10, b: r.rank_p90 })) + "</span>" : "") + "</span>" +
      '<span class="s' + (unk ? " unknown" : "") + '" style="' + (unk ? "" : "background:" + rampColor(v)) + '">' + (unk ? "?" : Math.round(v)) + "</span></button></li>";
  }

  function sortedForLayer() {
    return S.ranked.slice().sort(function (a, b) {
      var va = layerValue(a), vb = layerValue(b);
      if (va === null && vb === null) return a.name < b.name ? -1 : 1;
      if (va === null) return 1;
      if (vb === null) return -1;
      return vb - va || (a.name < b.name ? -1 : 1);
    });
  }

  function topView() {
    var top = sortedForLayer().slice(0, 5);
    var p = S.profile;
    var who = p ? (S.elig.statuses.filter(function (s) { return s.id === p.status; })[0] || {}) : {};
    return "<h2>" + esc(t("top")) + "</h2>" +
      (p ? '<p>' + esc(S.lang === "es" ? who.label_es : who.label) + '</p>' : "") +
      '<ul class="g-list">' + top.map(rowHTML).join("") + "</ul>" +
      '<div class="g-actions"><button class="g-secondary" data-go="list" type="button">' + esc(t("allStates")) + "</button>" +
      '<button class="g-secondary" data-go="profile" type="button">' + esc(p ? t("editAboutYou") : t("start")) + "</button></div>";
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
      return "<li><span>" + esc(S.lang === "es" ? g.label_es : g.label) + '</span><span class="v ' + rule.value + '">' + esc(t(rule.value)) + "</span>" +
        (note ? '<span class="note">' + esc(note) + "</span>" : "") + "</li>";
    });
    if (!undisclosed) {
      var dl = st.drivers_license_all;
      var lawful = ["undocumented", "unsure"].indexOf(p.status) === -1;
      var val = lawful ? "yes" : (dl ? "yes" : "no");
      rows.push("<li><span>" + esc(S.lang === "es" ? "Licencia o identificación estatal" : "Driver's license or state ID") + '</span><span class="v ' + val + '">' + esc(t(val)) + "</span>" +
        '<span class="note">' + esc(lawful ? "With your documents." : (dl ? "This state issues a " + dl.form + " regardless of status (since " + dl.year + ")." : "This state requires proof of lawful presence.")) + "</span></li>");
    }
    var pc = Fit.programRule(S.elig, "public_charge", p.status);
    var caution = (!undisclosed && pc.value === "limited") ? '<div class="g-caution"><strong>' + esc(t("caution")) + ":</strong> " + esc(pc.note) +
      '<br><a href="https://www.immigrationadvocates.org/legaldirectory/" target="_blank" rel="noopener">' + esc(t("legal")) + "</a></div>" : "";
    return caution + '<ul class="g-progs">' + rows.join("") + "</ul>";
  }

  function sourcesHTML() {
    var srcs = S.policy.sources;
    return '<details class="g-src"><summary>' + esc(t("sources")) + "</summary><ul>" + Object.keys(srcs).map(function (k) {
      var s = srcs[k];
      return '<li><a href="' + esc(s.url) + '" target="_blank" rel="noopener">' + esc(s.title) + "</a>, " + esc(s.publisher) + " (" + esc(t("asOf")) + " " + esc(s.as_of) + ")</li>";
    }).join("") + "</ul></details>";
  }

  function stateView() {
    var r = S.byCode[S.selected];
    if (!r) return "";
    var town = S.recorded.filter(function (x) { return x.state === r.state; })[0];
    var comps = r.components.map(function (c) {
      var unk = c.score === null;
      return '<div class="g-comp"><span class="name">' + esc(t("c_" + c.id)) + "<em>" + Math.round(100 * c.weight) + "%</em></span>" +
        '<span class="num">' + (unk ? "?" : Math.round(c.score)) + "</span>" +
        '<span class="track' + (unk ? " unknown" : "") + '">' + (unk ? "" : '<span class="fill" style="display:block;width:' + c.score + "%;background:" + rampColor(c.score) + '"></span>') + "</span>" +
        '<span class="why">' + esc(I.reason ? I.reason(S.lang, c.reason) : c.reason) + "</span></div>";
    }).join("");
    var rankLine = r.rank ? "<strong>" + esc(t("rank")) + " #" + r.rank + "</strong> " + esc(t("of")) + " " + S.ranked.filter(function (x) { return x.rank; }).length : "";
    return '<h2 id="g-state-title">' + esc(r.name) + "</h2>" +
      '<div class="g-score">' + scoreBadge(r.score) + '<div class="g-meta">' + esc(t("fit")) + "<br>" + rankLine +
      "<br>" + esc(t("confidence")) + ": <strong>" + esc(t("conf_" + r.confidence_label)) + "</strong>" +
      (r.rank_p10 ? '<br><span>' + esc(r.rank_p10 === r.rank_p90 ? t("rankFixed", { a: r.rank_p10 }) : t("rankRange", { a: r.rank_p10, b: r.rank_p90 })) + "</span>" : "") + "</div></div>" +
      '<div class="g-actions"><button class="g-secondary" data-go="fly" type="button">' + esc(t("flyIn")) + "</button>" +
      '<button class="g-secondary" data-go="rate" type="button">' + esc(t("rateHere")) + "</button>" +
      (town && !B.standalone ? '<a class="g-primary g-wide" href="#/receipt?' + new URLSearchParams({ lat: town.lat, lon: town.lon, profile: legacyProfile() }) + '">' + esc(t("openReceipt", { town: town.label })) + "</a>" : "") +
      "</div><h3>" + esc(t("why")) + '</h3><div class="g-comps">' + comps + "</div>" +
      "<h3>" + esc(t("programs")) + "</h3>" + programsHTML(r.state) +
      '<p><a href="tel:211" style="color:var(--g-ink)">' + esc(t("call211")) + "</a></p>" + sourcesHTML();
  }

  function legacyProfile() {
    var p = S.profile || {}, out = [];
    if ((p.situation || {}).car) out.push("car");
    if ((p.household || {}).kids) out.push("kids");
    return out.join(",");
  }

  function rateView() {
    var r = S.rating;
    var stars = function (dim) {
      return '<div class="g-dim"><span>' + esc(t(dim)) + '</span><div class="g-stars" role="group" aria-label="' + esc(t(dim)) + '">' +
        [1, 2, 3, 4, 5].map(function (n) {
          return '<button type="button" data-star="' + dim + '" data-n="' + n + '" aria-pressed="' + (r[dim] === n) + '" aria-label="' + n + ' / 5">' + (r[dim] >= n ? "&#9733;" : "&#9734;") + "</button>";
        }).join("") + "</div></div>";
    };
    var tags = ["shelter_full", "shelter_had_beds", "police_moved_people", "welcoming_immigrants", "spanish_spoken", "pets_ok",
      "quiet_place_to_rest", "outlets_wifi", "clean_restrooms", "free_meals_nearby"].map(function (k) {
      return '<button type="button" class="g-chip" data-tag="' + k + '" aria-pressed="' + (r.tags.indexOf(k) !== -1) + '">' + esc(t("tag_" + k)) + "</button>";
    }).join("");
    if (!S.ratingPoint) {
      return "<h2>" + esc(t("rateTitle")) + '</h2><p class="g-pick"><strong>' + esc(t("pickSpot")) + "</strong></p><p>" + esc(t("rateHelp")) + "</p>" +
        '<div class="g-actions"><button class="g-secondary g-wide" data-go="back" type="button">' + esc(t("back")) + "</button></div>";
    }
    var where = S.ratingPoint ? '<p><strong style="color:var(--g-ink)">' + S.ratingPoint.lat.toFixed(2) + ", " + S.ratingPoint.lon.toFixed(2) + "</strong></p>"
      : "<p>" + esc(t("pickSpot")) + "</p>";
    return "<h2>" + esc(t("rateTitle")) + "</h2><p>" + esc(t("rateHelp")) + "</p>" + where +
      stars("overall") + stars("safe") + stars("respect") + stars("help") +
      "<h3>" + esc(t("tags")) + '</h3><div class="g-chips">' + tags + "</div>" +
      '<div class="g-actions"><button class="g-primary g-wide" data-go="send" type="button"' + (S.ratingPoint && r.overall ? "" : " disabled") + ">" + esc(t("send")) + "</button></div>";
  }

  // ---------------- interactions ----------------
  function bindView() {
    var sh = $(".g-sheet");
    sh.querySelectorAll("[data-go]").forEach(function (b) { b.addEventListener("click", function () { go(b.dataset.go); }); });
    sh.querySelectorAll("[data-state]").forEach(function (b) { b.addEventListener("click", function () { selectState(b.dataset.state, true); }); });
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
    bindPriorities(sh);
    sh.querySelectorAll("[data-star]").forEach(function (b) {
      b.addEventListener("click", function () { S.rating[b.dataset.star] = +b.dataset.n; render(); });
    });
    sh.querySelectorAll("[data-tag]").forEach(function (b) {
      b.addEventListener("click", function () {
        var i = S.rating.tags.indexOf(b.dataset.tag);
        if (i === -1) S.rating.tags.push(b.dataset.tag); else S.rating.tags.splice(i, 1);
        b.setAttribute("aria-pressed", i === -1);
      });
    });
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
        d.priorities = order;
        rerenderPriorities();
        var again = $('.g-pri [data-pri="' + k + '"][data-dir="' + b.dataset.dir + '"]');
        if (again && !again.disabled) again.focus();
      });
    });
  }

  function go(what) {
    if (what === "profile") { _draft = null; S.view = "profile"; render(); focusHeading(); return; }
    if (what === "skip") { S.view = "top"; compute(); render(); flyUS(false); return; }
    if (what === "save") {
      S.profile = draft(); _draft = null;
      store.set("footing.globe.profile", S.profile);
      S.view = "top"; compute(); render(); flyUS(false); focusHeading(); return;
    }
    if (what === "forget") {
      try {
        Object.keys(localStorage).filter(function (k) { return k.indexOf("footing.") === 0 && k !== "footing.lang"; })
          .forEach(function (k) { localStorage.removeItem(k); });
      } catch (e) { /* fine */ }
      S.profile = null; _draft = null; S.view = "intro"; compute(); render(); toast(t("forgot")); return;
    }
    if (what === "list") { S.view = "list"; render(); return; }
    if (what === "fly") {
      if (S.selected && S.mapOk) {
        var code = S.selected;
        var town = S.recorded.filter(function (x) { return x.state === code; })[0];
        S.map.setPadding(sheetPad());
        if (town) S.map.flyTo({ center: [town.lon, town.lat], zoom: 12.5, duration: reduced ? 0 : 3500, essential: true });
        else S.map.fitBounds(bboxOf(S.statesGeo.features.filter(function (x) { return x.properties.code === code; })[0]), { padding: 16, maxZoom: 9, duration: reduced ? 0 : 2200 });
      }
      return;
    }
    if (what === "rate") { S.rating = { tags: [] }; S.ratingPoint = null; S.view = "rate"; render(); toast(t("pickSpot")); return; }
    if (what === "send") { sendRating(); return; }
    if (what === "back") {
      if (S.ratingMarker) { S.ratingMarker.remove(); S.ratingMarker = null; }
      S.ratingPoint = null; S.view = S.selected ? "state" : "top"; render(); return;
    }
  }

  function focusHeading() { var h = $(".g-sheet h1, .g-sheet h2"); if (h) h.focus({ preventScroll: true }); }

  function selectState(code, fly) {
    S.selected = code; S.view = "state"; render();
    if (fly) flyToState(code);
    focusHeading();
  }

  function setRatingPoint(lat, lon) {
    S.ratingPoint = { lat: lat, lon: lon };
    if (S.ratingMarker) S.ratingMarker.remove();
    var el = document.createElement("div"); el.className = "g-pin";
    S.ratingMarker = new maplibregl.Marker({ element: el }).setLngLat([lon, lat]).addTo(S.map);
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
        toast(t(j.shared === false ? "sentLocal" : "sent"));
        return loadHeat().then(function () { compute(); paintHeat(); S.selected = j.state; S.view = "state"; render(); });
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
    $("#g-lang").addEventListener("click", function () { S.lang = S.lang === "es" ? "en" : "es"; store.set("footing.lang", S.lang); render(); });
    $("#g-hide").addEventListener("click", function () {
      try { sessionStorage.clear(); } catch (e) { /* fine */ }
      if (B.hide) B.hide(); else location.replace("https://www.weather.gov/");
    });
    $("#g-listbtn").addEventListener("click", function () { S.view = S.view === "list" ? (S.selected ? "state" : "top") : "list"; render(); });
    $("#g-layer").addEventListener("change", function (e) { S.layer = e.target.value; paintStates(); paintHeat(); render(); if (S.layer === "community" && !(S.heat && S.heat.total)) toast(t("noRatings")); });
    window.addEventListener("resize", function () { drawStars(); updatePeek(); });
    window.addEventListener("online", function () { S.map && S.map.triggerRepaint(); });
  }

  // ---------------- lifecycle ----------------
  var started = false;
  function start() {
    started = true;
    drawStars();
    bindChrome();
    var base = B.dataBase || "data/";
    var loads = [B.policy ? B.policy() : getJSON(API + "/policy"), getJSON(base + "states-10m.json"), getJSON(base + "countries-110m.json")];
    Promise.all(loads).then(function (res) {
      S.policy = res[0].states; S.elig = res[0].eligibility;
      return Promise.all([loadHeat(), (B.towns ? B.towns() : getJSON(API + "/healthz")).then(function (h) {
        // Towns with recorded real data (replay mode). Label ends with the state code, e.g. "Downtown Christiansburg, VA".
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
    S.rating = { tags: [] }; S.view = "rate";
    var go2 = function () { setRatingPoint(lat, lon); S.map.jumpTo({ center: [lon, lat], zoom: 12 }); };
    if (S.mapOk) go2(); else if (S.map) S.map.once("load", go2); else S.ratingPoint = { lat: lat, lon: lon };
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
      return loadHeat().then(function () { if (!S.policy) return; compute(); if (S.mapOk) { paintStates(); paintHeat(); } render(); });
    },
    _state: S,
  };
})();
