/*
 * Arthropoda Keeper – mierenmodule.
 *
 * Tab Mieren (stichtingsstation + kolonies), tellingen (koningin, werksters,
 * broed), voedselstromen (water, suiker, eiwit, zaden, blad), instellingen per
 * kolonie, en blokken voor het werkscherm (mieren + nestmodules).
 */
import {
  esc, field, fmtDate, fmtNum, getStore, openDialog, readForm, selectHtml, toast, NUMBER, daysText,
} from "./arthropoda-common.js?v=0.14.0";

const TEXTS = {
  nl: {
    title: "Mieren", station: "Stichtingsstation", station_note: "Pas gevangen koninginnen. Claustrale stichting: niet voederen en zo weinig mogelijk storen.",
    colonies: "Kolonies", none: "Nog geen mierenkolonies. Voeg koninginnen toe of geef een soort de groep 'mier'.",
    add_queens: "＋ Koninginnen", census: "📋 Telling", settings: "⚙", check_selected: "📋 Controle voor geselecteerde",
    select_all: "Alles selecteren",
    stage_founding: "Stichting", stage_nanitics: "Eerste werksters", stage_growing: "Groeiend", stage_mature: "Volwassen",
    q_seen: "Koningin gezien", q_not_seen: "Koningin niet gezien", q_dead: "Koningin dood", q_unknown: "Koningin ?",
    q_last: "laatst gezien {date}", workers: "werksters", majors: "majors", alates: "gevleugelden gezien",
    eggs: "Eitjes", larvae: "Larven", pupae: "Poppen", brood: "Broed",
    lvl0: "geen", lvl1: "weinig", lvl2: "matig", lvl3: "veel",
    s_water: "Water", s_sugar: "Suiker", s_protein: "Eiwit", s_seeds: "Zaden", s_leaves: "Blad",
    fed: "gegeven ✓", never: "nog nooit", every: "elke {n} d",
    queen: "Koningin", queens: "Aantal koninginnen", worker_count: "Aantal werksters (leeg = niet geteld)",
    majors_count: "Aantal majors/soldaten", alates_seen: "Gevleugelden (alates) gezien", notes: "Notitie",
    census_saved: "Telling opgeslagen ✓", species: "Soort", count: "Aantal koninginnen", prefix: "Naam (begin)",
    caught_at: "Gevangen op", caught_place: "Vindplaats", queens_added: "{n} koningin(nen) toegevoegd ✓",
    type: "Soort mier", t_generalist: "Alleseter", t_harvester: "Oogstmier (zaden)", t_leafcutter: "Bladsnijder (blad)",
    t_predator: "Jager (eiwit)", t_honeypot: "Honingpotmier",
    founding: "Stichting", f_claustral: "Claustraal (niet voederen)", f_semi_claustral: "Semi-claustraal (wel voederen)",
    f_parasitic: "Sociaal parasitair", f_unknown: "Onbekend",
    stage: "Fase", stage_auto: "Automatisch (uit tellingen)", polygyne: "Meerdere koninginnen (polygyn)",
    polymorphic: "Majors/soldaten (polymorf)", queen_check_days: "Melding als koningin zoveel dagen niet gezien",
    food_title: "Voedselstromen (dagen; leeg = standaard, 0 = uit)", saved: "Opgeslagen ✓",
    i_claustral_founding: "Claustrale stichting: niet voederen, zo weinig mogelijk storen.",
    i_queen_dead: "De koningin is dood. Zonder nieuwe koningin sterft de kolonie langzaam uit.",
    i_queen_not_seen: "Koningin al {days} dagen niet gezien.", i_queen_never: "Koningin nog nooit als gezien genoteerd.",
    i_no_census: "Nog geen telling. Noteer koningin, werksters en broed met 📋 Telling.",
    i_founding_progress: "Eerste werksters verwacht tussen {min} en {max}.",
    i_founding_slow: "Eerste werksters lieten langer op zich wachten dan verwacht ({max}). Controleer temperatuur en vocht.",
    i_no_brood: "Geen broed gezien. Buiten de winterrust kan dat op een probleem wijzen.",
    i_larvae_protein: "Veel larven: eiwit vaker geven (nu elke {days} d).",
    modules: "Nestmodules", wetted: "💧 Bevochtigd", wet_due: "bevochtigen", module_saved: "Bevochtigd ✓",
    k_chamber: "Kamer (gips)", k_outworld: "Foerageergebied", k_tube: "Reageerbuis",
    r_: "—", r_brood: "Broedkamer", r_waste: "Afvalkamer", r_dry: "Droog", r_wet: "Nat", r_food: "Voedselkamer",
    m_name: "Naam", m_kind: "Soort", m_role: "Rol", m_temp: "Temperatuursensor", m_hum: "Luchtvochtsensor",
    m_moist: "Vochtsensor gips", m_hum_min: "Min. luchtvocht (%)", m_moist_min: "Min. gipsvocht",
    m_every: "Of: bevochtigen elke … dagen", add_module: "Module toevoegen",
    modules_note: "Elk gipsblok (kamer) of foerageergebied apart, met eigen sensoren. Met een vochtsensor en een minimum komt er een taak zodra het te droog is; anders op een vast interval.",
  },
  en: {
    title: "Ants", station: "Founding station", station_note: "Freshly caught queens. Claustral founding: don't feed and disturb as little as possible.",
    colonies: "Colonies", none: "No ant colonies yet. Add queens or give a species the group 'ant'.",
    add_queens: "＋ Queens", census: "📋 Census", settings: "⚙", check_selected: "📋 Check for selected",
    select_all: "Select all",
    stage_founding: "Founding", stage_nanitics: "First workers", stage_growing: "Growing", stage_mature: "Mature",
    q_seen: "Queen seen", q_not_seen: "Queen not seen", q_dead: "Queen dead", q_unknown: "Queen ?",
    q_last: "last seen {date}", workers: "workers", majors: "majors", alates: "alates seen",
    eggs: "Eggs", larvae: "Larvae", pupae: "Pupae", brood: "Brood",
    lvl0: "none", lvl1: "few", lvl2: "some", lvl3: "many",
    s_water: "Water", s_sugar: "Sugar", s_protein: "Protein", s_seeds: "Seeds", s_leaves: "Leaves",
    fed: "given ✓", never: "never", every: "every {n} d",
    queen: "Queen", queens: "Number of queens", worker_count: "Number of workers (empty = not counted)",
    majors_count: "Number of majors/soldiers", alates_seen: "Alates seen", notes: "Note",
    census_saved: "Census saved ✓", species: "Species", count: "Number of queens", prefix: "Name (prefix)",
    caught_at: "Caught on", caught_place: "Location", queens_added: "{n} queen(s) added ✓",
    type: "Ant type", t_generalist: "Generalist", t_harvester: "Harvester (seeds)", t_leafcutter: "Leafcutter (leaves)",
    t_predator: "Predator (protein)", t_honeypot: "Honeypot ant",
    founding: "Founding", f_claustral: "Claustral (don't feed)", f_semi_claustral: "Semi-claustral (feed)",
    f_parasitic: "Social parasite", f_unknown: "Unknown",
    stage: "Stage", stage_auto: "Automatic (from censuses)", polygyne: "Multiple queens (polygyne)",
    polymorphic: "Majors/soldiers (polymorphic)", queen_check_days: "Warn when the queen hasn't been seen for this many days",
    food_title: "Food streams (days; empty = default, 0 = off)", saved: "Saved ✓",
    i_claustral_founding: "Claustral founding: don't feed, disturb as little as possible.",
    i_queen_dead: "The queen is dead. Without a new queen the colony will slowly die out.",
    i_queen_not_seen: "Queen not seen for {days} days.", i_queen_never: "Queen never recorded as seen.",
    i_no_census: "No census yet. Record queen, workers and brood with 📋 Census.",
    i_founding_progress: "First workers expected between {min} and {max}.",
    i_founding_slow: "First workers are later than expected ({max}). Check temperature and moisture.",
    i_no_brood: "No brood seen. Outside hibernation this may indicate a problem.",
    i_larvae_protein: "Lots of larvae: give protein more often (now every {days} d).",
    modules: "Nest modules", wetted: "💧 Moistened", wet_due: "moisten", module_saved: "Moistened ✓",
    k_chamber: "Chamber (plaster)", k_outworld: "Outworld", k_tube: "Test tube",
    r_: "—", r_brood: "Brood chamber", r_waste: "Waste chamber", r_dry: "Dry", r_wet: "Wet", r_food: "Food chamber",
    m_name: "Name", m_kind: "Type", m_role: "Role", m_temp: "Temperature sensor", m_hum: "Humidity sensor",
    m_moist: "Plaster moisture sensor", m_hum_min: "Min. humidity (%)", m_moist_min: "Min. plaster moisture",
    m_every: "Or: moisten every … days", add_module: "Add module",
    modules_note: "Each plaster block (chamber) or outworld separately, with its own sensors. With a moisture sensor and a minimum you get a task as soon as it's too dry; otherwise on a fixed interval.",
  },
};

export function ta(hass, key, vars = {}) {
  const lang = (hass.language || "en").slice(0, 2);
  let text = (TEXTS[lang] || TEXTS.en)[key] ?? TEXTS.en[key] ?? key;
  for (const [k, v] of Object.entries(vars)) text = text.replaceAll(`{${k}}`, v ?? "");
  return text;
}

const STREAM_ICON = { water: "💧", sugar: "🍬", protein: "🥩", seeds: "🌾", leaves: "🍃" };
const STREAM_ENTRY = { water: "water_refill", sugar: "feed_sugar", protein: "feeding", seeds: "feed_seeds", leaves: "feed_leaves" };
const STREAM_TASK = { water: "ant_water", sugar: "ant_sugar", protein: "ant_protein", seeds: "ant_seeds", leaves: "ant_leaves" };
const STAGE_ICON = { founding: "👑", nanitics: "🐜", growing: "🐜🐜", mature: "🏰" };

export const ANTS_CSS = `
  .ant-grid { display:grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 12px; }
  .ant-card h3 { display:flex; align-items:center; gap:8px; margin:0 0 4px; }
  .ant-card .sub { font-size:.85em; color: var(--ak-muted); margin-bottom: 6px; }
  .ant-line { display:flex; flex-wrap:wrap; gap:6px; align-items:center; margin: 4px 0; font-size:.9em; }
  .lvl { letter-spacing: 1px; font-family: monospace; }
  .streams { display:flex; flex-wrap:wrap; gap:6px; margin-top:8px; }
  .streams button { display:flex; flex-direction:column; align-items:center; padding:6px 10px; min-width:64px; }
  .streams button small { font-size:.72em; color: var(--ak-muted); }
  .streams button.due { border-color: var(--ak-problem); }
  .ant-ins { font-size:.85em; margin-top:6px; }
  .ant-ins div { padding: 2px 0; }
  .ant-ins .warn { color: var(--ak-problem); }
  .module { display:flex; align-items:center; gap:8px; padding:6px 0; border-top:1px solid var(--ak-line); flex-wrap:wrap; }
  .module .grow { min-width: 140px; }
`;

const ants = (store) => (store.animals || []).filter((a) => a.ant && a.state !== "inactive");

function lvl(n) {
  if (n === null || n === undefined) return "–";
  return "▮".repeat(n) + "▯".repeat(3 - n);
}

function insightLine(hass, i) {
  const d = (iso) => (iso ? fmtDate(hass, iso) : "?");
  if (i.key === "queen_not_seen" && (i.days === null || i.days === undefined)) return ta(hass, "i_queen_never");
  return ta(hass, `i_${i.key}`, { days: i.days, min: d(i.expected_min), max: d(i.expected_max) });
}

const ANT_KEYS = new Set(["claustral_founding", "queen_dead", "queen_not_seen", "no_census", "founding_progress",
  "founding_slow", "no_brood", "larvae_protein"]);

/** Kaart van één kolonie (tab Mieren, werkscherm, dierpagina). */
export function antCard(hass, a, { selectable = false, selected = false } = {}) {
  const st = a.ant.state;
  const cfg = a.ant.settings;
  const q = st.queen || {};
  const qText = q.status ? ta(hass, `q_${q.status}`) : ta(hass, "q_unknown");
  const tasks = Object.fromEntries((a.tasks || []).map((t) => [t.kind, t]));
  const streams = Object.keys(a.ant.intervals || {});
  const blocked = (a.insights || []).some((i) => i.key === "claustral_founding");
  const ins = (a.insights || []).filter((i) => ANT_KEYS.has(i.key));
  return `<div class="card ant-card" data-ant="${esc(a.id)}">
    <h3>${selectable ? `<input type="checkbox" data-ant-select="${esc(a.id)}" ${selected ? "checked" : ""}>` : ""}
      <span>${STAGE_ICON[st.stage] || "🐜"}</span><span class="grow">${esc(a.name)}</span>
      <span class="chip">${esc(ta(hass, `stage_${st.stage}`))}</span>
      <button class="icon" data-ant-settings="${esc(a.id)}" title="${esc(ta(hass, "settings"))}">⚙</button></h3>
    <div class="sub"><i>${esc(a.species?.scientific_name || "?")}</i>${cfg.caught_place ? ` · ${esc(cfg.caught_place)}` : ""}${a.acquired_at ? ` · ${esc(fmtDate(hass, a.acquired_at))}` : ""}</div>
    <div class="ant-line"><span class="chip ${q.status === "dead" ? "problem" : q.status === "seen" ? "ok" : ""}">👑 ${esc(qText)}${q.count > 1 ? ` ×${q.count}` : ""}</span>
      ${q.last_seen ? `<span class="muted">${esc(ta(hass, "q_last", { date: fmtDate(hass, q.last_seen) }))}</span>` : ""}</div>
    <div class="ant-line">🐜 <b>${st.workers ?? "?"}</b> ${esc(ta(hass, "workers"))}${st.majors ? ` · ${st.majors} ${esc(ta(hass, "majors"))}` : ""}${st.alates ? ` · 🪽 ${esc(ta(hass, "alates"))}` : ""}</div>
    <div class="ant-line" title="${esc(ta(hass, "brood"))}">
      🥚 <span class="lvl">${lvl(st.brood?.eggs)}</span> 🐛 <span class="lvl">${lvl(st.brood?.larvae)}</span> 🫘 <span class="lvl">${lvl(st.brood?.pupae)}</span>
      ${st.last_census ? `<span class="muted">· ${esc(fmtDate(hass, st.last_census))}</span>` : ""}</div>
    ${blocked ? "" : `<div class="streams">${streams.map((s) => {
      const task = tasks[STREAM_TASK[s]];
      const due = task && new Date(task.due) <= new Date(new Date().setHours(23, 59, 59, 999));
      return `<button class="ak ${due ? "due" : ""}" data-ant-feed="${s}" data-animal="${esc(a.id)}">${STREAM_ICON[s]} ${esc(ta(hass, `s_${s}`))}
        <small>${a.ant.last?.[s] ? esc(daysText(hass, Math.floor((Date.now() - new Date(a.ant.last[s])) / 86400000))) : esc(ta(hass, "never"))} · ${esc(ta(hass, "every", { n: fmtNum(a.ant.intervals[s], 1) }))}</small></button>`;
    }).join("")}${tasks.ant_leftovers ? `<button class="ak" data-ant-leftovers="${esc(a.id)}">🧹<small>${esc(ta(hass, "s_protein"))} –</small></button>` : ""}</div>`}
    <div class="row wrap" style="margin-top:8px"><button class="ak primary" data-ant-census="${esc(a.id)}">${esc(ta(hass, "census"))}</button></div>
    ${ins.length ? `<div class="ant-ins">${ins.map((i) => `<div class="${i.level === "warn" ? "warn" : "muted"}">${i.level === "warn" ? "⚠" : "ℹ"} ${esc(insightLine(hass, i))}</div>`).join("")}</div>` : ""}
  </div>`;
}

function openCensusDialog(host, hass, animals, onDone) {
  const first = animals[0];
  const cfg = first.ant.settings;
  const lvlSelect = (name) => selectHtml(name, [0, 1, 2, 3].map((n) => [n, `${lvl(n)} ${ta(hass, `lvl${n}`)}`]), "", true, "–");
  const title = animals.length > 1 ? `${ta(hass, "census")}: ${animals.length}×` : `${ta(hass, "census")}: ${first.name}`;
  openDialog(hass, title, (body) => {
    body.innerHTML = `<div class="ak-grid">
      ${field(ta(hass, "queen"), selectHtml("queen", [["seen", ta(hass, "q_seen")], ["not_seen", ta(hass, "q_not_seen")], ["dead", ta(hass, "q_dead")]], "seen", true, "–"))}
      ${cfg.polygyne ? field(ta(hass, "queens"), NUMBER("queens", first.ant.state.queen?.count ?? "", 1)) : ""}
      ${field(ta(hass, "worker_count"), NUMBER("workers", "", 1))}
      ${cfg.polymorphic ? field(ta(hass, "majors_count"), NUMBER("majors", "", 1)) : ""}
      ${field(ta(hass, "eggs"), lvlSelect("eggs"))}
      ${field(ta(hass, "larvae"), lvlSelect("larvae"))}
      ${field(ta(hass, "pupae"), lvlSelect("pupae"))}
      ${field(ta(hass, "alates_seen"), `<input type="checkbox" name="alates">`)}
      ${field(ta(hass, "notes"), `<input name="notes">`, true)}
    </div>`;
  }, async (body) => {
    const d = readForm(body);
    const data = {};
    if (d.queen) data.queen = d.queen;
    for (const k of ["queens", "workers", "majors"]) if (d[k] !== null && d[k] !== undefined && d[k] !== "") data[k] = Number(d[k]);
    for (const k of ["eggs", "larvae", "pupae"]) if (d[k] !== "" && d[k] !== null && d[k] !== undefined) data[k] = Number(d[k]);
    if (d.alates) data.alates = true;
    await hass.callWS({ type: "arthropoda/journal/add", animal_ids: animals.map((a) => a.id), entry_type: "census",
      data, notes: d.notes || null });
    toast(host, ta(hass, "census_saved"));
    onDone?.();
    return true;
  });
}

function openAntSettings(host, hass, a) {
  const cfg = a.ant.settings;
  const own = a.ant.own || {};
  openDialog(hass, `${ta(hass, "settings")} ${a.name}`, (body) => {
    body.innerHTML = `<div class="ak-grid">
      ${field(ta(hass, "type"), selectHtml("type", ["generalist", "harvester", "leafcutter", "predator", "honeypot"].map((x) => [x, ta(hass, `t_${x}`)]), cfg.type, false))}
      ${field(ta(hass, "founding"), selectHtml("founding", ["claustral", "semi_claustral", "parasitic", "unknown"].map((x) => [x, ta(hass, `f_${x}`)]), cfg.founding, false))}
      ${field(ta(hass, "stage"), selectHtml("stage", ["founding", "nanitics", "growing", "mature"].map((x) => [x, ta(hass, `stage_${x}`)]), cfg.stage || "", true, ta(hass, "stage_auto")))}
      ${field(ta(hass, "caught_place"), `<input name="caught_place" value="${esc(cfg.caught_place || "")}">`)}
      ${field(ta(hass, "polygyne"), `<input type="checkbox" name="polygyne" ${cfg.polygyne ? "checked" : ""}>`)}
      ${field(ta(hass, "polymorphic"), `<input type="checkbox" name="polymorphic" ${cfg.polymorphic ? "checked" : ""}>`)}
      ${field(ta(hass, "queen_check_days"), NUMBER("queen_check_days", cfg.queen_check_days, 1))}
      <div class="ak-field wide"><b>${esc(ta(hass, "food_title"))}</b></div>
      ${Object.keys(STREAM_ICON).map((s) => field(`${STREAM_ICON[s]} ${ta(hass, `s_${s}`)}`,
        `<input type="number" min="0" step="0.5" data-food="${s}" value="${esc(own.food?.[s] ?? "")}" placeholder="${esc(cfg.food[s] ?? "–")}">`)).join("")}
    </div>`;
  }, async (body) => {
    const d = readForm(body);
    const food = {};
    body.querySelectorAll("[data-food]").forEach((i) => { if (i.value !== "") food[i.dataset.food] = Number(i.value); });
    await hass.callWS({ type: "arthropoda/ant/update", animal_id: a.id, changes: {
      type: d.type, founding: d.founding, stage: d.stage || null, caught_place: d.caught_place || null,
      polygyne: !!d.polygyne, polymorphic: !!d.polymorphic, queen_check_days: d.queen_check_days || null, food,
    } });
    toast(host, ta(hass, "saved"));
    return true;
  });
}

async function openAddQueens(host, hass, onDone) {
  const { species } = await hass.callWS({ type: "arthropoda/species/list" });
  const sorted = [...species].sort((x, y) => Number(y.group === "ant") - Number(x.group === "ant") || x.scientific_name.localeCompare(y.scientific_name));
  const today = new Date().toISOString().slice(0, 10);
  openDialog(hass, ta(hass, "add_queens"), (body) => {
    body.innerHTML = `<div class="ak-grid">
      ${field(ta(hass, "species"), selectHtml("species_id", sorted.map((s) => [s.id, `${s.group === "ant" ? "🐜 " : ""}${s.scientific_name}`]), sorted[0]?.id ?? "", false), true)}
      ${field(ta(hass, "count"), NUMBER("count", 1, 1))}
      ${field(ta(hass, "prefix"), `<input name="prefix" placeholder="Lasius Q">`)}
      ${field(ta(hass, "caught_at"), `<input type="date" name="caught_at" value="${today}">`)}
      ${field(ta(hass, "caught_place"), `<input name="caught_place">`)}
    </div>`;
    const sel = body.querySelector('[name="species_id"]');
    const prefix = body.querySelector('[name="prefix"]');
    const sync = () => {
      const sp = sorted.find((s) => String(s.id) === sel.value);
      prefix.placeholder = sp ? `${sp.scientific_name.split(" ")[0]} Q` : "Q";
    };
    sel.addEventListener("change", sync);
    sync();
  }, async (body) => {
    const d = readForm(body);
    const sp = sorted.find((s) => String(s.id) === String(d.species_id));
    if (!sp) throw new Error(ta(hass, "species"));
    const base = (d.prefix || body.querySelector('[name="prefix"]').placeholder).trim();
    const store = getStore(hass);
    const taken = new Set((store.animals || []).map((a) => a.name));
    let n = 1;
    const count = Math.max(1, Math.min(50, Number(d.count) || 1));
    for (let i = 0; i < count; i++) {
      while (taken.has(`${base}${n}`)) n++;
      const name = `${base}${n}`;
      taken.add(name);
      const res = await hass.callWS({ type: "arthropoda/animal/add", data: {
        name, species_id: sp.id, kind: "colony", acquired_at: d.caught_at || null, origin: "wild_caught" } });
      await hass.callWS({ type: "arthropoda/ant/update", animal_id: res.animal_id,
        changes: { enabled: true, caught_place: d.caught_place || null } });
    }
    toast(host, ta(hass, "queens_added", { n: count }));
    onDone?.();
    return true;
  });
}

/** Knoppen van mierenkaarten (tab, werkscherm, dierpagina). Geeft true als afgehandeld. */
export async function handleAntClick(host, hass, btn, onDone = null) {
  const store = getStore(hass);
  const find = (id) => (store.animals || []).find((a) => a.id === id);
  try {
    if (btn.dataset.antFeed) {
      const s = btn.dataset.antFeed;
      await hass.callWS({ type: "arthropoda/journal/add", animal_ids: [btn.dataset.animal], entry_type: STREAM_ENTRY[s],
        data: { source: "ants", stream: s } });
      toast(host, `${STREAM_ICON[s]} ${ta(hass, `s_${s}`)} ${ta(hass, "fed")}`);
      onDone?.();
      return true;
    }
    if (btn.dataset.antLeftovers) {
      await hass.callWS({ type: "arthropoda/journal/add", animal_ids: [btn.dataset.antLeftovers], entry_type: "remove_leftovers" });
      toast(host, "🧹 ✓");
      onDone?.();
      return true;
    }
    if (btn.dataset.antCensus) { openCensusDialog(host, hass, [find(btn.dataset.antCensus)], onDone); return true; }
    if (btn.dataset.antSettings) { openAntSettings(host, hass, find(btn.dataset.antSettings)); return true; }
    if (btn.dataset.moduleWet !== undefined && btn.dataset.enc) {
      await hass.callWS({ type: "arthropoda/module/wetted", enclosure_id: Number(btn.dataset.enc), index: Number(btn.dataset.moduleWet) });
      toast(host, ta(hass, "module_saved"));
      onDone?.();
      return true;
    }
  } catch (err) {
    toast(host, err.message || String(err));
    return true;
  }
  return false;
}

/** Werkscherm: mierenkolonies in deze kast. */
export function antsWorkCard(hass, residents) {
  const list = residents.filter((a) => a.ant);
  if (!list.length) return "";
  return `<div style="margin-top:12px" class="ant-grid">${list.map((a) => antCard(hass, a)).join("")}</div>`;
}

/** Werkscherm: nestmodules met metingen en 'bevochtigd'. */
export function modulesCard(hass, enc) {
  const modules = enc.modules || [];
  if (!modules.length) return "";
  const due = new Set((enc.tasks || []).filter((t) => t.kind === "module_wet" && new Date(t.due) <= new Date(new Date().setHours(23, 59, 59, 999))).map((t) => t.label));
  return `<div class="card" style="margin-top:12px"><h3>🧱 ${esc(ta(hass, "modules"))}</h3>
    ${modules.map((m, i) => {
      const v = m.values || {};
      const parts = [
        v.temperature != null ? `🌡 ${fmtNum(v.temperature)} °C` : "",
        v.humidity != null ? `💧 ${fmtNum(v.humidity, 0)} %${m.humidity_min != null ? ` (min ${fmtNum(m.humidity_min, 0)})` : ""}` : "",
        v.moisture != null ? `🧱 ${fmtNum(v.moisture, 0)}${m.moisture_min != null ? ` (min ${fmtNum(m.moisture_min, 0)})` : ""}` : "",
      ].filter(Boolean).join(" · ");
      const dry = due.has(m.name);
      return `<div class="module"><div class="grow"><b>${esc(m.name)}</b> <span class="muted small">${esc(ta(hass, `k_${m.kind}`))}${m.role ? ` · ${esc(ta(hass, `r_${m.role}`))}` : ""}</span>
        <div class="small ${dry ? "" : "muted"}" style="${dry ? "color:var(--error-color,#c62828)" : ""}">${parts || "–"}${m.wetted_at ? ` · 💧 ${esc(fmtDate(hass, m.wetted_at))}` : ""}${dry ? ` · ⚠ ${esc(ta(hass, "wet_due"))}` : ""}</div></div>
        ${m.kind !== "outworld" ? `<button class="ak ${dry ? "primary" : ""}" data-module-wet="${i}" data-enc="${enc.id}">${esc(ta(hass, "wetted"))}</button>` : ""}</div>`;
    }).join("")}</div>`;
}

/** Kastvenster: editor voor nestmodules. */
export function modulesEditor(hass, modules) {
  const sensors = (cls) => Object.keys(hass.states).filter((id) => id.startsWith("sensor.") || id.startsWith("input_number."))
    .filter((id) => !cls || cls.includes(hass.states[id].attributes.device_class)).sort()
    .map((id) => [id, hass.states[id].attributes.friendly_name || id]);
  const opts = { temp: sensors(["temperature"]), hum: sensors(["humidity", "moisture"]), moist: sensors(null) };
  const sel = (key, list, value) => `<select data-mod="${key}"><option value="">—</option>${
    [...(value && !list.some(([v]) => v === value) ? [[value, value]] : []), ...list]
      .map(([v, l]) => `<option value="${esc(v)}" ${v === value ? "selected" : ""}>${esc(l)}</option>`).join("")}</select>`;
  const row = (m = {}) => `<div class="ak-grid ak-mod" data-mod-id="${esc(m.id || "")}" style="align-items:end;margin-bottom:10px;padding-bottom:6px;border-bottom:1px dashed var(--divider-color,#ddd)">
    ${field(ta(hass, "m_name"), `<input data-mod="name" value="${esc(m.name || "")}" placeholder="Kamer 1">`)}
    ${field(ta(hass, "m_kind"), `<select data-mod="kind">${["chamber", "outworld", "tube"].map((k) => `<option value="${k}" ${m.kind === k ? "selected" : ""}>${esc(ta(hass, `k_${k}`))}</option>`).join("")}</select>`)}
    ${field(ta(hass, "m_role"), `<select data-mod="role">${["", "brood", "waste", "dry", "wet", "food"].map((r) => `<option value="${r}" ${(m.role || "") === r ? "selected" : ""}>${esc(ta(hass, `r_${r}`))}</option>`).join("")}</select>`)}
    ${field(ta(hass, "m_temp"), sel("temperature_sensor", opts.temp, m.temperature_sensor))}
    ${field(ta(hass, "m_hum"), sel("humidity_sensor", opts.hum, m.humidity_sensor))}
    ${field(ta(hass, "m_hum_min"), `<input type="number" data-mod="humidity_min" value="${esc(m.humidity_min ?? "")}">`)}
    ${field(ta(hass, "m_moist"), sel("moisture_sensor", opts.moist, m.moisture_sensor))}
    ${field(ta(hass, "m_moist_min"), `<input type="number" data-mod="moisture_min" value="${esc(m.moisture_min ?? "")}">`)}
    ${field(ta(hass, "m_every"), `<input type="number" step="0.5" data-mod="wet_every_days" value="${esc(m.wet_every_days ?? "")}">`)}
    <button type="button" class="ak-btn" data-mod-remove>✕</button></div>`;
  return {
    html: `<fieldset><legend>🧱 ${esc(ta(hass, "modules"))}</legend>
      <p style="margin:0 0 8px;font-size:.85em;color:var(--secondary-text-color)">${esc(ta(hass, "modules_note"))}</p>
      <div data-mod-list>${(modules || []).map(row).join("")}</div>
      <button type="button" class="ak-btn" data-mod-add>＋ ${esc(ta(hass, "add_module"))}</button></fieldset>`,
    wire(body) {
      body.querySelector("[data-mod-add]").addEventListener("click", () =>
        body.querySelector("[data-mod-list]").insertAdjacentHTML("beforeend", row()));
      body.querySelector("[data-mod-list]").addEventListener("click", (e) => {
        if (e.target.matches("[data-mod-remove]")) e.target.closest(".ak-mod").remove();
      });
    },
    read(body) {
      return [...body.querySelectorAll(".ak-mod")].map((r) => {
        const m = { id: r.dataset.modId || undefined };
        r.querySelectorAll("[data-mod]").forEach((el) => {
          const k = el.dataset.mod;
          if (el.value === "") return;
          m[k] = el.type === "number" ? Number(el.value) : el.value;
        });
        return m;
      }).filter((m) => m.name);
    },
  };
}

/** Tab Mieren. Geeft een functie terug die opnieuw tekent. */
export function renderAntsView(host, box, hass) {
  const store = getStore(hass);
  const selected = new Set();
  let stamp = null;
  const draw = (force = false) => {
    const list = ants(store);
    const next = JSON.stringify(list.map((a) => [a.id, a.name, a.ant, a.tasks, a.insights, a.acquired_at]));
    if (!force && next === stamp) return;
    stamp = next;
    const founding = list.filter((a) => a.ant.state.stage === "founding");
    const colonies = list.filter((a) => a.ant.state.stage !== "founding");
    box.innerHTML = `<div class="row wrap" style="margin-bottom:12px">
        <h2 class="grow" style="margin:0">🐜 ${esc(ta(hass, "title"))}</h2>
        <button class="ak primary" data-add-queens>${esc(ta(hass, "add_queens"))}</button></div>
      ${!list.length ? `<div class="card muted">${esc(ta(hass, "none"))}</div>` : ""}
      ${founding.length ? `<div class="card" style="margin-bottom:12px"><h3>👑 ${esc(ta(hass, "station"))} (${founding.length})</h3>
        <div class="muted small">${esc(ta(hass, "station_note"))}</div>
        <div class="row wrap" style="margin-top:8px">
          <button class="ak" data-select-all>${esc(ta(hass, "select_all"))}</button>
          <button class="ak primary" data-check-selected ${selected.size ? "" : "disabled"}>${esc(ta(hass, "check_selected"))}${selected.size ? ` (${selected.size})` : ""}</button></div></div>
        <div class="ant-grid" style="margin-bottom:16px">${founding.map((a) => antCard(hass, a, { selectable: true, selected: selected.has(a.id) })).join("")}</div>` : ""}
      ${colonies.length ? `<h3>${esc(ta(hass, "colonies"))} (${colonies.length})</h3>
        <div class="ant-grid">${colonies.map((a) => antCard(hass, a)).join("")}</div>` : ""}`;
  };
  box.onchange = (e) => {
    const id = e.target.dataset?.antSelect;
    if (!id) return;
    e.target.checked ? selected.add(id) : selected.delete(id);
    draw(true);
  };
  box.onclick = async (e) => {
    const btn = e.target.closest("button");
    if (!btn) return;
    if (btn.hasAttribute("data-add-queens")) return openAddQueens(host, hass, () => draw(true)).catch((err) => toast(host, err.message));
    if (btn.hasAttribute("data-select-all")) {
      ants(store).filter((a) => a.ant.state.stage === "founding").forEach((a) => selected.add(a.id));
      return draw(true);
    }
    if (btn.hasAttribute("data-check-selected")) {
      const list = ants(store).filter((a) => selected.has(a.id));
      if (list.length) openCensusDialog(host, hass, list, () => { selected.clear(); draw(true); });
      return;
    }
    await handleAntClick(host, hass, btn, () => draw(true));
  };
  draw(true);
  return draw;
}
