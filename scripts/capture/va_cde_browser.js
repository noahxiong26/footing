/* Capture 2025 violent and property crime counts for every Virginia city, town and county law-enforcement
 * agency from the FBI Crime Data Explorer (CDE), which serves the same numbers the CDE website charts.
 *
 * Run in a browser tab that is ON https://cde.ucr.cjis.gov (open the CDE web app first); the CDE endpoints
 * used here are same-origin there and need no key. Paste the file, wait for window.__cdeJob.status ===
 * "done", then save JSON.stringify(window.__cdeJob.result) and run scripts/build_va_crime.py.
 *
 * Kept per agency: ORI, name, type, county, CDE's map point, months reported, 12-month sums of offenses,
 * and the population CDE says the agency covers. State Police, campus and other special agencies are
 * skipped: their populations are 0 or overlap a city or county.
 */
(function () {
  var YEAR = window.__cdeYear || "2025";
  var KEEP = { City: 1, County: 1 };
  window.__cdeJob = { status: "starting", result: null, error: null };
  async function summed(ori, code) {
    var j = await (await fetch("/LATEST/summarized/agency/" + ori + "/" + code + "?from=01-" + YEAR + "&to=12-" + YEAR)).json();
    var act = (j.offenses && j.offenses.actuals) || {}, pops = (j.populations && j.populations.population) || {};
    var name = Object.keys(act).filter(function (k) { return / Offenses$/.test(k) && k.indexOf("Virginia") !== 0 && k.indexOf("United States") !== 0; })[0];
    if (!name) return { n: null, months: 0, pop: null };
    var series = act[name], months = 0, n = 0;
    Object.keys(series).forEach(function (m) { if (series[m] !== null && series[m] !== undefined) { months++; n += series[m]; } });
    var pname = name.replace(/ Offenses$/, ""), ps = pops[pname] || {}, pv = Object.values(ps).filter(function (x) { return x; });
    return { n: n, months: months, pop: pv.length ? Math.max.apply(null, pv) : null,
             max_data_date: j.cde_properties && j.cde_properties.max_data_date && j.cde_properties.max_data_date.UCR };
  }
  (async function () {
    var ag = await (await fetch("/LATEST/agency/byStateAbbr/VA")).json();
    var list = [];
    Object.keys(ag).forEach(function (k) { ag[k].forEach(function (a) { if (KEEP[a.agency_type_name]) list.push(a); }); });
    var out = [], next = 0, maxDate = null;
    async function worker() {
      while (next < list.length) {
        var a = list[next++];
        var v = await summed(a.ori, "V"), p = await summed(a.ori, "P");
        if (v.max_data_date) maxDate = v.max_data_date;
        out.push({ ori: a.ori, name: a.agency_name, type: a.agency_type_name, county: a.counties,
                   lat: a.latitude, lon: a.longitude, violent: v.n, property: p.n,
                   months_violent: v.months, months_property: p.months, population: v.pop || p.pop });
        window.__cdeJob.status = "fetched " + out.length + " of " + list.length;
      }
    }
    await Promise.all([worker(), worker(), worker(), worker(), worker(), worker()]);
    out.sort(function (x, y) { return x.ori < y.ori ? -1 : 1; });
    window.__cdeJob.result = { captured_at: new Date().toISOString(), year: YEAR, source: "https://cde.ucr.cjis.gov",
                               endpoint: "/LATEST/summarized/agency/{ORI}/{V|P}?from=01-YYYY&to=12-YYYY",
                               cde_max_data_date: maxDate, agencies: out };
    window.__cdeJob.status = "done";
  })().catch(function (e) { window.__cdeJob.error = String(e && e.stack || e); window.__cdeJob.status = "error"; });
  return "started";
})();
