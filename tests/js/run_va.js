// Usage: node tests/js/run_va.js <cases.json> -> Virginia locality results for each case (JSON).
const fs = require("fs"), path = require("path");
const VA = require(path.join(__dirname, "../../footing/web/va.js"));
const root = path.join(__dirname, "../../footing/static");
const read = (f) => JSON.parse(fs.readFileSync(path.join(root, f), "utf8"));
const elig = read("eligibility.json"), policy = read("state_policy.json"), va = read("va_localities.json");
const cases = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
const out = cases.map((c) => {
  const community = c.heat ? VA.communityByLocality(va, c.heat) : null;
  return {
    community,
    ranked: c.rank ? VA.rankLocalities(elig, policy, va, c.profile, community) : null,
    points: (c.points || []).map((p) => VA.fitPoint(elig, policy, va, p[0], p[1], c.profile, community)),
  };
});
process.stdout.write(JSON.stringify(out));
