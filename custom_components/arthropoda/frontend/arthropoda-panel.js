/*
 * Arthropoda Keeper – zijbalkpaneel.
 *
 * Tabbladen: Collectie · Dagboek · Soorten · Klimaat, plus een detailpagina
 * per dier (/arthropoda?animal=<id>).
 */
import {
  BASE_CSS, commonName, daysText, dueText, esc, fmtDate, fmtDateTime, fmtNum, getStore,
  navigate, nextTask, openAnimalDialog, openJournalDialog, quickLog, rangeBar, stageText, t, toast,
  feederFilter, field, isFeeder, openDialog, photoCredit, photoUrl,
} from "./arthropoda-common.js?v=0.10.0";
import {
  WORK_CSS, dims, getRound, openEnclosureDialog, openLabelsDialog, openNfcDialog, openRoundSummary,
  openTasks, renderWorkScreen, startRound, te,
} from "./arthropoda-enclosures.js?v=0.10.0";

const CSS = `
  ${BASE_CSS}
  ${WORK_CSS}
  .enc-code { font-size: 1.4em; font-weight: 600; }
  :host { display:block; min-height:100vh; background: var(--primary-background-color, #fafafa);
          color: var(--primary-text-color); font-family: var(--paper-font-body1_-_font-family, Roboto, sans-serif); }
  header { display:flex; align-items:center; gap:8px; height:56px; padding:0 12px;
           background: var(--app-header-background-color, var(--primary-color, #03a9f4));
           color: var(--app-header-text-color, #fff); position: sticky; top: 0; z-index: 2; }
  header h1 { font-size: 20px; font-weight: 400; margin: 0 0 0 4px; }
  nav { display:flex; gap:4px; padding: 0 12px; background: var(--app-header-background-color, var(--primary-color, #03a9f4));
        position: sticky; top: 56px; z-index: 2; overflow-x: auto; }
  nav button { font: inherit; border: none; background: none; color: var(--app-header-text-color, #fff); opacity: .75;
               padding: 10px 14px; cursor: pointer; border-bottom: 2px solid transparent; white-space: nowrap; }
  nav button.active { opacity: 1; border-bottom-color: var(--app-header-text-color, #fff); }
  main { padding: 16px; max-width: 1400px; margin: 0 auto; }
  .toolbar { display:flex; gap:8px; align-items:center; flex-wrap:wrap; margin-bottom: 14px; }
  .toolbar input, .toolbar select { font: inherit; padding: 8px 12px; border-radius: 18px; border: 1px solid var(--ak-line);
          background: var(--card-background-color, #fff); color: var(--primary-text-color); min-width: 0; }
  .toolbar input[type=search] { flex: 1; max-width: 360px; }
  .card { background: var(--card-background-color, #fff); border-radius: var(--ha-card-border-radius, 12px);
          box-shadow: var(--ha-card-box-shadow, 0 1px 3px rgba(0,0,0,.12)); border: var(--ha-card-border-width, 0) solid var(--ha-card-border-color, transparent);
          padding: 14px 16px; }
  .card h3 { margin: 0 0 10px; font-size: 1.05em; font-weight: 500; }
  .grid { display:grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 14px; }
  .tile { cursor: pointer; display:flex; flex-direction:column; gap: 10px; }
  .tile:hover { box-shadow: 0 2px 10px rgba(0,0,0,.18); }
  .tile .name { font-size: 1.1em; font-weight: 500; }
  .metric { display:grid; grid-template-columns: 110px 1fr 70px; align-items:center; gap: 8px; font-size: .9em; }
  .metric .val { text-align: right; font-variant-numeric: tabular-nums; }
  .facts { display:grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 6px 14px; font-size: .9em; }
  .facts div span:first-child { display:block; color: var(--ak-muted); font-size: .85em; }
  .actions { display:flex; gap: 6px; flex-wrap: wrap; }
  .detail { display:grid; grid-template-columns: repeat(auto-fit, minmax(340px, 1fr)); gap: 14px; }
  .detail .full { grid-column: 1 / -1; }
  .head { display:flex; align-items:flex-start; gap: 12px; flex-wrap: wrap; margin-bottom: 14px; }
  .head h2 { margin: 0; font-weight: 400; font-size: 1.6em; }
  table { width: 100%; border-collapse: collapse; font-size: .9em; }
  th { text-align: left; font-weight: 500; color: var(--ak-muted); padding: 6px 8px; border-bottom: 1px solid var(--ak-line); }
  td { padding: 8px; border-bottom: 1px solid var(--ak-line); vertical-align: top; }
  tr.click { cursor: pointer; } tr.click:hover td { background: var(--secondary-background-color, #f5f5f5); }
  .timeline .entry { display:flex; gap: 12px; padding: 8px 0; border-bottom: 1px solid var(--ak-line); }
  .timeline .entry:last-child { border-bottom: none; }
  .timeline .when { width: 150px; flex: none; color: var(--ak-muted); font-size: .85em; }
  .empty { padding: 30px; text-align:center; color: var(--ak-muted); }
  .species-layout { display:grid; grid-template-columns: minmax(240px, 340px) 1fr; gap: 14px; }
  .species-list .item { padding: 8px 10px; border-radius: 8px; cursor: pointer; }
  .species-list .item:hover, .species-list .item.active { background: var(--secondary-background-color, #f0f0f0); }
  textarea.yaml { width: 100%; min-height: 420px; font-family: var(--code-font-family, monospace); font-size: 13px;
                  padding: 10px; border-radius: 8px; border: 1px solid var(--ak-line); background: var(--code-editor-background-color, var(--secondary-background-color, #f7f7f7));
                  color: var(--primary-text-color); }
  .photo-box img { width: 100%; max-height: 280px; object-fit: cover; border-radius: 10px; display:block; }
  .photo-box .ph { height: 140px; display:flex; align-items:center; justify-content:center; font-size: 48px;
                   border-radius: 10px; background: var(--secondary-background-color, #f0f0f0); }
  .credit { font-size: .75em; color: var(--ak-muted); margin-top: 4px; }
  .credit a { color: inherit; }
  .species-list .item { display:flex; gap: 10px; align-items:center; }
  .species-list .thumb { width: 40px; height: 40px; border-radius: 8px; object-fit: cover; flex: none;
                         background: var(--secondary-background-color, #eee); }
  .photo-grid { display:grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 10px; }
  .photo-grid figure { margin: 0; cursor: pointer; border-radius: 10px; overflow: hidden; border: 2px solid transparent; }
  .photo-grid figure:hover { border-color: var(--ak-accent); }
  .photo-grid img { width: 100%; height: 120px; object-fit: cover; display:block; }
  .photo-grid figcaption { font-size: .7em; padding: 4px 6px; color: var(--ak-muted); }
  .chart { width: 100%; height: 150px; }
  .chart text { font-size: 10px; fill: var(--ak-muted); }
  .doc-row { display:flex; gap: 10px; align-items:center; padding: 6px 0; border-bottom: 1px solid var(--ak-line); font-size: .9em; }
  .doc-row:last-child { border-bottom: none; }
  .inline-form { display:grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 8px; margin-top: 10px; }
  .inline-form input, .inline-form select { font: inherit; padding: 7px 10px; border-radius: 8px; border: 1px solid var(--ak-line);
          background: var(--card-background-color, #fff); color: var(--primary-text-color); min-width: 0; width: 100%; }
  .qty { display:inline-flex; align-items:center; gap: 6px; font-variant-numeric: tabular-nums; }
  .qty button { width: 28px; height: 28px; border-radius: 50%; border: 1px solid var(--ak-line); background: none;
                color: var(--primary-text-color); cursor: pointer; }
  .msg { margin-top: 8px; } .msg.error { color: var(--ak-problem); }
  @media (max-width: 700px) {
    main { padding: 10px; } .species-layout { grid-template-columns: 1fr; }
    .metric { grid-template-columns: 90px 1fr 60px; } .timeline .when { width: 100px; }
  }
`;

const TABS = ["collection", "enclosures", "journal", "breeding", "stock", "species", "climate"];

class ArthropodaPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._view = null;
    this._search = "";
    this._journalTimer = null;
    this._onLocation = () => this._readLocation();
  }

  set hass(hass) {
    const first = !this._hass;
    this._hass = hass;
    if (this._menu) { this._menu.hass = hass; }
    if (first) {
      this._store = getStore(hass);
      this._store.addEventListener("change", () => this._update());
      this._build();
      this._readLocation();
    }
  }
  get hass() { return this._hass; }

  set narrow(value) { this._narrow = value; if (this._menu) this._menu.narrow = value; }

  connectedCallback() { window.addEventListener("location-changed", this._onLocation); window.addEventListener("popstate", this._onLocation); }
  disconnectedCallback() { window.removeEventListener("location-changed", this._onLocation); window.removeEventListener("popstate", this._onLocation); }

  // --- opbouw ---------------------------------------------------------------

  _build() {
    const h = this._hass;
    this.shadowRoot.innerHTML = `<style>${CSS}</style>
      <header><span class="menu"></span><h1>Arthropoda</h1></header>
      <nav>${TABS.map((tab) => `<button data-tab="${tab}">${esc(t(h, tab))}</button>`).join("")}</nav>
      <main></main>`;
    if (customElements.get("ha-menu-button")) {
      this._menu = document.createElement("ha-menu-button");
      this._menu.hass = h;
      this._menu.narrow = this._narrow;
      this.shadowRoot.querySelector(".menu").appendChild(this._menu);
    }
    this.shadowRoot.querySelectorAll("nav button").forEach((b) =>
      b.addEventListener("click", () => navigate(`/arthropoda?view=${b.dataset.tab}`)));
    this._main = this.shadowRoot.querySelector("main");
  }

  _readLocation() {
    if (!location.pathname.startsWith("/arthropoda")) return;
    const params = new URLSearchParams(location.search);
    const animal = params.get("animal");
    const enclosure = params.get("enclosure");
    const view = enclosure ? "work" : animal ? "animal"
      : (TABS.includes(params.get("view")) ? params.get("view") : "collection");
    if (view !== this._view || animal !== this._animalId || enclosure !== this._encCode) {
      this._view = view;
      this._animalId = animal;
      this._encCode = enclosure;
      this._renderView();
    }
  }

  _renderView() {
    if (!this._main) return;
    const h = this._hass;
    this.shadowRoot.querySelectorAll("nav button").forEach((b) =>
      b.classList.toggle("active", b.dataset.tab === this._view));
    // Nieuw element per weergave, zodat oude klik-handlers niet blijven hangen.
    const main = document.createElement("main");
    this._main.replaceWith(main);
    this._main = main;
    if (this._view === "collection") this._viewCollection();
    else if (this._view === "animal") this._viewAnimal();
    else if (this._view === "journal") this._viewJournal();
    else if (this._view === "species") this._viewSpecies();
    else if (this._view === "climate") this._viewClimate();
    else if (this._view === "breeding") this._viewBreeding();
    else if (this._view === "enclosures") this._viewEnclosures();
    else if (this._view === "work") this._viewWork();
    else if (this._view === "stock") this._viewStock();
    this._update();
    window.scrollTo(0, 0);
    void h;
  }

  _update() {
    if (!this._main) return;
    if (this._store.error && !this._store.animals) {
      this._main.innerHTML = `<div class="empty">${esc(this._store.error)}</div>`;
      return;
    }
    const fn = { collection: this._updateCollection, animal: this._updateAnimal,
                 climate: this._updateClimate, enclosures: this._updateEnclosures,
                 work: () => this._workDraw?.() }[this._view];
    if (fn) fn.call(this);
    if (this._view === "animal" || this._view === "journal") {
      clearTimeout(this._journalTimer);
      this._journalTimer = setTimeout(() => this._loadJournal(), 400);
    }
    if (this._view === "animal") {
      clearTimeout(this._extraTimer);
      this._extraTimer = setTimeout(() => this._loadAnimalExtras(), 500);
    }
    if (this._view === "breeding" || this._view === "stock") {
      clearTimeout(this._extraTimer);
      this._extraTimer = setTimeout(() => (this._view === "breeding" ? this._loadBreeding() : this._loadStock()), 400);
    }
  }

  _err(err) { toast(this, err.message || String(err)); }

  // --- collectie ------------------------------------------------------------

  _viewCollection() {
    const h = this._hass;
    this._main.innerHTML = `
      <div class="toolbar">
        <input type="search" placeholder="${esc(t(h, "search"))}" value="${esc(this._search)}">
        <select data-feeders>
          <option value="all">${esc(t(h, "filter_all"))}</option>
          <option value="no_feeders">${esc(t(h, "filter_no_feeders"))}</option>
          <option value="only_feeders">${esc(t(h, "filter_only_feeders"))}</option>
        </select>
        <select data-filter>
          <option value="active">${esc(t(h, "ok"))} + ${esc(t(h, "problem"))}</option>
          <option value="problem">${esc(t(h, "problem"))}</option>
          <option value="all">${esc(t(h, "show_inactive"))}</option>
        </select>
        <span class="grow"></span>
        <button class="ak" data-journal>✎ ${esc(t(h, "new_entry"))}</button>
        <button class="ak primary" data-add>＋ ${esc(t(h, "add_animal"))}</button>
      </div>
      <div class="grid" data-list></div>`;
    const search = this._main.querySelector("input[type=search]");
    search.addEventListener("input", () => { this._search = search.value; this._updateCollection(); });
    const filter = this._main.querySelector("[data-filter]");
    filter.value = this._filter || "active";
    filter.addEventListener("change", () => { this._filter = filter.value; this._updateCollection(); });
    const feeders = this._main.querySelector("[data-feeders]");
    feeders.value = this._feeders || "all";
    feeders.addEventListener("change", () => { this._feeders = feeders.value; this._updateCollection(); });
    this._main.querySelector("[data-add]").addEventListener("click", () =>
      openAnimalDialog(h).catch((e) => this._err(e)));
    this._main.querySelector("[data-journal]").addEventListener("click", () => openJournalDialog(h, []));
    this._main.querySelector("[data-list]").addEventListener("click", (e) => this._onTileClick(e));
  }

  _filtered() {
    const q = this._search.trim().toLowerCase();
    const filter = this._filter || "active";
    return feederFilter(this._store.animals || [], this._feeders || "all").filter((a) => {
      if (filter === "active" && a.state === "inactive") return false;
      if (filter === "problem" && a.state !== "problem") return false;
      if (!q) return true;
      return [a.name, a.species?.scientific_name, commonName(this._hass, a.species)]
        .some((v) => (v || "").toLowerCase().includes(q));
    });
  }

  _updateCollection() {
    const list = this._main.querySelector("[data-list]");
    if (!list) return;
    const h = this._hass;
    const animals = this._filtered();
    if (!this._store.animals) { list.innerHTML = `<div class="empty">…</div>`; return; }
    if (!animals.length) { list.innerHTML = `<div class="empty">${esc(t(h, "no_animals"))}</div>`; return; }
    list.innerHTML = animals.map((a) => this._tile(a)).join("");
  }

  _statusChip(a) {
    const h = this._hass;
    const label = a.state === "problem"
      ? a.problems.map((p) => this._problemText(p)).join(", ")
      : t(h, a.state === "ok" ? "ok" : "inactive");
    return `<span class="chip ${a.state}"><span class="dot ${a.state}"></span>${esc(label)}</span>`;
  }

  _problemText(problem) {
    const h = this._hass;
    const lang = (h.language || "en").slice(0, 2);
    const nl = { temperature_critical: "gevaarlijk warm", temperature_low: "te koud", temperature_high: "te warm",
      humidity_low: "te droog", humidity_high: "te vochtig", water_temperature_low: "water te koud",
      water_temperature_high: "water te warm", sensor_unavailable: "sensor weg", feeding_overdue: "voederen",
      cleaning_overdue: "schoonmaken", water_change_overdue: "waterwissel" };
    return lang === "nl" ? (nl[problem] || problem) : problem.replaceAll("_", " ");
  }

  _metrics(a) {
    const h = this._hass;
    const rows = [];
    const r = a.readings;
    if (r.temperature !== null || (a.climate_config || a.config).temperature_sensors?.length) {
      rows.push([t(h, "temperature"), r.temperature, a.targets.temperature, "°C"]);
    }
    if (r.humidity !== null || (a.climate_config || a.config).humidity_sensor) {
      rows.push([t(h, "humidity"), r.humidity, a.targets.humidity, "%"]);
    }
    if (r.water_temperature !== null || (a.climate_config || a.config).water_temperature_sensor) {
      rows.push([t(h, "water_temperature"), r.water_temperature, a.targets.water_temperature, "°C"]);
    }
    return rows.map(([label, value, target, unit]) => `
      <div class="metric"><span class="muted">${esc(label)}</span>${rangeBar(value, target)}
        <span class="val">${value === null || value === undefined ? `<span class="muted small">${esc(t(h, "unavailable"))}</span>` : `${fmtNum(value)} ${unit}`}</span></div>`).join("");
  }

  _tile(a) {
    const h = this._hass;
    const task = nextTask(a);
    const photo = photoUrl(this._hass, a);
    return `<div class="card tile" data-id="${esc(a.id)}">
      <div class="row">${photo ? `<img class="avatar" src="${esc(photo)}" alt="" loading="lazy">` : `<span class="avatar ph">🕷</span>`}<div class="grow">
        <div class="name ellipsis">${esc(a.name)}</div>
        <div class="muted small ellipsis"><i>${esc(a.species?.scientific_name || "")}</i>${commonName(h, a.species) ? ` · ${esc(commonName(h, a.species))}` : ""}</div>
      </div>${this._statusChip(a)}</div>
      ${isFeeder(a) || a.status === "diapause" ? `<div class="row wrap">
        ${isFeeder(a) ? `<span class="chip">🦗 ${esc(t(h, "feeder"))}</span>` : ""}
        ${a.status === "diapause" ? `<span class="chip">❄ ${esc(t(h, "diapause"))}${a.diapause?.earliest_end ? ` · ${esc(t(h, "earliest_end").toLowerCase())} ${esc(fmtDate(h, a.diapause.earliest_end))}` : ""}</span>` : ""}
      </div>` : ""}
      ${this._metrics(a)}
      <div class="facts">
        <div><span>${esc(t(h, "stage"))}</span><span>${esc(stageText(this._store, a) || "–")}${a.premolt ? ` · ${esc(t(h, "premolt"))}` : ""}</span></div>
        <div><span>${esc(t(h, "feeding"))}</span><span>${esc(daysText(h, a.days_since.feeding))}</span></div>
        ${task ? `<div><span>${esc(t(h, "next_task"))}</span><span>${esc(t(h, task.kind))} · ${esc(dueText(h, task.due))}</span></div>` : ""}
      </div>
      <div class="actions">
        <button class="ak" data-quick="feeding">🍽 ${esc(t(h, "fed"))}</button>
        <button class="ak" data-quick="misting_manual">💧 ${esc(t(h, "misted"))}</button>
        <button class="ak" data-entry>✎</button>
        <button class="ak" data-edit>⚙ ${esc(t(h, "edit"))}</button>
      </div>
    </div>`;
  }

  _onTileClick(e) {
    const tile = e.target.closest("[data-id]");
    if (!tile) return;
    const id = tile.dataset.id;
    const animal = this._store.animal(id);
    const btn = e.target.closest("button");
    if (btn?.dataset.quick) return quickLog(this, this._hass, id, btn.dataset.quick);
    if (btn?.hasAttribute("data-entry")) return openJournalDialog(this._hass, [id]);
    if (btn?.hasAttribute("data-edit")) return openAnimalDialog(this._hass, animal).catch((err) => this._err(err));
    if (!btn) navigate(`/arthropoda?animal=${encodeURIComponent(id)}`);
  }

  // --- dierdetail -----------------------------------------------------------

  _viewAnimal() {
    this._main.innerHTML = `<div data-detail></div>
      <div class="detail" style="margin-top:14px">
        <div class="card"><h3>${esc(t(this._hass, "growth"))}</h3><div data-growth>…</div></div>
        <div class="card"><h3>${esc(t(this._hass, "lineage"))}</h3><div data-lineage></div></div>
        <div class="card"><h3>${esc(t(this._hass, "documents"))}</h3><div data-docs>…</div>
          <div class="inline-form" data-doc-form>
            <select name="type">${["invoice", "cites", "permit", "breeder_statement", "health", "other"].map((d) => `<option value="${d}">${esc(t(this._hass, `doc_${d}`))}</option>`).join("")}</select>
            <input name="title" placeholder="${esc(t(this._hass, "doc_title"))}">
            <input name="issued_at" type="date" title="${esc(t(this._hass, "issued_at"))}">
            <input name="expires_at" type="date" title="${esc(t(this._hass, "expires_at"))}">
            <input name="file" type="file" accept="application/pdf,image/jpeg,image/png,image/webp">
            <button class="ak" data-doc-add>＋ ${esc(t(this._hass, "add_document"))}</button>
          </div>
        </div>
      </div>
      <div class="card" style="margin-top:14px"><h3>${esc(t(this._hass, "journal"))}</h3><div class="timeline" data-journal></div></div>`;
    this._main.addEventListener("click", (e) => this._onDetailClick(e));
  }

  _updateAnimal() {
    const box = this._main.querySelector("[data-detail]");
    if (!box) return;
    const h = this._hass;
    const a = this._store.animal(this._animalId);
    if (!a) { box.innerHTML = this._store.animals ? `<div class="empty">?</div>` : "…"; return; }
    const L = (g, v) => this._store.label(g, v);
    const tasks = [...a.tasks].sort((x, y) => x.due.localeCompare(y.due));
    const profile = Object.entries(a.profile || {}).filter(([k]) => k !== "notes");
    const climateLabel = t(h, `climate_${a.climate.status}`);
    box.innerHTML = `
      <div class="head">
        <button class="icon" data-back title="${esc(t(h, "back"))}">←</button>
        <div class="grow">
          <h2>${esc(a.name)}</h2>
          <div class="muted"><i>${esc(a.species?.scientific_name || "")}</i>${commonName(h, a.species) ? ` · ${esc(commonName(h, a.species))}` : ""}</div>
        </div>
        ${this._statusChip(a)}
      </div>
      <div class="actions" style="margin-bottom:14px">
        <button class="ak" data-quick="feeding">🍽 ${esc(t(h, "fed"))}</button>
        <button class="ak" data-quick="misting_manual">💧 ${esc(t(h, "misted"))}</button>
        <button class="ak" data-quick="spot_clean">🧹 ${esc(t(h, "cleaned"))}</button>
        <button class="ak" data-entry>✎ ${esc(t(h, "new_entry"))}</button>
        <button class="ak primary" data-edit>⚙ ${esc(t(h, "edit"))}</button>
      </div>
      <div class="detail">
        <div class="card photo-box">
          ${photoUrl(h, a) ? `<img src="${esc(photoUrl(h, a))}" alt="${esc(a.name)}">` : `<div class="ph">🕷</div>`}
          ${photoCredit(h, a) ? `<div class="credit">${esc(photoCredit(h, a))} · iNaturalist</div>` : ""}
          <div class="actions" style="margin-top:10px">
            <button class="ak" data-upload>📷 ${esc(t(h, "upload_photo"))}</button>
            ${h.states[a.entities.photo]?.attributes.source === "own" ? `<button class="ak danger" data-photo-del>${esc(t(h, "delete_photo"))}</button>` : ""}
            <input type="file" accept="image/jpeg,image/png,image/webp" data-file hidden>
          </div>
        </div>
        <div class="card"><h3>${esc(t(h, "climate"))} <span class="chip">${esc(climateLabel)}</span>
            <span class="chip">${esc(t(h, a.is_day ? "day" : "night"))}</span></h3>
          ${this._metrics(a) || `<div class="muted small">–</div>`}
          ${a.climate.actuators.length ? `<table style="margin-top:10px"><tr><th>${esc(t(h, "actuator"))}</th><th>${esc(t(h, "action"))}</th><th>${esc(t(h, "reason"))}</th></tr>
            ${a.climate.actuators.map((r) => `<tr><td>${esc(h.states[r.entity_id]?.attributes.friendly_name || r.entity_id)}<div class="muted small">${esc(t(h, r.role))}</div></td>
              <td>${esc(r.action)}</td><td>${esc(r.reason)}${r.conflict ? ` <span class="chip problem">${esc(t(h, "conflict"))}</span>` : ""}</td></tr>`).join("")}</table>` : ""}
        </div>
        <div class="card"><h3>${esc(t(h, "care"))}</h3>
          <div class="facts">
            <div><span>${esc(t(h, "stage"))}</span><span>${esc(stageText(this._store, a) || "–")}</span></div>
            <div><span>${esc(t(h, "sex"))}</span><span>${esc(L("sex", a.sex))}</span></div>
            <div><span>${esc(t(h, "feeding"))}</span><span>${esc(daysText(h, a.days_since.feeding))}${a.feeding_paused ? ` <span class="chip">${esc(t(h, "feeding_paused"))}</span>` : ""}</span></div>
            ${a.can_molt || a.molt_count ? `<div><span>${esc(t(h, "molt"))}</span><span>${esc(daysText(h, a.days_since.molt))} · ${a.molt_count} ${esc(t(h, "molts"))}</span></div>` : ""}
            <div><span>${esc(t(h, "cleaning"))}</span><span>${esc(daysText(h, a.days_since.cleaning))}</span></div>
            ${a.diapause ? `<div><span>${esc(t(h, "in_diapause_since"))}</span><span>❄ ${esc(fmtDate(h, a.diapause.start))}</span></div>` : ""}
            ${a.diapause?.earliest_end ? `<div><span>${esc(t(h, "earliest_end"))}</span><span>${esc(fmtDate(h, a.diapause.earliest_end))}</span></div>` : ""}
            ${a.diapause?.latest_end ? `<div><span>${esc(t(h, "latest_end"))}</span><span>${esc(fmtDate(h, a.diapause.latest_end))}</span></div>` : ""}
            ${a.diapause?.planned_end ? `<div><span>${esc(t(h, "planned_end"))}</span><span>${esc(fmtDate(h, a.diapause.planned_end))}</span></div>` : ""}
            ${a.next_molt ? `<div><span>${esc(t(h, "next_molt"))}</span><span>${esc(fmtDate(h, a.next_molt))}</span></div>` : ""}
            ${a.acquired_at ? `<div><span>${esc(t(h, "acquired_at"))}</span><span>${esc(fmtDate(h, a.acquired_at))}</span></div>` : ""}
            ${a.origin ? `<div><span>${esc(t(h, "origin"))}</span><span>${esc(L("origin", a.origin))}</span></div>` : ""}
            ${a.enclosure_id ? (() => { const enc = this._store.enclosure(a.enclosure_id);
                return enc ? `<div><span>${esc(t(h, "enclosure"))}</span><span><a href="/arthropoda?enclosure=${esc(enc.code)}&via=app" data-nav>${esc(enc.code)}${enc.name ? ` – ${esc(enc.name)}` : ""}</a></span></div>` : ""; })() : ""}
            ${a.config.seller ? `<div><span>${esc(t(h, "seller"))}</span><span>${esc(a.config.seller)}</span></div>` : ""}
            ${a.config.price !== undefined && a.config.price !== null ? `<div><span>${esc(t(h, "price"))}</span><span>€ ${fmtNum(a.config.price, 2)}</span></div>` : ""}
            ${a.lineage?.generation ? `<div><span>${esc(t(h, "generation"))}</span><span>${esc(a.lineage.generation)}</span></div>` : ""}
          </div>
          ${(a.config.food_plants || []).length ? `<h3 style="margin-top:14px">${esc(t(h, "food_plants"))}</h3>
            ${a.config.food_plants.map((id) => {
              const st = h.states[id];
              const state = st ? (st.state === "ok" ? "ok" : st.state === "problem" ? "problem" : "inactive") : "inactive";
              return `<div class="row small" style="padding:3px 0"><span class="dot ${state}"></span><span class="grow">${esc(st?.attributes.friendly_name || id)}</span><span class="muted">${esc(st?.state ?? "?")}</span></div>`;
            }).join("")}` : ""}
          <h3 style="margin-top:14px">${esc(t(h, "tasks"))}</h3>
          ${tasks.length ? tasks.map((tk) => `<div class="row small" style="padding:3px 0"><span class="grow">${esc(t(h, tk.kind))}</span><span class="muted">${esc(dueText(h, tk.due))}</span></div>`).join("") : `<div class="muted small">${esc(t(h, "no_tasks"))}</div>`}
        </div>
        <div class="card"><h3>${esc(t(h, "profile"))}</h3>
          ${profile.length ? `<table>${profile.map(([k, v]) => `<tr><td class="muted">${esc(t(h, `prof_${k}`) === `prof_${k}` ? k : t(h, `prof_${k}`))}</td><td>${esc(Array.isArray(v) ? v.join(" – ") : v)}</td></tr>`).join("")}</table>` : `<div class="muted small">–</div>`}
        </div>
        ${Object.keys(a.measurements).length ? `<div class="card"><h3>${esc(t(h, "measurements"))}</h3><div class="facts">
          ${Object.entries(a.measurements).map(([k, m]) => `<div><span>${esc(t(h, k))}</span><span>${fmtNum(m.value, 2)} ${esc(m.unit || "")} <span class="muted small">${esc(fmtDate(h, m.ts))}</span></span></div>`).join("")}
        </div></div>` : ""}
      </div>`;
    this._wireLinks(box);
  }

  _onDetailClick(e) {
    const btn = e.target.closest("button");
    if (!btn || this._view !== "animal") return;
    const id = this._animalId;
    if (btn.hasAttribute("data-back")) return navigate("/arthropoda?view=collection");
    if (btn.dataset.quick) return quickLog(this, this._hass, id, btn.dataset.quick);
    if (btn.hasAttribute("data-entry")) return openJournalDialog(this._hass, [id]);
    if (btn.hasAttribute("data-edit")) return openAnimalDialog(this._hass, this._store.animal(id)).catch((err) => this._err(err));
    if (btn.dataset.del) return this._deleteEntry(Number(btn.dataset.del));
    if (btn.hasAttribute("data-upload")) {
      const input = this._main.querySelector("[data-file]");
      input.onchange = () => input.files[0] && this._uploadPhoto(id, input.files[0]);
      return input.click();
    }
    if (btn.hasAttribute("data-doc-add")) return this._addDocument(id);
    if (btn.dataset.docDel) return this._deleteDocument(Number(btn.dataset.docDel));
    if (btn.hasAttribute("data-photo-del")) {
      return this._hass.callWS({ type: "arthropoda/animal/photo/delete", animal_id: id }).catch((err) => this._err(err));
    }
  }

  async _uploadPhoto(animalId, file) {
    const form = new FormData();
    form.append("file", file, file.name);
    try {
      const resp = await this._hass.fetchWithAuth(`/api/arthropoda/photo/${encodeURIComponent(animalId)}`, {
        method: "POST", body: form,
      });
      if (!resp.ok) throw new Error((await resp.json().catch(() => ({}))).message || resp.statusText);
      toast(this, `${t(this._hass, "photo")} ✓`);
    } catch (err) { this._err(err); }
  }

  // --- stamboom, groei, documenten op de dierpagina -----------------------

  _link(id) {
    const a = this._store.animal(id);
    return a ? `<a href="/arthropoda?animal=${esc(id)}" data-nav>${esc(a.name)}</a>` : `<span class="muted">?</span>`;
  }

  _wireLinks(box) {
    box.querySelectorAll("a[data-nav]").forEach((link) => link.addEventListener("click", (e) => {
      e.preventDefault();
      navigate(link.getAttribute("href"));
    }));
  }

  async _loadAnimalExtras() {
    const h = this._hass;
    const id = this._animalId;
    const a = this._store.animal(id);
    if (!a || !this._main?.querySelector("[data-growth]")) return;

    // Stamboom
    const lin = a.lineage || {};
    const lineageBox = this._main.querySelector("[data-lineage]");
    lineageBox.innerHTML = `<div class="facts">
        <div><span>${esc(t(h, "mother_id"))}</span><span>${lin.mother_id ? this._link(lin.mother_id) : "–"}</span></div>
        <div><span>${esc(t(h, "father_id"))}</span><span>${lin.father_id ? this._link(lin.father_id) : "–"}</span></div>
        <div><span>${esc(t(h, "generation"))}</span><span>${esc(lin.generation || "–")}</span></div>
      </div>
      <h3 style="margin-top:12px">${esc(t(h, "children"))}</h3>
      ${lin.children?.length ? lin.children.map((c) => `<div class="small" style="padding:2px 0">${this._link(c)}</div>`).join("") : `<div class="muted small">–</div>`}`;
    this._wireLinks(lineageBox);

    try {
      const [{ measurements, molts }, { documents }] = await Promise.all([
        h.callWS({ type: "arthropoda/measurements/list", animal_id: id }),
        h.callWS({ type: "arthropoda/documents/list", animal_id: id }),
      ]);
      if (this._animalId !== id) return;
      this._renderGrowth(measurements, molts);
      this._renderDocuments(documents);
    } catch (err) { this._err(err); }
  }

  _renderGrowth(measurements, molts) {
    const h = this._hass;
    const box = this._main.querySelector("[data-growth]");
    if (!box) return;
    const kinds = {};
    for (const m of measurements) (kinds[m.kind] ||= []).push(m);
    if (!Object.keys(kinds).length) { box.innerHTML = `<div class="muted small">${esc(t(h, "no_measurements"))}</div>`; return; }
    const W = 600, H = 150, P = 28;
    box.innerHTML = Object.entries(kinds).map(([kind, rows]) => {
      const times = rows.map((r) => new Date(r.ts).getTime());
      const moltTimes = (molts || []).map((m) => new Date(m).getTime());
      const tMin = Math.min(...times, ...moltTimes), tMax = Math.max(...times, ...moltTimes, tMin + 86400000);
      const vals = rows.map((r) => r.value);
      const vMin = Math.min(...vals) * 0.9, vMax = Math.max(...vals) * 1.1 || 1;
      const x = (tm) => P + ((tm - tMin) / (tMax - tMin)) * (W - 2 * P);
      const y = (v) => H - P + 10 - ((v - vMin) / (vMax - vMin || 1)) * (H - 2 * P);
      const pts = rows.map((r) => `${x(new Date(r.ts).getTime()).toFixed(1)},${y(r.value).toFixed(1)}`).join(" ");
      return `<div class="small muted">${esc(t(h, kind))} · ${fmtNum(vals[vals.length - 1], 2)} ${esc(rows[0].unit || "")}</div>
        <svg class="chart" viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" role="img" aria-label="${esc(t(h, kind))}">
          ${moltTimes.map((mt) => `<line x1="${x(mt)}" x2="${x(mt)}" y1="10" y2="${H - P + 10}" stroke="var(--ak-muted)" stroke-dasharray="3 3"/>`).join("")}
          <polyline points="${pts}" fill="none" stroke="var(--ak-accent)" stroke-width="2"/>
          ${rows.map((r) => `<circle cx="${x(new Date(r.ts).getTime())}" cy="${y(r.value)}" r="3.5" fill="var(--ak-accent)"><title>${esc(fmtDate(h, r.ts))}: ${r.value}</title></circle>`).join("")}
          <text x="${P}" y="${H - 4}">${esc(fmtDate(h, new Date(tMin).toISOString()))}</text>
          <text x="${W - P}" y="${H - 4}" text-anchor="end">${esc(fmtDate(h, new Date(tMax).toISOString()))}</text>
        </svg>`;
    }).join("") + (molts?.length ? `<div class="small muted">┆ = ${esc(t(h, "molt"))}</div>` : "");
  }

  _renderDocuments(documents) {
    const h = this._hass;
    const box = this._main.querySelector("[data-docs]");
    if (!box) return;
    const today = new Date().toISOString().slice(0, 10);
    box.innerHTML = documents.length ? documents.map((d) => `<div class="doc-row">
      <span class="grow">${d.url ? `<a href="${esc(d.url)}" target="_blank" rel="noopener">${esc(d.title)}</a>` : esc(d.title)}
        <div class="muted small">${esc(t(h, `doc_${d.type}`))}${d.issued_at ? ` · ${esc(fmtDate(h, d.issued_at))}` : ""}</div></span>
      ${d.expires_at ? `<span class="chip ${d.expires_at < today ? "problem" : ""}">${esc(t(h, "expires_at"))} ${esc(fmtDate(h, d.expires_at))}</span>` : ""}
      <button class="icon" data-doc-del="${d.id}" title="${esc(t(h, "delete"))}">🗑</button>
    </div>`).join("") : `<div class="muted small">${esc(t(h, "no_documents"))}</div>`;
  }

  async _addDocument(animalId) {
    const formBox = this._main.querySelector("[data-doc-form]");
    const form = new FormData();
    form.append("animal_id", animalId);
    for (const name of ["type", "title", "issued_at", "expires_at"]) {
      form.append(name, formBox.querySelector(`[name=${name}]`).value);
    }
    const file = formBox.querySelector("[name=file]").files[0];
    if (file) form.append("file", file, file.name);
    try {
      const resp = await this._hass.fetchWithAuth("/api/arthropoda/document", { method: "POST", body: form });
      if (!resp.ok) throw new Error((await resp.json().catch(() => ({}))).message || resp.statusText);
      formBox.querySelectorAll("input").forEach((i) => { i.value = ""; });
      this._loadAnimalExtras();
    } catch (err) { this._err(err); }
  }

  async _deleteDocument(docId) {
    if (!confirm(t(this._hass, "confirm_delete"))) return;
    try {
      await this._hass.callWS({ type: "arthropoda/documents/delete", document_id: docId });
      this._loadAnimalExtras();
    } catch (err) { this._err(err); }
  }

  // --- kasten -----------------------------------------------------------------

  _viewEnclosures() {
    const h = this._hass;
    this._main.innerHTML = `
      <div class="toolbar">
        <input type="search" placeholder="${esc(te(h, "search"))}" value="${esc(this._encSearch || "")}">
        <select data-enc-filter>
          <option value="all">${esc(te(h, "all"))}</option>
          <option value="in_use">${esc(te(h, "s_in_use"))}</option>
          <option value="empty">${esc(te(h, "s_empty"))}</option>
          <option value="maintenance">${esc(te(h, "s_maintenance"))}</option>
        </select>
        <span class="grow"></span>
        <button class="ak" data-round>🔁 ${esc(te(h, getRound() ? "finish_round" : "start_round"))}</button>
        <button class="ak" data-labels>🖨 ${esc(te(h, "labels"))}</button>
        <button class="ak primary" data-add-enc>＋ ${esc(te(h, "add_enclosure"))}</button>
      </div>
      <div class="grid" data-enc-list></div>`;
    const search = this._main.querySelector("input[type=search]");
    search.addEventListener("input", () => { this._encSearch = search.value; this._updateEnclosures(); });
    const filter = this._main.querySelector("[data-enc-filter]");
    filter.value = this._encFilter || "all";
    filter.addEventListener("change", () => { this._encFilter = filter.value; this._updateEnclosures(); });
    this._main.querySelector("[data-add-enc]").addEventListener("click", () => openEnclosureDialog(h));
    this._main.querySelector("[data-labels]").addEventListener("click", () => openLabelsDialog(h));
    this._main.querySelector("[data-round]").addEventListener("click", (e) => {
      if (getRound()) openRoundSummary(h);
      else { startRound(); e.currentTarget.textContent = `🔁 ${te(h, "finish_round")}`; toast(this, te(h, "start_round")); }
    });
    this._main.querySelector("[data-enc-list]").addEventListener("click", (e) => this._onEnclosureClick(e));
  }

  _updateEnclosures() {
    const box = this._main?.querySelector("[data-enc-list]");
    if (!box) return;
    const h = this._hass;
    const q = (this._encSearch || "").toLowerCase();
    const filter = this._encFilter || "all";
    const isEmpty = (e) => e.empty && !(e.plants || []).length;
    const list = (this._store.enclosures || []).filter((e) => {
      if (filter === "empty" && !isEmpty(e)) return false;
      if (filter === "in_use" && (isEmpty(e) || e.status === "maintenance")) return false;
      if (filter === "maintenance" && e.status !== "maintenance") return false;
      const names = [...(e.residents || []).map((id) => this._store.animal(id)?.name || ""),
        ...(e.plants || []).map((p) => p.name)].join(" ");
      return !q || [e.code, e.name, e.location, names].some((v) => (v || "").toLowerCase().includes(q));
    });
    if (!this._store.enclosures) { box.innerHTML = `<div class="empty">…</div>`; return; }
    if (!list.length) { box.innerHTML = `<div class="empty">${esc(te(h, "empty_list"))}</div>`; return; }
    box.innerHTML = list.map((e) => {
      const due = openTasks(this._store, e).length;
      const status = e.status === "maintenance" ? "maintenance" : isEmpty(e) ? "empty" : "in_use";
      const r = e.readings;
      return `<div class="card tile" data-enc="${esc(e.code)}">
        <div class="row"><div class="grow"><div class="enc-code">${esc(e.code)}</div>
          <div class="muted small">${esc(e.name || "")}${e.name ? " · " : ""}${esc(te(h, `t_${e.type}`))}</div></div>
          <span class="chip ${status === "empty" ? "" : status === "maintenance" ? "problem" : "ok"}">${esc(te(h, `s_${status}`))}</span></div>
        <div class="facts">
          ${dims(e) ? `<div><span>${esc(te(h, "dimensions"))}</span><span>${esc(dims(e))}${e.volume_l ? ` · ${fmtNum(e.volume_l)} ${esc(te(h, "liters"))}` : ""}</span></div>` : ""}
          ${e.location ? `<div><span>${esc(te(h, "place"))}</span><span>${esc(e.location)}</span></div>` : ""}
          ${r ? `<div><span>${esc(te(h, "climate_short"))}</span><span>${r.temperature !== null ? `${fmtNum(r.temperature)} °C` : ""} ${r.humidity !== null ? `· ${fmtNum(r.humidity, 0)} %` : ""}</span></div>` : ""}
          <div><span>${esc(te(h, "tasks_today"))}</span><span>${due ? `<b>${due}</b>` : "–"}</span></div>
        </div>
        ${(e.residents || []).length ? `<div class="small">${e.residents.map((id) => this._link(id)).join(", ")}</div>` : ""}
        ${(e.plants || []).length ? `<div class="small">🌿 ${e.plants.map((p) => `<span class="${p.state === "problem" ? "problem-text" : ""}">${esc(p.name)}${p.state === "problem" ? " ⚠" : ""}</span>`).join(", ")}</div>` : ""}
        ${e.plant_cabinet ? `<div><span class="chip ok">🌿 ${esc(te(h, "steers_plants"))}</span></div>` : ""}
        ${e.too_small_for?.length ? `<div class="chip problem">⚠ ${esc(te(h, "too_small"))}: ${esc(e.too_small_for.join(", "))}</div>` : ""}
        <div class="actions">
          <button class="ak primary" data-work>▶ ${esc(te(h, "work_screen"))}</button>
          <button class="ak" data-edit>⚙ ${esc(te(h, "edit"))}</button>
          <button class="ak" data-nfc>📶 ${esc(te(h, "nfc"))}${e.nfc_tag ? " ✓" : ""}</button>
        </div></div>`;
    }).join("");
    this._wireLinks(box);
  }

  _onEnclosureClick(e) {
    const tile = e.target.closest("[data-enc]");
    if (!tile || e.target.closest("a")) return;
    const enc = this._store.enclosure(tile.dataset.enc);
    const btn = e.target.closest("button");
    if (btn?.hasAttribute("data-edit")) return openEnclosureDialog(this._hass, enc);
    if (btn?.hasAttribute("data-nfc")) return openNfcDialog(this._hass, enc);
    navigate(`/arthropoda?enclosure=${encodeURIComponent(enc.code)}&via=app`);
  }

  _viewWork() {
    this.shadowRoot.querySelectorAll("nav button").forEach((b) =>
      b.classList.toggle("active", b.dataset.tab === "enclosures"));
    // Geopend via de QR-code/NFC-link op de kast (niet vanuit de app zelf) = scanbewijs.
    if (!new URLSearchParams(location.search).get("via")) {
      this._hass.callWS({ type: "arthropoda/enclosure/scanned", code: this._encCode }).catch(() => {});
    }
    this._workDraw = renderWorkScreen(this, this._main, this._hass, this._encCode, {
      onEdit: (enc) => openEnclosureDialog(this._hass, enc),
      onBack: () => navigate("/arthropoda?view=enclosures"),
    });
  }

  // --- kweek ------------------------------------------------------------------

  _viewBreeding() {
    const h = this._hass;
    this._main.innerHTML = `
      <div class="toolbar"><span class="grow"></span>
        <button class="ak primary" data-new>✎ ${esc(t(h, "new_entry"))}</button></div>
      <div class="card"><h3>${esc(t(h, "broods"))}</h3><div data-broods>…</div></div>
      <div class="card" style="margin-top:14px"><h3>${esc(t(h, "pairings"))}</h3><div data-pairings>…</div></div>`;
    this._main.querySelector("[data-new]").addEventListener("click", () => openJournalDialog(h, [], "ootheca"));
    this._main.addEventListener("click", (e) => this._onBreedingClick(e));
  }

  async _loadBreeding() {
    const h = this._hass;
    const box = this._main?.querySelector("[data-broods]");
    if (!box) return;
    let data;
    try { data = await h.callWS({ type: "arthropoda/breeding/list" }); } catch (err) { return this._err(err); }
    this._broods = data.broods;
    const L = (id) => this._link(id);
    box.innerHTML = data.broods.length ? `<table>
      <tr><th>${esc(t(h, "mother_id"))}</th><th>${esc(t(h, "father_id"))}</th><th>${esc(t(h, "laid_at"))}</th>
          <th>${esc(t(h, "expected"))}</th><th>${esc(t(h, "status"))}</th><th></th></tr>
      ${data.broods.map((b) => `<tr>
        <td>${L(b.mother_id)}<div class="muted small">${esc(this._store.label("entry_type", b.type))}${b.count_laid ? ` · ${b.count_laid}` : ""}</div></td>
        <td>${b.father_id ? L(b.father_id) : "–"}</td>
        <td>${esc(fmtDate(h, b.laid_at))}</td>
        <td>${b.expected ? `${esc(fmtDate(h, b.expected[0]))} – ${esc(fmtDate(h, b.expected[1]))}` : "–"}</td>
        <td><span class="chip ${b.status === "failed" ? "problem" : b.status === "hatched" ? "ok" : ""}">${esc(t(h, `status_${b.status}`))}</span>
            ${b.count_hatched ? `<div class="muted small">${b.count_hatched}</div>` : ""}</td>
        <td><div class="actions">
          ${b.status === "incubating" ? `<button class="ak" data-brood="${b.id}" data-act="hatched">🐣 ${esc(t(h, "mark_hatched"))}</button>
            <button class="ak danger" data-brood="${b.id}" data-act="failed">${esc(t(h, "mark_failed"))}</button>` : ""}
          ${b.status === "hatched" ? `<button class="ak primary" data-brood="${b.id}" data-act="offspring">＋ ${esc(t(h, "register_offspring"))}</button>` : ""}
        </div></td></tr>`).join("")}</table>` : `<div class="muted small">${esc(t(h, "no_broods"))}</div>`;
    const pbox = this._main.querySelector("[data-pairings]");
    pbox.innerHTML = data.pairings.length ? data.pairings.map((pr) => `<div class="doc-row">
      <span class="grow">${L(pr.animal_id)} × ${pr.partner_id ? L(pr.partner_id) : esc(pr.partner_text || "?")}</span>
      <span class="muted">${esc(pr.outcome || "")}</span><span class="muted small">${esc(fmtDate(h, pr.ts))}</span></div>`).join("")
      : `<div class="muted small">–</div>`;
    this._wireLinks(box);
    this._wireLinks(pbox);
  }

  async _onBreedingClick(e) {
    const btn = e.target.closest("button[data-brood]");
    if (!btn || this._view !== "breeding") return;
    const h = this._hass;
    const brood = (this._broods || []).find((b) => b.id === Number(btn.dataset.brood));
    if (!brood) return;
    try {
      if (btn.dataset.act === "offspring") {
        const mother = this._store.animal(brood.mother_id);
        const father = brood.father_id ? this._store.animal(brood.father_id) : null;
        const gen = [mother?.lineage?.generation, father?.lineage?.generation]
          .map((g) => /^F(\d+)$/.exec(g || "")).filter(Boolean).map((m) => Number(m[1]));
        await openAnimalDialog(h, null, {
          name: `${mother?.name || ""} – ${fmtDate(h, brood.hatched_at || brood.laid_at)}`,
          species_id: mother?.species?.id, kind: "colony", count: brood.count_hatched,
          stage: mother?.species?.development === "holometabolous" ? "larva" : "nymph",
          born_at: (brood.hatched_at || new Date().toISOString()).slice(0, 10),
          mother_id: brood.mother_id, father_id: brood.father_id, brood_id: brood.id,
          generation: gen.length ? `F${Math.max(...gen) + 1}` : "F1", origin: "bred",
        });
        return;
      }
      const msg = { type: "arthropoda/brood/update", brood_id: brood.id, status: btn.dataset.act };
      if (btn.dataset.act === "hatched") {
        const count = prompt(t(h, "count_hatched"), "");
        if (count) msg.count_hatched = Number(count);
      }
      await h.callWS(msg);
      this._loadBreeding();
    } catch (err) { this._err(err); }
  }

  // --- voorraad ---------------------------------------------------------------

  _viewStock() {
    const h = this._hass;
    const colonies = (this._store.animals || []).filter((a) => a.kind === "colony")
      .sort((x, y) => Number(isFeeder(y)) - Number(isFeeder(x)) || x.name.localeCompare(y.name));
    this._main.innerHTML = `
      <div class="card"><h3>${esc(t(h, "stock"))}</h3><div data-stock>…</div>
        <div class="inline-form" data-stock-form>
          <input name="name" placeholder="${esc(t(h, "name"))} (bv. Huisvlieg)">
          <input name="size" placeholder="${esc(t(h, "size"))}">
          <input name="quantity" type="number" step="any" placeholder="${esc(t(h, "count"))}">
          <input name="unit" placeholder="${esc(t(h, "unit"))} (st, g, potje)">
          <input name="min_quantity" type="number" step="any" placeholder="${esc(t(h, "min_quantity"))}">
          <select name="colony_id"><option value="">${esc(t(h, "colony"))}: –</option>
            ${colonies.map((c) => `<option value="${esc(c.id)}">${isFeeder(c) ? "🦗 " : ""}${esc(c.name)}</option>`).join("")}</select>
          <button class="ak primary" data-stock-add>＋ ${esc(t(h, "add_stock"))}</button>
        </div></div>`;
    this._main.addEventListener("click", (e) => this._onStockClick(e));
  }

  async _loadStock() {
    const h = this._hass;
    const box = this._main?.querySelector("[data-stock]");
    if (!box) return;
    let stock;
    try { stock = await this._store.loadStock(); } catch (err) { return this._err(err); }
    box.innerHTML = stock.length ? `<table>
      <tr><th>${esc(t(h, "name"))}</th><th>${esc(t(h, "count"))}</th><th>${esc(t(h, "min_quantity"))}</th><th>${esc(t(h, "colony"))}</th><th></th></tr>
      ${stock.map((it) => {
        const low = it.min_quantity !== null && it.quantity < it.min_quantity;
        return `<tr><td>${esc(it.name)}${it.size ? `<div class="muted small">${esc(it.size)}</div>` : ""}</td>
          <td><span class="qty"><button data-adj="${it.id}" data-d="-1">−</button>
            <b style="${low ? "color:var(--ak-problem)" : ""}">${fmtNum(it.quantity, 1)}</b>${it.unit ? ` ${esc(it.unit)}` : ""}
            <button data-adj="${it.id}" data-d="1">＋</button></span>
            ${low ? `<span class="chip problem">${esc(t(h, "low"))}</span>` : ""}</td>
          <td>${it.min_quantity ?? "–"}</td>
          <td>${it.colony_id ? this._link(it.colony_id) : "–"}</td>
          <td><button class="icon" data-stock-edit="${it.id}" title="${esc(t(h, "edit"))}">✎</button>
              <button class="icon" data-stock-del="${it.id}" title="${esc(t(h, "delete"))}">🗑</button></td></tr>`;
      }).join("")}</table>` : `<div class="muted small">${esc(t(h, "no_stock"))}</div>`;
    this._wireLinks(box);
  }

  async _onStockClick(e) {
    const btn = e.target.closest("button");
    if (!btn || this._view !== "stock") return;
    const h = this._hass;
    const form = this._main.querySelector("[data-stock-form]");
    try {
      if (btn.dataset.adj) {
        const step = e.shiftKey ? 10 : 1;
        await h.callWS({ type: "arthropoda/stock/adjust", stock_id: Number(btn.dataset.adj), delta: Number(btn.dataset.d) * step });
      } else if (btn.dataset.stockDel) {
        if (!confirm(t(h, "confirm_delete"))) return;
        await h.callWS({ type: "arthropoda/stock/delete", stock_id: Number(btn.dataset.stockDel) });
      } else if (btn.dataset.stockEdit) {
        const it = (this._store.stock || []).find((x) => x.id === Number(btn.dataset.stockEdit));
        for (const k of ["name", "size", "quantity", "unit", "min_quantity", "colony_id"]) {
          form.querySelector(`[name=${k}]`).value = it[k] ?? "";
        }
        form.dataset.editId = it.id;
        return;
      } else if (btn.hasAttribute("data-stock-add")) {
        const val = (k) => form.querySelector(`[name=${k}]`).value;
        const item = {
          name: val("name").trim(), size: val("size") || null, unit: val("unit") || null,
          quantity: val("quantity") === "" ? 0 : Number(val("quantity")),
          min_quantity: val("min_quantity") === "" ? null : Number(val("min_quantity")),
          colony_id: val("colony_id") || null,
        };
        if (!item.name) throw new Error(t(h, "name"));
        if (form.dataset.editId) item.id = Number(form.dataset.editId);
        await h.callWS({ type: "arthropoda/stock/save", item });
        form.querySelectorAll("input").forEach((i) => { i.value = ""; });
        form.querySelector("select").value = "";
        delete form.dataset.editId;
      } else {
        return;
      }
      this._loadStock();
    } catch (err) { this._err(err); }
  }

  // --- dagboek --------------------------------------------------------------

  _viewJournal() {
    const h = this._hass;
    const animals = this._store.animals || [];
    const types = this._store.meta?.entry_types || [];
    this._main.innerHTML = `
      <div class="toolbar">
        <select data-animal><option value="">${esc(t(h, "all_animals"))}</option>
          ${animals.map((a) => `<option value="${esc(a.id)}">${esc(a.name)}</option>`).join("")}</select>
        <select data-type><option value="">${esc(t(h, "all_types"))}</option>
          ${types.map(({ type }) => `<option value="${type}">${esc(this._store.label("entry_type", type))}</option>`).join("")}</select>
        <span class="grow"></span>
        <button class="ak primary" data-new>✎ ${esc(t(h, "new_entry"))}</button>
      </div>
      <div class="card"><div class="timeline" data-journal></div></div>`;
    this._main.querySelector("[data-new]").addEventListener("click", () => openJournalDialog(h, []));
    this._main.querySelectorAll("select").forEach((s) => s.addEventListener("change", () => this._loadJournal()));
    this._main.addEventListener("click", (e) => {
      const btn = e.target.closest("button[data-del]");
      if (btn) this._deleteEntry(Number(btn.dataset.del));
    });
  }

  async _loadJournal() {
    const box = this._main?.querySelector("[data-journal]");
    if (!box) return;
    const h = this._hass;
    const msg = { type: "arthropoda/journal/list", limit: this._view === "animal" ? 50 : 200 };
    if (this._view === "animal") msg.animal_id = this._animalId;
    const animalSel = this._main.querySelector("[data-animal]");
    const typeSel = this._main.querySelector("[data-type]");
    if (animalSel?.value) msg.animal_id = animalSel.value;
    if (typeSel?.value) msg.entry_type = typeSel.value;
    try {
      const { entries } = await h.callWS(msg);
      const names = Object.fromEntries((this._store.animals || []).map((a) => [a.id, a.name]));
      box.innerHTML = entries.length ? entries.map((en) => {
        const details = Object.entries(en.data || {}).filter(([k]) => k !== "source")
          .map(([k, v]) => `${esc(t(h, k))}: ${esc(v === true ? t(h, "yes") : Array.isArray(v) ? v.map((id) => h.states[id]?.attributes.friendly_name || id).join(", ") : v)}`).join(" · ");
        return `<div class="entry">
          <div class="when">${esc(fmtDateTime(h, en.timestamp))}</div>
          <div class="grow"><b>${esc(this._store.label("entry_type", en.type))}</b>
            ${this._view !== "animal" ? ` · ${esc(names[en.animal_id] || "?")}` : ""}
            ${details ? `<div class="small muted">${details}</div>` : ""}
            ${en.notes ? `<div class="small">${esc(en.notes)}</div>` : ""}</div>
          <button class="icon" data-del="${en.id}" title="${esc(t(h, "delete"))}">🗑</button>
        </div>`;
      }).join("") : `<div class="empty">–</div>`;
    } catch (err) { box.innerHTML = `<div class="msg error">${esc(err.message)}</div>`; }
  }

  async _deleteEntry(id) {
    if (!confirm(t(this._hass, "confirm_delete"))) return;
    try {
      await this._hass.callWS({ type: "arthropoda/journal/delete", entry_id: id });
      this._loadJournal();
    } catch (err) { this._err(err); }
  }

  // --- soorten --------------------------------------------------------------

  _viewSpecies() {
    const h = this._hass;
    this._main.innerHTML = `
      <div class="species-layout">
        <div class="card">
          <div class="toolbar"><input type="search" placeholder="${esc(t(h, "search"))}">
            <button class="ak" data-ai>✨ ${esc(t(h, "ai_import"))}</button>
            <button class="ak" data-photos-all title="${esc(t(h, "photos_all"))}">🖼 ${esc(t(h, "photos_all"))}</button>
            <button class="ak primary" data-new>＋ ${esc(t(h, "new_species"))}</button></div>
          <div class="species-list" data-list>…</div>
        </div>
        <div class="card" data-editor><div class="empty">${esc(t(h, "species"))}</div></div>
      </div>`;
    const search = this._main.querySelector("input[type=search]");
    search.addEventListener("input", () => this._renderSpeciesList(search.value));
    this._main.querySelector("[data-new]").addEventListener("click", () => this._editSpecies(null));
    this._main.querySelector("[data-ai]").addEventListener("click", () => this._aiImport());
    this._main.querySelector("[data-photos-all]").addEventListener("click", async (e) => {
      const btn = e.currentTarget;
      btn.disabled = true;
      try {
        const res = await h.callWS({ type: "arthropoda/species/photo/auto_all" });
        toast(this, t(h, "photos_found", { n: res.found.length }));
        await this._store.loadSpecies();
        this._renderSpeciesList(search.value);
      } catch (err) { this._err(err); } finally { btn.disabled = false; }
    });
    this._main.querySelector("[data-list]").addEventListener("click", (e) => {
      const item = e.target.closest("[data-sid]");
      if (item) this._editSpecies(Number(item.dataset.sid));
    });
    this._store.loadSpecies().then(() => this._renderSpeciesList(search.value)).catch((e) => this._err(e));
  }

  _renderSpeciesList(query = "") {
    const box = this._main.querySelector("[data-list]");
    if (!box) return;
    const h = this._hass;
    const q = query.toLowerCase();
    const list = (this._store.species || []).filter((s) =>
      !q || s.scientific_name.toLowerCase().includes(q) || commonName(h, s).toLowerCase().includes(q));
    box.innerHTML = list.map((s) => `<div class="item ${s.id === this._speciesId ? "active" : ""}" data-sid="${s.id}">
      ${s.photo?.url ? `<img class="thumb" src="${esc(s.photo.url)}" alt="" loading="lazy">` : `<span class="thumb"></span>`}
      <div style="min-width:0"><div><i>${esc(s.scientific_name)}</i>${s.feeder ? " 🦗" : ""}</div>
      <div class="muted small">${esc(commonName(h, s))}${s.group ? ` · ${esc(this._store.label("group", s.group))}` : ""}${s.used_by.length ? ` · ${s.used_by.length}×` : ""}</div></div>
    </div>`).join("") || `<div class="empty">–</div>`;
  }

  async _editSpecies(id, presetYaml = null, note = null) {
    const h = this._hass;
    this._speciesId = id;
    this._renderSpeciesList(this._main.querySelector("input[type=search]")?.value || "");
    const box = this._main.querySelector("[data-editor]");
    let yaml = presetYaml || TEMPLATE;
    let usedBy = [];
    if (id !== null) {
      try {
        yaml = (await h.callWS({ type: "arthropoda/species/get", species_id: id })).yaml;
        usedBy = (this._store.species || []).find((s) => s.id === id)?.used_by || [];
      } catch (err) { return this._err(err); }
    }
    const sp = id !== null ? (this._store.species || []).find((x) => x.id === id) : null;
    box.innerHTML = `
      ${sp ? `<div class="row" style="margin-bottom:12px; align-items:flex-start">
        ${sp.photo?.url ? `<img src="${esc(sp.photo.url)}" alt="" style="width:120px;height:90px;object-fit:cover;border-radius:8px">` : ""}
        <div class="grow">
          ${sp.photo ? `<div class="credit">${esc(sp.photo.attribution || "")}<br><a href="${esc(sp.photo.source_url || "#")}" target="_blank" rel="noopener">iNaturalist</a> · ${esc(sp.photo.license || "")}</div>` : `<div class="muted small">${esc(t(h, "no_photo"))}</div>`}
          <button class="ak" data-photo style="margin-top:6px">🖼 ${esc(t(h, "choose_photo"))}</button>
        </div></div>` : ""}
      ${note ? `<div class="msg ${note.error ? "error" : ""}" style="margin-bottom:8px">${esc(note.text)}</div>` : ""}
      <h3>${esc(t(h, "caresheet"))}</h3>
      ${usedBy.length ? `<div class="small muted" style="margin-bottom:8px">${esc(t(h, "used_by"))}: ${esc(usedBy.join(", "))}</div>` : ""}
      <textarea class="yaml" spellcheck="false"></textarea>
      <div class="toolbar" style="margin-top:10px">
        <span class="grow"></span>
        ${id !== null ? `<button class="ak danger" data-delete>${esc(t(h, "delete"))}</button>` : ""}
        <button class="ak primary" data-save>${esc(t(h, "save"))}</button>
      </div>
      <div class="msg" data-msg></div>`;
    box.querySelector("textarea").value = yaml;
    box.querySelector("[data-photo]")?.addEventListener("click", () => this._choosePhoto(id));
    const msg = box.querySelector("[data-msg]");
    box.querySelector("[data-save]").addEventListener("click", async () => {
      msg.className = "msg";
      msg.textContent = "…";
      try {
        // Bestaande soort: op id bijwerken, ook als de naam gewijzigd is.
        const res = await h.callWS({
          type: "arthropoda/species/save", yaml: box.querySelector("textarea").value,
          ...(id !== null ? { species_id: id } : {}),
        });
        msg.textContent = `${t(h, "saved")}: ${res.saved.join(", ") || "–"}${res.skipped.length ? ` (${t(h, "exists_skipped")}: ${res.skipped.join(", ")})` : ""}`;
        await this._store.loadSpecies();
        if (id === null && res.saved.length === 1) {
          const created = (this._store.species || []).find((x) => x.scientific_name === res.saved[0]);
          if (created) this._speciesId = created.id;
        }
        this._renderSpeciesList(this._main.querySelector("input[type=search]")?.value || "");
      } catch (err) { msg.className = "msg error"; msg.textContent = err.message; }
    });
    box.querySelector("[data-delete]")?.addEventListener("click", () => this._deleteSpecies(id, usedBy, box, msg));
  }

  /** Soort verwijderen; is ze in gebruik, dan eerst de dieren naar een andere soort verplaatsen. */
  async _deleteSpecies(id, usedBy, box, msg) {
    const h = this._hass;
    const done = async () => {
      await this._store.loadSpecies();
      this._speciesId = null;
      this._renderSpeciesList(this._main.querySelector("input[type=search]")?.value || "");
      box.innerHTML = `<div class="empty">✓</div>`;
    };
    if (!usedBy.length) {
      if (!confirm(t(h, "confirm_delete_species"))) return;
      try {
        await h.callWS({ type: "arthropoda/species/delete", species_id: id });
        await done();
      } catch (err) { msg.className = "msg error"; msg.textContent = err.message; }
      return;
    }
    const others = (this._store.species || []).filter((x) => x.id !== id);
    if (!others.length) { msg.className = "msg error"; msg.textContent = t(h, "no_other_species"); return; }
    const current = (this._store.species || []).find((x) => x.id === id);
    // Voorstel: een soort met (bijna) dezelfde naam, bv. na een tikfout.
    const norm = (n) => n.toLowerCase().replace(/[^a-z]/g, "");
    const suggestion = others.find((x) => norm(x.scientific_name).startsWith(norm(current?.scientific_name || "").slice(0, 8)));
    openDialog(h, `${t(h, "delete")}: ${current?.scientific_name || ""}`, (body) => {
      body.innerHTML = `<p>${esc(t(h, "reassign_explain", { animals: usedBy.join(", ") }))}</p>
        ${field(t(h, "reassign_to"), `<select name="target">${others.map((x) =>
          `<option value="${x.id}" ${x.id === suggestion?.id ? "selected" : ""}>${esc(x.scientific_name)}${commonName(h, x) ? ` (${esc(commonName(h, x))})` : ""}</option>`).join("")}</select>`, true)}`;
    }, async (body) => {
      const target = Number(body.querySelector("[name=target]").value);
      await h.callWS({ type: "arthropoda/species/delete", species_id: id, reassign_to: target });
      await done();
      return true;
    }, t(h, "move_and_delete"));
  }

  async _choosePhoto(speciesId) {
    const h = this._hass;
    let photos = [];
    const dialog = openDialog(h, t(h, "choose_photo"), (body) => { body.innerHTML = `<div class="empty">…</div>`; },
      async () => {
        await h.callWS({ type: "arthropoda/species/photo/set", species_id: speciesId, photo: null });
        await this._store.loadSpecies();
        this._editSpecies(speciesId);
        return true;
      }, t(h, "no_photo"));
    const body = dialog.querySelector(".ak-d-body");
    try {
      photos = (await h.callWS({ type: "arthropoda/species/photo/search", species_id: speciesId })).photos;
    } catch (err) { body.innerHTML = `<div class="ak-error">${esc(err.message)}</div>`; return; }
    body.innerHTML = photos.length ? `<div class="photo-grid" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(140px,1fr));gap:10px">
      ${photos.map((p, i) => `<figure data-i="${i}" style="margin:0;cursor:pointer">
        <img src="${esc(p.url)}" alt="" style="width:100%;height:120px;object-fit:cover;border-radius:8px;display:block">
        <figcaption style="font-size:.7em;color:var(--secondary-text-color)">${esc(p.license)} · ${esc(p.attribution)}</figcaption></figure>`).join("")}
      </div>` : `<div class="empty">${esc(t(h, "none_found"))}</div>`;
    body.querySelectorAll("figure").forEach((fig) => fig.addEventListener("click", async () => {
      try {
        await h.callWS({ type: "arthropoda/species/photo/set", species_id: speciesId, photo: photos[Number(fig.dataset.i)] });
        dialog.close();
        dialog.remove();
        await this._store.loadSpecies();
        this._renderSpeciesList(this._main.querySelector("input[type=search]")?.value || "");
        this._editSpecies(speciesId);
      } catch (err) { this._err(err); }
    }));
  }

  async _aiImport() {
    const h = this._hass;
    let entities = [];
    try {
      entities = (await h.callWS({ type: "arthropoda/ai/entities" })).entities;
    } catch (err) { return this._err(err); }
    if (!entities.length) return this._err(new Error(t(h, "ai_missing")));
    openDialog(h, t(h, "ai_import"), (body) => {
      body.innerHTML = `<div class="ak-grid">
        ${field(t(h, "ai_entity"), `<select name="entity">${entities.map((e) => `<option value="${esc(e.entity_id)}">${esc(e.name)}</option>`).join("")}</select>`)}
        ${field(t(h, "url"), `<input name="url" type="url" placeholder="https://…">`, true)}
        ${field(t(h, "file"), `<input name="file" type="file" accept="application/pdf,image/jpeg,image/png,image/webp">`, true)}
        ${field(t(h, "hint"), `<input name="hint" placeholder="bv. alleen de adulten">`, true)}
      </div><div class="msg small" data-status style="margin-top:10px"></div>`;
    }, async (body) => {
      const status = body.querySelector("[data-status]");
      const entity = body.querySelector("[name=entity]").value;
      const url = body.querySelector("[name=url]").value.trim();
      const file = body.querySelector("[name=file]").files[0];
      const hint = body.querySelector("[name=hint]").value.trim() || null;
      if (!url && !file) throw new Error(t(h, "url"));
      const msg = { type: "arthropoda/caresheet/extract", entity_id: entity, hint };
      if (file) {
        if (!entities.find((e) => e.entity_id === entity)?.attachments) throw new Error(t(h, "ai_no_files"));
        const form = new FormData();
        form.append("file", file, file.name);
        const resp = await h.fetchWithAuth("/api/arthropoda/caresheet_upload", { method: "POST", body: form });
        const res = await resp.json();
        if (!resp.ok) throw new Error(res.message || resp.statusText);
        msg.media_content_id = res.media_content_id;
        msg.source_name = file.name;
      } else {
        msg.url = url;
      }
      status.textContent = t(h, "reading");
      const result = await h.callWS(msg);
      status.textContent = "";
      this._speciesId = null;
      this._editSpecies(null, result.yaml, result.error
        ? { error: true, text: result.error }
        : { error: false, text: t(h, "ai_review") + (result.moved?.length ? ` ${t(h, "ai_moved")} ${result.moved.join(", ")}` : "") });
      return true;
    }, t(h, "extract"));
  }

  // --- klimaat --------------------------------------------------------------

  _viewClimate() {
    this._main.innerHTML = `<div class="card"><div data-climate></div></div>`;
  }

  _updateClimate() {
    const box = this._main.querySelector("[data-climate]");
    if (!box) return;
    const h = this._hass;
    const groups = new Map();
    const names = Object.fromEntries((this._store.animals || []).map((a) => [a.id, a.name]));
    for (const a of this._store.animals || []) for (const r of a.climate.actuators) groups.set(r.entity_id, r);
    if (!groups.size) { box.innerHTML = `<div class="empty">–</div>`; return; }
    box.innerHTML = `<table>
      <tr><th>${esc(t(h, "actuator"))}</th><th>${esc(t(h, "members"))}</th><th>${esc(t(h, "target"))}</th><th>${esc(t(h, "action"))}</th><th>${esc(t(h, "reason"))}</th></tr>
      ${[...groups.values()].map((r) => `<tr>
        <td>${esc(h.states[r.entity_id]?.attributes.friendly_name || r.entity_id)}<div class="muted small">${esc(t(h, r.role))} · ${esc(r.entity_id)}</div></td>
        <td>${r.members.map((m) => `<a href="/arthropoda?animal=${esc(m)}" data-nav>${esc(names[m] || "?")}</a>`).join(", ")}</td>
        <td>${r.target ? esc(r.target.join(" – ")) : "–"}${r.setpoint !== null ? `<div class="muted small">→ ${fmtNum(r.setpoint)}</div>` : ""}</td>
        <td>${esc(r.action)}</td>
        <td>${esc(r.reason)}${r.conflict ? ` <span class="chip problem">${esc(t(h, "conflict"))}</span>` : ""}</td>
      </tr>`).join("")}</table>`;
    box.querySelectorAll("a[data-nav]").forEach((link) => link.addEventListener("click", (e) => {
      e.preventDefault();
      navigate(link.getAttribute("href"));
    }));
  }
}

const TEMPLATE = `format: arthropoda-caresheet/1
species:
  scientific_name: Genus species
  common_names: {nl: Nederlandse naam, en: English name}
  group: other            # tarantula, scorpion, mantis, phasmid, isopod, roach, beetle, ant, aquatic, ...
  development: hemimetabolous
  habitat: terrestrial
  feeder: false            # true = voederdier
  # diapause: {min_days: 60, max_days: 120, start_months: [11, 12], stage: pupa}
care_profiles:
  - temp_day: [22, 26]
    temp_night: [18, 22]
    humidity: [60, 70]
    feeding_interval_days: 7
    cleaning_interval_days: 30
source: ""
`;

customElements.define("arthropoda-panel", ArthropodaPanel);
