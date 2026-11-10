/*
 * Arthropoda Keeper – dashboardkaarten.
 *
 *   type: custom:arthropoda-animal-card       één dier (foto later), klimaat, verzorging, knoppen
 *     animal: <dier-id>                       (kies in de visuele editor)
 *
 *   type: custom:arthropoda-collection-card   lijst van alle dieren
 *     title: Mijn dieren                      (optioneel)
 *     show_inactive: false                    overleden/verkochte dieren ook tonen
 *     sort: name | species | status | feeding
 *     max_rows: 10                            daarboven verschijnt een scrollbalk
 *     feeders: all | no_feeders | only_feeders  voederdieren tonen, verbergen of alleen die
 */
import {
  BASE_CSS, commonName, daysText, dueText, esc, feederFilter, fmtNum, getStore, isFeeder, navigate, nextTask,
  openAnimalDialog, openJournalDialog, photoUrl, quickLog, rangeBar, stageText, t, toast,
} from "./arthropoda-common.js?v=0.9.0";

const CARD_CSS = `
  ${BASE_CSS}
  ha-card, .ha-card { display:block; padding: 14px 16px; }
  .ha-card { background: var(--ha-card-background, var(--card-background-color, #fff)); border-radius: var(--ha-card-border-radius, 12px);
             box-shadow: var(--ha-card-box-shadow, none); border: var(--ha-card-border-width, 1px) solid var(--ha-card-border-color, var(--divider-color, #e0e0e0)); }
  .title { font-size: 1.15em; font-weight: 500; }
  .metric { display:grid; grid-template-columns: 96px 1fr 64px; align-items:center; gap: 8px; font-size: .9em; margin-top: 8px; }
  .metric .val { text-align:right; font-variant-numeric: tabular-nums; }
  .facts { display:grid; grid-template-columns: repeat(auto-fill, minmax(120px, 1fr)); gap: 4px 12px; font-size:.88em; margin-top: 10px; }
  .facts span:first-child { display:block; color: var(--ak-muted); font-size: .85em; }
  .actions { display:flex; gap:6px; flex-wrap:wrap; margin-top: 12px; }
  .actions button.ak { padding: 5px 12px; font-size: .9em; }
  .clickable { cursor: pointer; }
  .warn { color: var(--ak-muted); padding: 8px 0; }
  /* collectielijst */
  .list { overflow-y: auto; margin: 6px -16px -6px; padding: 0 16px; }
  .list.scroll { border-top: 1px solid var(--ak-line); border-bottom: 1px solid var(--ak-line); }
  .item { display:grid; grid-template-columns: 12px minmax(0, 1fr) auto; gap: 10px; align-items:center;
          height: 52px; border-bottom: 1px solid var(--ak-line); cursor: pointer; }
  .item:last-child { border-bottom: none; }
  .item:hover { background: var(--secondary-background-color, #f6f6f6); }
  .item .side { text-align: right; font-size: .85em; white-space: nowrap; }
  .head { display:flex; align-items:center; gap: 8px; margin-bottom: 6px; }
  .count { color: var(--ak-muted); font-size: .9em; }
`;

const ROW_HEIGHT = 52;

/** Basis: koppelt aan de gedeelde store en hertekent bij elke wijziging. */
class BaseCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._onChange = () => this._render();
  }

  set hass(hass) {
    const first = !this._hass;
    this._hass = hass;
    if (first) {
      this._store = getStore(hass);
      this._store.addEventListener("change", this._onChange);
      this._render();
    }
  }

  connectedCallback() { if (this._store) { this._store.addEventListener("change", this._onChange); this._render(); } }
  disconnectedCallback() { this._store?.removeEventListener("change", this._onChange); }

  _card(inner) {
    const tag = customElements.get("ha-card") ? "ha-card" : "div";
    return `<style>${CARD_CSS}</style><${tag} class="${tag === "div" ? "ha-card" : ""}">${inner}</${tag}>`;
  }
}

// --------------------------------------------------------------- dierkaart --

class ArthropodaAnimalCard extends BaseCard {
  static getConfigElement() { return document.createElement("arthropoda-animal-card-editor"); }
  static getStubConfig(hass) {
    const store = getStore(hass);
    return { animal: store.animals?.[0]?.id || "" };
  }

  setConfig(config) {
    this._config = config;
    if (this._hass) this._render();
  }

  getCardSize() { return 5; }
  getGridOptions() { return { columns: 6, min_columns: 4, rows: "auto" }; }

  _render() {
    if (!this._hass || !this._config) return;
    const h = this._hass;
    const store = this._store;
    if (!store.animals) { this.shadowRoot.innerHTML = this._card(`<div class="warn">…</div>`); return; }
    const a = store.animal(this._config.animal);
    if (!a) {
      this.shadowRoot.innerHTML = this._card(`<div class="warn">${esc(t(h, "select_animal"))}</div>`);
      return;
    }
    const r = a.readings;
    const metric = (label, value, target, unit) => `
      <div class="metric"><span class="muted">${esc(label)}</span>${rangeBar(value, target)}
      <span class="val">${value === null || value === undefined ? "–" : `${fmtNum(value)} ${unit}`}</span></div>`;
    const task = nextTask(a);
    const chipLabel = a.state === "problem" ? t(h, "problem") : t(h, a.state === "ok" ? "ok" : "inactive");
    this.shadowRoot.innerHTML = this._card(`
      <div class="row clickable" data-open>
        ${photoUrl(h, a) ? `<img class="avatar" src="${esc(photoUrl(h, a))}" alt="">` : ""}
        <div class="grow">
          <div class="title ellipsis">${esc(a.name)}</div>
          <div class="muted small ellipsis"><i>${esc(a.species?.scientific_name || "")}</i>${commonName(h, a.species) ? ` · ${esc(commonName(h, a.species))}` : ""}</div>
        </div>
        <span class="chip ${a.state}" title="${esc(a.problems.join(", "))}"><span class="dot ${a.state}"></span>${esc(chipLabel)}</span>
      </div>
      ${(a.climate_config || a.config).temperature_sensors?.length ? metric(t(h, "temperature"), r.temperature, a.targets.temperature, "°C") : ""}
      ${(a.climate_config || a.config).humidity_sensor ? metric(t(h, "humidity"), r.humidity, a.targets.humidity, "%") : ""}
      ${(a.climate_config || a.config).water_temperature_sensor ? metric(t(h, "water_temperature"), r.water_temperature, a.targets.water_temperature, "°C") : ""}
      <div class="facts">
        <div><span>${esc(t(h, "stage"))}</span><span>${esc(stageText(store, a) || "–")}${a.premolt ? ` · ${esc(t(h, "premolt"))}` : ""}</span></div>
        <div><span>${esc(t(h, "feeding"))}</span><span>${esc(daysText(h, a.days_since.feeding))}</span></div>
        ${a.can_molt || a.molt_count ? `<div><span>${esc(t(h, "molt"))}</span><span>${esc(daysText(h, a.days_since.molt))}</span></div>` : ""}
        ${task ? `<div><span>${esc(t(h, "next_task"))}</span><span>${esc(t(h, task.kind))} · ${esc(dueText(h, task.due))}</span></div>` : ""}
      </div>
      <div class="actions">
        <button class="ak" data-quick="feeding">🍽 ${esc(t(h, "fed"))}</button>
        <button class="ak" data-quick="misting_manual">💧 ${esc(t(h, "misted"))}</button>
        <button class="ak" data-entry>✎ ${esc(t(h, "journal"))}</button>
        <button class="ak" data-edit>⚙ ${esc(t(h, "edit"))}</button>
      </div>`);
    this.shadowRoot.querySelector("[data-open]").addEventListener("click", () =>
      navigate(`/arthropoda?animal=${encodeURIComponent(a.id)}`));
    this.shadowRoot.querySelectorAll("[data-quick]").forEach((b) =>
      b.addEventListener("click", () => quickLog(this, h, a.id, b.dataset.quick)));
    this.shadowRoot.querySelector("[data-entry]").addEventListener("click", () => openJournalDialog(h, [a.id]));
    this.shadowRoot.querySelector("[data-edit]").addEventListener("click", () =>
      openAnimalDialog(h, a).catch((err) => toast(this, err.message)));
  }
}

// ---------------------------------------------------------- collectielijst --

const SORTS = {
  name: (a, b) => a.name.localeCompare(b.name),
  species: (a, b) => (a.species?.scientific_name || "").localeCompare(b.species?.scientific_name || "") || a.name.localeCompare(b.name),
  status: (a, b) => ({ problem: 0, ok: 1, inactive: 2 }[a.state] - { problem: 0, ok: 1, inactive: 2 }[b.state]) || a.name.localeCompare(b.name),
  feeding: (a, b) => (b.days_since.feeding ?? -1) - (a.days_since.feeding ?? -1),
};

class ArthropodaCollectionCard extends BaseCard {
  static getConfigElement() { return document.createElement("arthropoda-collection-card-editor"); }
  static getStubConfig() { return { title: "", show_inactive: false, sort: "name", max_rows: 10 }; }

  setConfig(config) {
    this._config = { show_inactive: false, sort: "name", max_rows: 10, feeders: "all", ...config };
    if (this._hass) this._render();
  }

  getCardSize() { return Math.min(this._store?.animals?.length || 3, this._config?.max_rows || 10) + 1; }
  getGridOptions() { return { columns: 12, min_columns: 6, rows: "auto" }; }

  _render() {
    if (!this._hass || !this._config) return;
    const h = this._hass;
    const store = this._store;
    const cfg = this._config;
    const all = store.animals || [];
    const animals = feederFilter(all, cfg.feeders)
      .filter((a) => cfg.show_inactive || a.state !== "inactive")
      .sort(SORTS[cfg.sort] || SORTS.name);
    const maxRows = Math.max(1, Number(cfg.max_rows) || 10);
    const scroll = animals.length > maxRows;
    const title = cfg.title || store.meta?.collection || t(h, "collection");
    const problems = animals.filter((a) => a.state === "problem").length;

    const rows = animals.map((a) => {
      const r = a.readings;
      const climate = [
        r.temperature !== null && r.temperature !== undefined ? `${fmtNum(r.temperature)} °C` : "",
        r.humidity !== null && r.humidity !== undefined ? `${fmtNum(r.humidity, 0)} %` : "",
      ].filter(Boolean).join(" · ");
      const task = nextTask(a);
      const sub = [stageText(store, a), `${t(h, "feeding")}: ${daysText(h, a.days_since.feeding)}`].filter(Boolean).join(" · ");
      return `<div class="item" data-id="${esc(a.id)}" title="${esc(a.problems.join(", "))}">
        <span class="dot ${a.state}"></span>
        <div style="min-width:0">
          <div class="ellipsis">${isFeeder(a) ? "🦗 " : ""}${a.status === "diapause" ? "❄ " : ""}${esc(a.name)} <span class="muted small"><i>${esc(a.species?.scientific_name || "")}</i></span></div>
          <div class="muted small ellipsis">${esc(sub)}</div>
        </div>
        <div class="side">${esc(climate)}${task ? `<div class="muted">${esc(t(h, task.kind))} · ${esc(dueText(h, task.due))}</div>` : ""}</div>
      </div>`;
    }).join("");

    this.shadowRoot.innerHTML = this._card(`
      <div class="head"><span class="title grow">${esc(title)}</span>
        <span class="count">${animals.length}${problems ? ` · <span style="color:var(--ak-problem)">${problems} ${esc(t(h, "problem").toLowerCase())}</span>` : ""}</span>
        <button class="icon" data-add title="${esc(t(h, "add_animal"))}">＋</button>
      </div>
      ${store.animals ? (animals.length
        ? `<div class="list ${scroll ? "scroll" : ""}" style="${scroll ? `max-height:${maxRows * ROW_HEIGHT}px` : ""}">${rows}</div>`
        : `<div class="warn">${esc(t(h, "no_animals"))}</div>`) : `<div class="warn">…</div>`}`);
    this.shadowRoot.querySelector(".list")?.addEventListener("click", (e) => {
      const item = e.target.closest("[data-id]");
      if (item) navigate(`/arthropoda?animal=${encodeURIComponent(item.dataset.id)}`);
    });
    this.shadowRoot.querySelector("[data-add]").addEventListener("click", () =>
      openAnimalDialog(h).catch((err) => toast(this, err.message)));
  }
}

// ---------------------------------------------------------------- editors --

class BaseEditor extends HTMLElement {
  set hass(hass) {
    const first = !this._hass;
    this._hass = hass;
    if (first) {
      this._store = getStore(hass);
      this._store.addEventListener("change", () => this._render());
      this._render();
    }
  }

  setConfig(config) { this._config = { ...config }; this._render(); }

  _changed(key, value) {
    this._config = { ...this._config, [key]: value };
    this.dispatchEvent(new CustomEvent("config-changed", { detail: { config: this._config }, bubbles: true, composed: true }));
  }

  _style() {
    return `<style>
      .f { display:flex; flex-direction:column; gap:4px; margin: 8px 0; font-size:.9em; color: var(--secondary-text-color); }
      select, input[type=text], input[type=number] { font: inherit; font-size: 1rem; padding: 8px; border-radius: 6px;
        border: 1px solid var(--divider-color, #ccc); background: var(--card-background-color, #fff); color: var(--primary-text-color); }
      label.c { display:flex; gap:8px; align-items:center; color: var(--primary-text-color); }
    </style>`;
  }
}

class AnimalCardEditor extends BaseEditor {
  _render() {
    if (!this._hass || !this._config) return;
    const h = this._hass;
    const animals = this._store.animals || [];
    this.innerHTML = `${this._style()}
      <label class="f">${esc(t(h, "select_animal"))}
        <select>${animals.map((a) => `<option value="${esc(a.id)}" ${a.id === this._config.animal ? "selected" : ""}>${esc(a.name)} – ${esc(a.species?.scientific_name || "")}</option>`).join("")}</select>
      </label>`;
    this.querySelector("select").addEventListener("change", (e) => this._changed("animal", e.target.value));
  }
}

class CollectionCardEditor extends BaseEditor {
  _render() {
    if (!this._hass || !this._config) return;
    if (this.querySelector("input[type=text]") === document.activeElement) return;
    const h = this._hass;
    const c = this._config;
    this.innerHTML = `${this._style()}
      <label class="f">${esc(t(h, "title"))}<input type="text" data-k="title" value="${esc(c.title || "")}"></label>
      <label class="f">${esc(t(h, "sort"))}<select data-k="sort">
        ${["name", "species", "status", "feeding"].map((s) => `<option value="${s}" ${c.sort === s ? "selected" : ""}>${esc(t(h, s === "status" ? "status" : s === "feeding" ? "feeding" : s === "species" ? "species" : "name"))}</option>`).join("")}
      </select></label>
      <label class="f">${esc(t(h, "feeders"))}<select data-k="feeders">
        ${["all", "no_feeders", "only_feeders"].map((v) => `<option value="${v}" ${(c.feeders || "all") === v ? "selected" : ""}>${esc(t(h, `filter_${v}`))}</option>`).join("")}
      </select></label>
      <label class="f">${esc(t(h, "max_rows"))}<input type="number" min="1" max="100" data-k="max_rows" value="${esc(c.max_rows ?? 10)}"></label>
      <label class="c"><input type="checkbox" data-k="show_inactive" ${c.show_inactive ? "checked" : ""}> ${esc(t(h, "show_inactive"))}</label>`;
    this.querySelectorAll("[data-k]").forEach((el) => el.addEventListener("change", () => {
      const value = el.type === "checkbox" ? el.checked : el.type === "number" ? Number(el.value) : el.value;
      this._changed(el.dataset.k, value);
    }));
  }
}

customElements.define("arthropoda-animal-card", ArthropodaAnimalCard);
customElements.define("arthropoda-collection-card", ArthropodaCollectionCard);
customElements.define("arthropoda-animal-card-editor", AnimalCardEditor);
customElements.define("arthropoda-collection-card-editor", CollectionCardEditor);

window.customCards = window.customCards || [];
window.customCards.push(
  { type: "arthropoda-animal-card", name: "Arthropoda: dier", description: "Eén dier: klimaat, verzorging en snelknoppen.", preview: false },
  { type: "arthropoda-collection-card", name: "Arthropoda: collectie", description: "Lijst van al je dieren, met scrollbalk vanaf 10 dieren.", preview: false },
);
