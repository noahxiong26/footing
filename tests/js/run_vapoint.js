// Usage: node tests/js/run_vapoint.js <points.json> -> footing/web/vapoint.js result per point (JSON).
// Fed the same geometry footing/va.py uses, so tests/test_vafit.py can require identical output.
const fs = require("fs"), path = require("path");
const topojson = require(path.join(__dirname, "../../footing/web/vendor/topojson-client.min.js"));
const VaPoint = require(path.join(__dirname, "../../footing/web/vapoint.js"));

const web = path.join(__dirname, "../../footing/web");
const read = (p) => JSON.parse(fs.readFileSync(p, "utf8"));

const vt = read(path.join(web, "data/va-localities.json"));
const geo = topojson.feature(vt, vt.objects.localities);
const bboxOf = (f) => {
  const b = [180, 90, -180, -90];
  const walk = (c) => {
    if (typeof c[0] === "number") {
      if (c[0] < b[0]) b[0] = c[0]; if (c[1] < b[1]) b[1] = c[1];
      if (c[0] > b[2]) b[2] = c[0]; if (c[1] > b[3]) b[3] = c[1];
    } else c.forEach(walk);
  };
  walk(f.geometry.coordinates);
  return b;
};
geo.features.forEach((f) => { f.properties.bbox = bboxOf(f); });

// Virginia's shoreline rings from the same us-atlas file footing/va.py reads.
const ct = read(path.join(web, "data/counties-10m.json"));
const counties = topojson.feature(ct, ct.objects.counties);
const shore = [];
counties.features.filter((f) => String(f.id).startsWith("51")).forEach((f) => {
  const polys = f.geometry.type === "Polygon" ? [f.geometry.coordinates] : f.geometry.coordinates;
  polys.forEach((p) => shore.push(p[0]));
});

// State lookup from the same states TopoJSON the globe already loads.
const st = read(path.join(web, "data/states-10m.json"));
const states = topojson.feature(st, st.objects.states);
const stateCodes = read(path.join(__dirname, "state_codes.json"));
const inRing = (lon, lat, ring) => {
  let inside = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const xi = ring[i][0], yi = ring[i][1], xj = ring[j][0], yj = ring[j][1];
    if ((yi > lat) !== (yj > lat) && lon < ((xj - xi) * (lat - yi)) / (yj - yi) + xi) inside = !inside;
  }
  return inside;
};
const stateAt = (lat, lon) => {
  for (const f of states.features) {
    const polys = f.geometry.type === "Polygon" ? [f.geometry.coordinates] : f.geometry.coordinates;
    for (const p of polys) {
      if (inRing(lon, lat, p[0]) && !p.slice(1).some((h) => inRing(lon, lat, h))) {
        return stateCodes.byFips[String(f.id).padStart(2, "0")] || null;
      }
    }
  }
  return null;
};

const points = read(process.argv[2]);
const out = points.map((p) => VaPoint.checkPoint(geo, p[0], p[1], { shore, stateAt, stateName: stateCodes.names }));
process.stdout.write(JSON.stringify(out));
