// Usage: node tests/js/run_vafit.js <cases.json>  -> prints rankLocalities output for each case (JSON).
const fs = require("fs"), path = require("path");
const VaFit = require(path.join(__dirname, "../../footing/web/vafit.js"));
const root = path.join(__dirname, "../../footing/static");
const elig = JSON.parse(fs.readFileSync(path.join(root, "eligibility.json"), "utf8"));
const va = JSON.parse(fs.readFileSync(path.join(root, "va_localities.json"), "utf8"));
const cases = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
const out = cases.map((c) => VaFit.rankLocalities(elig, va, c.profile, c.community || null, { samples: c.samples || 200 }));
process.stdout.write(JSON.stringify(out));
