# Arthropoda Keeper: ontwerp van de Home Assistant-integratie

*Versie 0.1 (concept), 6 november 2026*

Een custom integratie voor Home Assistant om insecten en andere geleedpotigen te houden: alle exotische en inheemse soorten, ook waterinsecten. De opzet lijkt op de plant monitor (één apparaat per dier of kolonie, met statussensoren en grenswaarden) en wordt uitgebreid met een soortendatabase, een dagboek, actieve klimaatsturing, kweek en voorraadbeheer.

- **Domein:** `arthropoda`
- **Distributie:** HACS-compatibele GitHub-repo (kan privé blijven)
- **Talen:** Nederlands en Engels (`translations/nl.json`, `en.json`)

---

## 1. Gemaakte keuzes (uit de vragenronde)

| Onderwerp | Keuze |
|---|---|
| Diergroepen | Alle arthropoda: spinnen, schorpioenen, bidsprinkhanen, phasmiden, kolonies (isopoden, roaches, miljoenpoten), kevers, mieren, waterinsecten, inheems én exotisch |
| Centrale eenheid | **Per dier of kolonie** één HA-apparaat (zoals de plant monitor) |
| Klimaat | De integratie **stuurt zelf** en geeft alarmen |
| Gedeelde behuizing | **Combineren:** dieren delen sensoren en actuatoren; het doelbereik is de overlap van hun caresheets, met een waarschuwing als er geen overlap is |
| Caresheets | AI-extractie uit PDF/URL (Claude via AI Task), gestructureerd YAML-bestand, handmatig in de UI |
| Interface | Eigen **zijbalkpaneel** + **dashboardkaart** per dier |
| Opvolging | Takenlijst, kalender, meldingen, tellers |
| Foto's | Profielfoto per dier + automatische soortfoto (iNaturalist, met licentievermelding) |
| Actuatoren | Verwarming, verneveling/beregening, verlichting, ventilatie, waterapparatuur |
| Extra modules | Kweek & stamboom, voedseldieren-voorraad, groei & metingen, herkomst & documenten |

---

## 2. Architectuur

```
┌──────────────────────── Home Assistant ────────────────────────┐
│                                                                │
│  Config entry "Collectie" (1×)                                 │
│   ├─ Database (SQLite, /config/arthropoda/arthropoda.db)       │
│   ├─ Soortendatabase + caresheet-import (YAML / AI Task)       │
│   ├─ Klimaatregelaar (per actuator, combineert dieren)         │
│   ├─ Planner (taken, kalender, meldingen)                      │
│   ├─ WebSocket-API  ─────────────► Zijbalkpaneel (Lit)         │
│   ├─ Acties (services) ──────────► Dashboardkaart (Lit)        │
│   ├─ todo.arthropoda_onderhoud                                 │
│   └─ calendar.arthropoda                                       │
│                                                                │
│  Subentry "Dier/kolonie" (n×) ─► HA-apparaat met entiteiten    │
│                                                                │
│  Bestaande HA-entiteiten (Zigbee, ESPHome, Shelly, ...):       │
│   sensoren (temp, RV, watertemp, ...) ──► lezen                │
│   schakelaars/lampen/climate ◄────────── sturen                │
└────────────────────────────────────────────────────────────────┘
```

**Waarom één hoofd-entry met subentries?** Home Assistant ondersteunt sinds 2025 *config subentries*. Eén hoofdentry beheert de gedeelde zaken (database, paneel, regelaar, kalender, takenlijst). Elk dier of elke kolonie is een subentry, en dus een eigen apparaat in **Instellingen → Apparaten**, net als bij de plant monitor. Toevoegen kan via de standaard HA-dialoog of via het paneel.

**Klimaatgroepen zonder terrarium-apparaat.** Je koos voor "alleen per dier". Intern groepeert de regelaar dieren automatisch zodra ze een actuator delen (bv. dezelfde `switch.warmtemat_rek_2`). Zo'n groep is geen apparaat, maar wordt wel getoond in het paneel ("Klimaatgroep: warmtemat rek 2 → 3 dieren, doelbereik 24–26 °C").

**Opslag: SQLite in plaats van `.storage`-JSON.** Dagboek, metingen, stamboom en voorraad groeien snel en moeten bevraagd kunnen worden ("alle vervellingen van dier X", "nakomelingen van koppeling Y"). SQLite zit in de Python-standaardbibliotheek en heeft dus geen extra afhankelijkheden. Het bestand staat onder `/config`, waardoor het **automatisch meegaat in HA-back-ups**. Bestanden (foto's, PDF's, documenten) staan in `/config/arthropoda/files/`.

---

## 3. Datamodel

```
taxon ──< species ──< care_profile (per levensfase × seizoen)
             │
             └──< animal (dier of kolonie) >── animal (ouders, via pairing)
                    │
                    ├──< journal_entry ──< attachment
                    ├──< measurement
                    ├──< schedule (terugkerende taken)
                    ├──< document
                    ├──  climate_binding (welke HA-entiteiten)
                    └──< pairing ──< brood (eicocon/ootheek/legsel)

feeder_stock (voedseldieren; kan zelf naar een animal-kolonie verwijzen)
```

### 3.1 `species`: soortendatabase

| Veld | Voorbeeld |
|---|---|
| `scientific_name` | *Brachypelma hamorii* |
| `common_names` | {nl: "Mexicaanse roodknie", en: "Mexican redknee"} |
| `taxonomy` | klasse, orde, familie (Arachnida › Araneae › Theraphosidae) |
| `group` | `tarantula`, `scorpion`, `mantis`, `phasmid`, `isopod`, `roach`, `myriapod`, `beetle`, `ant`, `aquatic`, `other`. Dit bepaalt welke velden en dagboekacties relevant zijn |
| `development` | `hemimetabolous` (nimfen) / `holometabolous` (larve → pop) / `ametabolous` / `molting_adult` (vervelt ook als adult, bv. vogelspinnen) |
| `habitat` | `terrestrial`, `arboreal`, `fossorial`, `semi_aquatic`, `aquatic` |
| `temperament`, `venom`, `urticating_hairs` | veiligheidsinfo |
| `lifespan` | per geslacht (♀ 20–30 j, ♂ 5–7 j) |
| `adult_size` | lichaamslengte / spanwijdte (mm) |
| `diet` | voedseltypes, prooigrootte t.o.v. lichaam |
| `enclosure` | minimale afmetingen, substraat, diepte, inrichting, waterbak |
| `legal` | CITES-bijlage, invasieve exoot (EU-lijst), beschermd inheems |
| `photo` | referentiefoto + auteur, licentie, bron-URL |
| `source` | herkomst van de gegevens (caresheet-URL/PDF, "handmatig", "AI-extractie op datum X") |

### 3.2 `care_profile`: klimaat- en verzorgingswaarden

Eén soort kan meerdere profielen hebben, per **levensfase** (ei, L1–Lx, juveniel, subadult, adult, larve, pop) en per **seizoen** (`normal`, `winter`/`diapause`, `breeding`).

| Veld | Uitleg |
|---|---|
| `temp_day_min/max`, `temp_night_min/max` | °C |
| `temp_hotspot_max` | optioneel |
| `humidity_min/max` | % RV |
| `substrate_moisture` | `dry`, `slightly_moist`, `moist`, `wet` (ook als je geen sensor hebt) |
| `light_hours`, `uv` | daglengte, UV ja/nee |
| `misting` | frequentie (bv. 2×/week), voorkeursmoment |
| `ventilation` | `low`/`medium`/`high` |
| `water_temp_min/max`, `ph_min/max`, `gh`, `kh`, `water_change_interval` | waterinsecten |
| `feeding_interval_days` | per fase (L2: 3 dagen, adult: 14 dagen) |
| `cleaning_interval_days`, `substrate_change_interval_days` | |
| `months` | bij seizoensprofielen: in welke maanden (bv. diapauze nov–feb) |

### 3.3 `animal`: dier of kolonie (= HA-apparaat)

| Veld | Uitleg |
|---|---|
| `name`, `species_id`, `kind` | `individual` / `colony` |
| `sex` | ♀ / ♂ / onbekend / *mogelijk* ♀ (bevestigd via exuvia: ja/nee) |
| `stage`, `stage_number` | bv. nimf L4, of "vervelling 7" |
| `count`, `count_estimated` | voor kolonies (geschat aantal + laatste telling) |
| `born_at`, `acquired_at`, `origin` | `bred` (eigen kweek, met ouders), `bought`, `wild_caught` (inheems: vindplaats en vergunning), `gift` |
| `seller`, `price`, `documents` | herkomst |
| `status` | `active`, `diapause`, `premolt`, `deceased`, `sold`, `released` |
| `climate_binding` | sensor- en actuator-entiteiten (zie 5) |
| `profile_photo` | pad + datum |

### 3.4 `journal_entry`: dagboek

Elke regel heeft: `animal_id` (of meerdere: één schoonmaak voor een heel rek), `type`, `timestamp`, `notes`, `data` (type-specifieke velden als JSON) en optionele bijlagen.

**Standaard actietypes** (uitbreidbaar met eigen types):

| Categorie | Types en hun velden |
|---|---|
| **Voeding** | `feeding` (prooi, aantal, grootte, geaccepteerd/geweigerd/deels, voedseldier-voorraad −n) · `feeding_refused` · `water_refill` · `remove_leftovers` · `plant_food` (bramenblad, eik, … voor phasmiden/isopoden) · `supplement` (kalk, visvoer, ...) |
| **Hygiëne** | `spot_clean` · `full_clean` · `substrate_change` (type, diepte) · `substrate_moisten` · `mold_mites_check` (gevonden: schimmel, mijten, fruitvliegjes, nematoden) |
| **Klimaat** | `misting_manual` · `climate_adjust` · `water_change` (%, watertemperatuur) · `water_test` (pH, GH, KH, NO₂, NO₃) · `filter_clean` |
| **Ontwikkeling** | `premolt_observed` · `molt` (stadium voor/na, compleet/problemen, exuvia bewaard, geslacht bepaald) · `molt_problem` · `pupation` · `eclosion` (uit pop/adult) · `stage_change` · `diapause_start/end` |
| **Kweek** | `pairing` (partner, geslaagd/kannibalisme/geen interesse) · `egg_sac` / `ootheca` / `egg_laying` (aantal, datum) · `brood_pulled` (eicocon uit, incubatie) · `hatch` (aantal) · `split_colony` · `offspring_registered` (maakt nieuwe dieren of kolonies aan) |
| **Metingen** | `measurement` (lichaamslengte, spanwijdte, gewicht, stadium) · `count` (koloniegrootte) |
| **Gezondheid** | `observation` (gedrag, eten in de schuilplaats, gesponnen web) · `health_issue` (letsel, uitdroging, parasieten) · `treatment` · `death` (oorzaak) |
| **Verplaatsing** | `rehouse` (nieuwe behuizing, nieuwe klimaat-entiteiten) · `escape` / `recaptured` |
| **Administratie** | `acquired` · `sold` / `given_away` · `released` (inheems) · `document_added` |

Elke actie kan **gevolgen** hebben die de integratie automatisch verwerkt:
- `feeding` → teller "dagen sinds voedering" op 0, voorraad verminderen, volgende voedertaak inplannen.
- `molt` → stadium +1, teller vervellingen +1, premolt-status uit, **voederpauze** instellen (instelbaar, bv. 7 dagen na de vervelling geen voederherinnering).
- `premolt_observed` → voederherinneringen gepauzeerd.
- `egg_sac`/`ootheca` → kalendergebeurtenis "verwachte uitkomst" (incubatieduur uit de caresheet).
- `diapause_start` → klimaatprofiel schakelt naar het winterprofiel.
- `death` / `sold` → apparaat gearchiveerd (de geschiedenis blijft bewaard, de entiteiten worden uitgeschakeld).

### 3.5 Overige tabellen

- **`measurement`**: type (lengte, spanwijdte, gewicht, aantal), waarde, eenheid, datum. Wordt ook als HA-sensor met `state_class: measurement` gepubliceerd, zodat de standaard geschiedenisgrafieken werken.
- **`pairing`** / **`brood`**: ♀, ♂ (of kolonie), datum, resultaat; legsel, verwachte en werkelijke uitkomst, aantal jongen → gekoppeld aan nieuwe `animal`-records. Zo ontstaat de **stamboom** (ouders ↔ nakomelingen, met generaties F1, F2, ...).
- **`feeder_stock`**: voedseldiersoort (krekels, Dubia, Shelfordella, fruitvliegjes, meelwormen, ...), maat, aantal, minimum. Een stock kan verwijzen naar een **eigen voederkolonie** (een `animal` met `kind: colony`), waarvan het geschatte aantal dan daalt bij elke voedering.
- **`document`**: aankoopbewijs, CITES-certificaat, vergunning, kwekersverklaring: bestand + type + geldigheidsdatum.
- **`schedule`**: terugkerende taken per dier (voederen, sproeien, schoonmaken, substraat verversen, waterwissel). Standaard afgeleid uit het actieve care_profile, per dier aanpasbaar.

---

## 4. Entiteiten per dier/kolonie

*Gebaseerd op het patroon van de plant monitor, uitgebreid.*

| Platform | Entiteit | Toelichting |
|---|---|---|
| `sensor` | Temperatuur, Luchtvochtigheid, Watertemperatuur, pH, ... | Spiegelt de gekoppelde bronsensor, zodat het dier één samenhangend apparaat is (zoals bij de plant monitor) |
| `sensor` | **Status** | `ok` / `probleem` + attribuut met de oorzaken (`temperatuur_hoog`, `voederen_achterstallig`, `sensor_onbereikbaar`) |
| `sensor` | Doeltemperatuur, Doel-RV (min/max) | Actief profiel (dag/nacht, seizoen, gecombineerd in de klimaatgroep) |
| `sensor` | Stadium | bv. "L5", "adult ♀" |
| `sensor` | Dagen sinds voedering / vervelling / schoonmaak / waterwissel | Plus `last_*`-tijdstempels als attributen |
| `sensor` | Aantal vervellingen, Koloniegrootte, Lengte, Gewicht | Grafiekbaar |
| `sensor` | Volgende taak | Tijdstempel + type |
| `binary_sensor` | Probleem, Premolt, Klimaat buiten bereik, Voederen achterstallig | Bruikbaar in eigen automatiseringen |
| `switch` | **Klimaatsturing actief** | Uit = alleen monitoren (handig bij onderhoud) |
| `select` | **Seizoensprofiel** | `automatisch` / `normaal` / `diapauze` / `kweek` |
| `button` | Gevoederd, Gesproeid, Spot-clean | Snelle dagboekregel met één klik (standaardwaarden) |
| `image` | Profielfoto, Soortfoto | Soortfoto met de licentie en auteur als attributen |

Op het niveau van de hoofdentry: `todo.arthropoda_onderhoud`, `calendar.arthropoda` en een `sensor` met het aantal dieren met een probleem.

---

## 5. Klimaatsturing

### 5.1 Koppeling per dier

In de configuratie van een dier kies je (alle velden optioneel):

- **Sensoren:** temperatuur (meerdere toegestaan: warme en koele zijde), luchtvochtigheid, watertemperatuur, pH/EC, substraatvocht.
- **Actuatoren:**
  - verwarming: `switch`, `light` (dimbaar = proportioneel) of `climate`
  - vernevelaar/beregening: `switch` of `script`
  - verlichting: `switch` of `light`
  - ventilator: `switch` of `fan`
  - waterverwarmer, pomp, filter, luchtpomp: `switch`/`climate`

### 5.2 Regellogica (per actuator)

1. **Doelbereik bepalen:** het actieve care_profile van elk gekoppeld dier, afhankelijk van dag/nacht (lichtschema of zon), seizoen (maanden of diapauze in het dagboek) en levensfase.
2. **Combineren:** voor dieren die dezelfde actuator delen, wordt de doorsnede van hun bereiken genomen. Is er geen overlap, dan volgt een **waarschuwing** (melding + reparatiemelding in HA) en wordt het gemiddelde van de bereiken gebruikt.
3. **Regelen:**
   - *Verwarming:* thermostaatlogica met hysterese (zoals de *generic thermostat* van HA), minimale aan/uit-tijd, en proportioneel bij dimbare verwarming.
   - *Verneveling:* een puls van x s wanneer de RV onder het minimum zakt, met een minimale pauze tussen pulsen en een maximum per dag. Daarnaast vaste momenten uit de caresheet (bv. 's avonds sproeien).
   - *Verlichting:* daglengte per seizoen, optioneel geleidelijk dimmen (zonsopgang/-ondergang), optioneel gekoppeld aan echte zonsopgang/-ondergang.
   - *Ventilatie:* aan bij te hoge RV of temperatuur, of interval-gestuurd.
   - *Water:* waterverwarmer zoals verwarming; pomp/filter/luchtpomp continu of op schema, met een "onderhoudsmodus"-knop (pomp tijdelijk uit tijdens een waterwissel).
4. **Veiligheid (altijd actief, ook bij een fout in een profiel):**
   - absolute maximumtemperatuur per dier → verwarming direct uit + kritieke melding;
   - sensor onbereikbaar of verouderd (> x min geen update) → verwarming in een veilige stand (uit, of een ingesteld duty-cycle) + melding;
   - maximale aaneengesloten aan-tijd per actuator;
   - na een herstart van HA eerst de sensoren lezen, pas dan sturen.

### 5.3 Alarmen

Grenswaarden komen uit het profiel, met een instelbare **vertraging** (bv. 15 min buiten bereik voor een melding) om valse alarmen bij het openen van de deur te vermijden. Meldingen gaan naar een of meer gekozen `notify`-doelen, met prioriteit (kritiek: oververhitting, ontsnapping; normaal: onderhoud).

---

## 6. Caresheets importeren

Drie wegen, die allemaal hetzelfde **canonieke YAML-formaat** opleveren. Je kijkt het resultaat altijd na in het paneel voor het wordt opgeslagen.

### 6.1 Gestructureerd bestand (YAML)

```yaml
# arthropoda caresheet v1
species:
  scientific_name: Brachypelma hamorii
  common_names: {nl: Mexicaanse roodknie, en: Mexican redknee}
  group: tarantula
  development: molting_adult
  habitat: terrestrial
  lifespan: {female_years: [20, 30], male_years: [5, 7]}
  adult_size: {legspan_mm: [130, 150]}
  urticating_hairs: true
  legal: {cites: II}
  diet: {prey: [cricket, roach, locust], prey_size: "≤ lichaamslengte"}
  enclosure: {substrate: "turf/kokos", depth_cm: 10, water_dish: true}
care_profiles:
  - stage: juvenile
    temp_day: [24, 27]
    temp_night: [20, 23]
    humidity: [60, 70]
    substrate_moisture: slightly_moist
    feeding_interval_days: 5
  - stage: adult
    temp_day: [22, 26]
    temp_night: [18, 22]
    humidity: [55, 65]
    feeding_interval_days: 14
  - season: winter
    months: [12, 1, 2]
    temp_day: [18, 22]
    feeding_interval_days: 28
source: "https://voorbeeld.be/caresheet.pdf"
```

Importeren kan per bestand of als map met meerdere soorten (eigen database delen en uitwisselen). Elke soort kan ook weer naar dit formaat **geëxporteerd** worden.

### 6.2 PDF/webpagina via AI (Claude)

1. In het paneel: PDF uploaden of een URL plakken.
2. De integratie roept de HA-actie `ai_task.generate_data` aan met je Claude-entiteit, een vaste instructie en een **gestructureerd uitvoerschema** dat overeenkomt met het YAML hierboven. PDF's gaan mee als bijlage; bij een URL haalt de integratie de pagina op en geeft de leesbare tekst door.
3. Het resultaat verschijnt als **voorstel** naast de bron, velden die de AI niet vond blijven leeg (en worden niet gegokt), en onzekere waarden worden gemarkeerd.
4. Na bevestiging volgen opslag + bronvermelding ("AI-extractie uit X, datum Y, nagekeken").

*Technische noot: bijlagen bij AI Task en de Claude-ondersteuning daarvoor zitten in recente HA-versies. De exacte minimale versie verifieer ik tijdens het bouwen, en ik neem ze op in `hacs.json`.*

### 6.3 Handmatig

Een formulier in het paneel met dezelfde velden, gegroepeerd per tabblad (algemeen, klimaat per fase, voeding, behuizing, wettelijk).

### 6.4 Soortfoto

Bij het aanmaken van een soort zoekt de integratie de wetenschappelijke naam op via de **iNaturalist-API** en stelt ze foto's voor met een Creative Commons-licentie. De auteur, licentie en link worden bewaard en getoond. Je kunt ook een eigen foto kiezen.

---

## 7. Opvolging

- **Takenlijst** (`todo.arthropoda_onderhoud`): taken worden aangemaakt wanneer ze vervallen ("Voederen: Rosie (B. hamorii)"). **Afvinken = dagboekregel** met de standaardwaarden; voor details open je de regel in het paneel.
- **Kalender** (`calendar.arthropoda`): geplande taken, uitgevoerde handelingen (uit het dagboek), verwachte vervelling (geschat op basis van eerdere intervallen), verwachte uitkomst van eicocons/ootheken, vervaldatum van documenten.
- **Meldingen:** klimaatalarm, achterstallige taken (dagelijks verzamelbericht op een gekozen uur in plaats van losse berichten), lage voorraad aan voedseldieren, uitkomstdatum nadert.
- **Tellers:** zie de sensoren in deel 4.

Intelligente uitzonderingen: geen voederherinnering tijdens premolt, kort na een vervelling of in diapauze.

---

## 8. Interface

### 8.1 Zijbalkpaneel "Arthropoda"

| Tabblad | Inhoud |
|---|---|
| **Collectie** | Rasterweergave van alle dieren (foto, naam, soort, status-icoon, stadium, eerstvolgende taak), filters op groep, status en locatie |
| **Dier** (detail) | Profiel, klimaatgrafieken met het doelbereik als band, **dagboektijdlijn**, metingen, stamboom, documenten, instellingen |
| **Dagboek** | Snel invoeren voor één of meerdere dieren tegelijk (bv. "rek 2 gesproeid"), formulier per actietype, overzicht van alle regels |
| **Soorten** | Soortendatabase: bekijken, bewerken, importeren (YAML/AI/handmatig), exporteren |
| **Kweek** | Lopende koppelingen en legsels, stamboomweergave |
| **Voorraad** | Voedseldieren en voederkolonies |
| **Klimaat** | Klimaatgroepen, actuatoren met hun huidige toestand en reden ("verwarming aan: 23,4 °C < 24 °C"), conflicten |

### 8.2 Dashboardkaart `arthropoda-card`

In de stijl van de flower-card: foto, naam en soort, balken voor temperatuur en vochtigheid met het doelbereik, status, "dagen sinds voedering/vervelling", en snelknoppen (gevoederd, gesproeid, dagboek…). Instelbaar via de visuele kaarteditor van HA.

### 8.3 Acties (services)

Alles wat het paneel kan, kan ook via acties, zodat je het in eigen automatiseringen, scripts en spraakassistent gebruikt:

`arthropoda.log_entry`, `arthropoda.log_feeding`, `arthropoda.log_molt`, `arthropoda.add_measurement`, `arthropoda.set_stage`, `arthropoda.set_season_profile`, `arthropoda.register_offspring`, `arthropoda.adjust_stock`, `arthropoda.import_caresheet`, `arthropoda.export_species`.

---

## 9. Bestandsstructuur van de repo

```
arthropoda/
├─ hacs.json
├─ README.md
├─ docs/ONTWERP.md
├─ caresheets/                    # voorbeeld-YAML's
├─ custom_components/arthropoda/
│  ├─ __init__.py                 # setup, paneel en kaart registreren
│  ├─ manifest.json
│  ├─ config_flow.py              # hoofdentry + subentry "dier"
│  ├─ const.py
│  ├─ db/                         # SQLite-schema, migraties, repository-klassen
│  ├─ models.py                   # dataclasses
│  ├─ caresheet/                  # YAML-schema, AI-extractie, iNaturalist
│  ├─ climate_controller.py       # regellogica + veiligheid
│  ├─ scheduler.py                # taken, todo, kalender, meldingen
│  ├─ journal.py                  # actietypes + hun gevolgen
│  ├─ websocket_api.py
│  ├─ services.yaml
│  ├─ sensor.py binary_sensor.py switch.py select.py button.py image.py
│  ├─ todo.py calendar.py
│  ├─ translations/{nl,en}.json
│  └─ frontend/                   # gebouwde JS (paneel + kaart)
├─ frontend/                      # bron: Lit + TypeScript + Vite
└─ tests/                         # pytest-homeassistant-custom-component
```

---

## 10. Bouwfasen

| Fase | Inhoud | Resultaat |
|---|---|---|
| **1. Kern** | Database, soorten (handmatig + YAML-import), dier als subentry, sensoren/tellers/status, dagboek via acties en knoppen | Bruikbaar zoals de plant monitor + dagboek |
| **2. Klimaat** | Regelaar met dag/nacht/seizoen, gedeelde actuatoren, veiligheid, alarmen | Actieve sturing |
| **3. Opvolging** | Planner, takenlijst, kalender, meldingen | Herinneringen |
| **4. Interface** | Zijbalkpaneel + dashboardkaart | Volledige UI |
| **5. Caresheets & foto's** | AI-extractie (Claude), iNaturalist, profielfoto's | Snel soorten toevoegen |
| **6. Extra modules** | Kweek & stamboom, voorraad, metingen, documenten | Volledig pakket |
| **7. Afwerking** | Tests, vertalingen, HACS-validatie, README | Klaar om te delen |

Na elke fase is er iets dat je in je eigen HA kunt testen.

---

## 11. Open punten om nog te bevestigen

1. **Naam:** "Arthropoda Keeper" met domein `arthropoda`: akkoord, of een andere naam?
2. **Startdatabase:** je koos niet voor een ingebouwde set soorten. Wil je toch een paar voorbeeld-YAML's (bv. 5 veelgehouden soorten uit verschillende groepen) om mee te testen?
3. **Lichtschema:** vaste uren per seizoen, of de echte zonsopgang/-ondergang van je locatie (eventueel van het herkomstgebied)?
4. **HA-versie:** welke versie draai je nu? (Instellingen → Info.) Subentries en AI Task-bijlagen vereisen een recente versie.
