// Usage: node tests/js/run_fit.js <profiles.json>  -> prints rankStates output for each profile (JSON).
const fs = require("fs"), path = require("path");
const Fit = require(path.join(__dirname, "../../footing/web/fit.js"));
const root = path.join(__dirname, "../../footing/static");
const elig = JSON.parse(fs.readFileSync(path.join(root, "eligibility.json"), "utf8"));
const policy = JSON.parse(fs.readFileSync(path.join(root, "state_policy.json"), "utf8"));
const cases = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
const out = cases.map((c) => ({
  ranked: Fit.rankStates(elig, policy, c.profile, c.community || null, { samples: c.samples || 300 }),
  bayes: c.ratings ? Fit.bayesScore(c.ratings, c.now) : null,
}));
process.stdout.write(JSON.stringify(out));
