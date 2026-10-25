/* Footing: is this point usable, and how much should we trust it?
 *
 * Mirrors the point-checking half of footing/va.py (tests/test_vafit.py runs both on the same points and
 * requires equal output). Runs on the phone so a tap can be answered without a round trip.
 *
 * Never guesses. A point is either refused with a plain reason, or accepted with every doubt listed:
 *   not_a_number | off_globe | swapped | outside_virginia | open_water   -> refused, validity 0
 *   ok  with issues: coarse (rounded coordinates), near_boundary (close to the locality line)
 * `validity` is the product of the issue factors. It never changes a score: footing/web/vafit.js multiplies
 * it into the CONFIDENCE, so a rounded or borderline point says the numbers may be the next town's.
 *
 * Geometry comes from the caller: `geo` is the decoded data/va-localities.json FeatureCollection the map
 * already holds (each feature has properties.bbox), so nothing is downloaded twice. `shore` is optional and
 * only used for the open-water check; the phone leaves it out to avoid a second big file, and the server
 * (footing/va.py) always has it, so a rating is re-checked with it before being stored.
 */
(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.FootingVaPoint = factory();
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  var VA_BBOX = [-83.68, 36.54, -75.24, 39.47];   // lon_min, lat_min, lon_max, lat_max
  var WATER_TOLERANCE_M = 2000;
  var BOUNDARY_M = 1000;

  function round3(x) { return Math.round(x * 1000) / 1000; }

  function decimals(x) {
    var s = String(x);
    if (s.indexOf("e") !== -1 || s.indexOf(".") === -1) return 0;
    return s.split(".")[1].length;
  }

  function inRing(lon, lat, ring) {
    var inside = false;
    for (var i = 0, j = ring.length - 1; i < ring.length; j = i++) {
      var xi = ring[i][0], yi = ring[i][1], xj = ring[j][0], yj = ring[j][1];
      if ((yi > lat) !== (yj > lat) && lon < ((xj - xi) * (lat - yi)) / (yj - yi) + xi) inside = !inside;
    }
    return inside;
  }

  function polysOf(f) {
    var g = f.geometry;
    return g.type === "Polygon" ? [g.coordinates] : g.coordinates;
  }

  function inFeature(lon, lat, f) {
    var polys = polysOf(f);
    for (var p = 0; p < polys.length; p++) {
      if (!inRing(lon, lat, polys[p][0])) continue;
      var hole = false;
      for (var h = 1; h < polys[p].length; h++) if (inRing(lon, lat, polys[p][h])) hole = true;
      if (!hole) return true;
    }
    return false;
  }

  function localityAt(geo, lat, lon) {
    if (!geo || !isFinite(lat) || !isFinite(lon)) return null;
    for (var i = 0; i < geo.features.length; i++) {
      var f = geo.features[i], b = f.properties.bbox;
      if (b && (lon < b[0] || lon > b[2] || lat < b[1] || lat > b[3])) continue;
      if (inFeature(lon, lat, f)) return f;
    }
    return null;
  }

  // Point-to-segment distance on a local flat plane; same constants as footing/va.py.
  function segDistM(lat, lon, a, b) {
    var kx = Math.cos((lat * Math.PI) / 180) * 111320.0, ky = 110540.0;
    var ax = (a[0] - lon) * kx, ay = (a[1] - lat) * ky;
    var bx = (b[0] - lon) * kx, by = (b[1] - lat) * ky;
    var dx = bx - ax, dy = by - ay;
    var t = dx === 0 && dy === 0 ? 0.0 : Math.max(0.0, Math.min(1.0, -(ax * dx + ay * dy) / (dx * dx + dy * dy)));
    return Math.sqrt(Math.pow(ax + t * dx, 2) + Math.pow(ay + t * dy, 2));
  }

  function boundaryDistanceM(lat, lon, f) {
    var best = Infinity, polys = polysOf(f);
    for (var p = 0; p < polys.length; p++) {
      for (var r = 0; r < polys[p].length; r++) {
        var ring = polys[p][r];
        for (var i = 0; i < ring.length - 1; i++) {
          var d = segDistM(lat, lon, ring[i], ring[i + 1]);
          if (d < best) best = d;
        }
      }
    }
    return best;
  }

  function distanceToLandM(shore, lat, lon) {
    var i, j, best = Infinity;
    for (i = 0; i < shore.length; i++) if (inRing(lon, lat, shore[i])) return 0.0;
    for (i = 0; i < shore.length; i++) {
      for (j = 0; j < shore[i].length - 1; j++) {
        var d = segDistM(lat, lon, shore[i][j], shore[i][j + 1]);
        if (d < best) best = d;
      }
    }
    return best;
  }

  function nameOf(f) {
    return f.properties.full || f.properties.name || String(f.id);
  }

  /** checkPoint(geo, lat, lon, opts?) -> the same object footing/va.py check_point returns.
   *  opts.shore      rings of Virginia's cartographic shoreline; without it the open-water check is skipped
   *  opts.stateAt    function(lat, lon) -> two-letter state code or null, for naming the state a point is in
   *  opts.stateName  object mapping state code -> full name
   *  The phone passes what the map already holds; the parity test passes all three, so the two engines are
   *  compared on identical information.
   */
  function checkPoint(geo, lat, lon, opts) {
    opts = opts || {};
    var shore = opts.shore;
    var issues = [];
    function out(ok, code, reason, extra) {
      var validity = 0.0;
      if (ok) { validity = 1.0; for (var i = 0; i < issues.length; i++) validity *= issues[i].factor; }
      var o = { ok: ok, code: code, reason: reason, issues: issues, validity: round3(validity) };
      if (extra) for (var k in extra) if (Object.prototype.hasOwnProperty.call(extra, k)) o[k] = extra[k];
      return o;
    }
    // Python's float() accepts "nan", "inf" and "-Infinity" as text, so those reach the second message
    // there; match that split exactly or the two engines would word the same refusal differently.
    var NUMWORD = /^[+-]?(nan|inf(inity)?)$/i;
    function parse(v) {
      if (typeof v === "number") return v;
      if (typeof v === "string" && NUMWORD.test(v.trim())) {
        return /nan/i.test(v) ? NaN : (v.trim()[0] === "-" ? -Infinity : Infinity);
      }
      if (v === null || v === undefined || v === "") return undefined;   // Number("") is 0; float("") raises
      var n = Number(v);
      return isNaN(n) ? undefined : n;
    }
    var la = parse(lat), lo = parse(lon);
    if (la === undefined || lo === undefined) {
      return out(false, "not_a_number", "That location is not a pair of numbers.");
    }
    if (isNaN(la) || isNaN(lo) || !isFinite(la) || !isFinite(lo)) {
      return out(false, "not_a_number", "That location is not a real number (NaN or infinity).");
    }
    if (!(la >= -90 && la <= 90 && lo >= -180 && lo <= 180)) {
      return out(false, "off_globe", "Latitude must be -90..90 and longitude -180..180.");
    }
    var f = localityAt(geo, la, lo);
    if (f) {
      if (shore && distanceToLandM(shore, la, lo) > WATER_TOLERANCE_M) {
        return out(false, "open_water", "That point is on open water (inside " + nameOf(f) +
          "'s water area). Move it onto land.", { fips: String(f.id), name: nameOf(f) });
      }
      if (Math.min(decimals(la), decimals(lo)) <= 1) {
        issues.push({ code: "coarse", factor: 0.6,
          text: "These coordinates are rounded (one decimal place is about 11 km), so the local numbers may be " +
                "for a neighbouring city or county." });
      }
      var edge = boundaryDistanceM(la, lo, f);
      if (edge < BOUNDARY_M) {
        issues.push({ code: "near_boundary", factor: 0.85,
          text: "About " + Math.round(edge) + " m from the " + nameOf(f) + " line, so the neighbouring city or " +
                "county's numbers may apply instead." });
      }
      return out(true, "ok", "", { fips: String(f.id), name: nameOf(f) });
    }
    if (lo >= -90 && lo <= 90 && localityAt(geo, lo, la)) {
      return out(false, "swapped", "These look like latitude and longitude swapped. Did you mean " +
        String(lo) + ", " + String(la) + "?", { suggest: { lat: lo, lon: la } });
    }
    var st = opts.stateAt ? opts.stateAt(la, lo) : null;
    if (st && st !== "VA") {
      var full = (opts.stateName && opts.stateName[st]) || st;
      return out(false, "outside_virginia", "That point is in " + full + ". Footing covers Virginia only for now.",
        { state: st });
    }
    if (lo >= VA_BBOX[0] && lo <= VA_BBOX[2] && la >= VA_BBOX[1] && la <= VA_BBOX[3]) {
      return out(false, "open_water",
        "That point is on open water or right on a border, not inside a Virginia city or county.");
    }
    return out(false, "outside_virginia", "That point is outside Virginia. Footing covers Virginia only for now.");
  }

  return { checkPoint: checkPoint, localityAt: localityAt, boundaryDistanceM: boundaryDistanceM,
    BOUNDARY_M: BOUNDARY_M, WATER_TOLERANCE_M: WATER_TOLERANCE_M };
});
