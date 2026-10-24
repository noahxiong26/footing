// Every engine sentence fit.js can produce must have Spanish. Prints reasons whose Spanish still contains
// an untranslated engine sentence, as JSON (expect []). Quoted source notes may stay English (marked).
const fs = require("fs"), path = require("path");
const Fit = require(path.join(__dirname, "../../footing/web/fit.js"));
const ctx = {};
new Function("self", fs.readFileSync(path.join(__dirname, "../../footing/web/i18n.js"), "utf8"))(ctx);
const I = ctx.FootingI18n;
const root = path.join(__dirname, "../../footing/static");
const elig = JSON.parse(fs.readFileSync(path.join(root, "eligibility.json"), "utf8"));
const policy = JSON.parse(fs.readFileSync(path.join(root, "state_policy.json"), "utf8"));
const statuses = elig.statuses.map((s) => s.id).concat([null]);
const hhs = [{}, { kids: true }, { pregnant: true }, { kids: true, mixed: true }];
const sits = [{}, { disability: true }, { no_id: true }];
const community = { VA: { n: 1, score: 50, freshness: 0.5 }, TX: { n: 3, score: 60, freshness: 0.5 } };
// English engine words that must never survive translation (source notes don't use these exact phrases).
const ENGINE = /hours\/week|people without homes|State law:|Statewide camping|State law pushes|Not checked|No ratings yet|Medicaid expansion|Medicaid wait|Marketplace tax|limited Marketplace|regardless of status$|lawful presence|State food program|State program for adults|Shown only|You chose|Add your status|ER care|SNAP: (yes|no|limited|varies)(;|$| \()|SNAP: (children|U\.S\.)/;
const bad = new Set();
let checked = 0;
for (const code of Object.keys(policy.states)) for (const status of statuses) for (const household of hhs) for (const situation of sits) {
  for (const age_band of [null, "62_plus"]) {
    const comps = Fit.components(elig, policy, code, { status, household, situation, age_band }, community);
    for (const k of Object.keys(comps)) {
      const es = I.reason("es", comps[k].reason); checked++;
      const stripped = es.replace(/: .*?\(en inglés\)/g, ":");    // quoted source notes may stay English
      if (ENGINE.test(stripped) || I.reason("en", comps[k].reason) !== comps[k].reason) bad.add(comps[k].reason + "  =>  " + es);
    }
  }
}
process.stdout.write(JSON.stringify({ checked, bad: [...bad] }));
