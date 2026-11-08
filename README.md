# Arthropoda Keeper

Home Assistant-integratie voor het houden van insecten, spinnen, schorpioenen, pissebedden en andere geleedpotigen, inclusief waterinsecten. Elk dier of elke kolonie wordt een eigen apparaat met klimaatbewaking, tellers en een dagboek, vergelijkbaar met de plant monitor.

> **Status: fase 6 – alle geplande functies aanwezig** (kern, klimaat, opvolging, paneel/kaarten, AI-caresheets, foto's, kweek, voorraad, documenten). Zie [docs/ONTWERP.md](docs/ONTWERP.md).

## Kweek, voorraad, groei en documenten (fase 6)

> **Bestaande gegevens blijven bewaard.** Bij de eerste start na de update wordt de database automatisch uitgebreid naar versie 2. Er wordt alleen iets toegevoegd, en vooraf komt er een reservekopie: `/config/arthropoda/arthropoda.db.bak-v1`.

- **Kweek** (tab *Kweek*):
  - Een **koppeling** noteer je in het dagboek, met de partner als keuze uit je eigen dieren.
  - Een **eicocon, ootheek of legsel** (met de vader) wordt automatisch een legsel. De verwachte uitkomst komt uit `incubation_days` van de soort en verschijnt in de kalender en in de dagelijkse samenvatting.
  - Een legsel markeer je als **uitgekomen** of **mislukt**. Bij een uitgekomen legsel registreer je met **Nakomelingen registreren** een nieuwe kolonie. Moeder, vader, soort, aantal, geboortedatum en generatie (F1, F2, …) zijn dan al ingevuld.
  - Bestaande eicocons en ootheken uit je dagboek zijn bij de update mee overgezet.
- **Stamboom:** de ouders en de generatie stel je in via *Wijzigen → Herkomst & stamboom*. De dierpagina toont de ouders en de nakomelingen als klikbare links.
- **Voorraad** (tab *Voorraad*):
  - voedseldieren met maat, aantal, eenheid en minimum;
  - aantallen pas je aan met de knoppen − en ＋ (met Shift: per 10);
  - een voorraad kan gekoppeld zijn aan een **eigen voederkolonie**;
  - bij een voedering kies je *Uit voorraad*, en het aantal wordt afgetrokken (bij een eigen kolonie ook van de kolonie);
  - onder het minimum: sensor **Voorraad laag** en een vermelding in de samenvatting.
- **Groei:** op de dierpagina staat een grafiek per meting (lengte, spanwijdte, gewicht, aantal), met de vervellingen als stippellijnen.
- **Herkomst en documenten:**
  - kweker/verkoper en prijs vul je in via *Wijzigen*;
  - documenten (factuur, CITES, vergunning, kwekersverklaring, dierenarts, …) voeg je toe op de dierpagina, met een PDF of foto en een vervaldatum;
  - documenten die binnen 30 dagen vervallen, staan in de kalender en in de samenvatting;
  - bestanden staan in `/config/arthropoda/documents` en gaan mee in je back-ups.
- **Soortfoto's voor bestaande soorten:** *Soorten → 🖼 Foto's voor alle soorten zonder foto*.

## Diapauze en voederdieren

- **Diapauze / winterrust:**
  1. Leg per soort in de caresheet vast hoe lang de diapauze duurt:
     ```yaml
     species:
       scientific_name: Lasius niger
       diapause: {min_days: 90, max_days: 150, start_months: [10, 11], stage: adult}
     ```
  2. Noteer in het dagboek **Diapauze gestart**, eventueel met een eigen *gepland einde*.
  3. Het dier krijgt de badge ❄. De kalender toont de periode *Diapauze kan eindigen* (vroegst tot uiterlijk).
  4. Op het geplande einde, of anders het vroegste einde, verschijnt de taak **Uit diapauze halen** in de takenlijst en in de samenvatting. Afvinken noteert *Diapauze beëindigd*.

  Tijdens een diapauze komen er geen voederherinneringen. Gebruikt de caresheet een winterprofiel (`season: winter`), dan geldt dat profiel.
  Dit werkt ook voor overwinterende poppen van vlinders (`stage: pupa`) en voor mierenkolonies.
- **Voederdieren:**
  - Zet `feeder: true` bij de soort (in de caresheet of met het vinkje in *Soort toevoegen*).
  - Die dieren krijgen de badge 🦗.
  - In de collectie en de collectiekaart (`feeders: all | no_feeders | only_feeders`) kun je ze tonen, verbergen of alleen die tonen.
  - Bij de voorraad staan voederkolonies bovenaan in de keuzelijst *Eigen kolonie*.

## Caresheets met AI en foto's (fase 5)

### Caresheet inlezen met AI

Hiervoor heb je in HA een AI-integratie met een **AI Task**-entiteit nodig, bv. de officiële **Anthropic**-integratie (Claude).

1. Ga naar het paneel → **Soorten** → **✨ Caresheet met AI**.
2. Geef een **webadres** op, of upload een **PDF** of een **foto van een papieren caresheet**. Voor een PDF of foto moet de AI bijlagen ondersteunen; Claude kan dat.
3. De AI zet de caresheet om naar ons formaat:
   - met aparte profielen per levensfase of seizoen als de bron die geeft;
   - waarden die niet in de bron staan, laat ze weg (de AI vult niets zelf in).
4. Het resultaat verschijnt in de editor en is **nog niet opgeslagen**. Kijk het na, pas aan waar nodig en klik op **Opslaan**. In de bronvermelding staat "AI-extractie – nakijken".

Geüploade bestanden komen in de mediamap (`/media/arthropoda`).

### Foto's

- **Soortfoto:** bij een nieuwe soort zoekt de integratie automatisch een foto op **iNaturalist**, alleen met een Creative Commons-licentie of CC0. Een andere foto kies je in **Soorten → 🖼 Soortfoto kiezen**. De auteur, licentie en link worden altijd mee getoond.
- **Eigen foto per dier:** dierpagina → **📷 Foto uploaden** (JPG, PNG of WEBP). De foto staat in `/config/arthropoda/photos` en gaat mee in je back-ups. Een eigen foto gaat voor op de soortfoto.
- Elk dier heeft een **foto-entiteit** (`image.<dier>_foto`). Je kunt die ook in gewone HA-kaarten gebruiken (bv. een *Picture entity*-kaart).

## Paneel en dashboardkaarten (fase 4)

### Zijbalkpaneel *Arthropoda*

- **Collectie:** tegels per dier met status, klimaat (balk met doelbereik), levensfase, voedering en de volgende taak. Je kunt zoeken en filteren, en vanaf elke tegel snel noteren dat je gevoederd of gesproeid hebt, of het dier wijzigen.
- **Dier** (klik op een tegel): klimaat en wat de toestellen doen, verzorging en taken, het actieve profiel, metingen en het volledige dagboek (regels verwijderen kan).
- **Dagboek:** alle regels, gefilterd per dier of handeling. Eén regel kan voor meerdere dieren tegelijk gelden (bv. "rek 2 gesproeid").
- **Soorten:** caresheets bekijken, bewerken (YAML), nieuwe soorten toevoegen, en ongebruikte soorten verwijderen.
- **Klimaat:** alle toestellen met hun dieren, het doelbereik, de actie en de reden.
- **Voedselplanten:** koppel in *Wijzigen → Voeding* de planten uit de plant monitor (`plant.*`) die je voor een dier kweekt.
  - Bij *Gevoederd* en *Voedselplanten vervangen* staan ze in het dagboek voorgeselecteerd.
  - Op de dierpagina zie je hun status (ok of probleem).
  - Ook in acties: `arthropoda.log_feeding` met `plants: [plant.braam]`.
- **Dier toevoegen** en **Wijzigen** openen één formulier met alle gegevens, sensoren, toestellen en afstelling. Het tandwiel op de integratiepagina blijft ook werken.

### Kaarten

Toevoegen via *Dashboard bewerken → Kaart toevoegen → zoek "Arthropoda"*, of in YAML:

```yaml
type: custom:arthropoda-animal-card       # één dier
animal: 01JX…                             # kies het dier in de visuele editor
```

```yaml
type: custom:arthropoda-collection-card   # lijst van alle dieren
title: Mijn dieren                        # optioneel (standaard: naam van de collectie)
sort: status                              # name | species | status | feeding
max_rows: 10                              # vanaf zoveel dieren een scrollbalk
show_inactive: false                      # overleden/verkochte dieren ook tonen
```

Klik op een dier in de kaart om het in het paneel te openen.

> Na een update: druk in de browser één keer op **Ctrl + F5**, zodat de nieuwe versie van het paneel en de kaarten geladen wordt.

## Opvolging (fase 3)

Op het apparaat **Collectie** vind je:

- **Takenlijst *Onderhoud*** (`todo.…_onderhoud`): wat vandaag of eerder moet gebeuren (voederen, schoonmaken, substraat vervangen, waterwissel), op basis van de intervallen in de caresheet.
  - **Afvinken** noteert de handeling meteen in het dagboek.
  - **Verwijderen** stelt de taak uit tot morgen.
  - Tijdens premolt, kort na een vervelling of in diapauze komt er geen voedertaak.
- **Kalender** (`calendar.…_kalender`) toont:
  - geplande taken, als terugkerende items;
  - alles uit het dagboek, op het tijdstip waarop het gebeurde;
  - de **verwachte vervelling**: een ruwe schatting (laatste vervelling + laatste interval), vanaf twee vervellingen;
  - de **verwachte uitkomst** van eicocons, ootheken en eieren, op basis van `incubation_days` uit de caresheet of uit de dagboekregel.
- **Sensoren:**
  - *Openstaande taken*;
  - *Dieren met een probleem*, met in de attributen welk dier welk probleem heeft.
- **Dagelijkse samenvatting** (standaard om 18:00, instelbaar onder *Configureren → Instellingen*): één bericht met de taken van vandaag en de dieren met een probleem. Zonder meldingsdoelen verschijnt ze als melding in HA. De actie `arthropoda.send_digest` stuurt ze meteen.
- **Acties:** `arthropoda.snooze_task` stelt een taak een aantal dagen uit.

Elk dier heeft op zijn apparaatpagina nu een link naar de instellingen van de integratie (waar het tandwiel staat).

## Klimaatsturing (fase 2)

Bij *Dier toevoegen* / *Dier wijzigen* kies je in de stap **Klimaatsturing** wat de integratie mag aansturen:

| Actuator | Werking |
|---|---|
| Verwarming | Een schakelaar werkt als thermostaat met hysterese rond het midden van het doelbereik. Een dimbare lamp wordt proportioneel geregeld. Bij een bestaande thermostaat (`climate`) stelt de integratie de doeltemperatuur in. |
| Vernevelaar | Geeft pulsen van x seconden als de vochtigheid te laag is, met een minimale pauze en een daglimiet. Daarnaast vaste momenten (bv. `08:00, 20:00`). Een script mag ook. |
| Verlichting | Volgt het dagritme: vaste uren met de daglengte uit de caresheet (`light_hours`, per seizoen), of de echte zon. Dimbare lampen kunnen optioneel geleidelijk op- en afdimmen. |
| Ventilator | Gaat aan bij te hoge vochtigheid of temperatuur. |
| Waterverwarming | Thermostaat op de watertemperatuur. |
| Pompen, filter | Altijd aan, behalve in onderhoudsmodus. |

- **Gedeelde actuatoren:** dieren met dezelfde warmtemat of vernevelaar worden samen geregeld, op de overlap van hun caresheets. Is er geen overlap, dan verschijnt er een **reparatiemelding** onder Instellingen en wordt het gemiddelde gebruikt.
- **Veiligheid:**
  - De verwarming gaat meteen uit als het gevaarlijk warm wordt (`temp_max_safe` uit de caresheet, of dagmaximum + 5 °C).
  - Ze gaat ook uit als een sensor wegvalt of te lang niets doorgeeft (standaard 30 minuten).
  - Een gewone schakelaar wordt hoogstens één keer per minuut aangezet, om relais te sparen.
  - Een lopende vernevelpuls stopt bij een herstart.
- **Per dier:**
  - de schakelaar **Klimaatsturing** (uit = alleen bewaken, de integratie raakt de actuatoren niet aan);
  - de schakelaar **Onderhoudsmodus**: vernevelaar, ventilator en pompen staan maximaal 60 minuten uit, bv. tijdens het schoonmaken;
  - de diagnostische sensor **Klimaatregeling**, die per actuator toont wat er gebeurt en waarom (bv. `below_setpoint`, doel 24–26 °C).
- **Alarmen:**
  - Je krijgt een melding in HA en optioneel op je gsm (instellen via *Configureren → Instellingen → Meldingen sturen naar*, bv. `notify.mobile_app_mijn_gsm`).
  - Een melding volgt pas als het probleem langer duurt dan de alarmvertraging (standaard 15 min). Gevaarlijk warm wordt meteen gemeld.
  - Als het probleem weg is, krijg je een "opgelost"-bericht.

## Wat werkt sinds fase 1

- **Soortendatabase** (SQLite in `/config/arthropoda/arthropoda.db`, gaat mee in je HA-back-ups):
  - soorten handmatig toevoegen;
  - caresheets importeren en exporteren als YAML;
  - klimaatprofielen per levensfase en per seizoen (bv. winterrust).
- **Eén apparaat per dier of kolonie**, met:
  - de temperatuur/luchtvochtigheid/watertemperatuur van je bestaande sensoren;
  - een **status** (ok/probleem) met de oorzaken, zoals te warm, te droog, voederen achterstallig of sensor offline;
  - levensfase, stadium (L-nummer), aantal vervellingen, koloniegrootte;
  - "dagen sinds" voedering, vervelling, schoonmaak, substraatwissel, waterwissel; volgende voedering;
  - laatste lengte/spanwijdte/gewicht (standaard uitgeschakeld);
  - het doelbereik dat nu geldt (dag/nacht, seizoen, levensfase).
- **Dagboek** met 46 handelingen, waarvan sommige automatische gevolgen hebben:
  - vervelling → stadium +1, premolt uit, voederpauze (niet mogelijk bij adulten die niet meer vervellen, zoals bidsprinkhanen en wandelende takken);
  - premolt → geen voederwaarschuwing;
  - diapauze → winterprofiel;
  - overlijden/verkoop → niet meer bewaakt.
- **Snelknoppen**: gevoederd, gesproeid, plaatselijk schoongemaakt, water bijgevuld.
- **Acties** voor automatiseringen en scripts: `arthropoda.log_entry`, `log_feeding`, `log_molt`, `add_measurement`, `set_stage`, `get_journal`, `import_caresheet`, `export_species`, `list_species`.
- Bij elke dagboekregel vuurt de gebeurtenis `arthropoda_journal_entry`, zodat je erop kunt automatiseren.

## Installatie

**Via HACS (aanbevolen):** HACS → ⋮ → *Aangepaste repositories* → URL van deze repo, type *Integratie* → installeren → HA herstarten.

**Handmatig:** kopieer `custom_components/arthropoda` naar `/config/custom_components/arthropoda` en herstart HA.

Vereist Home Assistant **2025.6 of nieuwer** (config subentries).

## Aan de slag

1. **Instellingen → Apparaten & diensten → Integratie toevoegen → Arthropoda Keeper.** Hiermee maak je de collectie aan.
2. **Soorten toevoegen:** klik bij de integratie op **Configureren** en kies:
   - *Caresheet importeren:* plak de inhoud van [caresheets/voorbeelden.yaml](caresheets/voorbeelden.yaml), of kopieer het bestand naar `/config/arthropoda/caresheets/` en geef dat pad op;
   - *Soort toevoegen:* een eenvoudig formulier met één klimaatprofiel.
3. **Dieren toevoegen:** klik bij de integratie op **Dier toevoegen**, kies de soort en koppel eventueel sensoren. Dieren in hetzelfde terrarium mogen dezelfde sensoren gebruiken.
4. Wijzigen kan via ⋮ → *Dier wijzigen* bij het dier.

## Voorbeelden

Voedering noteren vanuit een script:

```yaml
action: arthropoda.log_feeding
data:
  animal: <device_id van het dier>
  prey: Shelfordella
  quantity: 2
  result: accepted
```

Vervelling met spanwijdte:

```yaml
action: arthropoda.log_molt
data:
  animal: <device_id>
  sex: female
  legspan_mm: 55
```

Melding bij een probleem:

```yaml
triggers:
  - trigger: state
    entity_id: binary_sensor.rosie_probleem
    to: "on"
    for: "00:15:00"
actions:
  - action: notify.mobile_app_telefoon
    data:
      message: >
        {{ state_attr('sensor.rosie_status', 'problems') | join(', ') }}
```

## Caresheet-formaat

```yaml
format: arthropoda-caresheet/1
species:
  scientific_name: Brachypelma hamorii
  common_names: {nl: Mexicaanse roodknievogelspin}
  group: tarantula          # tarantula, scorpion, mantis, phasmid, isopod, roach, beetle, ant, aquatic, …
  development: molting_adult
  habitat: terrestrial
care_profiles:
  - temp_day: [22, 26]      # [min, max]
    temp_night: [18, 22]
    humidity: [55, 70]
    feeding_interval_days: 14
  - stage: juvenile         # overschrijft alleen wat hier staat
    feeding_interval_days: 5
  - season: winter
    months: [12, 1, 2]
    temp_day: [19, 23]
source: "https://…"
```

Profielen worden samengevoegd in deze volgorde: algemeen → levensfase → seizoen. Elke laag overschrijft alleen de velden die ze zelf opgeeft.

Profielvelden:

- **Klimaat:** `temp_day`, `temp_night`, `temp_max_safe`, `humidity`, `water_temp`, `ph`, `light_hours`, `uv`, `substrate_moisture`, `misting`, `ventilation`
- **Intervallen in dagen:** `feeding_interval_days`, `cleaning_interval_days`, `substrate_change_interval_days`, `water_change_interval_days`, `post_molt_fast_days`
- **Overig:** `notes`

Meerdere soorten in één bestand scheid je met `---`.

> De voorbeeld-caresheets bevatten **richtwaarden om mee te testen**. Controleer ze met een betrouwbare bron voor je ze voor je dieren gebruikt.

## Ontwikkeling

```bash
python scripts/gen_translations.py      # vertalingen (nl/en) opnieuw genereren
pytest tests/core                       # kernlogica, zonder Home Assistant
pytest tests/ha                         # integratietests (pytest-homeassistant-custom-component; Linux/macOS, Python ≥ 3.13)
```

## Licentie

Copyright © 2026 Entomobiel.

Arthropoda Keeper is vrije software onder de [GNU General Public License versie 3](LICENSE) (GPL-3.0).

- Je mag de code gebruiken, aanpassen en verspreiden.
- Wie een (aangepaste) versie verspreidt, moet dat ook onder GPL-3.0 doen, met de volledige broncode en met vermelding van de oorspronkelijke auteur.
- De software wordt geleverd zonder enige garantie.

Versies tot en met commit `8f83226` (8 november 2026) werden onder de MIT-licentie gepubliceerd.
