/*
 * Arthropoda Keeper – voedselplanning (tab Voer + blok op de werkschermen).
 *
 * Gewassen (gras, erwten, kool …): zaaien → voerklaar → in een dierenbak → op.
 * Vaste planten (eik, liguster, braam …): in een dierenbak afgrazen → terug
 * naar de plantenkast om te herstellen → weer klaar.
 */
import {
  esc, field, fmtDate, getStore, openDialog, readForm, selectHtml, toast, NUMBER,
} from "./arthropoda-common.js?v=0.14.0";

const TEXTS = {
  nl: {
    title: "Voedselplanning", intro: "Volg elk bakje voedselplanten: zaaien, voerklaar, in een dierenbak en weer vervangen. Stel per plant in of het een gewas of een vaste plant is.",
    crop: "Gewas", perennial: "Vaste plant", not_set: "Nog niet ingesteld", settings: "Instellingen",
    kind: "Soort plant", days_to_ready: "Dagen van zaaien tot voerklaar", sow_every_days: "Zaaien elke … dagen (leeg = alleen bij tekort)",
    days_in_use: "Dagen in de dierenbak (daarna vervangen)", days_to_recover: "Dagen herstel in de plantenkast",
    sow: "Zaaien", add_perennial: "Plant toevoegen", cabinet: "Kast", count: "Aantal bakjes", label: "Naam (optioneel)", notes: "Notitie",
    ready_n: "voerklaar", growing_n: "groeien", in_use_n: "in gebruik", first_ready: "eerste klaar",
    shortfall: "Tekort vanaf {date} – zaai bij!", enough: "Genoeg voer", last_sown: "Laatst gezaaid", never_sown: "Nog nooit gezaaid",
    every: "elke {n} d", no_pots: "Nog geen bakjes.",
    s_growing: "Groeit – klaar {date}", s_ready: "Voerklaar", s_recovering: "Herstelt – klaar {date}",
    s_in_use: "In {loc} sinds {date} · vervangen {due}",
    feed: "→ Voederen", replace: "↻ Vervangen", back: "↩ Terug", done: "✓ Op", failed: "Mislukt",
    move_to: "Naar welke bak?", move_title: "Bakje voederen", other_plants: "Andere planten (nog niet ingesteld)",
    pots_title: "Voerbakjes", moved: "Verplaatst ✓", replaced: "Vervangen ✓", returned: "Terug naar de plantenkast ✓",
    finished: "Bakje afgesloten ✓", sown: "Gezaaid ✓", saved: "Opgeslagen ✓", confirm_failed: "Dit bakje als mislukt markeren?",
    no_cabinet: "Maak eerst een kast aan (type Plantenkast).",
    days_to_germinate: "Dagen tot kiemen (optioneel)", st_sown: "Gezaaid", st_germinated: "Gekiemd", st_ready: "Voerklaar",
    st_recovering: "Herstelt", st_fed: "In dierenbak", st_added: "Toegevoegd", st_back: "Terug", st_done: "Op", st_failed: "Mislukt",
    germinate_expected: "kiemt rond {date}", late: "Nog niet gekiemd?",
    mark_germinated: "🌱 Gekiemd", mark_ready: "✓ Klaar", photo: "📷", photos: "Foto's", timeline: "Tijdlijn",
    photo_added: "Foto toegevoegd ✓", add_photo: "📷 Foto toevoegen", no_photos: "Nog geen foto's.", stage_set: "Fase bijgewerkt ✓",
  },
  en: {
    title: "Food planning", intro: "Track every pot of food plants: sowing, ready to feed, in an animal enclosure and replaced again. Set per plant whether it is a crop or a perennial.",
    crop: "Crop", perennial: "Perennial", not_set: "Not set up yet", settings: "Settings",
    kind: "Plant type", days_to_ready: "Days from sowing to ready", sow_every_days: "Sow every … days (empty = only on shortage)",
    days_in_use: "Days in the animal enclosure (then replace)", days_to_recover: "Days of recovery in the plant cabinet",
    sow: "Sow", add_perennial: "Add plant", cabinet: "Enclosure", count: "Number of pots", label: "Name (optional)", notes: "Note",
    ready_n: "ready", growing_n: "growing", in_use_n: "in use", first_ready: "first ready",
    shortfall: "Shortage from {date} – sow more!", enough: "Enough food", last_sown: "Last sown", never_sown: "Never sown",
    every: "every {n} d", no_pots: "No pots yet.",
    s_growing: "Growing – ready {date}", s_ready: "Ready to feed", s_recovering: "Recovering – ready {date}",
    s_in_use: "In {loc} since {date} · replace {due}",
    feed: "→ Feed", replace: "↻ Replace", back: "↩ Back", done: "✓ Finished", failed: "Failed",
    move_to: "Into which enclosure?", move_title: "Feed pot", other_plants: "Other plants (not set up yet)",
    pots_title: "Food pots", moved: "Moved ✓", replaced: "Replaced ✓", returned: "Back to the plant cabinet ✓",
    finished: "Pot closed ✓", sown: "Sown ✓", saved: "Saved ✓", confirm_failed: "Mark this pot as failed?",
    no_cabinet: "Create an enclosure first (type Plant cabinet).",
    days_to_germinate: "Days to germinate (optional)", st_sown: "Sown", st_germinated: "Germinated", st_ready: "Ready",
    st_recovering: "Recovering", st_fed: "In animal enclosure", st_added: "Added", st_back: "Back", st_done: "Finished", st_failed: "Failed",
    germinate_expected: "germinates around {date}", late: "Not germinated yet?",
    mark_germinated: "🌱 Germinated", mark_ready: "✓ Ready", photo: "📷", photos: "Photos", timeline: "Timeline",
    photo_added: "Photo added ✓", add_photo: "📷 Add photo", no_photos: "No photos yet.", stage_set: "Stage updated ✓",
  },
};

export function tf(hass, key, vars = {}) {
  const lang = (hass.language || "en").slice(0, 2);
  let text = (TEXTS[lang] || TEXTS.en)[key] ?? TEXTS.en[key] ?? key;
  for (const [k, v] of Object.entries(vars)) text = text.replace(`{${k}}`, v);
  return text;
}

export const FOOD_CSS = `
  .food-plant { margin-bottom: 12px; }
  .food-plant h3 { display:flex; align-items:center; gap:8px; margin: 0 0 6px; }
  .food-plant img.pic { width: 36px; height: 36px; border-radius: 50%; object-fit: cover; }
  .pot { display:flex; align-items:center; gap:8px; padding:6px 0; border-top:1px solid var(--ak-line); flex-wrap: wrap; }
  .pot .grow { min-width: 140px; }
  .pot button.ak { padding: 4px 10px; font-size: .9em; }
  .food-stats { display:flex; flex-wrap:wrap; gap:6px; margin: 4px 0 8px; }
`;

const day = (hass, iso) => (iso ? fmtDate(hass, iso) : "–");

function potStatus(hass, pot) {
  if (pot.status === "in_use") {
    return tf(hass, "s_in_use", { loc: pot.location || "?", date: day(hass, pot.status_since), due: day(hass, pot.replace_at) });
  }
  if (pot.ready) return tf(hass, "s_ready");
  const base = tf(hass, pot.status === "recovering" ? "s_recovering" : "s_growing", { date: day(hass, pot.ready_at) });
  if (pot.stage === "germinated") return `${tf(hass, "st_germinated")} · ${base}`;
  if (pot.stage === "sown" && pot.germinate_at) return `${base} · ${tf(hass, "germinate_expected", { date: day(hass, pot.germinate_at) })}`;
  return base;
}

/** Eén bakje met zijn knoppen (gebruikt op de tab Voer en de werkschermen). */
export function potRow(hass, pot, { showPlant = false } = {}) {
  const chip = pot.status === "in_use" ? "" : pot.ready ? "ok" : "";
  const buttons = [];
  if (pot.status === "growing" || pot.status === "recovering") {
    if (pot.stage === "sown") buttons.push(`<button class="ak" data-pot-act="germinated" data-pot="${pot.id}">${esc(tf(hass, "mark_germinated"))}</button>`);
    if (!pot.ready) buttons.push(`<button class="ak" data-pot-act="ready" data-pot="${pot.id}">${esc(tf(hass, "mark_ready"))}</button>`);
    buttons.push(`<button class="ak${pot.ready ? " primary" : ""}" data-pot-act="move" data-pot="${pot.id}">${esc(tf(hass, "feed"))}</button>`);
    if (pot.kind === "crop") buttons.push(`<button class="ak danger" data-pot-act="failed" data-pot="${pot.id}">${esc(tf(hass, "failed"))}</button>`);
  } else if (pot.status === "in_use") {
    buttons.push(`<button class="ak primary" data-pot-act="replace" data-pot="${pot.id}">${esc(tf(hass, "replace"))}</button>`);
    buttons.push(pot.kind === "perennial"
      ? `<button class="ak" data-pot-act="return" data-pot="${pot.id}">${esc(tf(hass, "back"))}</button>`
      : `<button class="ak" data-pot-act="done" data-pot="${pot.id}">${esc(tf(hass, "done"))}</button>`);
  }
  if (pot.status !== "done" && pot.status !== "failed") {
    buttons.push(`<button class="ak" data-pot-act="photo" data-pot="${pot.id}" title="${esc(tf(hass, "photos"))}">${esc(tf(hass, "photo"))}${(pot.photos || []).length ? ` ${pot.photos.length}` : ""}</button>`);
  }
  return `<div class="pot"><div class="grow"><b>${esc(pot.name)}</b>
      <div class="small"><span class="chip ${chip}">${esc(potStatus(hass, pot))}</span>${pot.late_germination ? ` <span class="chip problem">⚠ ${esc(tf(hass, "late"))}</span>` : ""}</div></div>${buttons.join("")}</div>`;
}

/** Blok 'Voerbakjes' op het werkscherm van een kast. */
export function potsCard(hass, enc) {
  const pots = enc.pots || [];
  if (!pots.length) return "";
  return `<div class="card" style="margin-top:12px"><h3>🥬 ${esc(tf(hass, "pots_title"))}</h3>
    ${pots.map((p) => potRow(hass, p, { showPlant: true })).join("")}</div>`;
}

function enclosureOptions(store, exclude = null) {
  return (store.enclosures || []).filter((e) => e.id !== exclude)
    .sort((a, b) => Number(a.type === "plant_cabinet") - Number(b.type === "plant_cabinet") || a.code.localeCompare(b.code))
    .map((e) => [e.id, `${e.code}${e.name ? ` – ${e.name}` : ""}${e.residents?.length ? ` (${e.residents.length} 🦗)` : ""}`]);
}

/**
 * Knop van een bakje afhandelen. Geeft true terug als het een bakjesknop was.
 * `pot` mag ontbreken: dan wordt het bakje in de kasten van de store gezocht.
 */
export async function handlePotClick(host, hass, btn, pots = null, onDone = null) {
  const act = btn.dataset.potAct;
  if (!act) return false;
  const store = getStore(hass);
  const id = Number(btn.dataset.pot);
  const pot = (pots || (store.enclosures || []).flatMap((e) => e.pots || [])).find((p) => p.id === id) || { id };
  const finish = (msg) => { toast(host, msg); onDone?.(); };
  if (act === "move") {
    openDialog(hass, `${tf(hass, "move_title")}: ${pot.name || ""}`, (body) => {
      body.innerHTML = `<div class="ak-grid">${field(tf(hass, "move_to"),
        selectHtml("enclosure_id", enclosureOptions(store, pot.enclosure_id), "", false), true)}</div>`;
    }, async (body) => {
      const { enclosure_id: enc } = readForm(body);
      await hass.callWS({ type: "arthropoda/pot/move", pot_id: id, enclosure_id: Number(enc) });
      finish(tf(hass, "moved"));
      return true;
    });
    return true;
  }
  if (act === "photo") { openPhotoDialog(host, hass, pot, onDone); return true; }
  if (act === "germinated" || act === "ready") {
    try {
      await hass.callWS({ type: "arthropoda/pot/stage", pot_id: id, stage: act });
      finish(tf(hass, "stage_set"));
    } catch (err) { toast(host, err.message || String(err)); }
    return true;
  }
  if (act === "failed" && !confirm(tf(hass, "confirm_failed"))) return true;
  const calls = {
    replace: [{ type: "arthropoda/pot/replace", pot_id: id }, "replaced"],
    return: [{ type: "arthropoda/pot/return", pot_id: id }, "returned"],
    done: [{ type: "arthropoda/pot/finish", pot_id: id, status: "done" }, "finished"],
    failed: [{ type: "arthropoda/pot/finish", pot_id: id, status: "failed" }, "finished"],
  };
  const [msg, label] = calls[act];
  try {
    await hass.callWS(msg);
    finish(tf(hass, label));
  } catch (err) { toast(host, err.message || String(err)); }
  return true;
}

const STAGE_ICON = { sown: "🟤", germinated: "🌱", ready: "🥬", recovering: "🌿", added: "🌿", fed: "🦗", back: "↩", done: "✓", failed: "✕" };

/** Fototijdlijn van een bakje, met knop om een foto toe te voegen (camera op de gsm). */
function openPhotoDialog(host, hass, pot, onDone) {
  const urls = [];
  openDialog(hass, `${tf(hass, "timeline")}: ${pot.name}`, async (body) => {
    const photos = pot.photos || [];
    const steps = Object.entries(pot.stages || {}).sort((a, b) => a[1].localeCompare(b[1]));
    body.innerHTML = `<div class="small muted" style="margin-bottom:8px">${steps
        .map(([k, ts]) => `${STAGE_ICON[k] || "•"} ${esc(tf(hass, `st_${k}`))} ${esc(day(hass, ts))}`).join(" → ")}</div>
      <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(120px,1fr));gap:8px">
        ${photos.length ? photos.map((ph, i) => `<figure style="margin:0"><img data-n="${i}" alt="" style="width:100%;aspect-ratio:1;object-fit:cover;border-radius:8px;background:#eee">
          <figcaption class="small muted">${STAGE_ICON[ph.stage] || ""} ${esc(day(hass, ph.ts))}</figcaption></figure>`).join("")
          : `<div class="muted">${esc(tf(hass, "no_photos"))}</div>`}</div>
      <input type="file" accept="image/*" capture="environment" data-file hidden>`;
    // Afbeeldingen ophalen met aanmelding (een img-tag kan geen token meesturen).
    for (const img of body.querySelectorAll("img[data-n]")) {
      try {
        const resp = await hass.fetchWithAuth(`/api/arthropoda/pot_photo/${pot.id}?n=${img.dataset.n}`);
        if (resp.ok) { const url = URL.createObjectURL(await resp.blob()); urls.push(url); img.src = url; }
      } catch { /* foto ontbreekt */ }
    }
  }, async (body) => {
    const input = body.querySelector("[data-file]");
    const file = await new Promise((resolve) => {
      input.onchange = () => resolve(input.files[0] || null);
      input.click();
    });
    if (!file) return false;
    const form = new FormData();
    form.append("file", file, file.name);
    const resp = await hass.fetchWithAuth(`/api/arthropoda/pot_photo/${pot.id}`, { method: "POST", body: form });
    if (!resp.ok) throw new Error((await resp.json().catch(() => ({}))).message || "Upload mislukt");
    urls.forEach((u) => URL.revokeObjectURL(u));
    toast(host, tf(hass, "photo_added"));
    onDone?.();
    return true;
  }, tf(hass, "add_photo"));
}

function openProfileDialog(hass, plant, onDone) {
  const p = plant.profile || { kind: "crop" };
  const s = plant.settings || {};
  openDialog(hass, `${tf(hass, "settings")}: ${plant.name}`, (body) => {
    body.innerHTML = `<div class="ak-grid">
      ${field(tf(hass, "kind"), selectHtml("kind", [["crop", tf(hass, "crop")], ["perennial", tf(hass, "perennial")]], p.kind, false), true)}
      <div data-only="crop" style="display:contents">
        ${field(tf(hass, "days_to_ready"), NUMBER("days_to_ready", p.days_to_ready ?? s.days_to_ready, 1))}
        ${field(tf(hass, "sow_every_days"), NUMBER("sow_every_days", p.sow_every_days, 1))}
        ${field(tf(hass, "days_to_germinate"), NUMBER("days_to_germinate", p.days_to_germinate, 1))}
      </div>
      ${field(tf(hass, "days_in_use"), NUMBER("days_in_use", p.days_in_use ?? s.days_in_use, 1))}
      <div data-only="perennial" style="display:contents">
        ${field(tf(hass, "days_to_recover"), NUMBER("days_to_recover", p.days_to_recover ?? s.days_to_recover ?? 28, 1))}
      </div></div>`;
    const kind = body.querySelector('[name="kind"]');
    const sync = () => body.querySelectorAll("[data-only]").forEach((el) => {
      el.style.display = el.dataset.only === kind.value ? "contents" : "none";
    });
    kind.addEventListener("change", sync);
    sync();
  }, async (body) => {
    const d = readForm(body);
    const crop = d.kind === "crop";
    await hass.callWS({
      type: "arthropoda/food/profile/save", plant: plant.entity_id, kind: d.kind,
      days_in_use: d.days_in_use,
      days_to_ready: crop ? d.days_to_ready : null, sow_every_days: crop ? d.sow_every_days : null,
      days_to_germinate: crop ? d.days_to_germinate : null,
      days_to_recover: crop ? null : d.days_to_recover,
    });
    onDone?.();
    return true;
  });
}

function openSowDialog(hass, plant, onDone, host) {
  const store = getStore(hass);
  const options = (store.enclosures || [])
    .sort((a, b) => Number(b.type === "plant_cabinet") - Number(a.type === "plant_cabinet") || a.code.localeCompare(b.code))
    .map((e) => [e.id, `${e.code}${e.name ? ` – ${e.name}` : ""}`]);
  if (!options.length) { toast(host, tf(hass, "no_cabinet")); return; }
  const home = (store.enclosures || []).find((e) => e.code === plant.home)?.id ?? options[0][0];
  const perennial = plant.profile?.kind === "perennial";
  openDialog(hass, `${tf(hass, perennial ? "add_perennial" : "sow")}: ${plant.name}`, (body) => {
    body.innerHTML = `<div class="ak-grid">
      ${field(tf(hass, "cabinet"), selectHtml("enclosure_id", options, home, false))}
      ${field(tf(hass, "count"), NUMBER("count", 1, 1))}
      ${field(tf(hass, "label"), `<input name="label" placeholder="${esc(plant.name)}">`)}
      ${field(tf(hass, "notes"), `<input name="notes">`)}
    </div>`;
  }, async (body) => {
    const d = readForm(body);
    await hass.callWS({
      type: "arthropoda/food/sow", plant: plant.entity_id, enclosure_id: Number(d.enclosure_id),
      count: Math.max(1, Number(d.count) || 1), label: d.label || null, notes: d.notes || null,
    });
    toast(host, tf(hass, "sown"));
    onDone?.();
    return true;
  });
}

function plantCard(hass, plant, pots) {
  const fc = plant.forecast || {};
  const kind = plant.profile?.kind;
  const stats = plant.profile || pots.length ? `<div class="food-stats">
      <span class="chip ok">✅ ${fc.ready ?? 0} ${esc(tf(hass, "ready_n"))}</span>
      <span class="chip">🌱 ${fc.growing ?? 0} ${esc(tf(hass, "growing_n"))}${fc.next_ready ? ` · ${esc(tf(hass, "first_ready"))} ${esc(day(hass, fc.next_ready))}` : ""}</span>
      <span class="chip">🦗 ${fc.in_use ?? 0} ${esc(tf(hass, "in_use_n"))}</span>
      ${fc.shortfall ? `<span class="chip problem">⚠ ${esc(tf(hass, "shortfall", { date: day(hass, fc.shortfall) }))}</span>`
        : fc.in_use ? `<span class="chip ok">${esc(tf(hass, "enough"))}</span>` : ""}
    </div>` : "";
  const sown = kind === "crop" ? `<div class="muted small">${plant.last_sown
    ? `${esc(tf(hass, "last_sown"))}: ${esc(day(hass, plant.last_sown))}` : esc(tf(hass, "never_sown"))}${plant.profile?.sow_every_days
    ? ` · ${esc(tf(hass, "every", { n: plant.profile.sow_every_days }))}` : ""}</div>` : "";
  return `<div class="card food-plant" data-plant="${esc(plant.entity_id)}">
    <h3>${plant.picture ? `<img class="pic" src="${esc(plant.picture)}" alt="">` : "🌱"} <span class="grow">${esc(plant.name)}</span>
      <span class="chip">${esc(kind ? tf(hass, kind) : tf(hass, "not_set"))}</span>
      <button class="icon" data-food-settings title="${esc(tf(hass, "settings"))}">⚙</button></h3>
    ${stats}${sown}
    <div class="row wrap" style="margin:8px 0">
      <button class="ak primary" data-food-sow>${esc(tf(hass, kind === "perennial" ? "add_perennial" : "sow"))}</button></div>
    ${pots.map((p) => potRow(hass, p)).join("") || `<div class="muted small">${esc(tf(hass, "no_pots"))}</div>`}
  </div>`;
}

/** Tab Voer. Geeft een functie terug die de gegevens opnieuw laadt. */
export function renderFoodView(host, box, hass) {
  let data = null;
  const load = async () => {
    try { data = await hass.callWS({ type: "arthropoda/food/overview" }); } catch (err) { toast(host, err.message || String(err)); return; }
    draw();
  };
  const draw = () => {
    if (!data) { box.innerHTML = `<div class="card">…</div>`; return; }
    const active = data.plants.filter((p) => p.profile || data.pots.some((x) => x.plant === p.entity_id));
    const other = data.plants.filter((p) => !active.includes(p));
    box.innerHTML = `<div class="card" style="margin-bottom:12px"><h3>🥬 ${esc(tf(hass, "title"))}</h3>
        <div class="muted small">${esc(tf(hass, "intro"))}</div></div>
      ${active.map((p) => plantCard(hass, p, data.pots.filter((x) => x.plant === p.entity_id))).join("")}
      ${other.length ? `<div class="card"><h3>${esc(tf(hass, "other_plants"))}</h3>
        ${other.map((p) => `<div class="pot" data-plant="${esc(p.entity_id)}"><span class="grow">${esc(p.name)}</span>
          <button class="ak" data-food-settings>⚙ ${esc(tf(hass, "settings"))}</button></div>`).join("")}</div>` : ""}`;
  };
  box.onclick = async (e) => {
    const btn = e.target.closest("button");
    if (!btn || !data) return;
    if (await handlePotClick(host, hass, btn, data.pots, load)) return;
    const plant = data.plants.find((p) => p.entity_id === btn.closest("[data-plant]")?.dataset.plant);
    if (!plant) return;
    if (btn.hasAttribute("data-food-settings")) openProfileDialog(hass, plant, () => { toast(host, tf(hass, "saved")); load(); });
    else if (btn.hasAttribute("data-food-sow")) openSowDialog(hass, plant, load, host);
  };
  draw();
  load();
  return load;
}
