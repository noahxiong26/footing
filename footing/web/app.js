/* Footing PWA. Plain JS, no build step. Every screen reads the pipeline's JSON; nothing is
   invented in the browser. Missing data is shown as Unknown with its reason. */
"use strict";

const API = "api";
const view = document.getElementById("view");
const TOWNS = [
  { name: "Christiansburg, VA", lat: 37.1299, lon: -80.4089 },
  { name: "Blacksburg, VA", lat: 37.2296, lon: -80.4139 },
  { name: "Radford, VA", lat: 37.1318, lon: -80.5764 },
  { name: "Roanoke, VA", lat: 37.2710, lon: -79.9414 },
];
const KIND_LABEL = {
  shelter: "Shelter", day_center: "Day center", soup_kitchen: "Meal site", food_bank: "Food bank",
  snap_retailer: "Takes EBT", library: "Library (Wi-Fi, charging)", toilets: "Restroom", drinking_water: "Drinking water",
  shower: "Shower", laundry: "Laundromat", clinic: "Clinic", health_center: "Health center", pharmacy: "Pharmacy",
  post_office: "Post office (General Delivery)", employment_agency: "Job help", school: "School",
  transit_stop: "Bus stop", community_centre: "Community center",
};
const SHOW_KINDS = ["shelter", "day_center", "soup_kitchen", "food_bank", "snap_retailer", "library", "toilets",
  "drinking_water", "laundry", "clinic", "pharmacy", "post_office", "employment_agency", "school", "transit_stop"];

const state = { profile: new Set(), health: null };

// ---------- helpers ----------
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const money = (v, unit) => {
  if (v === null || v === undefined) return "Unknown";
  if (typeof v !== "number") return esc(v);
  const s = v >= 100 ? `$${Math.round(v).toLocaleString()}` : `$${v.toFixed(2)}`;
  return unit && unit.includes("/") ? `${s}/${unit.split("/")[1].replace("month", "mo").replace("hour", "hr")}` : s;
};
const storage = {
  get(k, d) { try { const v = localStorage.getItem(k); return v ? JSON.parse(v) : d; } catch { return d; } },
  set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch { /* private mode: fine */ } },
};
function params() {
  const q = location.hash.split("?")[1] || "";
  return Object.fromEntries(new URLSearchParams(q));
}
function go(path, p) { location.hash = `#/${path}${p ? "?" + new URLSearchParams(p) : ""}`; }
async function getJSON(path, p) {
  const res = await fetch(`${API}/${path}?${new URLSearchParams(p)}`);
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(body.detail || `Request failed (${res.status})`);
  return body;
}
function loading(msg) { view.innerHTML = `<div class="spinner" role="status">${esc(msg)}</div>`; }
function fail(err) {
  view.innerHTML = `<div class="notice warn" role="alert"><strong>Something went wrong.</strong> ${esc(err.message)}</div>
    <p><a class="btn" href="tel:211">Talk to a person: call 211</a></p><p><a class="btn" href="#/">Start over</a></p>`;
}
function backBar(title, sub, to = "#/") {
  return `<div class="row" style="align-items:center;gap:12px;margin-top:8px">
    <a href="${to}" class="btn" style="flex:0 0 48px;width:48px;padding:0" aria-label="Back">&larr;</a>
    <div style="flex:1"><div style="font-size:18px;font-weight:600">${esc(title)}</div>
    ${sub ? `<div class="dim">${esc(sub)}</div>` : ""}</div></div>`;
}
const where = () => { const p = params(); return { lat: p.lat, lon: p.lon, profile: p.profile || "" }; };
const demoNote = () => state.health && state.health.mode === "replay"
  ? `<div class="notice">Demo mode: real data recorded on ${esc(state.health.captured_at || "")} for ${esc(state.health.demo_label || "no place yet")}. Other places show Unknown until the server runs live.</div>` : "";
// Town picker: preset towns plus any recorded demo set. In demo mode, towns without a recording say so.
const towns = () => {
  const h = state.health || {};
  const rec = h.mode === "replay" ? (h.recorded || []) : null;
  const near = (a, b) => Math.abs(a.lat - b.lat) < 0.01 && Math.abs(a.lon - b.lon) < 0.01;
  const list = TOWNS.map((t) => ({ ...t }));
  (rec || []).forEach((r) => { if (!list.some((t) => near(t, r))) list.push({ name: r.label, lat: r.lat, lon: r.lon }); });
  return list.map((t) => ({ ...t, noData: rec !== null && !rec.some((r) => near(t, r)) }));
};
const townButton = (t, attr) =>
  `<button class="btn" ${attr}>${esc(t.name)}${t.noData ? ` <span class="nodata">no demo data</span>` : ""}</button>`;

// ---------- screens ----------
function startScreen() {
  const saved = storage.get("footing.profile", []);
  state.profile = new Set(saved);
  const chips = [["car", "I have a car"], ["kids", "Kids with me"], ["tonight", "I need a place tonight"]];
  view.innerHTML = `
    <h1>Where could you land for the next 30 days?</h1>
    <p class="quiet">We add up food, gas, shelter, school and buses near you, and show where each number comes from.</p>
    ${demoNote()}
    <div class="stack" style="margin-top:16px">
      <button class="btn primary" id="locate">Use my location</button>
      <div class="dim">Your location is rounded to about 1 km before it leaves this phone.</div>
      <div><label>Or pick a town</label><div class="towns" style="margin-top:6px">
        ${towns().map((t, i) => townButton(t, `data-town="${i}"`)).join("")}
      </div></div>
      <div><label id="chips-label">Tap what fits you</label>
        <div class="chips" role="group" aria-labelledby="chips-label" style="margin-top:6px">
        ${chips.map(([k, l]) => `<button class="chip" data-chip="${k}" aria-pressed="${state.profile.has(k)}">${l}</button>`).join("")}
        </div></div>
      <a class="btn" href="#/flyer">Snap a flyer</a>
      <a class="btn" href="tel:211">Talk to a person: call 211</a>
    </div>`;
  view.querySelectorAll("[data-chip]").forEach((b) => b.addEventListener("click", () => {
    const k = b.dataset.chip;
    state.profile.has(k) ? state.profile.delete(k) : state.profile.add(k);
    b.setAttribute("aria-pressed", state.profile.has(k));
    storage.set("footing.profile", [...state.profile]);
  }));
  const open = (lat, lon) => {
    const profile = [...state.profile].filter((k) => k !== "tonight").join(",");
    if (state.profile.has("tonight")) go("tonight", { lat, lon });
    else go("receipt", { lat, lon, profile });
  };
  view.querySelectorAll("[data-town]").forEach((b) => b.addEventListener("click", () => {
    const t = towns()[+b.dataset.town]; open(t.lat, t.lon);
  }));
  document.getElementById("locate").addEventListener("click", () => {
    if (!navigator.geolocation) { alert("Location is not available here. Pick a town instead."); return; }
    navigator.geolocation.getCurrentPosition(
      (pos) => open(pos.coords.latitude.toFixed(3), pos.coords.longitude.toFixed(3)),
      () => alert("We could not get your location. Pick a town instead."),
      { enableHighAccuracy: false, timeout: 10000, maximumAge: 600000 });
  });
}

function barColor(s) { return s >= 70 ? "var(--bar-good)" : s >= 40 ? "var(--bar-mid)" : "var(--bar-low)"; }

function receiptHTML(r) {
  const known = r.categories.filter((c) => c.state === "known").length;
  const lines = r.money.map((m) => `
    <div class="line ${m.state}"><span>${esc(m.label)}</span><span class="v">${money(m.value, m.unit)}</span></div>
    <div class="src">${m.state === "known" ? `${esc(m.source)}${m.as_of ? " · " + esc(m.as_of) : ""}` : "not found for this area"}</div>`).join("");
  return `<section class="receipt" aria-label="Settle receipt">
    <div class="title">SETTLE RECEIPT</div>
    <div class="sub">${esc(r.area.nws_city || r.area.county || r.tile.id)} · ${esc(r.profile.map((x) => x.replace("_", " ")).join(", "))}</div>
    <hr>${lines}<hr>
    <div class="stamp-row"><div>
      <div class="src">SETTLE SCORE</div>
      <div class="src">Confidence: ${esc(r.confidence_label)} (${known} of ${r.categories.length} categories known)</div>
    </div>
    <div class="stamp ${r.settle_score === null ? "none" : ""}" aria-label="Settle score ${r.settle_score ?? "unknown"}">${r.settle_score === null ? "?" : Math.round(r.settle_score)}</div></div>
  </section>`;
}

function categoriesHTML(r) {
  return `<div class="cats">${r.categories.map((c, i) => {
    const unk = c.score === null;
    const params = c.parameters.map((p) => `<li>${esc(p.label)}: ${p.state === "known"
      ? `<strong>${esc(typeof p.value === "number" ? +p.value.toFixed(2) : p.value)} ${esc(p.unit)}</strong> → ${p.score}`
      : `Unknown <span class="dim">(${esc(p.reason)})</span>`}</li>`).join("");
    return `<button class="cat" aria-expanded="false" aria-controls="cat-${i}" data-cat="${i}">
        <span>${esc(c.label)}</span>
        <span class="track ${unk ? "unknown" : ""}">${unk ? "" : `<span class="fill" style="display:block;width:${c.score}%;background:${barColor(c.score)}"></span>`}</span>
        <span class="num">${unk ? "?" : Math.round(c.score)}</span></button>
      <ul class="details" id="cat-${i}" hidden>${params}</ul>`;
  }).join("")}</div>`;
}

function placeHTML(p, kind) {
  const badge = p.open_now === true ? `<span class="badge open">OPEN${p.closes ? " · closes " + esc(p.closes) : ""}</span>`
    : p.open_now === false ? `<span class="badge closed">CLOSED NOW</span>` : `<span class="badge">HOURS UNKNOWN</span>`;
  const phone = p.tags && p.tags.phone ? `<a href="tel:${esc(p.tags.phone.replace(/[^+\d]/g, ""))}">Call</a>` : "";
  const map = `<a href="https://www.google.com/maps/dir/?api=1&destination=${p.lat},${p.lon}&travelmode=walking" target="_blank" rel="noopener">Directions</a>`;
  const extra = p.tags && p.tags.inferred_from ? ` · <span class="dim">from ${esc(p.tags.inferred_from)}</span>` : "";
  const name = p.name === "(unnamed)" ? (KIND_LABEL[kind] || kind) : p.name;
  return `<li class="place"><span class="name">${esc(name)}</span>
    <span class="meta"><span>${esc(KIND_LABEL[kind] || kind)}</span><span>${p.walk_min != null ? Math.round(p.walk_min) + " min walk" : ""}</span>${badge}</span>
    <span class="meta">${phone} ${map} <span class="dim">${esc(p.source)}${extra}</span></span></li>`;
}

async function receiptScreen() {
  const w = where();
  loading("Adding up what is near you…");
  try {
    const r = await getJSON("receipt", w);
    storage.set("footing.last", w);
    const close = (k) => (r.nearest[k] || []).filter((p) => p.walk_min == null || p.walk_min <= 45);
    const near = SHOW_KINDS.filter((k) => close(k).length)
      .map((k) => close(k).slice(0, k === "snap_retailer" ? 3 : 2).map((p) => placeHTML(p, k)).join("")).join("");
    const alerts = (r.alerts || []).map((a) => `<div class="notice warn"><strong>${esc(a.event)}</strong> · National Weather Service</div>`).join("");
    view.innerHTML = `${backBar(r.area.nws_city || r.area.county || "This area", `${r.mode === "replay" ? "Recorded real data" : "Live data"} · tile ${r.tile.id}`)}
      ${demoNote()}${alerts}${receiptHTML(r)}
      <h2>What's here</h2><p class="dim">Tap a row to see every number and why some are Unknown.</p>
      ${categoriesHTML(r)}
      <div class="actions no-print">
        <a class="btn primary" href="#/plan?${new URLSearchParams(w)}">30-day plan</a>
        <a class="btn" href="#/compare?${new URLSearchParams(w)}">Compare towns</a>
        <a class="btn" href="#/tonight?${new URLSearchParams({ lat: w.lat, lon: w.lon })}">Tonight</a>
        <a class="btn" href="#/card?${new URLSearchParams(w)}">Pocket card</a>
      </div>
      <h2>Closest places</h2><p class="dim">Within about a 45-minute walk.</p><ul class="places">${near || "<li class='notice'>No places found in public data for this tile.</li>"}</ul>
      <h2>Not found here</h2><p class="dim">${r.unknowns.length} measures had no data. We say so instead of guessing.</p>
      <ul class="details">${r.unknowns.slice(0, 12).map((u) => `<li>${esc(u.parameter.replace(/_/g, " "))}: ${esc(u.reason)}</li>`).join("")}</ul>
      <p class="dim">Excluded on purpose: crime and demographics. Footing rates access to help, not who lives somewhere.</p>`;
    view.querySelectorAll("[data-cat]").forEach((b) => b.addEventListener("click", () => {
      const d = document.getElementById(`cat-${b.dataset.cat}`);
      d.hidden = !d.hidden; b.setAttribute("aria-expanded", !d.hidden);
    }));
  } catch (e) { fail(e); }
}

async function planScreen() {
  const w = where();
  const lang = params().lang || "English";
  loading("Writing a plan from the places we found…");
  try {
    const p = await getJSON("plan", { ...w, lang });
    const key = `footing.plan.${w.lat},${w.lon}`;
    const done = storage.get(key, {});
    const phases = [["day1", "Day 1"], ["week1", "Week 1"], ["month1", "Month 1"]];
    const sel = params().phase || "day1";
    const steps = p.plan[sel] || [];
    view.innerHTML = `${backBar("Your 30-day plan", p.engine === "rule-based" ? "Rule-based plan (Gemma 4 not connected)" : `Written by ${p.engine} · every place checked against our data`, `#/receipt?${new URLSearchParams(w)}`)}
      ${p.note ? `<div class="notice">${esc(p.note)}</div>` : ""}
      <p class="quiet">${esc(p.plan.summary)}</p>
      <div class="tabs" role="tablist">${phases.map(([k, l]) => `<button role="tab" aria-selected="${k === sel}" data-phase="${k}">${l}</button>`).join("")}</div>
      <div class="stack">${steps.length ? steps.map((s, i) => {
        const id = `${sel}-${i}`;
        const pl = s.place;
        return `<div class="step"><input type="checkbox" id="${id}" ${done[id] ? "checked" : ""} aria-label="Done: ${esc(s.action)}">
          <div><label for="${id}" class="a" style="color:var(--ink);font-size:15px">${esc(s.action)}</label>
          <div class="quiet" style="font-size:13px">${esc(s.why)}</div>
          ${pl ? `<div class="meta dim" style="margin-top:4px">${esc(pl.name)}${pl.walk_min != null ? " · " + Math.round(pl.walk_min) + " min walk" : ""}${pl.hours ? " · " + esc(pl.hours) : " · hours unknown"}</div>
          ${pl.phone ? `<a href="tel:${esc(pl.phone.replace(/[^+\d]/g, ""))}">Call ${esc(pl.phone)}</a>` : ""}` : ""}</div></div>`;
      }).join("") : `<div class="notice">No steps for this phase.</div>`}</div>
      ${p.removed.length ? `<p class="dim">${p.removed.length} suggested step(s) removed because they named places not in our data.</p>` : ""}
      <div class="row no-print" style="margin-top:16px">
        <button class="btn" id="read">Read aloud</button>
        <button class="btn" id="lang">${lang === "Español" ? "English" : "Español"}</button></div>
      <p class="dim">Checkmarks stay on this phone.</p>`;
    view.querySelectorAll("[data-phase]").forEach((b) => b.addEventListener("click", () => go("plan", { ...w, lang, phase: b.dataset.phase })));
    view.querySelectorAll(".step input").forEach((c) => c.addEventListener("change", () => { done[c.id] = c.checked; storage.set(key, done); }));
    document.getElementById("lang").addEventListener("click", () => go("plan", { ...w, lang: lang === "Español" ? "English" : "Español", phase: sel }));
    document.getElementById("read").addEventListener("click", () => {
      if (!("speechSynthesis" in window)) return alert("Read aloud is not supported on this device.");
      const u = new SpeechSynthesisUtterance(steps.map((s) => s.action).join(". "));
      u.lang = lang === "Español" ? "es-US" : "en-US"; speechSynthesis.cancel(); speechSynthesis.speak(u);
    });
  } catch (e) { fail(e); }
}

async function tonightScreen() {
  const w = where();
  document.body.classList.add("tonight");
  loading("Finding what is open now…");
  try {
    const t = await getJSON("tonight", { lat: w.lat, lon: w.lon });
    const first = t.places.find((p) => p.open_now) || null;
    view.innerHTML = `${backBar("Tonight", t.local_time ? `Local time ${t.local_time.slice(11, 16)}` : "", "#/")}
      ${t.alerts.map((a) => `<div class="notice warn"><strong>${esc(a.event)}</strong> · National Weather Service</div>`).join("")}
      ${t.tonight_low_f != null ? `<div class="notice">Low tonight about <strong>${Math.round(t.tonight_low_f)}°F</strong> (Open-Meteo forecast).</div>` : ""}
      ${t.message ? `<div class="notice warn" role="alert"><strong>${esc(t.message)}</strong></div>` : ""}
      <a class="btn go" href="tel:211" style="margin-top:12px;min-height:64px;font-size:19px">Call 211 now</a>
      ${first ? `<h2>Open now</h2><div class="place"><span class="big">${esc(first.name === "(unnamed)" ? first.label : first.name)}</span>
        <span class="meta">${esc(first.label)} · ${first.walk_min != null ? Math.round(first.walk_min) + " min walk" : ""}${first.closes ? " · closes " + esc(first.closes) : ""}</span>
        <a class="btn" href="https://www.google.com/maps/dir/?api=1&destination=${first.lat},${first.lon}&travelmode=walking" target="_blank" rel="noopener">Walking directions</a></div>` : ""}
      <h2>Also near</h2><ul class="places">${t.places.filter((p) => p !== first).map((p) => `
        <li class="place"><span class="name">${esc(p.name === "(unnamed)" ? p.label : p.name)}</span><span class="meta"><span>${esc(p.label)}</span>
        <span>${p.walk_min != null ? Math.round(p.walk_min) + " min" : ""}</span>
        ${p.open_now === true ? '<span class="badge open">OPEN</span>' : p.open_now === false ? '<span class="badge closed">CLOSED</span>' : '<span class="badge">HOURS UNKNOWN</span>'}</span></li>`).join("")}</ul>
      <p class="dim">${esc(t.fallback)}</p>`;
  } catch (e) { fail(e); }
}

async function compareScreen() {
  const w = where();
  const other = params().other;
  if (!other) {
    view.innerHTML = `${backBar("Compare towns", "Pick a second place", `#/receipt?${new URLSearchParams(w)}`)}
      <div class="towns" style="margin-top:12px">${towns().map((t) => townButton(t, `data-o="${t.lat},${t.lon}"`)).join("")}</div>`;
    view.querySelectorAll("[data-o]").forEach((b) => b.addEventListener("click", () => go("compare", { ...w, other: b.dataset.o })));
    return;
  }
  loading("Comparing…");
  try {
    const d = await getJSON("compare", { points: `${w.lat},${w.lon};${other}`, profile: w.profile });
    const c = d.compare;
    // A place with no data has no county name from the pipeline; use the town button's name if it was one.
    const pts = [[+w.lat, +w.lon], other.split(",").map(Number)];
    c.areas = c.areas.map((a, i) => {
      if (!a.startsWith("No data")) return a;
      const t = towns().find((x) => Math.abs(x.lat - pts[i][0]) < 0.01 && Math.abs(x.lon - pts[i][1]) < 0.01);
      return t ? `${t.name} (no data)` : a;
    });
    view.innerHTML = `${backBar("Stay or move?", c.areas.join(" vs "), `#/receipt?${new URLSearchParams(w)}`)}
      <div class="cmp"><table><thead><tr><th></th>${c.areas.map((a) => `<th class="n">${esc(a)}</th>`).join("")}</tr></thead><tbody>
      <tr><td><strong>Settle Score</strong></td>${c.settle_scores.map((s) => `<td class="n">${s === null ? "?" : Math.round(s)}</td>`).join("")}</tr>
      ${c.categories.map((r) => `<tr><td>${esc(r.category)}</td>${r.scores.map((s) => `<td class="n">${s === null ? "?" : Math.round(s)}</td>`).join("")}</tr>`).join("")}
      ${c.money.map((m) => `<tr><td>${esc(m.label)}</td>${m.values.map((v) => `<td class="n">${money(v, m.unit)}</td>`).join("")}</tr>`).join("")}
      </tbody></table></div>
      <h2>What changes if you move</h2><ul class="details">${c.what_changes.map((x) => `<li>${esc(x)}</li>`).join("") || "<li>No big differences in the data we have.</li>"}</ul>`;
  } catch (e) { fail(e); }
}

function cardScreen() {
  const w = where();
  const src = `${API}/pocket-card.svg?${new URLSearchParams(w)}`;
  view.innerHTML = `${backBar("Pocket card", "Print it or save it for when there is no signal", `#/receipt?${new URLSearchParams(w)}`)}
    <div class="card-frame" style="margin-top:12px"><img src="${src}" alt="Pocket card with nearby places, hours and phone numbers" width="336" height="576"></div>
    <div class="row no-print" style="margin-top:12px"><button class="btn primary" onclick="window.print()">Print</button>
    <a class="btn" href="${src}" download="footing-pocket-card.svg">Save image</a></div>`;
}

function flyerScreen() {
  view.innerHTML = `${backBar("Snap a flyer", "Gemma 4 reads it. You check it before anything is saved.")}
    <div class="stack" style="margin-top:12px">
      <label for="photo">Take or choose a photo of a paper flyer</label>
      <input id="photo" type="file" accept="image/*" capture="environment">
      <div id="out"></div></div>`;
  document.getElementById("photo").addEventListener("change", async (e) => {
    const f = e.target.files[0]; if (!f) return;
    const out = document.getElementById("out");
    out.innerHTML = `<div class="spinner" role="status">Reading the flyer…</div>`;
    const fd = new FormData(); fd.append("photo", f);
    try {
      const res = await fetch(`${API}/flyer`, { method: "POST", body: fd });
      const body = await res.json();
      if (!res.ok) throw new Error(body.detail || "Could not read the flyer");
      out.innerHTML = `<p class="dim">${esc(body.status)}. Fix anything that is wrong.</p>
        ${body.warnings.map((w) => `<div class="notice warn">${esc(w)}</div>`).join("")}
        ${Object.entries(body.fields).map(([k, v]) => `<label for="f-${k}">${esc(k.replace("_", " "))}</label>
        <input id="f-${k}" value="${esc(v || "")}" placeholder="not on the flyer">`).join("")}
        <p class="dim">Sharing community tips needs a moderation step that is not built yet, so nothing is sent.</p>`;
    } catch (err) {
      out.innerHTML = `<div class="notice warn" role="alert"><strong>${esc(err.message)}</strong></div>`;
    }
  });
}

// ---------- router ----------
const routes = { "": startScreen, receipt: receiptScreen, plan: planScreen, tonight: tonightScreen,
  compare: compareScreen, card: cardScreen, flyer: flyerScreen };
function route() {
  document.body.classList.remove("tonight");
  const name = location.hash.replace(/^#\/?/, "").split("?")[0];
  (routes[name] || startScreen)();
  view.focus();
  window.scrollTo(0, 0);
}
window.addEventListener("hashchange", route);
fetch(`${API}/healthz`).then((r) => r.json()).then((h) => { state.health = h; }).catch(() => {}).finally(route);
if ("serviceWorker" in navigator) navigator.serviceWorker.register("sw.js").catch(() => {});
