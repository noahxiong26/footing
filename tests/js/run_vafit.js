// Usage: node tests/js/run_vafit.js <cases.json>  -> prints the JS engine's output for each case (JSON).
// A case is {profile, community?, samples?} for rankLocalities, or adds {tiles: [[lat, lon], ...]} to also
// score those points with fitScore, which is how the block-level crime path gets compared with Python.
const fs = require("fs"), path = require("path");
const VaFit = require(path.join(__dirname, "../../footing/web/vafit.js"));
const VaPoint = require(path.join(__dirname, "../../footing/web/vapoint.js"));
const topojson = require(path.join(__dirname, "../../footing/web/vendor/topojson-client.min.js"));
const root = path.join(__dirname, "../../footing/static");
const web = path.join(__dirname, "../../footing/web");
const read = (p) => JSON.parse(fs.readFileSync(p, "utf8"));
const elig = read(path.join(root, "eligibility.json"));
const va = read(path.join(root, "va_localities.json"));

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

const cases = read(process.argv[2]);
const out = cases.map((c) => {
  const ranked = VaFit.rankLocalities(elig, va, c.profile, c.community || null, { samples: c.samples || 200 });
  if (!c.tiles) return ranked;
  const points = c.tiles.map(([lat, lon]) => {
    const pt = VaPoint.checkPoint(geo, lat, lon);
    if (!pt.ok) return { fips: null, score: null };
    return VaFit.fitScore(elig, va, pt.fips, c.profile, c.community || null, VaFit.tileOf(lat, lon));
  });
  return { ranked, points };
});
process.stdout.write(JSON.stringify(out));
