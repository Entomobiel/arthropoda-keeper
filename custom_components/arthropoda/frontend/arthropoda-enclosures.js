/*
 * Arthropoda Keeper – kasten/terraria: formulier, NFC, etiketten, werkscherm, rondes.
 */
import {
  NUMBER, dueText, entityField, esc, field, fmtDate, fmtNum, getStore, openDialog,
  INSIGHT_ICON, insightText,
  openJournalDialog, photoUrl, readForm, selectHtml, toast, wireMulti,
} from "./arthropoda-common.js?v=0.13.0";
import { qrSvg } from "./arthropoda-qr.js?v=0.13.0";
import { handlePotClick, potsCard } from "./arthropoda-food.js?v=0.13.0";

const ENC_TYPES = ["terrarium", "faunabox", "breeding_box", "formicarium", "aquarium", "net_cage", "plant_cabinet", "other"];
const ENC_STATUSES = ["in_use", "empty", "maintenance"];

const TEXTS = {
  nl: {
    dimensions: "Afmetingen", place: "Plaats", climate_short: "Klimaat",
    enclosures: "Kasten", enclosure: "Kast", add_enclosure: "Kast toevoegen", code: "Code",
    enc_name: "Naam", enc_type: "Type", enc_status: "Status", location: "Plaats (rek, plank …)",
    length_cm: "Lengte (cm)", width_cm: "Breedte (cm)", height_cm: "Hoogte (cm)", material: "Materiaal",
    ventilation: "Ventilatie", acquired_at: "Aangeschaft op", price: "Prijs (€)", seller: "Verkoper / gemaakt door",
    notes: "Notities", climate: "Klimaat (sensoren en toestellen)", equipment: "Uitrusting en onderhoud",
    equipment_name: "Toestel (bv. UV-lamp)", interval_days: "Vervangen/reinigen elke … dagen",
    serviced_at: "Laatst vervangen/gereinigd", add_equipment: "Toestel toevoegen", residents: "Bewoners",
    t_terrarium: "Terrarium", t_faunabox: "Faunabox", t_breeding_box: "Kweekbak", t_formicarium: "Formicarium",
    t_aquarium: "Aquarium", t_net_cage: "Gaaskooi", t_plant_cabinet: "Plantenkast", t_other: "Andere",
    plants_section: "Planten (Plant Monitor)", plants_field: "Planten in deze kast", light_hours: "Daglengte voor de planten (uren)",
    plant_climate: "Klimaat sturen op de grenswaarden van de planten",
    dli_label: "Lichtsom vandaag", dli_reached: "lampen uit", light_dli: "Groeilampen uit zodra de planten genoeg licht kregen (DLI uit Plant Monitor)",
    care_moisture: "Sproeien op bodemvocht (taak als de grond te droog is)", care_pump: "Pompje (automatisch sproeien)",
    pump_seconds: "Pomptijd (s)", pump_max: "Max. beurten per dag", pump_pause: "Pauze tussen beurten (min)",
    care_title: "Verzorging per plant", care_water: "Sproeien elke … dagen", care_fertilize: "Bemesten elke … dagen",
    care_note: "Leeg = geen taak. Een taak is afgehandeld zodra je die handeling voor de plant noteert op het werkscherm (of de taak afvinkt).",
    plants_note: "Zonder dieren in de kast stuurt de kast op de min/max-waarden die je in Plant Monitor bij elke plant instelt (overlap van alle planten). Zitten er dieren in, dan zijn de planten voedsel en telt alleen het klimaat van de dieren.",
    no_plants: "Geen planten gevonden. Installeer Plant Monitor (Marketplace) en maak eerst planten aan.",
    steers_plants: "Stuurt op planten", target: "Doel", plants_title: "Planten",
    p_watered: "Water gegeven", p_fertilized: "Bemest", p_pruned: "Gesnoeid", p_repotted: "Verpot",
    p_harvested: "Geoogst", p_pest: "Plaag", p_sown: "Gezaaid", p_moved: "Verplaatst", p_note: "Notitie",
    no_plants_selected: "Kies minstens één plant.", last_watered: "laatst water", never: "nog nooit",
    scan_ok: "Kast gescand ✓ – taken over tijd kun je nu afvinken.",
    scan_needed: "Scan de NFC-tag of QR-code van deze kast om taken over tijd af te vinken.",
    plant_ok: "in orde", plant_problem: "probleem", today: "vandaag", yesterday: "gisteren", days_ago: "{n} dagen geleden",
    s_in_use: "In gebruik", s_empty: "Leeg", s_maintenance: "Onderhoud", all: "Alle kasten",
    work_screen: "Werkscherm", nfc: "NFC-tag", labels: "Etiketten afdrukken", start_round: "Ronde starten",
    finish_round: "Ronde afronden", next_enclosure: "Volgende kast", round: "Ronde",
    round_visited: "{n} kast(en) bezocht", round_summary: "Overzicht van de ronde",
    visited: "Bezocht", not_visited_tasks: "Nog open taken (niet bezocht)", nothing_open: "Niets meer open.",
    fed: "Gevoederd", misted: "Gesproeid", cleaned: "Schoongemaakt", water: "Water", plants: "Voedselplant",
    substrate: "Substraat", note: "Notitie", photo: "Foto", more: "Meer…", tasks_today: "Taken vandaag",
    no_tasks_today: "Geen taken vandaag 🎉", last_actions: "Laatste handelingen", too_small: "Te klein voor",
    no_residents: "Deze kast heeft geen bewoners.", choose_one: "Kies precies één bewoner voor een foto.",
    note_prompt: "Notitie", saved: "Opgeslagen", unknown_enclosure: "Onbekende kast: {code}",
    climate_note: "Sensoren en toestellen van de kast gelden voor alle bewoners (eigen instellingen van het dier worden dan niet gebruikt).",
    nfc_title: "NFC-tag koppelen", nfc_step1: "Schrijf een tag met de HA-app: Instellingen → Companion-app → NFC-tags → Tag schrijven.",
    nfc_step2: "Houd de tag nu tegen je gsm (met de HA-app open of op de achtergrond).",
    nfc_waiting: "Wachten op scan…", nfc_linked: "Tag gekoppeld ✓", nfc_current: "Huidige tag",
    nfc_unlink: "Tag ontkoppelen", nfc_android: "Android, in één stap: schrijf deze link met de app 'NFC Tools' (Schrijven → URL/URI):",
    copy: "Kopiëren", copied: "Gekopieerd", label_format: "Formaat", labels_select: "Welke kasten?",
    print: "Afdrukken", scan_hint: "Scan of tik NFC", qr_link: "Link in de QR-code",
    close: "Sluiten", empty_list: "Nog geen kasten. Voeg je eerste kast toe.", search: "Zoeken…",
    volume: "inhoud", liters: "l", tasks: "taken", required_code: "Een code is verplicht (bv. T-01).",
    confirm_delete: "Deze kast verwijderen? De dieren blijven bestaan, zonder kast.", delete: "Verwijderen",
    edit: "Wijzigen", back: "Terug",
  },
  en: {
    dimensions: "Dimensions", place: "Location", climate_short: "Climate",
    enclosures: "Enclosures", enclosure: "Enclosure", add_enclosure: "Add enclosure", code: "Code",
    enc_name: "Name", enc_type: "Type", enc_status: "Status", location: "Location (rack, shelf …)",
    length_cm: "Length (cm)", width_cm: "Width (cm)", height_cm: "Height (cm)", material: "Material",
    ventilation: "Ventilation", acquired_at: "Acquired on", price: "Price (€)", seller: "Seller / built by",
    notes: "Notes", climate: "Climate (sensors and devices)", equipment: "Equipment and maintenance",
    equipment_name: "Device (e.g. UV lamp)", interval_days: "Replace/clean every … days",
    serviced_at: "Last replaced/cleaned", add_equipment: "Add device", residents: "Residents",
    t_terrarium: "Terrarium", t_faunabox: "Faunabox", t_breeding_box: "Breeding box", t_formicarium: "Formicarium",
    t_aquarium: "Aquarium", t_net_cage: "Mesh cage", t_plant_cabinet: "Plant cabinet", t_other: "Other",
    plants_section: "Plants (Plant Monitor)", plants_field: "Plants in this enclosure", light_hours: "Day length for the plants (hours)",
    plant_climate: "Control the climate on the plants' thresholds",
    dli_label: "Light today", dli_reached: "lights off", light_dli: "Grow lights off once the plants had enough light (DLI from Plant Monitor)",
    care_moisture: "Water on soil moisture (task when the soil is too dry)", care_pump: "Pump (automatic watering)",
    pump_seconds: "Pump time (s)", pump_max: "Max. runs per day", pump_pause: "Pause between runs (min)",
    care_title: "Care per plant", care_water: "Water every … days", care_fertilize: "Fertilize every … days",
    care_note: "Empty = no task. A task is done as soon as you log that action for the plant on the work screen (or tick off the task).",
    plants_note: "Without animals in the enclosure, it is controlled on the min/max values you set for each plant in Plant Monitor (overlap of all plants). With animals inside, the plants are food and only the animals' climate counts.",
    no_plants: "No plants found. Install Plant Monitor (Marketplace) and create plants first.",
    steers_plants: "Controlled by plants", target: "Target", plants_title: "Plants",
    p_watered: "Watered", p_fertilized: "Fertilized", p_pruned: "Pruned", p_repotted: "Repotted",
    p_harvested: "Harvested", p_pest: "Pest", p_sown: "Sown", p_moved: "Moved", p_note: "Note",
    no_plants_selected: "Select at least one plant.", last_watered: "last watered", never: "never",
    scan_ok: "Enclosure scanned ✓ – you can now complete overdue tasks.",
    scan_needed: "Scan this enclosure's NFC tag or QR code to complete overdue tasks.",
    plant_ok: "ok", plant_problem: "problem", today: "today", yesterday: "yesterday", days_ago: "{n} days ago",
    s_in_use: "In use", s_empty: "Empty", s_maintenance: "Maintenance", all: "All enclosures",
    work_screen: "Work screen", nfc: "NFC tag", labels: "Print labels", start_round: "Start round",
    finish_round: "Finish round", next_enclosure: "Next enclosure", round: "Round",
    round_visited: "{n} enclosure(s) visited", round_summary: "Round summary",
    visited: "Visited", not_visited_tasks: "Still open (not visited)", nothing_open: "Nothing left open.",
    fed: "Fed", misted: "Misted", cleaned: "Cleaned", water: "Water", plants: "Food plant",
    substrate: "Substrate", note: "Note", photo: "Photo", more: "More…", tasks_today: "Tasks today",
    no_tasks_today: "No tasks today 🎉", last_actions: "Last actions", too_small: "Too small for",
    no_residents: "This enclosure has no residents.", choose_one: "Select exactly one resident for a photo.",
    note_prompt: "Note", saved: "Saved", unknown_enclosure: "Unknown enclosure: {code}",
    climate_note: "The enclosure's sensors and devices apply to all residents (the animals' own settings are then not used).",
    nfc_title: "Link NFC tag", nfc_step1: "Write a tag with the HA app: Settings → Companion app → NFC tags → Write tag.",
    nfc_step2: "Now hold the tag against your phone (HA app open or in the background).",
    nfc_waiting: "Waiting for scan…", nfc_linked: "Tag linked ✓", nfc_current: "Current tag",
    nfc_unlink: "Unlink tag", nfc_android: "Android, in one step: write this link with the 'NFC Tools' app (Write → URL/URI):",
    copy: "Copy", copied: "Copied", label_format: "Format", labels_select: "Which enclosures?",
    print: "Print", scan_hint: "Scan or tap NFC", qr_link: "Link in the QR code",
    close: "Close", empty_list: "No enclosures yet. Add your first one.", search: "Search…",
    volume: "volume", liters: "l", tasks: "tasks", required_code: "A code is required (e.g. T-01).",
    confirm_delete: "Delete this enclosure? The animals are kept, without enclosure.", delete: "Delete",
    edit: "Edit", back: "Back",
  },
};

export function te(hass, key, vars) {
  const lang = (hass?.language || "en").slice(0, 2);
  let text = (TEXTS[lang] || TEXTS.en)[key] ?? TEXTS.en[key] ?? key;
  if (vars) for (const [k, v] of Object.entries(vars)) text = text.replace(`{${k}}`, v);
  return text;
}

export const dims = (e) =>
  [e.length_cm, e.width_cm, e.height_cm].every((v) => v) ? `${fmtNum(e.length_cm, 0)}×${fmtNum(e.width_cm, 0)}×${fmtNum(e.height_cm, 0)} cm` : "";

const isDueToday = (iso) => {
  const end = new Date();
  end.setHours(23, 59, 59, 999);
  return new Date(iso) <= end;
};

// ------------------------------------------------------------- formulier ---

/** Kast toevoegen (enc = null) of wijzigen, inclusief bewoners en uitrusting. */
export function openEnclosureDialog(hass, enc = null) {
  const store = getStore(hass);
  const cfg = enc?.config || {};
  const current = enc?.residents || [];
  const animalOptions = (store.animals || []).filter((a) => a.state !== "inactive")
    .map((a) => [a.id, `${a.name}${a.species ? ` – ${a.species.scientific_name}` : ""}`]);
  const equipmentRow = (item = {}) => `<div class="ak-grid ak-eq" style="align-items:end;margin-bottom:6px">
      ${field(te(hass, "equipment_name"), `<input data-eq="name" value="${esc(item.name || "")}">`)}
      ${field(te(hass, "interval_days"), `<input type="number" data-eq="interval_days" value="${esc(item.interval_days ?? "")}">`)}
      ${field(te(hass, "serviced_at"), `<input type="date" data-eq="serviced_at" value="${esc(item.serviced_at || "")}">`)}
      <button type="button" class="ak-btn" data-eq-remove>✕</button></div>`;
  // Interval per plant (sproeien/bemesten); rijen volgen de gekozen planten.
  const pumpOptions = Object.keys(hass.states)
    .filter((id) => /^(switch|input_boolean|valve|script)\./.test(id)).sort()
    .map((id) => [id, hass.states[id].attributes.friendly_name || id]);
  const pumpSelect = (value) => `<select data-care="pump"><option value="">—</option>${
    [...(value && !pumpOptions.some(([v]) => v === value) ? [[value, value]] : []), ...pumpOptions]
      .map(([v, label]) => `<option value="${esc(v)}" ${v === value ? "selected" : ""}>${esc(label)}</option>`).join("")}</select>`;
  const careRows = (plants, care) => plants.length ? `
      <div style="font-weight:500;margin:8px 0 2px">${esc(te(hass, "care_title"))}</div>
      <p style="margin:0 0 6px;font-size:.85em;color:var(--secondary-text-color)">${esc(te(hass, "care_note"))}</p>
      ${plants.map((p) => {
        const c = care[p] || {};
        return `<div class="ak-grid ak-care" data-care-plant="${esc(p)}" style="align-items:end;margin-bottom:10px;padding-bottom:6px;border-bottom:1px dashed var(--divider-color,#ddd)">
        <div class="ak-field wide"><b>${esc(hass.states[p]?.attributes.friendly_name || p)}</b></div>
        ${field(te(hass, "care_water"), `<input type="number" min="0" step="0.5" data-care="plant_water" value="${esc(c.plant_water ?? "")}">`)}
        ${field(te(hass, "care_fertilize"), `<input type="number" min="0" step="1" data-care="plant_fertilize" value="${esc(c.plant_fertilize ?? "")}">`)}
        ${field(te(hass, "care_moisture"), `<input type="checkbox" data-care="water_on_moisture" ${c.water_on_moisture ? "checked" : ""}>`)}
        ${field(te(hass, "care_pump"), pumpSelect(c.pump || ""))}
        ${field(te(hass, "pump_seconds"), `<input type="number" min="1" max="120" step="1" data-care="pump_seconds" value="${esc(c.pump_seconds ?? "")}" placeholder="5">`)}
        ${field(te(hass, "pump_max"), `<input type="number" min="1" max="24" step="1" data-care="pump_max_per_day" value="${esc(c.pump_max_per_day ?? "")}" placeholder="3">`)}
        ${field(te(hass, "pump_pause"), `<input type="number" min="1" step="5" data-care="pump_pause_minutes" value="${esc(c.pump_pause_minutes ?? "")}" placeholder="60">`)}
      </div>`;
      }).join("")}` : "";
  const readCare = (body) => Object.fromEntries([...body.querySelectorAll(".ak-care")].map((row) => [
    row.dataset.carePlant,
    Object.fromEntries([...row.querySelectorAll("[data-care]")].map((i) => {
      if (i.type === "checkbox") return i.checked ? [i.dataset.care, true] : null;
      if (i.value === "") return null;
      return [i.dataset.care, i.dataset.care === "pump" ? i.value : Number(i.value)];
    }).filter(Boolean)),
  ]));

  openDialog(hass, enc ? `${te(hass, "edit")}: ${enc.code}` : te(hass, "add_enclosure"), (body) => {
    body.innerHTML = `
      <fieldset><legend>${esc(te(hass, "enclosure"))}</legend><div class="ak-grid">
        ${field(te(hass, "code"), `<input name="code" value="${esc(enc?.code || "")}" placeholder="T-01" required>`)}
        ${field(te(hass, "enc_name"), `<input name="name" value="${esc(enc?.name || "")}">`)}
        ${field(te(hass, "enc_type"), selectHtml("type", ENC_TYPES.map((x) => [x, te(hass, `t_${x}`)]), enc?.type || "terrarium", false))}
        ${field(te(hass, "enc_status"), selectHtml("status", ENC_STATUSES.map((x) => [x, te(hass, `s_${x}`)]), enc?.status || "in_use", false))}
        ${field(te(hass, "length_cm"), NUMBER("length_cm", enc?.length_cm, 0.5))}
        ${field(te(hass, "width_cm"), NUMBER("width_cm", enc?.width_cm, 0.5))}
        ${field(te(hass, "height_cm"), NUMBER("height_cm", enc?.height_cm, 0.5))}
        ${field(te(hass, "location"), `<input name="location" value="${esc(enc?.location || "")}">`)}
        ${field(te(hass, "material"), `<input name="material" value="${esc(enc?.material || "")}" placeholder="glas, kunststof, hout …">`)}
        ${field(te(hass, "ventilation"), `<input name="ventilation" value="${esc(enc?.ventilation || "")}" placeholder="voorkant + deksel …">`)}
        ${field(te(hass, "acquired_at"), `<input type="date" name="acquired_at" value="${esc(enc?.acquired_at || "")}">`)}
        ${field(te(hass, "price"), NUMBER("price", enc?.price, 0.01))}
        ${field(te(hass, "seller"), `<input name="seller" value="${esc(enc?.seller || "")}">`)}
        ${field(te(hass, "notes"), `<textarea name="notes" rows="2">${esc(enc?.notes || "")}</textarea>`, true)}
      </div></fieldset>
      <fieldset><legend>${esc(te(hass, "residents"))}</legend><div class="ak-grid">
        ${field(te(hass, "residents"), `<div class="ak-multi" data-multi="residents"><div class="chips">${current.map((id) => {
          const a = store.animal(id);
          return `<span class="chip" data-value="${esc(id)}">${esc(a?.name || id)}<button type="button" data-remove>×</button></span>`;
        }).join("")}</div>${selectHtml("", animalOptions, "", true, "+ …")}</div>`, true)}
      </div></fieldset>
      <fieldset><legend>${esc(te(hass, "plants_section"))}</legend>
        <p style="margin:0 0 8px;font-size:.85em;color:var(--secondary-text-color)">${esc(te(hass, "plants_note"))}</p>
        <div class="ak-grid">
        ${Object.keys(hass.states).some((id) => id.startsWith("plant.")) || (cfg.plants || []).length
          ? entityField(hass, "plants", te(hass, "plants_field"), ["plant"], cfg.plants || [], { multiple: true })
          : `<div class="ak-field wide"><span>${esc(te(hass, "plants_field"))}</span><span>${esc(te(hass, "no_plants"))}</span></div>`}
        ${field(te(hass, "light_hours"), NUMBER("light_hours", cfg.light_hours, 0.5))}
        ${field(te(hass, "plant_climate"), `<input type="checkbox" name="plant_climate" ${cfg.plant_climate === false ? "" : "checked"}>`)}
        ${field(te(hass, "light_dli"), `<input type="checkbox" name="light_dli" ${cfg.light_dli ? "checked" : ""}>`)}
      </div><div data-care-list>${careRows(cfg.plants || [], cfg.plant_care || {})}</div></fieldset>
      <fieldset><legend>${esc(te(hass, "climate"))}</legend>
        <p style="margin:0 0 8px;font-size:.85em;color:var(--secondary-text-color)">${esc(te(hass, "climate_note"))}</p>
        <div class="ak-grid">
        ${entityField(hass, "temperature_sensors", "Temperatuursensor(en)", ["sensor"], cfg.temperature_sensors, { multiple: true, deviceClass: "temperature" })}
        ${entityField(hass, "humidity_sensor", "Vochtigheidssensor", ["sensor"], cfg.humidity_sensor, { deviceClass: "humidity" })}
        ${entityField(hass, "water_temperature_sensor", "Watertemperatuursensor", ["sensor"], cfg.water_temperature_sensor, { deviceClass: "temperature" })}
        ${entityField(hass, "heater", "Verwarming", ["switch", "light", "climate", "input_boolean"], cfg.heater)}
        ${entityField(hass, "mister", "Vernevelaar", ["switch", "script", "input_boolean"], cfg.mister)}
        ${entityField(hass, "lights", "Verlichting", ["switch", "light", "input_boolean"], cfg.lights, { multiple: true })}
        ${entityField(hass, "fan", "Ventilator", ["switch", "fan", "input_boolean"], cfg.fan)}
        ${entityField(hass, "water_heater", "Waterverwarming", ["switch", "climate", "input_boolean"], cfg.water_heater)}
        ${entityField(hass, "pumps", "Pompen / filter", ["switch", "input_boolean"], cfg.pumps, { multiple: true })}
        ${field("Hysterese (°C)", NUMBER("hysteresis", cfg.hysteresis ?? 0.5, 0.1))}
        ${field("Pulsduur vernevelaar (s)", NUMBER("mist_seconds", cfg.mist_seconds ?? 10))}
        ${field("Pauze tussen pulsen (min)", NUMBER("mist_pause_minutes", cfg.mist_pause_minutes ?? 30))}
        ${field("Max. pulsen per dag", NUMBER("mist_max_per_day", cfg.mist_max_per_day ?? 6))}
        ${field("Op-/afdimmen (min)", NUMBER("light_ramp_minutes", cfg.light_ramp_minutes ?? 0))}
        ${field("Vaste vernevelmomenten", `<input name="mist_times" value="${esc(cfg.mist_times || "")}" placeholder="08:00, 20:00">`)}
      </div></fieldset>
      <fieldset><legend>${esc(te(hass, "equipment"))}</legend>
        <div data-eq-list>${(enc?.equipment || []).map(equipmentRow).join("")}</div>
        <button type="button" class="ak-btn" data-eq-add>＋ ${esc(te(hass, "add_equipment"))}</button>
      </fieldset>
      ${enc ? `<button type="button" class="ak-btn" data-enc-delete style="color:var(--error-color,#c62828)">${esc(te(hass, "delete"))}</button>` : ""}`;
    wireMulti(body);
    const plantChips = body.querySelector('[data-multi="plants"] .chips');
    if (plantChips) {
      new MutationObserver(() => {
        const care = { ...(cfg.plant_care || {}), ...readCare(body) };
        const plants = [...plantChips.querySelectorAll(".chip")].map((c) => c.dataset.value);
        body.querySelector("[data-care-list]").innerHTML = careRows(plants, care);
      }).observe(plantChips, { childList: true });
    }
    body.querySelector("[data-eq-add]").addEventListener("click", () =>
      body.querySelector("[data-eq-list]").insertAdjacentHTML("beforeend", equipmentRow()));
    body.addEventListener("click", (e) => {
      if (e.target.matches("[data-eq-remove]")) e.target.closest(".ak-eq").remove();
    });
    body.querySelector("[data-enc-delete]")?.addEventListener("click", async () => {
      if (!confirm(te(hass, "confirm_delete"))) return;
      await hass.callWS({ type: "arthropoda/enclosure/delete", enclosure_id: enc.id });
      body.closest("dialog").close();
      body.closest("dialog").remove();
    });
  }, async (body) => {
    const data = readForm(body);
    if (!data.code?.trim()) throw new Error(te(hass, "required_code"));
    const climateKeys = ["temperature_sensors", "humidity_sensor", "water_temperature_sensor", "heater", "mister",
      "lights", "fan", "water_heater", "pumps", "hysteresis", "mist_seconds", "mist_pause_minutes",
      "mist_max_per_day", "light_ramp_minutes", "mist_times"];
    const config = Object.fromEntries(climateKeys.map((k) => [k, data[k]]));
    Object.assign(config, { plants: data.plants || [], light_hours: data.light_hours, plant_climate: data.plant_climate !== false, light_dli: data.light_dli === true,
      plant_care: readCare(body) });
    const equipment = [...body.querySelectorAll(".ak-eq")].map((row) => {
      const get = (k) => row.querySelector(`[data-eq="${k}"]`).value;
      return { name: get("name") || null, interval_days: get("interval_days") ? Number(get("interval_days")) : null,
        serviced_at: get("serviced_at") || null };
    }).filter((x) => x.name || x.interval_days);
    const item = {
      ...(enc ? { id: enc.id, nfc_tag: enc.nfc_tag } : {}),
      code: data.code.trim(), name: data.name || null, type: data.type, status: data.status,
      length_cm: data.length_cm, width_cm: data.width_cm, height_cm: data.height_cm,
      location: data.location || null, material: data.material || null, ventilation: data.ventilation || null,
      acquired_at: data.acquired_at || null, price: data.price, seller: data.seller || null,
      notes: data.notes || null, config, equipment,
    };
    const { id } = await hass.callWS({ type: "arthropoda/enclosure/save", item });
    const wanted = data.residents || [];
    for (const animalId of wanted.filter((x) => !current.includes(x))) {
      await hass.callWS({ type: "arthropoda/enclosure/assign", animal_id: animalId, enclosure_id: id });
    }
    for (const animalId of current.filter((x) => !wanted.includes(x))) {
      await hass.callWS({ type: "arthropoda/enclosure/assign", animal_id: animalId, enclosure_id: null });
    }
    return true;
  });
}

// ------------------------------------------------------------------ NFC ----

export function openNfcDialog(hass, enc) {
  let unsubscribe = null;
  const dialog = openDialog(hass, `${te(hass, "nfc_title")}: ${enc.code}`, (body) => {
    body.innerHTML = `
      <ol style="padding-left:20px;line-height:1.5">
        <li>${esc(te(hass, "nfc_step1"))}</li>
        <li>${esc(te(hass, "nfc_step2"))}</li>
      </ol>
      <p data-nfc-status style="font-weight:500">⏳ ${esc(te(hass, "nfc_waiting"))}</p>
      ${enc.nfc_tag ? `<p style="font-size:.85em">${esc(te(hass, "nfc_current"))}: <code>${esc(enc.nfc_tag)}</code>
        <button type="button" class="ak-btn" data-nfc-unlink>${esc(te(hass, "nfc_unlink"))}</button></p>` : ""}
      <hr style="border:none;border-top:1px solid var(--divider-color,#ddd)">
      <p style="font-size:.85em">${esc(te(hass, "nfc_android"))}</p>
      <p><code style="word-break:break-all">${esc(enc.link)}</code>
        <button type="button" class="ak-btn" data-copy>${esc(te(hass, "copy"))}</button></p>`;
    const status = body.querySelector("[data-nfc-status]");
    hass.connection.subscribeMessage(async (msg) => {
      if (!msg.tag_id) return;
      try {
        await hass.callWS({ type: "arthropoda/enclosure/save", item: { ...enc, nfc_tag: msg.tag_id } });
        status.textContent = `✅ ${te(hass, "nfc_linked")} (${msg.tag_id})`;
        unsubscribe?.();
        unsubscribe = null;
      } catch (err) {
        status.textContent = `⚠ ${err.message}`;
      }
    }, { type: "arthropoda/nfc/listen" }).then((unsub) => { unsubscribe = unsub; });
    body.querySelector("[data-copy]").addEventListener("click", async (e) => {
      try { await navigator.clipboard.writeText(enc.link); e.target.textContent = te(hass, "copied"); } catch { /* geen klembord */ }
    });
    body.querySelector("[data-nfc-unlink]")?.addEventListener("click", async () => {
      await hass.callWS({ type: "arthropoda/enclosure/save", item: { ...enc, nfc_tag: null } });
      status.textContent = "–";
    });
  }, async () => true, te(hass, "close"));
  const stop = () => { unsubscribe?.(); unsubscribe = null; };
  dialog.addEventListener("close", stop);
  new MutationObserver((_, obs) => { if (!dialog.isConnected) { stop(); obs.disconnect(); } })
    .observe(document.body, { childList: true });
}

// -------------------------------------------------------------- etiketten ---

const LABEL_FORMATS = {
  "3x8": { cols: 3, rows: 8, w: 63.5, h: 38.1, top: 15.15, left: 7.2, gapX: 2.5, gapY: 0, name: "A4 3×8 – 63,5 × 38,1 mm" },
  "2x7": { cols: 2, rows: 7, w: 99.1, h: 38.1, top: 15.15, left: 4.65, gapX: 2.5, gapY: 0, name: "A4 2×7 – 99,1 × 38,1 mm" },
  "3x7": { cols: 3, rows: 7, w: 70, h: 42.3, top: 0, left: 0, gapX: 0, gapY: 0, name: "A4 3×7 – 70 × 42,3 mm" },
};

export function openLabelsDialog(hass) {
  const store = getStore(hass);
  const enclosures = store.enclosures || [];
  openDialog(hass, te(hass, "labels"), (body) => {
    body.innerHTML = `
      ${field(te(hass, "label_format"), selectHtml("format", Object.entries(LABEL_FORMATS).map(([k, f]) => [k, f.name]), "3x8", false))}
      <fieldset><legend>${esc(te(hass, "labels_select"))}</legend><div class="ak-animals">
        ${enclosures.map((e) => `<label class="ak-check"><input type="checkbox" data-enc="${e.id}" checked> ${esc(e.code)}${e.name ? ` – ${esc(e.name)}` : ""}</label>`).join("")}
      </div></fieldset>`;
  }, async (body) => {
    const format = LABEL_FORMATS[body.querySelector("[name=format]").value];
    const chosen = enclosures.filter((e) => body.querySelector(`[data-enc="${e.id}"]`)?.checked);
    printLabels(hass, chosen, format);
    return true;
  }, te(hass, "print"));
}

export function labelsHtml(hass, enclosures, format) {
  const store = getStore(hass);
  const qrMm = Math.min(format.h - 6, 32);
  const labels = enclosures.map((e) => {
    const names = (e.residents || []).map((id) => store.animal(id)).filter(Boolean)
      .map((a) => a.species?.scientific_name || a.name);
    return `<div class="label">
      <div class="qr">${qrSvg(e.link, { sizeMm: qrMm })}</div>
      <div class="txt"><div class="code">${esc(e.code)}</div>
        ${e.name ? `<div class="name">${esc(e.name)}</div>` : ""}
        ${names.length ? `<div class="sp">${esc([...new Set(names)].join(", "))}</div>` : ""}
        <div class="hint">${esc(te(hass, "scan_hint"))}</div></div>
    </div>`;
  }).join("");
  return `<!doctype html><html><head><meta charset="utf-8"><title>Etiketten</title><style>
    @page { size: A4; margin: 0; }
    body { margin: 0; font-family: Arial, sans-serif; }
    .sheet { padding: ${format.top}mm 0 0 ${format.left}mm; display: grid;
      grid-template-columns: repeat(${format.cols}, ${format.w}mm); grid-auto-rows: ${format.h}mm;
      column-gap: ${format.gapX}mm; row-gap: ${format.gapY}mm; }
    .label { box-sizing: border-box; padding: 3mm; display: flex; gap: 3mm; align-items: center; overflow: hidden; }
    .qr svg { display: block; }
    .code { font-size: 16pt; font-weight: bold; }
    .name { font-size: 9pt; }
    .sp { font-size: 7pt; font-style: italic; color: #333; }
    .hint { font-size: 6pt; color: #666; margin-top: 1mm; }
    @media screen { .label { outline: 1px dashed #ccc; } }
  </style></head><body><div class="sheet">${labels}</div></body></html>`;
}

function printLabels(hass, enclosures, format) {
  const frame = document.createElement("iframe");
  frame.style.cssText = "position:fixed;right:0;bottom:0;width:0;height:0;border:0";
  document.body.appendChild(frame);
  const doc = frame.contentWindow.document;
  doc.open();
  doc.write(labelsHtml(hass, enclosures, format));
  doc.close();
  setTimeout(() => {
    frame.contentWindow.focus();
    frame.contentWindow.print();
    setTimeout(() => frame.remove(), 60000);
  }, 300);
}

// ----------------------------------------------------------------- ronde ---

const ROUND_KEY = "arthropoda_round";

export function getRound() {
  try { return JSON.parse(localStorage.getItem(ROUND_KEY) || "null"); } catch { return null; }
}

function saveRound(round) {
  try {
    if (round) localStorage.setItem(ROUND_KEY, JSON.stringify(round));
    else localStorage.removeItem(ROUND_KEY);
  } catch { /* geen opslag: ronde werkt dan alleen in deze sessie */ }
}

export function startRound() { saveRound({ started: new Date().toISOString(), visited: {} }); }

export function noteRound(code, action = null) {
  const round = getRound();
  if (!round) return;
  round.visited[code] ||= [];
  if (action) round.visited[code].push(action);
  saveRound(round);
}

export function openRoundSummary(hass) {
  const store = getStore(hass);
  const round = getRound() || { visited: {} };
  const visited = Object.entries(round.visited);
  const open = (store.enclosures || []).filter((e) => !round.visited[e.code])
    .map((e) => ({ e, due: openTasks(store, e).length })).filter((x) => x.due);
  openDialog(hass, te(hass, "round_summary"), (body) => {
    body.innerHTML = `
      <h3 style="margin:4px 0">${esc(te(hass, "visited"))} (${visited.length})</h3>
      ${visited.map(([code, actions]) => `<div>✓ <b>${esc(code)}</b> <span style="color:var(--secondary-text-color)">${esc([...new Set(actions)].join(", "))}</span></div>`).join("") || "–"}
      <h3 style="margin:14px 0 4px">${esc(te(hass, "not_visited_tasks"))}</h3>
      ${open.map(({ e, due }) => `<div>• <b>${esc(e.code)}</b>${e.name ? ` – ${esc(e.name)}` : ""}: ${due} ${esc(te(hass, "tasks"))}</div>`).join("") || esc(te(hass, "nothing_open"))}`;
  }, async () => { saveRound(null); return true; }, te(hass, "finish_round"));
}

// -------------------------------------------------------------- werkscherm ---

/** Open taken van een kast: kasttaken + taken van de bewoners, tot en met vandaag. */
export function openTasks(store, enc) {
  const tasks = (enc.tasks || []).filter((t) => isDueToday(t.due)).map((t) => ({ ...t, target: enc.code }));
  for (const id of enc.residents || []) {
    const a = store.animal(id);
    for (const task of a?.tasks || []) {
      if (isDueToday(task.due)) tasks.push({ ...task, target: a.name });
    }
  }
  return tasks.sort((x, y) => x.due.localeCompare(y.due));
}

export const WORK_CSS = `
  .work { max-width: 720px; margin: 0 auto; }
  .work .whead { display:flex; align-items:center; gap:10px; margin-bottom: 10px; }
  .work .wcode { font-size: 1.9em; font-weight: 600; letter-spacing: .02em; }
  .work .residents { display:flex; flex-wrap:wrap; gap:8px; margin: 8px 0 12px; }
  .work .res { display:flex; align-items:center; gap:8px; padding: 6px 12px 6px 6px; border-radius: 24px;
               border: 2px solid var(--ak-line); background: var(--card-background-color,#fff); cursor:pointer; font: inherit;
               color: var(--primary-text-color); }
  .work .res.on { border-color: var(--ak-accent); background: color-mix(in srgb, var(--ak-accent) 12%, transparent); }
  .work .res img, .work .res .ph { width: 32px; height: 32px; border-radius: 50%; object-fit: cover; background: var(--secondary-background-color); display:inline-flex; align-items:center; justify-content:center; }
  .work .big { display:grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin: 12px 0; }
  .work .big button { font: inherit; font-size: 1.02em; min-height: 76px; border-radius: 16px; border: 1px solid var(--ak-line);
                      background: var(--card-background-color,#fff); color: var(--primary-text-color); cursor: pointer;
                      display:flex; flex-direction:column; align-items:center; justify-content:center; gap: 4px; }
  .work .big button span { font-size: 1.6em; }
  .work .big button.done { border-color: var(--ak-ok); background: color-mix(in srgb, var(--ak-ok) 12%, transparent); }
  .work .task { display:flex; align-items:center; gap: 10px; padding: 8px 0; border-bottom: 1px solid var(--ak-line); }
  .work .task:last-child { border-bottom: none; }
  .work .task button { width: 40px; height: 40px; border-radius: 50%; border: 2px solid var(--ak-ok); background: none;
                       color: var(--ak-ok); font-size: 1.2em; cursor: pointer; }
  .work .roundbar { display:flex; gap:8px; align-items:center; flex-wrap:wrap; padding: 10px 12px; border-radius: 12px;
                    background: color-mix(in srgb, var(--ak-accent) 12%, transparent); margin-bottom: 12px; }
  .work .plants { display:flex; flex-direction:column; gap:6px; margin: 8px 0 4px; }
  .work .plant { display:flex; align-items:center; gap:10px; padding: 6px 10px 6px 6px; border-radius: 14px; text-align:left;
                 border: 2px solid var(--ak-line); background: var(--card-background-color,#fff); cursor:pointer; font: inherit;
                 color: var(--primary-text-color); }
  .work .plant.on { border-color: var(--ak-ok); background: color-mix(in srgb, var(--ak-ok) 10%, transparent); }
  .work .plant img, .work .plant .ph { width: 40px; height: 40px; border-radius: 10px; object-fit: cover; flex: none;
               background: var(--secondary-background-color); display:inline-flex; align-items:center; justify-content:center; }
  .work .plant .bad { color: var(--ak-problem, #c62828); }
  .work .climate { display:flex; gap: 16px; font-size: 1.1em; flex-wrap: wrap; }
  @media (max-width: 420px) { .work .big { grid-template-columns: repeat(2, 1fr); } .work .wcode { font-size: 1.6em; } }
`;

const PLANT_ACTIONS = [
  ["watered", "💧"], ["fertilized", "🧪"], ["pruned", "✂️"], ["harvested", "🧺"],
  ["repotted", "🪴"], ["pest", "🐛"], ["sown", "🌱"], ["note", "📝"],
];

function daysAgo(hass, iso) {
  if (!iso) return te(hass, "never");
  const start = new Date(); start.setHours(0, 0, 0, 0);
  const then = new Date(iso); then.setHours(0, 0, 0, 0);
  const days = Math.round((start - then) / 86400000);
  if (days <= 0) return te(hass, "today");
  if (days === 1) return te(hass, "yesterday");
  return te(hass, "days_ago", { n: days });
}

/** Plantenblok van het werkscherm: planten (aan/uit te vinken) en handelingen. */
export function plantsHtml(hass, enc, selectedPlants) {
  const plants = enc.plants || [];
  if (!plants.length) return "";
  const unit = (role) => (role === "heater" ? " °C" : " %");
  const targets = (enc.actuators || []).filter((a) => a.target).map((a) =>
    `${a.role === "heater" ? "🌡" : "💧"} ${fmtNum(a.target[0])}–${fmtNum(a.target[1])}${unit(a.role)}${a.conflict ? " ⚠" : ""}`);
  return `<div class="card" style="margin-top:12px"><h3>🌿 ${esc(te(hass, "plants_title"))}
      ${enc.plant_cabinet ? `<span class="chip ok" style="margin-left:6px">${esc(te(hass, "steers_plants"))}</span>` : ""}</h3>
    ${enc.plant_cabinet && targets.length ? `<div class="muted small">${esc(te(hass, "target"))}: ${esc([...new Set(targets)].join(" · "))}</div>` : ""}
    ${enc.config?.light_dli && enc.dli ? `<div class="small" style="margin:4px 0"><span class="chip ${enc.dli.reached ? "ok" : ""}">☀ ${esc(te(hass, "dli_label"))}: ${enc.dli.current ?? "–"} / ${enc.dli.target ?? "–"} mol/m²${enc.dli.reached ? ` · ${esc(te(hass, "dli_reached"))}` : ""}</span></div>` : ""}
    <div class="plants">${plants.map((p) => {
      // Problemen van Plant Monitor; anders de afwijkende statussen (bv. moisture: Low).
      const issues = (p.problems || []).length ? p.problems
        : Object.entries(p.statuses || {}).map(([k, v]) => `${k} ${String(v).toLowerCase()}`);
      const bad = p.state === "problem" || issues.length > 0;
      return `<button class="plant ${selectedPlants.has(p.entity_id) ? "on" : ""}" data-plant="${esc(p.entity_id)}">
        ${p.picture ? `<img src="${esc(p.picture)}" alt="">` : `<span class="ph">🌿</span>`}
        <span class="grow"><b>${esc(p.name)}</b>${p.species ? ` <i class="muted small">${esc(p.species)}</i>` : ""}
          <span class="small ${bad ? "bad" : "muted"}" style="display:block">${bad ? `⚠ ${esc(issues.join(", ") || te(hass, "plant_problem"))}` : `✓ ${esc(te(hass, "plant_ok"))}`}
            · ${esc(te(hass, "last_watered"))}: ${esc(daysAgo(hass, p.last?.watered))}</span>
          ${p.moisture != null ? `<span class="small ${p.thresholds?.moisture && p.moisture < p.thresholds.moisture[0] ? "bad" : "muted"}" style="display:block">💧 ${fmtNum(p.moisture, 0)} %${p.thresholds?.moisture ? ` (min ${fmtNum(p.thresholds.moisture[0], 0)})` : ""}${p.dli != null ? ` · ☀ ${fmtNum(p.dli)} mol/m²` : ""}</span>` : ""}</span></button>`;
    }).join("")}</div>
    <div class="big">${PLANT_ACTIONS.map(([type, icon]) =>
      `<button data-pact="${type}"><span>${icon}</span>${esc(te(hass, `p_${type}`))}</button>`).join("")}</div>
  </div>`;
}

const BIG_ACTIONS = [
  ["feeding", "🍽", "fed"], ["misting_manual", "💧", "misted"], ["spot_clean", "🧹", "cleaned"],
  ["water_refill", "🥤", "water"], ["plant_food", "🌿", "plants"], ["substrate_change", "🪨", "substrate"],
];

/** Werkscherm tekenen in `box`; geeft een functie terug die het scherm bijwerkt. */
export function renderWorkScreen(host, box, hass, code, { onEdit, onBack }) {
  const store = getStore(hass);
  let selected = null;
  let selectedPlants = null;
  let doneLocally = new Set();

  const draw = () => {
    const enc = store.enclosure(code);
    if (!store.enclosures) { box.innerHTML = `<div class="empty">…</div>`; return; }
    if (!enc) { box.innerHTML = `<div class="empty">${esc(te(hass, "unknown_enclosure", { code }))}</div>`; return; }
    const residents = (enc.residents || []).map((id) => store.animal(id)).filter(Boolean);
    if (selected === null) selected = new Set(residents.map((a) => a.id));
    if (selectedPlants === null) selectedPlants = new Set((enc.plants || []).map((p) => p.entity_id));
    const round = getRound();
    if (round && !round.visited[enc.code]) noteRound(enc.code);
    const tasks = openTasks(store, enc);
    const r = enc.readings;
    box.innerHTML = `<div class="work">
      ${round ? `<div class="roundbar">🔁 <b>${esc(te(hass, "round"))}</b> · ${esc(te(hass, "round_visited", { n: Object.keys(getRound()?.visited || {}).length }))}
        <span class="grow"></span><button class="ak" data-round-finish>${esc(te(hass, "finish_round"))}</button></div>` : ""}
      <div class="whead">
        <button class="icon" data-back title="${esc(te(hass, "back"))}">←</button>
        <div class="grow"><div class="wcode">${esc(enc.code)}</div>
          <div class="muted">${esc(enc.name || "")}${dims(enc) ? ` · ${esc(dims(enc))}` : ""}${enc.location ? ` · ${esc(enc.location)}` : ""}</div></div>
        <button class="ak" data-edit-enc>⚙</button>
      </div>
      ${r ? `<div class="climate">${r.temperature !== null ? `🌡 ${fmtNum(r.temperature)} °C` : ""}${r.humidity !== null ? `💧 ${fmtNum(r.humidity, 0)} %` : ""}${r.water_temperature !== null ? `🌊 ${fmtNum(r.water_temperature)} °C` : ""}</div>` : ""}
      ${enc.scan?.required && tasks.some((tk) => new Date(tk.due) < new Date(new Date().setHours(0, 0, 0, 0)))
        ? `<div class="chip ${enc.scan.recent ? "ok" : "problem"}" style="margin-top:8px;white-space:normal">${enc.scan.recent ? "📶 " + esc(te(hass, "scan_ok")) : "📶 " + esc(te(hass, "scan_needed"))}</div>` : ""}
      ${enc.too_small_for?.length ? `<div class="chip problem" style="margin-top:8px">⚠ ${esc(te(hass, "too_small"))}: ${esc(enc.too_small_for.join(", "))}</div>` : ""}
      ${residents.length ? `<div class="residents">${residents.map((a) => {
        const p = photoUrl(hass, a);
        return `<button class="res ${selected.has(a.id) ? "on" : ""}" data-res="${esc(a.id)}">
          ${p ? `<img src="${esc(p)}" alt="">` : `<span class="ph">🕷</span>`}<span>${esc(a.name)}${(a.insights || []).some((i) => i.level === "warn")
            ? `<span class="small" style="display:block;color:var(--error-color,#c62828)">${(a.insights || []).filter((i) => i.level === "warn").map((i) => `${INSIGHT_ICON[i.key] || "⚠"} ${esc(insightText(hass, i).split(/[.:]/)[0])}`).join(" · ")}</span>` : ""}</span></button>`;
      }).join("")}</div>
      <div class="big">
        ${BIG_ACTIONS.map(([type, icon, key]) => `<button data-act="${type}" class="${doneLocally.has(type) ? "done" : ""}"><span>${icon}</span>${esc(te(hass, key))}</button>`).join("")}
        <button data-note><span>📝</span>${esc(te(hass, "note"))}</button>
        <button data-photo><span>📷</span>${esc(te(hass, "photo"))}</button>
        <button data-more><span>⋯</span>${esc(te(hass, "more"))}</button>
      </div>
      <input type="file" accept="image/*" capture="environment" data-file hidden>` : (enc.plants || []).length ? "" : `<p class="muted">${esc(te(hass, "no_residents"))}</p>`}
      ${plantsHtml(hass, enc, selectedPlants)}
      ${potsCard(hass, enc)}
      <div class="card"><h3>${esc(te(hass, "tasks_today"))}</h3>
        ${tasks.length ? tasks.map((tk) => `<div class="task"><button data-task="${esc(tk.uid)}" title="✓">✓</button>
          <div class="grow"><b>${esc(tk.plant ? `${taskLabel(hass, tk.kind)}: ${tk.label}` : (tk.label || taskLabel(hass, tk.kind)))}</b><div class="muted small">${esc(tk.target)} · ${esc(dueText(hass, tk.due))}</div></div></div>`).join("")
          : `<div class="muted">${esc(te(hass, "no_tasks_today"))}</div>`}
      </div>
      <div class="card" style="margin-top:12px"><h3>${esc(te(hass, "last_actions"))}</h3><div data-last class="small">…</div></div>
    </div>`;
    loadLast(enc, residents);
  };

  const loadLast = async (enc, residents) => {
    const target = box.querySelector("[data-last]");
    if (!target) return;
    const plants = enc.plants || [];
    if (!residents.length && !plants.length) { target.textContent = "–"; return; }
    try {
      const lists = await Promise.all(residents.slice(0, 6).map((a) =>
        hass.callWS({ type: "arthropoda/journal/list", animal_id: a.id, limit: 5 })));
      const names = Object.fromEntries(residents.map((a) => [a.id, a.name]));
      const rows = lists.flatMap((l) => l.entries).map((en) => ({
        ts: en.timestamp, label: store.label("entry_type", en.type), who: names[en.animal_id] || "" }));
      if (plants.length) {
        const plantNames = Object.fromEntries(plants.map((p) => [p.entity_id, p.name]));
        const { entries } = await hass.callWS({ type: "arthropoda/plant/journal", plants: plants.map((p) => p.entity_id), limit: 8 });
        rows.push(...entries.map((en) => ({ ts: en.ts, label: `🌿 ${te(hass, `p_${en.type}`)}`,
          who: plantNames[en.plant] || en.plant, notes: en.notes })));
      }
      rows.sort((x, y) => y.ts.localeCompare(x.ts));
      target.innerHTML = rows.slice(0, 8).map((r) => `<div style="padding:3px 0">${esc(fmtDate(hass, r.ts))} · <b>${esc(r.label)}</b> · ${esc(r.who)}${r.notes ? ` <span class="muted">– ${esc(r.notes)}</span>` : ""}</div>`).join("") || "–";
    } catch { target.textContent = "–"; }
  };

  const logPlants = async (entryType) => {
    const enc = store.enclosure(code);
    const plants = [...selectedPlants];
    if (!plants.length) { toast(host, te(hass, "no_plants_selected")); return; }
    let notes = null;
    if (entryType === "note" || entryType === "pest") {
      notes = prompt(te(hass, `p_${entryType}`));
      if (entryType === "note" && !notes) return;
    }
    await hass.callWS({ type: "arthropoda/plant/log", plants, entry_type: entryType, enclosure_id: enc.id, notes });
    noteRound(enc.code, te(hass, `p_${entryType}`));
    toast(host, `${te(hass, `p_${entryType}`)} ✓`);
    draw();
  };

  const log = async (entryType, extra = {}) => {
    const enc = store.enclosure(code);
    const ids = [...selected];
    if (!ids.length) { toast(host, te(hass, "no_residents")); return; }
    await hass.callWS({ type: "arthropoda/enclosure/log", enclosure_id: enc.id, entry_type: entryType, animal_ids: ids, ...extra });
    doneLocally.add(entryType);
    noteRound(enc.code, store.label("entry_type", entryType));
    toast(host, `${store.label("entry_type", entryType)} ✓`);
    draw();
  };

  box.onclick = async (e) => {
    const btn = e.target.closest("button");
    if (!btn) return;
    const enc = store.enclosure(code);
    try {
      if (await handlePotClick(host, hass, btn, enc.pots || [], () => noteRound(enc.code, "🥬"))) return;
      if (btn.dataset.plant) {
        selectedPlants.has(btn.dataset.plant) ? selectedPlants.delete(btn.dataset.plant) : selectedPlants.add(btn.dataset.plant);
        draw();
      } else if (btn.dataset.pact) {
        await logPlants(btn.dataset.pact);
      } else if (btn.dataset.res) {
        selected.has(btn.dataset.res) ? selected.delete(btn.dataset.res) : selected.add(btn.dataset.res);
        draw();
      } else if (btn.dataset.act) {
        await log(btn.dataset.act);
      } else if (btn.hasAttribute("data-note")) {
        const text = prompt(te(hass, "note_prompt"));
        if (text) await log("observation", { notes: text });
      } else if (btn.hasAttribute("data-more")) {
        openJournalDialog(hass, [...selected]);
      } else if (btn.hasAttribute("data-photo")) {
        if (selected.size !== 1) { toast(host, te(hass, "choose_one")); return; }
        const input = box.querySelector("[data-file]");
        input.onchange = async () => {
          const file = input.files[0];
          if (!file) return;
          const form = new FormData();
          form.append("file", file, file.name);
          const resp = await hass.fetchWithAuth(`/api/arthropoda/photo/${encodeURIComponent([...selected][0])}`, { method: "POST", body: form });
          toast(host, resp.ok ? `${te(hass, "photo")} ✓` : (await resp.json().catch(() => ({}))).message || "Fout");
        };
        input.click();
      } else if (btn.dataset.task) {
        await hass.callWS({ type: "arthropoda/task/done", uid: btn.dataset.task });
        noteRound(enc.code, "✓");
        toast(host, "✓");
      } else if (btn.hasAttribute("data-edit-enc")) {
        onEdit(enc);
      } else if (btn.hasAttribute("data-back")) {
        onBack();
      } else if (btn.hasAttribute("data-round-finish")) {
        openRoundSummary(hass);
      }
    } catch (err) { toast(host, err.message || String(err)); }
  };

  draw();
  return draw;
}

function taskLabel(hass, kind) {
  const lang = (hass.language || "en").slice(0, 2);
  const nl = { feeding: "Voederen", cleaning: "Schoonmaken", substrate_change: "Substraat vervangen",
    water_change: "Waterwissel", diapause_end: "Uit diapauze halen", equipment: "Onderhoud uitrusting",
    plant_water: "Sproeien", plant_fertilize: "Bemesten", plant_sow: "Zaaien", pot_replace: "Voerbakje vervangen" };
  const en = { feeding: "Feed", cleaning: "Clean", substrate_change: "Change substrate",
    water_change: "Water change", diapause_end: "End diapause", equipment: "Equipment maintenance",
    plant_water: "Water", plant_fertilize: "Fertilize", plant_sow: "Sow", pot_replace: "Replace food pot" };
  return (lang === "nl" ? nl : en)[kind] || kind;
}
