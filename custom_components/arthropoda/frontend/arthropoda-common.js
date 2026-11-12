/*
 * Arthropoda Keeper – gedeelde frontendcode voor paneel en kaarten.
 *
 * Geen externe bibliotheken en geen bouwstap: gewone Web Components.
 * Gegevens komen live binnen via de WebSocket `arthropoda/subscribe`.
 */

// ---------------------------------------------------------------- teksten --

const TEXTS = {
  nl: {
    collection: "Collectie", journal: "Dagboek", species: "Soorten", climate: "Klimaat",
    add_animal: "Dier toevoegen", edit: "Wijzigen", save: "Opslaan", cancel: "Annuleren",
    delete: "Verwijderen", close: "Sluiten", back: "Terug", search: "Zoeken…",
    new_entry: "Dagboekregel", fed: "Gevoederd", misted: "Gesproeid", cleaned: "Schoongemaakt",
    ok: "OK", problem: "Probleem", inactive: "Niet actief", no_animals: "Nog geen dieren.",
    no_species: "Voeg eerst een soort toe (tabblad Soorten).",
    days_ago: "{n} d geleden", today: "vandaag", in_days: "over {n} d", overdue: "{n} d te laat",
    never: "nog nooit", feeding: "Voedering", molt: "Vervelling", cleaning: "Schoonmaak",
    substrate_change: "Substraat", water_change: "Waterwissel", misting: "Sproeien",
    temperature: "Temperatuur", humidity: "Vochtigheid", water_temperature: "Watertemperatuur",
    target: "doel", next_task: "Volgende taak", tasks: "Taken", no_tasks: "Geen taken gepland.",
    next_molt: "Verwachte vervelling", molts: "vervellingen", count: "Aantal",
    stage: "Levensfase", instar: "Stadium", sex: "Geslacht", status: "Status", kind: "Type",
    general: "Algemeen", sensors: "Sensoren", actuators: "Klimaatsturing", tuning: "Afstelling",
    name: "Naam", born_at: "Geboren / uitgekomen", acquired_at: "Aangeschaft op", origin: "Herkomst",
    temperature_sensors: "Temperatuursensor(en)", humidity_sensor: "Vochtigheidssensor",
    water_temperature_sensor: "Watertemperatuursensor", heater: "Verwarming",
    mister: "Vernevelaar", lights: "Verlichting", fan: "Ventilator",
    water_heater: "Waterverwarming", pumps: "Pompen / filter", hysteresis: "Hysterese (°C)",
    mist_seconds: "Pulsduur (s)", mist_pause_minutes: "Pauze tussen pulsen (min)",
    mist_max_per_day: "Max. pulsen per dag", mist_times: "Vaste vernevelmomenten (bv. 08:00, 20:00)",
    light_ramp_minutes: "Op-/afdimmen (min)", none: "— geen —", add: "Toevoegen",
    entry_type: "Handeling", animals: "Dieren", when: "Tijdstip", notes: "Notities",
    details: "Details", profile: "Actief profiel", measurements: "Metingen",
    care: "Verzorging", actuator: "Toestel", action: "Actie", reason: "Reden", members: "Dieren",
    conflict: "conflict", climate_status: "Klimaatregeling", day: "dag", night: "nacht",
    caresheet: "Caresheet (YAML)", new_species: "Nieuwe soort", overwrite: "Bestaande overschrijven",
    used_by: "Gebruikt door", saved: "Opgeslagen", confirm_delete: "Deze regel verwijderen?",
    confirm_delete_species: "Deze soort verwijderen?", all_animals: "Alle dieren", all_types: "Alle handelingen",
    open_panel: "Openen in paneel", load_more: "Meer laden", unavailable: "geen meting",
    maintenance: "Onderhoud", premolt: "Premolt", season: "Seizoen", select_animal: "Kies een dier",
    show_inactive: "Ook niet-actieve dieren tonen", sort: "Sorteren", title: "Titel",
    max_rows: "Rijen voor scrollbalk", required: "Naam en soort zijn verplicht.",
    feeding_paused: "voederpauze", climate_active: "Actief", climate_paused: "Gepauzeerd",
    climate_monitoring: "Alleen bewaken", climate_maintenance: "Onderhoud",
    prey: "Prooi / voedsel", quantity: "Aantal", prey_size: "Prooigrootte", result: "Resultaat",
    accepted: "Gegeten", partial: "Deels", refused: "Geweigerd", instar_after: "Stadium na vervelling",
    legspan_mm: "Spanwijdte (mm)", length_mm: "Lichaamslengte (mm)", weight_g: "Gewicht (g)",
    exuvia_kept: "Exuvia bewaard", incubation_days: "Incubatieduur (dagen)", ph: "pH",
    gh: "GH", kh: "KH", no2: "NO₂", no3: "NO₃", percent: "Ververst (%)", substrate: "Substraat",
    cause: "Oorzaak", treatment_text: "Behandeling", partner: "Partner", outcome: "Resultaat",
    yes: "ja", no: "nee",
    reassign_explain: "Deze soort wordt gebruikt door: {animals}. Kies naar welke soort die dieren verhuizen; daarna wordt deze soort verwijderd. Dagboek, foto's en gegevens van de dieren blijven bewaard.",
    reassign_to: "Dieren verplaatsen naar", move_and_delete: "Verplaatsen en verwijderen",
    no_other_species: "Er is geen andere soort om de dieren naar te verplaatsen.", exists_skipped: "bestond al",
    diapause: "Diapauze", planned_end: "Gepland einde (optioneel)", in_diapause_since: "In diapauze sinds",
    earliest_end: "Vroegst uit", latest_end: "Uiterlijk uit", feeder: "Voederdier", feeders: "Voederdieren",
    filter_all: "Alle dieren", filter_no_feeders: "Zonder voederdieren", filter_only_feeders: "Alleen voederdieren",
    diapause_end: "Uit diapauze halen",
    enclosures: "Kasten", enclosure: "Kast", no_enclosure: "— geen kast —",
    breeding: "Kweek", food: "Voer", stock: "Voorraad", lineage: "Stamboom", growth: "Groei", documents: "Documenten",
    origin_section: "Herkomst & stamboom", seller: "Kweker / verkoper", price: "Prijs (€)",
    mother_id: "Moeder", father_id: "Vader", generation: "Generatie", partner_id: "Partner (eigen dier)",
    stock_id: "Uit voorraad", broods: "Legsels", pairings: "Koppelingen", laid_at: "Gelegd",
    expected: "Verwachte uitkomst", status_incubating: "Broedt", status_hatched: "Uitgekomen",
    status_failed: "Mislukt", mark_hatched: "Uitgekomen", mark_failed: "Mislukt",
    register_offspring: "Nakomelingen registreren", children: "Nakomelingen", parents: "Ouders",
    no_broods: "Nog geen legsels. Noteer een eicocon, ootheek of eieren in het dagboek.",
    no_stock: "Nog geen voorraad.", add_stock: "Voorraad toevoegen", min_quantity: "Minimum",
    unit: "Eenheid", size: "Maat", colony: "Eigen kolonie", low: "laag", no_documents: "Nog geen documenten.",
    add_document: "Document toevoegen", doc_type: "Soort document", doc_title: "Titel",
    issued_at: "Datum", expires_at: "Vervalt op", doc_invoice: "Factuur / aankoopbewijs", doc_cites: "CITES-certificaat",
    doc_permit: "Vergunning", doc_breeder_statement: "Kwekersverklaring", doc_health: "Gezondheid / dierenarts",
    doc_other: "Ander document", expired: "vervallen", no_measurements: "Nog geen metingen. Voeg een meting toe in het dagboek.",
    photos_all: "Foto's voor alle soorten zonder foto", photos_found: "{n} foto('s) gevonden",
    count_laid: "Aantal gelegd", count_hatched: "Aantal uitgekomen",
    ai_moved: "Velden zonder eigen plaats staan onder 'extra':",
    photo: "Foto", upload_photo: "Foto uploaden", delete_photo: "Eigen foto verwijderen",
    choose_photo: "Soortfoto kiezen", no_photo: "Geen foto", photo_source: "Foto",
    none_found: "Niets gevonden.", ai_import: "Caresheet met AI", ai_entity: "AI",
    url: "Webpagina (URL)", file: "of bestand (PDF / foto)", hint: "Extra uitleg voor de AI (optioneel)",
    reading: "De AI leest de caresheet… dit kan een minuut duren.", extract: "Inlezen",
    ai_review: "Nagekeken? Pas aan waar nodig en klik op Opslaan.", ai_missing:
      "Geen AI gevonden. Voeg in HA een AI-integratie toe (bv. Anthropic) met een AI Task-entiteit.",
    ai_no_files: "Deze AI kan geen bestanden lezen; gebruik een webadres.", license: "Licentie",
    species_one: "Soort", plants: "Voedselplanten", food_plants: "Voedselplanten", nutrition: "Voeding",
    no_plants: "Geen planten gevonden. Voeg ze toe met de plant monitor.",
    prof_temp_day: "Temperatuur overdag (°C)", prof_temp_night: "Temperatuur 's nachts (°C)",
    prof_temp_max_safe: "Gevaarlijk vanaf (°C)", prof_humidity: "Luchtvochtigheid (%)",
    prof_water_temp: "Watertemperatuur (°C)", prof_ph: "pH", prof_light_hours: "Daglengte (uur)",
    prof_uv: "UV", prof_substrate_moisture: "Substraatvocht", prof_misting: "Sproeien",
    prof_ventilation: "Ventilatie", prof_feeding_interval_days: "Voederen elke … dagen",
    prof_cleaning_interval_days: "Schoonmaken elke … dagen", prof_substrate_change_interval_days: "Substraat vervangen elke … dagen",
    prof_water_change_interval_days: "Waterwissel elke … dagen", prof_post_molt_fast_days: "Voederpauze na vervelling (dagen)",
    cat_feeding: "Voeding", cat_hygiene: "Hygiëne", cat_climate: "Klimaat & water", cat_development: "Ontwikkeling",
    cat_breeding: "Kweek", cat_measurement: "Metingen", cat_health: "Gezondheid", cat_movement: "Verplaatsing",
    cat_admin: "Administratie", cat_other: "Overig",
  },
  en: {
    collection: "Collection", journal: "Journal", species: "Species", climate: "Climate",
    add_animal: "Add animal", edit: "Edit", save: "Save", cancel: "Cancel",
    delete: "Delete", close: "Close", back: "Back", search: "Search…",
    new_entry: "Journal entry", fed: "Fed", misted: "Misted", cleaned: "Cleaned",
    ok: "OK", problem: "Problem", inactive: "Inactive", no_animals: "No animals yet.",
    no_species: "Add a species first (Species tab).",
    days_ago: "{n} d ago", today: "today", in_days: "in {n} d", overdue: "{n} d overdue",
    never: "never", feeding: "Feeding", molt: "Molt", cleaning: "Cleaning",
    substrate_change: "Substrate", water_change: "Water change", misting: "Misting",
    temperature: "Temperature", humidity: "Humidity", water_temperature: "Water temperature",
    target: "target", next_task: "Next task", tasks: "Tasks", no_tasks: "No tasks planned.",
    next_molt: "Expected molt", molts: "molts", count: "Count",
    stage: "Life stage", instar: "Instar", sex: "Sex", status: "Status", kind: "Type",
    general: "General", sensors: "Sensors", actuators: "Climate control", tuning: "Tuning",
    name: "Name", born_at: "Born / hatched", acquired_at: "Acquired on", origin: "Origin",
    temperature_sensors: "Temperature sensor(s)", humidity_sensor: "Humidity sensor",
    water_temperature_sensor: "Water temperature sensor", heater: "Heater",
    mister: "Mister", lights: "Lighting", fan: "Fan",
    water_heater: "Water heater", pumps: "Pumps / filter", hysteresis: "Hysteresis (°C)",
    mist_seconds: "Pulse duration (s)", mist_pause_minutes: "Pause between pulses (min)",
    mist_max_per_day: "Max pulses per day", mist_times: "Scheduled misting (e.g. 08:00, 20:00)",
    light_ramp_minutes: "Dim up/down (min)", none: "— none —", add: "Add",
    entry_type: "Action", animals: "Animals", when: "Time", notes: "Notes",
    details: "Details", profile: "Active profile", measurements: "Measurements",
    care: "Care", actuator: "Device", action: "Action", reason: "Reason", members: "Animals",
    conflict: "conflict", climate_status: "Climate control", day: "day", night: "night",
    caresheet: "Caresheet (YAML)", new_species: "New species", overwrite: "Overwrite existing",
    used_by: "Used by", saved: "Saved", confirm_delete: "Delete this entry?",
    confirm_delete_species: "Delete this species?", all_animals: "All animals", all_types: "All actions",
    open_panel: "Open in panel", load_more: "Load more", unavailable: "no reading",
    maintenance: "Maintenance", premolt: "Premolt", season: "Season", select_animal: "Choose an animal",
    show_inactive: "Also show inactive animals", sort: "Sort", title: "Title",
    max_rows: "Rows before scrollbar", required: "Name and species are required.",
    feeding_paused: "feeding pause", climate_active: "Active", climate_paused: "Paused",
    climate_monitoring: "Monitoring only", climate_maintenance: "Maintenance",
    prey: "Prey / food", quantity: "Quantity", prey_size: "Prey size", result: "Result",
    accepted: "Eaten", partial: "Partially", refused: "Refused", instar_after: "Instar after molt",
    legspan_mm: "Leg span (mm)", length_mm: "Body length (mm)", weight_g: "Weight (g)",
    exuvia_kept: "Exuvia kept", incubation_days: "Incubation (days)", ph: "pH",
    gh: "GH", kh: "KH", no2: "NO₂", no3: "NO₃", percent: "Changed (%)", substrate: "Substrate",
    cause: "Cause", treatment_text: "Treatment", partner: "Partner", outcome: "Outcome",
    yes: "yes", no: "no",
    reassign_explain: "This species is used by: {animals}. Choose which species these animals move to; then this species is deleted. Journal, photos and animal data are kept.",
    reassign_to: "Move animals to", move_and_delete: "Move and delete",
    no_other_species: "There is no other species to move the animals to.", exists_skipped: "already existed",
    diapause: "Diapause", planned_end: "Planned end (optional)", in_diapause_since: "In diapause since",
    earliest_end: "Earliest end", latest_end: "Latest end", feeder: "Feeder", feeders: "Feeders",
    filter_all: "All animals", filter_no_feeders: "Without feeders", filter_only_feeders: "Feeders only",
    diapause_end: "End diapause",
    enclosures: "Enclosures", enclosure: "Enclosure", no_enclosure: "— no enclosure —",
    breeding: "Breeding", food: "Food", stock: "Stock", lineage: "Family tree", growth: "Growth", documents: "Documents",
    origin_section: "Origin & family tree", seller: "Breeder / seller", price: "Price (€)",
    mother_id: "Mother", father_id: "Father", generation: "Generation", partner_id: "Partner (own animal)",
    stock_id: "From stock", broods: "Broods", pairings: "Pairings", laid_at: "Laid",
    expected: "Expected hatch", status_incubating: "Incubating", status_hatched: "Hatched",
    status_failed: "Failed", mark_hatched: "Hatched", mark_failed: "Failed",
    register_offspring: "Register offspring", children: "Offspring", parents: "Parents",
    no_broods: "No broods yet. Log an egg sac, ootheca or eggs in the journal.",
    no_stock: "No stock yet.", add_stock: "Add stock", min_quantity: "Minimum",
    unit: "Unit", size: "Size", colony: "Own colony", low: "low", no_documents: "No documents yet.",
    add_document: "Add document", doc_type: "Document type", doc_title: "Title",
    issued_at: "Date", expires_at: "Expires on", doc_invoice: "Invoice / receipt", doc_cites: "CITES certificate",
    doc_permit: "Permit", doc_breeder_statement: "Breeder statement", doc_health: "Health / vet",
    doc_other: "Other document", expired: "expired", no_measurements: "No measurements yet. Add one in the journal.",
    photos_all: "Photos for all species without one", photos_found: "{n} photo(s) found",
    count_laid: "Count laid", count_hatched: "Count hatched",
    ai_moved: "Fields without a place of their own are under 'extra':",
    photo: "Photo", upload_photo: "Upload photo", delete_photo: "Remove own photo",
    choose_photo: "Choose species photo", no_photo: "No photo", photo_source: "Photo",
    none_found: "Nothing found.", ai_import: "Caresheet with AI", ai_entity: "AI",
    url: "Web page (URL)", file: "or file (PDF / photo)", hint: "Extra instruction for the AI (optional)",
    reading: "The AI is reading the caresheet… this can take a minute.", extract: "Read",
    ai_review: "Check, adjust where needed and click Save.", ai_missing:
      "No AI found. Add an AI integration in HA (e.g. Anthropic) with an AI Task entity.",
    ai_no_files: "This AI cannot read files; use a web address.", license: "License",
    species_one: "Species", plants: "Food plants", food_plants: "Food plants", nutrition: "Food",
    no_plants: "No plants found. Add them with the plant monitor.",
    prof_temp_day: "Day temperature (°C)", prof_temp_night: "Night temperature (°C)",
    prof_temp_max_safe: "Dangerous from (°C)", prof_humidity: "Humidity (%)",
    prof_water_temp: "Water temperature (°C)", prof_ph: "pH", prof_light_hours: "Day length (h)",
    prof_uv: "UV", prof_substrate_moisture: "Substrate moisture", prof_misting: "Misting",
    prof_ventilation: "Ventilation", prof_feeding_interval_days: "Feed every … days",
    prof_cleaning_interval_days: "Clean every … days", prof_substrate_change_interval_days: "Change substrate every … days",
    prof_water_change_interval_days: "Water change every … days", prof_post_molt_fast_days: "Feeding pause after molt (days)",
    cat_feeding: "Feeding", cat_hygiene: "Hygiene", cat_climate: "Climate & water", cat_development: "Development",
    cat_breeding: "Breeding", cat_measurement: "Measurements", cat_health: "Health", cat_movement: "Movement",
    cat_admin: "Administration", cat_other: "Other",
  },
};

export function t(hass, key, vars) {
  const lang = (hass && hass.language ? hass.language : "en").slice(0, 2);
  let text = (TEXTS[lang] || TEXTS.en)[key] ?? TEXTS.en[key] ?? key;
  if (vars) for (const [k, v] of Object.entries(vars)) text = text.replace(`{${k}}`, v);
  return text;
}

export const esc = (value) =>
  String(value ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

// ------------------------------------------------------------------ store --

/** Eén abonnement per HA-verbinding, gedeeld door paneel en alle kaarten. */
class Store extends EventTarget {
  constructor(hass) {
    super();
    this.hass = hass;
    this.animals = null;
    this.meta = null;
    this.species = null;
    hass.connection
      .subscribeMessage((msg) => {
        this.animals = msg.animals;
        this.enclosures = msg.enclosures || [];
        this._emit();
      }, { type: "arthropoda/subscribe" })
      .catch((err) => {
        this.error = err.message || String(err);
        this._emit();
      });
    this.loadMeta();
  }

  _emit() { this.dispatchEvent(new Event("change")); }

  async loadMeta() {
    try {
      this.meta = await this.hass.callWS({ type: "arthropoda/meta", language: this.hass.language });
      this._emit();
    } catch (err) { this.error = err.message; this._emit(); }
  }

  async loadSpecies() {
    const res = await this.hass.callWS({ type: "arthropoda/species/list" });
    this.species = res.species;
    this._emit();
    return this.species;
  }

  async loadStock() {
    const res = await this.hass.callWS({ type: "arthropoda/stock/list" });
    this.stock = res.stock;
    return this.stock;
  }

  label(group, value) {
    if (value === null || value === undefined || value === "") return "";
    return this.meta?.labels?.[group]?.[value] ?? value;
  }

  animal(id) { return (this.animals || []).find((a) => a.id === id); }

  enclosure(idOrCode) {
    const key = String(idOrCode).toLowerCase();
    return (this.enclosures || []).find((e) => String(e.id) === key || e.code.toLowerCase() === key);
  }

  log(animalIds, entryType, extra = {}) {
    return this.hass.callWS({
      type: "arthropoda/journal/add", animal_ids: animalIds, entry_type: entryType, ...extra,
    });
  }
}

const stores = new WeakMap();
export function getStore(hass) {
  let store = stores.get(hass.connection);
  if (!store) {
    store = new Store(hass);
    stores.set(hass.connection, store);
  }
  store.hass = hass;
  return store;
}

// --------------------------------------------------------------- opmaak ----

export function daysText(hass, days) {
  if (days === null || days === undefined) return t(hass, "never");
  if (days === 0) return t(hass, "today");
  return t(hass, "days_ago", { n: days });
}

export function dueText(hass, iso) {
  if (!iso) return "";
  const due = new Date(iso);
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const day = new Date(due);
  day.setHours(0, 0, 0, 0);
  const diff = Math.round((day - today) / 86400000);
  if (diff < 0) return t(hass, "overdue", { n: -diff });
  if (diff === 0) return t(hass, "today");
  return t(hass, "in_days", { n: diff });
}

export function fmtDateTime(hass, iso) {
  if (!iso) return "";
  return new Date(iso).toLocaleString(hass.locale?.language || hass.language || undefined, {
    dateStyle: "medium", timeStyle: "short",
  });
}

export function fmtDate(hass, iso) {
  if (!iso) return "";
  return new Date(iso).toLocaleDateString(hass.locale?.language || hass.language || undefined, {
    dateStyle: "medium",
  });
}

export function fmtNum(value, digits = 1) {
  if (value === null || value === undefined) return "–";
  return Number(value).toLocaleString(undefined, { maximumFractionDigits: digits });
}

export function commonName(hass, species) {
  if (!species) return "";
  const lang = (hass.language || "en").slice(0, 2);
  return species.common_names?.[lang] || Object.values(species.common_names || {})[0] || "";
}

export function stageText(store, animal) {
  const parts = [];
  if (animal.stage) parts.push(store.label("stage", animal.stage));
  if (animal.instar !== null && animal.instar !== undefined && animal.kind === "individual") {
    parts.push(`L${animal.instar}`);
  }
  if (animal.kind === "colony" && animal.count !== null && animal.count !== undefined) {
    parts.push(`± ${animal.count}`);
  }
  return parts.join(" · ");
}

/** URL van de foto van een dier (via HA's beveiligde afbeeldingslink), of null. */
export function photoUrl(hass, animal) {
  const id = animal.entities?.photo;
  const state = id ? hass.states[id] : null;
  if (!state || !state.attributes.entity_picture || !state.attributes.source) return null;
  return state.attributes.entity_picture;
}

export function photoCredit(hass, animal) {
  const state = animal.entities?.photo ? hass.states[animal.entities.photo] : null;
  return state?.attributes.source === "inaturalist" ? state.attributes.attribution || "" : "";
}

export const isFeeder = (animal) => !!animal.species?.feeder;

/** Filter op voederdieren: "all" | "no_feeders" | "only_feeders". */
export function feederFilter(animals, mode) {
  if (mode === "no_feeders") return animals.filter((a) => !isFeeder(a));
  if (mode === "only_feeders") return animals.filter(isFeeder);
  return animals;
}

export function nextTask(animal) {
  return [...(animal.tasks || [])].sort((a, b) => a.due.localeCompare(b.due))[0];
}

/** Navigeer binnen HA (zonder de pagina te herladen). */
export function navigate(path) {
  history.pushState(null, "", path);
  window.dispatchEvent(new CustomEvent("location-changed", { detail: { replace: false } }));
}

export function toast(element, message) {
  element.dispatchEvent(new CustomEvent("hass-notification", {
    detail: { message }, bubbles: true, composed: true,
  }));
}

// ---------------------------------------------------------- gedeelde CSS --

export const BASE_CSS = `
  :host { --ak-ok: var(--success-color, #2e7d32); --ak-problem: var(--error-color, #c62828);
          --ak-muted: var(--secondary-text-color, #6b6b6b); --ak-line: var(--divider-color, #e0e0e0);
          --ak-accent: var(--primary-color, #03a9f4); }
  * { box-sizing: border-box; }
  .muted { color: var(--ak-muted); }
  .small { font-size: 0.85em; }
  .row { display: flex; align-items: center; gap: 8px; }
  .wrap { flex-wrap: wrap; }
  .grow { flex: 1; min-width: 0; }
  .ellipsis { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .dot { width: 10px; height: 10px; border-radius: 50%; flex: none; display: inline-block; }
  .dot.ok { background: var(--ak-ok); } .dot.problem { background: var(--ak-problem); }
  .dot.inactive { background: var(--ak-muted); }
  .chip { display: inline-flex; align-items: center; gap: 4px; padding: 2px 10px; border-radius: 12px;
          font-size: 0.8em; background: var(--secondary-background-color, #f2f2f2); white-space: nowrap; }
  .chip.problem { background: color-mix(in srgb, var(--ak-problem) 15%, transparent); color: var(--ak-problem); }
  .chip.ok { background: color-mix(in srgb, var(--ak-ok) 15%, transparent); color: var(--ak-ok); }
  button.ak { font: inherit; border: 1px solid var(--ak-line); background: var(--card-background-color, #fff);
              color: var(--primary-text-color); border-radius: 18px; padding: 6px 14px; cursor: pointer;
              display: inline-flex; align-items: center; gap: 6px; }
  button.ak:hover { border-color: var(--ak-accent); }
  button.ak.primary { background: var(--ak-accent); color: var(--text-primary-color, #fff); border-color: var(--ak-accent); }
  button.ak.danger { color: var(--ak-problem); }
  button.ak[disabled] { opacity: 0.5; cursor: default; }
  button.icon { border: none; background: none; cursor: pointer; color: var(--ak-muted); padding: 4px;
                border-radius: 50%; font-size: 1.1em; line-height: 1; }
  button.icon:hover { color: var(--primary-text-color); background: var(--secondary-background-color, #eee); }
  .avatar { width: 48px; height: 48px; border-radius: 50%; object-fit: cover; flex: none;
            background: var(--secondary-background-color, #eee); }
  .avatar.ph { display:inline-flex; align-items:center; justify-content:center; font-size: 22px; }
  .bar { position: relative; height: 8px; border-radius: 4px; background: var(--secondary-background-color, #eee); }
  .bar .band { position: absolute; top: 0; bottom: 0; background: color-mix(in srgb, var(--ak-ok) 35%, transparent); border-radius: 4px; }
  .bar .mark { position: absolute; top: -3px; width: 4px; height: 14px; border-radius: 2px; background: var(--primary-text-color); transform: translateX(-2px); }
  .bar .mark.problem { background: var(--ak-problem); }
`;

/** Balk met doelbereik (band) en huidige waarde (streepje). */
export function rangeBar(value, target, pad = 6) {
  if (!target && (value === null || value === undefined)) return "";
  const lo = target ? target[0] : value - pad;
  const hi = target ? target[1] : value + pad;
  const min = Math.min(lo - pad, value ?? lo);
  const max = Math.max(hi + pad, value ?? hi);
  const pos = (v) => `${(((v - min) / (max - min)) * 100).toFixed(1)}%`;
  const band = target
    ? `<div class="band" style="left:${pos(lo)};width:calc(${pos(hi)} - ${pos(lo)})"></div>` : "";
  const out = target && value !== null && value !== undefined && (value < lo || value > hi);
  const mark = value === null || value === undefined
    ? "" : `<div class="mark ${out ? "problem" : ""}" style="left:${pos(value)}"></div>`;
  return `<div class="bar">${band}${mark}</div>`;
}

// ---------------------------------------------------------- dialoogbasis --

const DIALOG_CSS = `
  dialog.ak-dialog { border: none; border-radius: 16px; padding: 0; width: min(640px, 96vw);
    max-height: 92vh; background: var(--card-background-color, #fff); color: var(--primary-text-color, #222);
    box-shadow: 0 8px 32px rgba(0,0,0,.3); font-family: var(--paper-font-body1_-_font-family, Roboto, sans-serif); }
  dialog.ak-dialog *, dialog.ak-dialog *::before, dialog.ak-dialog *::after { box-sizing: border-box; }
  dialog.ak-dialog::backdrop { background: rgba(0,0,0,.45); }
  .ak-d-head { display:flex; align-items:center; justify-content:space-between; padding:16px 20px 8px; }
  .ak-d-head h2 { margin:0; font-size:1.25em; font-weight:500; }
  .ak-d-body { padding: 4px 20px 12px; overflow-y: auto; max-height: calc(92vh - 130px); }
  .ak-d-foot { display:flex; justify-content:flex-end; gap:8px; padding:12px 20px 16px; border-top:1px solid var(--divider-color,#e0e0e0); }
  .ak-d-body fieldset { border:1px solid var(--divider-color,#e0e0e0); border-radius:12px; margin:10px 0; padding:8px 14px 12px; }
  .ak-d-body legend { padding:0 6px; font-weight:500; }
  .ak-grid { display:grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 10px 14px; }
  .ak-field { display:flex; flex-direction:column; gap:4px; font-size:.85em; color: var(--secondary-text-color,#666); }
  .ak-field.wide { grid-column: 1 / -1; }
  .ak-field input, .ak-field select, .ak-field textarea { font: inherit; font-size: 1rem; color: var(--primary-text-color,#222);
    background: var(--secondary-background-color,#f5f5f5); border:1px solid transparent; border-bottom:1px solid var(--divider-color,#bbb);
    border-radius:6px 6px 0 0; padding:8px 10px; height: 42px; width: 100%; }
  .ak-field textarea { height: auto; min-height: 64px; }
  .ak-field input:focus, .ak-field select:focus, .ak-field textarea:focus { outline:none; border-bottom:2px solid var(--primary-color,#03a9f4); }
  .ak-field input[type=checkbox] { width:auto; min-height:auto; }
  .ak-check { display:flex; align-items:center; gap:8px; font-size:1rem; color: var(--primary-text-color,#222); }
  .ak-multi .chips { display:flex; flex-wrap:wrap; gap:6px; margin-bottom:4px; }
  .ak-multi .chip { display:inline-flex; align-items:center; gap:4px; padding:2px 4px 2px 10px; border-radius:12px;
    background: var(--secondary-background-color,#eee); color: var(--primary-text-color,#222); font-size: .9rem; }
  .ak-multi .chip button { border:none; background:none; cursor:pointer; color:inherit; font-size:1rem; }
  .ak-error { color: var(--error-color,#c62828); margin: 8px 0 0; }
  .ak-animals { display:flex; flex-wrap:wrap; gap:6px 14px; }
  .ak-btn { font: inherit; border: 1px solid var(--divider-color,#ccc); background: transparent; color: var(--primary-text-color,#222);
    border-radius: 18px; padding: 7px 16px; cursor: pointer; }
  .ak-btn.primary { background: var(--primary-color,#03a9f4); color: var(--text-primary-color,#fff); border-color: var(--primary-color,#03a9f4); }
  .ak-btn[disabled] { opacity:.5; cursor: default; }
  .ak-x { border:none; background:none; font-size:1.4em; cursor:pointer; color: var(--secondary-text-color,#666); }
`;

function ensureDialogStyles() {
  if (document.getElementById("ak-dialog-css")) return;
  const style = document.createElement("style");
  style.id = "ak-dialog-css";
  style.textContent = DIALOG_CSS;
  document.head.appendChild(style);
}

/** Opent een dialoog; `render(body)` vult de inhoud, `onSave()` → true = sluiten. */
export function openDialog(hass, title, render, onSave, saveLabel) {
  ensureDialogStyles();
  const dialog = document.createElement("dialog");
  dialog.className = "ak-dialog";
  dialog.innerHTML = `
    <div class="ak-d-head"><h2>${esc(title)}</h2><button class="ak-x" data-close aria-label="${esc(t(hass, "close"))}">×</button></div>
    <div class="ak-d-body"></div>
    <div class="ak-error ak-d-err" style="padding:0 20px"></div>
    <div class="ak-d-foot">
      <button class="ak-btn" data-close>${esc(t(hass, "cancel"))}</button>
      <button class="ak-btn primary" data-save>${esc(saveLabel || t(hass, "save"))}</button>
    </div>`;
  document.body.appendChild(dialog);
  const body = dialog.querySelector(".ak-d-body");
  const err = dialog.querySelector(".ak-d-err");
  const close = () => { dialog.close(); dialog.remove(); };
  dialog.querySelectorAll("[data-close]").forEach((b) => b.addEventListener("click", close));
  dialog.addEventListener("cancel", (e) => { e.preventDefault(); close(); });
  const save = dialog.querySelector("[data-save]");
  save.addEventListener("click", async () => {
    err.textContent = "";
    save.disabled = true;
    try {
      if (await onSave(body)) close();
    } catch (e) {
      err.textContent = e.message || String(e);
    } finally {
      save.disabled = false;
    }
  });
  render(body);
  dialog.showModal();
  return dialog;
}

// ----------------------------------------------------------- formvelden --

export function field(label, inner, wide = false) {
  return `<label class="ak-field ${wide ? "wide" : ""}"><span>${esc(label)}</span>${inner}</label>`;
}

export function selectHtml(name, options, value, includeEmpty = true, emptyLabel = "—") {
  const opts = options.map(([v, l]) =>
    `<option value="${esc(v)}" ${String(v) === String(value ?? "") ? "selected" : ""}>${esc(l)}</option>`).join("");
  return `<select name="${esc(name)}">${includeEmpty ? `<option value="">${esc(emptyLabel)}</option>` : ""}${opts}</select>`;
}

/** Andere dieren als keuzelijst (voor ouders, partner, ...). */
function animalOptions(store, excludeId) {
  return (store.animals || [])
    .filter((a) => a.id !== excludeId)
    .map((a) => [a.id, `${a.name}${a.species ? ` – ${a.species.scientific_name}` : ""}`]);
}

function entityOptions(hass, domains, deviceClass) {
  return Object.values(hass.states)
    .filter((s) => domains.includes(s.entity_id.split(".")[0]))
    .filter((s) => !deviceClass || s.attributes.device_class === deviceClass)
    .map((s) => [s.entity_id, `${s.attributes.friendly_name || s.entity_id} (${s.entity_id})`])
    .sort((a, b) => a[1].localeCompare(b[1]));
}

/** Keuze uit entiteiten; meervoudig = chips + keuzelijst om toe te voegen. */
export function entityField(hass, name, label, domains, value, { multiple = false, deviceClass = null } = {}) {
  let options = entityOptions(hass, domains, deviceClass);
  const current = multiple ? (value || []) : value;
  // Huidige waarde altijd tonen, ook als het device_class-filter ze niet vindt.
  for (const id of multiple ? current : current ? [current] : []) {
    if (!options.some(([v]) => v === id)) options = [[id, id], ...options];
  }
  if (!multiple) return field(label, selectHtml(name, options, value, true, t(hass, "none")));
  const chips = current.map((id) =>
    `<span class="chip" data-value="${esc(id)}">${esc(hass.states[id]?.attributes.friendly_name || id)}<button type="button" data-remove>×</button></span>`).join("");
  return field(label, `<div class="ak-multi" data-multi="${esc(name)}"><div class="chips">${chips}</div>
    ${selectHtml("", options, "", true, `+ ${t(hass, "add")}`)}</div>`);
}

/** Keuze uit planten van de plant monitor (domein plant.*). */
function plantField(hass, name, value) {
  const hasPlants = Object.keys(hass.states).some((id) => id.startsWith("plant."));
  if (!hasPlants && !(value || []).length) {
    return `<div class="ak-field wide"><span>${esc(t(hass, "food_plants"))}</span><span>${esc(t(hass, "no_plants"))}</span></div>`;
  }
  return entityField(hass, name, t(hass, "food_plants"), ["plant"], value || [], { multiple: true });
}

export function wireMulti(body) {
  body.querySelectorAll("[data-multi]").forEach((box) => {
    const chips = box.querySelector(".chips");
    chips.addEventListener("click", (e) => {
      if (e.target.matches("[data-remove]")) e.target.closest(".chip").remove();
    });
    const select = box.querySelector("select");
    select.addEventListener("change", () => {
      const id = select.value;
      if (id && !chips.querySelector(`[data-value="${CSS.escape(id)}"]`)) {
        const label = select.selectedOptions[0].textContent.replace(/\s*\([^)]*\)$/, "");
        chips.insertAdjacentHTML("beforeend",
          `<span class="chip" data-value="${esc(id)}">${esc(label)}<button type="button" data-remove>×</button></span>`);
      }
      select.value = "";
    });
  });
}

export function readForm(body) {
  const data = {};
  body.querySelectorAll("[name]").forEach((el) => {
    if (!el.name) return;
    if (el.type === "checkbox") data[el.name] = el.checked;
    else if (el.type === "number") data[el.name] = el.value === "" ? null : Number(el.value);
    else data[el.name] = el.value;
  });
  body.querySelectorAll("[data-multi]").forEach((box) => {
    data[box.dataset.multi] = [...box.querySelectorAll(".chip")].map((c) => c.dataset.value);
  });
  return data;
}

// ------------------------------------------------------ dier wijzigen/toe --

export const NUMBER = (name, value, step = 1) =>
  `<input type="number" name="${name}" step="${step}" value="${value ?? ""}">`;

/** Dialoog om een dier toe te voegen (animal = null) of te wijzigen. */
export async function openAnimalDialog(hass, animal = null, preset = null) {
  const store = getStore(hass);
  const species = store.species || (await store.loadSpecies());
  if (!species.length) throw new Error(t(hass, "no_species"));
  const cfg = animal ? { ...animal.config } : { kind: "individual", sex: "unknown", ...(preset || {}) };
  if (animal) Object.assign(cfg, { sex: animal.sex, stage: animal.stage, instar: animal.instar, count: animal.count });
  const L = (g, v) => store.label(g, v);
  const opts = (group, values) => values.map((v) => [v, L(group, v)]);
  const speciesOpts = species.map((s) => [s.id, `${s.scientific_name}${commonName(hass, s) ? ` (${commonName(hass, s)})` : ""}`]);
  const meta = store.meta || {};

  openDialog(
    hass,
    animal ? `${t(hass, "edit")}: ${animal.name}` : t(hass, "add_animal"),
    (body) => {
      body.innerHTML = `
        <fieldset><legend>${esc(t(hass, "general"))}</legend><div class="ak-grid">
          ${field(t(hass, "name"), `<input name="name" value="${esc(cfg.name ?? animal?.name ?? "")}" required>`)}
          ${field(t(hass, "species_one"), selectHtml("species_id", speciesOpts, cfg.species_id))}
          ${field(t(hass, "kind"), selectHtml("kind", opts("kind", meta.kinds || ["individual", "colony"]), cfg.kind, false))}
          ${field(t(hass, "sex"), selectHtml("sex", opts("sex", meta.sexes || ["unknown"]), cfg.sex, false))}
          ${field(t(hass, "stage"), selectHtml("stage", opts("stage", meta.stages || []), cfg.stage))}
          ${field(t(hass, "instar"), NUMBER("instar", cfg.instar))}
          ${field(t(hass, "count"), NUMBER("count", cfg.count))}
          ${field(t(hass, "origin"), selectHtml("origin", opts("origin", meta.origins || []), cfg.origin))}
          ${field(t(hass, "enclosure"), selectHtml("_enclosure", (store.enclosures || []).map((e) => [e.id, `${e.code}${e.name ? ` – ${e.name}` : ""}`]), animal?.enclosure_id ?? preset?._enclosure ?? "", true, t(hass, "no_enclosure")))}
          ${field(t(hass, "born_at"), `<input type="date" name="born_at" value="${esc(cfg.born_at || "")}">`)}
          ${field(t(hass, "acquired_at"), `<input type="date" name="acquired_at" value="${esc(cfg.acquired_at || "")}">`)}
        </div></fieldset>
        <fieldset><legend>${esc(t(hass, "origin_section"))}</legend><div class="ak-grid">
          ${field(t(hass, "seller"), `<input name="seller" value="${esc(cfg.seller || "")}">`)}
          ${field(t(hass, "price"), NUMBER("price", cfg.price, 0.01))}
          ${field(t(hass, "mother_id"), selectHtml("mother_id", animalOptions(store, animal?.id), cfg.mother_id))}
          ${field(t(hass, "father_id"), selectHtml("father_id", animalOptions(store, animal?.id), cfg.father_id))}
          ${field(t(hass, "generation"), `<input name="generation" value="${esc(cfg.generation || "")}" placeholder="F1, F2, WC …">`)}
          <input type="hidden" name="brood_id" value="${esc(cfg.brood_id ?? "")}">
        </div></fieldset>
        <fieldset><legend>${esc(t(hass, "sensors"))}</legend><div class="ak-grid">
          ${entityField(hass, "temperature_sensors", t(hass, "temperature_sensors"), ["sensor"], cfg.temperature_sensors, { multiple: true, deviceClass: "temperature" })}
          ${entityField(hass, "humidity_sensor", t(hass, "humidity_sensor"), ["sensor"], cfg.humidity_sensor, { deviceClass: "humidity" })}
          ${entityField(hass, "water_temperature_sensor", t(hass, "water_temperature_sensor"), ["sensor"], cfg.water_temperature_sensor, { deviceClass: "temperature" })}
        </div></fieldset>
        <fieldset><legend>${esc(t(hass, "nutrition"))}</legend><div class="ak-grid">
          ${plantField(hass, "food_plants", cfg.food_plants)}
        </div></fieldset>
        <fieldset><legend>${esc(t(hass, "actuators"))}</legend><div class="ak-grid">
          ${entityField(hass, "heater", t(hass, "heater"), ["switch", "light", "climate", "input_boolean"], cfg.heater)}
          ${entityField(hass, "mister", t(hass, "mister"), ["switch", "script", "input_boolean"], cfg.mister)}
          ${entityField(hass, "lights", t(hass, "lights"), ["switch", "light", "input_boolean"], cfg.lights, { multiple: true })}
          ${entityField(hass, "fan", t(hass, "fan"), ["switch", "fan", "input_boolean"], cfg.fan)}
          ${entityField(hass, "water_heater", t(hass, "water_heater"), ["switch", "climate", "input_boolean"], cfg.water_heater)}
          ${entityField(hass, "pumps", t(hass, "pumps"), ["switch", "input_boolean"], cfg.pumps, { multiple: true })}
        </div></fieldset>
        <fieldset><legend>${esc(t(hass, "tuning"))}</legend><div class="ak-grid">
          ${field(t(hass, "hysteresis"), NUMBER("hysteresis", cfg.hysteresis ?? 0.5, 0.1))}
          ${field(t(hass, "mist_seconds"), NUMBER("mist_seconds", cfg.mist_seconds ?? 10))}
          ${field(t(hass, "mist_pause_minutes"), NUMBER("mist_pause_minutes", cfg.mist_pause_minutes ?? 30))}
          ${field(t(hass, "mist_max_per_day"), NUMBER("mist_max_per_day", cfg.mist_max_per_day ?? 6))}
          ${field(t(hass, "light_ramp_minutes"), NUMBER("light_ramp_minutes", cfg.light_ramp_minutes ?? 0))}
          ${field(t(hass, "mist_times"), `<input name="mist_times" value="${esc(cfg.mist_times || "")}" placeholder="08:00, 20:00">`, true)}
        </div></fieldset>`;
      wireMulti(body);
    },
    async (body) => {
      const data = readForm(body);
      if (!data.name || !data.species_id) throw new Error(t(hass, "required"));
      const enclosureId = data._enclosure ? Number(data._enclosure) : null;
      delete data._enclosure;
      if (animal) {
        if ((animal.enclosure_id ?? null) !== enclosureId) {
          await hass.callWS({ type: "arthropoda/enclosure/assign", animal_id: animal.id, enclosure_id: enclosureId });
        }
        await hass.callWS({ type: "arthropoda/animal/update", animal_id: animal.id, data });
      } else {
        const { animal_id: newId } = await hass.callWS({ type: "arthropoda/animal/add", data });
        if (enclosureId !== null) {
          // Het nieuwe dier is pas na het herladen van de integratie gekend.
          for (let attempt = 0; attempt < 10; attempt++) {
            await new Promise((r) => setTimeout(r, 700));
            try {
              await hass.callWS({ type: "arthropoda/enclosure/assign", animal_id: newId, enclosure_id: enclosureId });
              break;
            } catch (err) { if (attempt === 9) throw err; }
          }
        }
      }
      return true;
    },
  );
}

// -------------------------------------------------------- dagboekregel ----

// Extra velden per handeling: [sleutel, soort invoer]
const ENTRY_FIELDS = {
  feeding: [["stock_id", "stock"], ["plants", "plants"], ["prey", "text"], ["quantity", "number"], ["prey_size", "text"], ["result", "result"]],
  plant_food: [["plants", "plants"]],
  molt: [["instar_after", "number"], ["sex", "sex"], ["legspan_mm", "decimal"], ["length_mm", "decimal"], ["exuvia_kept", "bool"]],
  measurement: [["length_mm", "decimal"], ["legspan_mm", "decimal"], ["weight_g", "decimal"], ["count", "number"]],
  count: [["count", "number"]],
  stage_change: [["stage", "stage"], ["instar", "number"]],
  egg_sac: [["father_id", "animal"], ["count", "number"], ["incubation_days", "number"]],
  ootheca: [["father_id", "animal"], ["count", "number"], ["incubation_days", "number"]],
  egg_laying: [["father_id", "animal"], ["count", "number"], ["incubation_days", "number"]],
  hatch: [["count", "number"]],
  split_colony: [["count_remaining", "number"]],
  water_test: [["ph", "decimal"], ["gh", "decimal"], ["kh", "decimal"], ["no2", "decimal"], ["no3", "decimal"]],
  water_change: [["percent", "number"]],
  substrate_change: [["substrate", "text"]],
  health_issue: [["cause", "text"]],
  treatment: [["treatment_text", "text"]],
  death: [["cause", "text"]],
  pairing: [["partner_id", "animal"], ["partner", "text"], ["outcome", "text"]],
  diapause_start: [["planned_end", "date"]],
};

function localNow() {
  const d = new Date();
  d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
  return d.toISOString().slice(0, 16);
}

/** Dialoog voor een dagboekregel, voor één of meer dieren. */
export async function openJournalDialog(hass, preselected = [], presetType = null) {
  const store = getStore(hass);
  try { await store.loadStock(); } catch (err) { store.stock = []; }
  const animals = (store.animals || []).filter((a) => a.status !== "archived");
  const meta = store.meta || { entry_types: [] };
  const categories = {};
  for (const { type, category } of meta.entry_types) (categories[category] ||= []).push(type);
  const typeSelect = `<select name="entry_type">${Object.entries(categories).map(([cat, types]) =>
    `<optgroup label="${esc(t(hass, `cat_${cat}`))}">${types.map((ty) =>
      `<option value="${ty}" ${ty === presetType ? "selected" : ""}>${esc(store.label("entry_type", ty))}</option>`).join("")}</optgroup>`).join("")}</select>`;

  const renderExtra = (body) => {
    const type = body.querySelector("[name=entry_type]").value;
    const box = body.querySelector(".ak-extra");
    const fields = ENTRY_FIELDS[type] || [];
    box.innerHTML = fields.map(([key, kind]) => {
      const label = t(hass, key);
      if (kind === "result") return field(label, selectHtml(`x_${key}`, ["accepted", "partial", "refused"].map((v) => [v, t(hass, v)]), "accepted", false));
      if (kind === "sex") return field(label, selectHtml(`x_${key}`, (meta.sexes || []).map((v) => [v, store.label("sex", v)]), ""));
      if (kind === "stage") return field(label, selectHtml(`x_${key}`, (meta.stages || []).map((v) => [v, store.label("stage", v)]), "", false));
      if (kind === "animal") return field(label, selectHtml(`x_${key}`, animalOptions(store, preselected[0]), ""));
      if (kind === "stock") {
        const items = store.stock || [];
        if (!items.length) return "";
        return field(label, selectHtml(`x_${key}`, items.map((it) => [it.id, `${it.name}${it.size ? ` (${it.size})` : ""} – ${it.quantity}${it.unit ? " " + it.unit : ""}`]), ""));
      }
      if (kind === "plants") {
        const preset = [...new Set(preselected.flatMap((id) => store.animal(id)?.config?.food_plants || []))];
        return plantField(hass, `x_${key}`, preset);
      }
      if (kind === "date") return field(label, `<input type="date" name="x_${key}">`);
      if (kind === "bool") return `<label class="ak-check"><input type="checkbox" name="x_${key}"> ${esc(label)}</label>`;
      const step = kind === "decimal" ? "any" : "1";
      const type_ = kind === "text" ? "text" : "number";
      return field(label, `<input type="${type_}" step="${step}" name="x_${key}">`);
    }).join("");
    wireMulti(box);
    box.parentElement.style.display = fields.length ? "" : "none";
  };

  openDialog(
    hass,
    t(hass, "new_entry"),
    (body) => {
      body.innerHTML = `
        <div class="ak-grid">
          ${field(t(hass, "entry_type"), typeSelect)}
          ${field(t(hass, "when"), `<input type="datetime-local" name="when" value="${localNow()}">`)}
        </div>
        <fieldset><legend>${esc(t(hass, "animals"))}</legend><div class="ak-animals">
          ${animals.map((a) => `<label class="ak-check"><input type="checkbox" data-animal="${esc(a.id)}" ${preselected.includes(a.id) ? "checked" : ""}> ${esc(a.name)}</label>`).join("")}
        </div></fieldset>
        <fieldset><legend>${esc(t(hass, "details"))}</legend><div class="ak-grid ak-extra"></div></fieldset>
        <div class="ak-grid">${field(t(hass, "notes"), `<textarea name="notes" rows="2"></textarea>`, true)}</div>`;
      body.querySelector("[name=entry_type]").addEventListener("change", () => renderExtra(body));
      renderExtra(body);
    },
    async (body) => {
      const ids = [...body.querySelectorAll("[data-animal]:checked")].map((c) => c.dataset.animal);
      if (!ids.length) throw new Error(t(hass, "select_animal"));
      let entryType = body.querySelector("[name=entry_type]").value;
      const data = {};
      body.querySelectorAll("[name^=x_]").forEach((el) => {
        const key = el.name.slice(2);
        if (el.type === "checkbox") { if (el.checked) data[key] = true; }
        else if (el.value !== "") data[key] = el.type === "number" || key === "stock_id" ? Number(el.value) : el.value;
      });
      body.querySelectorAll("[data-multi^=x_]").forEach((multi) => {
        const values = [...multi.querySelectorAll(".chip")].map((c) => c.dataset.value);
        if (values.length) data[multi.dataset.multi.slice(2)] = values;
      });
      if (entryType === "feeding" && data.result === "refused") entryType = "feeding_refused";
      const when = body.querySelector("[name=when]").value;
      await store.log(ids, entryType, {
        timestamp: when ? new Date(when).toISOString() : undefined,
        notes: body.querySelector("[name=notes]").value || null,
        data,
      });
      return true;
    },
  );
}

/** Snelle dagboekregel met standaardwaarden (snelknoppen). */
export async function quickLog(element, hass, animalId, entryType) {
  const store = getStore(hass);
  try {
    await store.log([animalId], entryType, { data: { source: "card" } });
    toast(element, `${store.label("entry_type", entryType)} ✓`);
  } catch (err) {
    toast(element, err.message || String(err));
  }
}
