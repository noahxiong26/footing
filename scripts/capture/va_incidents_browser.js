/* Capture Virginia city police incidents and reduce them to ~1 km tile counts.
 *
 * Why a browser: the build sandbox cannot reach these hosts, and the Census batch geocoder does not allow
 * cross-site calls. So this runs in a browser tab that is ON https://geocoding.geo.census.gov (open any
 * geocoder URL first), pulls the city feeds (both allow cross-site reads), geocodes each hundred-block
 * address with the Census batch geocoder (same origin), keeps only points inside that city's own FIPS,
 * and returns counts per tile. No address, name or incident ID leaves this tab; officer names in the
 * Charlottesville feed are never read.
 *
 * Paste the whole file into the console (or a javascript tool). It starts a background job and returns at
 * once; read window.__vaJob.status until it says "done", then copy JSON.stringify(window.__vaJob.result)
 * into footing/static/va_incident_tiles.json via scripts/build_va_incidents.py.
 *
 * RULES must equal footing/static/va_offense_classes.json "rules" (tests/test_va_data.py checks this).
 */
(function () {
  var RULES = [
    ["other", "domestic|family|child|\\bleo\\b|statutory|pornograph|peeping|indecent|obscene|harass|stalk|fraud|forgery|counterfeit|identity|embezzl|extortion|hacking|impersonat|shoplif|hit (&|and) run|accident|death|doa|suicide|overdose|missing|runaway|lost|animal|recovered vehicle|alarm|bomb threat|stolen property|possess stolen|receive stolen|tampering|unauthorized use|weapons? violation|concealed weapon|driving under|\\bdui\\b|traffic|assist agency|assist citizen - (misc|medical|welfare)|non-criminal|suspicious|noise|littering|juvenile|false report|problem solving|initiative"],
    ["violent", "assault|robbery|carjack|home invasion|rape|sodomy|sexual battery|sexual penetration|forcible|fondling|abduct|kidnap|homicide|murder|manslaughter|brandish|shoot into|reckless use of firearm|shots fired|threaten bodily|threat to burn|intimidation|road rage"],
    ["property", "larceny|theft|pocket|purse|burglary|stolen vehicle|motor vehicle theft|vandal|graffiti|damage|arson|fire ?bomb"],
    ["enforcement", "trespass|disorderly|drunk|liquor|curfew|loiter|vagranc|narcotic|drug|paraphernalia|pc - buy|warrant|fugitive|flight to avoid|obstruct|prostitution|mental|tdo|eco\\b"]
  ].map(function (r) { return [r[0], new RegExp(r[1], "i")]; });
  function classify(offense) {
    for (var i = 0; i < RULES.length; i++) if (RULES[i][1].test(offense || "")) return RULES[i][0];
    return "other";
  }
  var SINCE = window.__vaSince || "2025-10-24";       // 12 months before capture day
  var CITIES = [
    { id: "norfolk", fips: "51710", city: "Norfolk", agency: "Norfolk Police Department",
      url: "https://data.norfolk.gov/resource/r7bn-2egr.json", license: "Norfolk open data (public)",
      fetch: async function () {
        var q = "?$select=offense,streetno,street,date_occu&$limit=100000&$where=" +
          encodeURIComponent("date_occu>='" + SINCE + "'");
        var rows = await (await fetch(this.url + q)).json();
        return rows.map(function (r) {
          var addr = (r.streetno && r.street) ? (r.streetno + " " + r.street) : null;
          return { offense: r.offense, addr: addr, date: (r.date_occu || "").slice(0, 10) };
        });
      } },
    { id: "charlottesville", fips: "51540", city: "Charlottesville", agency: "Charlottesville Police Department",
      url: "https://gisweb.charlottesville.org/arcgis/rest/services/OpenData_2/MapServer/6",
      license: "City of Charlottesville open data (public)",
      fetch: async function () {
        var out = [], off = 0, where = "DateReported>=timestamp '" + SINCE + " 00:00:00'";
        while (true) {
          var u = this.url + "/query?where=" + encodeURIComponent(where) +
            "&outFields=Offense,BlockNumber,StreetName,DateReported&orderByFields=RecordID&resultOffset=" + off +
            "&resultRecordCount=1000&f=json";
          var j = await (await fetch(u)).json();
          var f = j.features || [];
          f.forEach(function (x) {
            var a = x.attributes, s = a.StreetName || "";
            var addr = (a.BlockNumber && s && s.indexOf("/") < 0) ? (a.BlockNumber + " " + s) : null;
            out.push({ offense: a.Offense, addr: addr, date: new Date(a.DateReported).toISOString().slice(0, 10) });
          });
          if (f.length < 1000) break;
          off += f.length;
        }
        return out;
      } }
  ];

  function parseCsvLine(line) {
    var cells = [], m, re = /"([^"]*)"/g;
    while ((m = re.exec(line))) cells.push(m[1]);
    return cells;
  }
  async function geocode(addrs, city) {            // addrs: unique strings -> {addr: [lat, lon, countyFips]}
    var res = {}, chunks = [];
    for (var i = 0; i < addrs.length; i += 1000) chunks.push(addrs.slice(i, i + 1000));
    var next = 0;
    async function worker() {
      while (next < chunks.length) {
        var c = chunks[next++], start = addrs.indexOf(c[0]);
        var csv = c.map(function (a, k) { return (start + k) + ',"' + a.replace(/"/g, "") + '",' + city + ",VA,"; }).join("\n");
        var fd = new FormData();
        fd.append("benchmark", "Public_AR_Current");
        fd.append("vintage", "Current_Current");
        fd.append("addressFile", new Blob([csv], { type: "text/csv" }), "a.csv");
        var txt = await (await fetch("/geocoder/geographies/addressbatch", { method: "POST", body: fd })).text();
        txt.split("\n").forEach(function (line) {
          var c2 = parseCsvLine(line);
          if (c2.length >= 6 && c2[2] === "Match") {
            var ll = c2[5].split(","), st = c2[8], co = c2[9];
            res[addrs[+c2[0]]] = [+ll[1], +ll[0], (st || "") + (co || "")];
          }
        });
        window.__vaJob.status = "geocoding " + city + ": " + Object.keys(res).length + " matched so far";
      }
    }
    await Promise.all([worker(), worker(), worker(), worker()]);
    return res;
  }
  function tileOf(lat, lon) {
    var i = Math.floor(lat / 0.01), j = Math.floor(lon / 0.01);
    return { id: "t" + i + "_" + j, lat: Math.round((i + 0.5) * 0.01 * 1e4) / 1e4, lon: Math.round((j + 0.5) * 0.01 * 1e4) / 1e4 };
  }

  window.__vaJob = { status: "starting", result: null, error: null };
  (async function () {
    var result = { captured_at: new Date().toISOString(), window_start: SINCE, tile_deg: 0.01, cities: [] };
    for (var ci = 0; ci < CITIES.length; ci++) {
      var C = CITIES[ci];
      window.__vaJob.status = "fetching " + C.id;
      var rows = await C.fetch();
      var classes = {}, labels = {};
      rows.forEach(function (r) {
        r.cls = classify(r.offense);
        classes[r.cls] = (classes[r.cls] || 0) + 1;
        labels[r.offense] = r.cls;
      });
      var used = rows.filter(function (r) { return r.cls !== "other"; });
      var uniq = Array.from(new Set(used.filter(function (r) { return r.addr; }).map(function (r) { return r.addr; })));
      var geo = await geocode(uniq, C.city);
      var tiles = {}, placed = 0, outside = 0, noAddr = 0, noMatch = 0, maxDate = "";
      used.forEach(function (r) {
        if (r.date > maxDate) maxDate = r.date;
        if (!r.addr) { noAddr++; return; }
        var g = geo[r.addr];
        if (!g) { noMatch++; return; }
        if (g[2] !== C.fips) { outside++; return; }
        var t = tileOf(g[0], g[1]);
        var T = tiles[t.id] || (tiles[t.id] = { tile: t.id, lat: t.lat, lon: t.lon, violent: 0, property: 0, enforcement: 0 });
        T[r.cls]++; placed++;
      });
      result.cities.push({
        id: C.id, fips: C.fips, name: C.city, agency: C.agency, source_url: C.url, license: C.license,
        records_in_window: rows.length, by_class: classes, used: used.length, placed: placed,
        not_placed: { no_block_address: noAddr, geocoder_no_match: noMatch, outside_city_fips: outside },
        latest_date: maxDate, offense_classes: labels,
        tiles: Object.keys(tiles).sort().map(function (k) { return tiles[k]; })
      });
    }
    window.__vaJob.result = result;
    window.__vaJob.status = "done";
  })().catch(function (e) { window.__vaJob.error = String(e && e.stack || e); window.__vaJob.status = "error"; });
  return "started";
})();
