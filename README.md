# Arthropoda Keeper

Home Assistant-integratie voor het houden van insecten, spinnen, schorpioenen, pissebedden en andere geleedpotigen, inclusief waterinsecten. Elk dier of elke kolonie wordt een eigen apparaat met klimaatbewaking, tellers en een dagboek, vergelijkbaar met de plant monitor.

> **Status: versie 0.10** – kern, klimaat, opvolging, paneel/kaarten, AI-caresheets, foto's, kweek, voorraad, documenten, diapauze, kasten met NFC/QR, plantenkasten met Plant Monitor en verzorgingstaken per plant, aandringen met scanbewijs. Zie [docs/ONTWERP.md](docs/ONTWERP.md).

## Aandringen bij taken over tijd (fase 9)

Inschakelen via **Instellingen → Apparaten & diensten → Arthropoda Keeper → Configureren → Aandringen bij taken over tijd**. Meldingen gaan naar de doelen uit *Instellingen*; gebruik `notify.mobile_app_<gsm>` voor knoppen en dringende meldingen.

| Achterstand | Wat er gebeurt |
|---|---|
| Vervaldag | In de dagelijkse samenvatting |
| Over tijd | Elke *x* uur een melding met de open taken, buiten de stille uren. Knoppen *Over 1 uur* en *Morgen* (maximaal *n* keer per taak). Bewust geen knop *Gedaan* |
| *Dringend na* (standaard 2 dagen) | Melding op een eigen kanaal met hoge prioriteit, blijft staan en is niet weg te vegen (Android). Uitstellen kan niet meer |
| *Speaker/lamp na* (standaard 3 dagen) | Daarbovenop een gesproken boodschap (`tts.speak`) op de gekozen speaker en een knipperende lamp |

Zijn alle taken gedaan, dan wordt de melding automatisch van de gsm gehaald.

**Scanbewijs:** een taak die over tijd is, kan pas afgehandeld worden als je kort ervoor (standaard 15 minuten) de **NFC-tag of QR-code van de kast** gescand hebt. Dat geldt voor elke manier van afvinken: werkscherm, paneel, kaarten, takenlijst en acties. Op de herinnering tikken of het werkscherm vanuit de app openen telt niet als scan. Het geldt voor kasten met een NFC-tag of die al eens gescand werden; dieren zonder kast kunnen niets bewijzen en worden niet tegengehouden.

## Plantenkasten en Plant Monitor (fase 8)

Planten uit [Plant Monitor](https://github.com/Olen/homeassistant-plant) (`plant.*`) kunnen in een kast staan, naast of zonder dieren.

- **Kast wijzigen → Planten:** kies de planten. Type *Plantenkast* is er voor kasten die alleen planten kweken.
- **Sturing op de planten:** zitten er **geen dieren** in de kast, dan stuurt de kast haar verwarming, vernevelaar, ventilator en verlichting op de **min/max-grenswaarden die je in Plant Monitor** bij elke plant instelt (temperatuur en luchtvochtigheid). Bij meerdere planten geldt de overlap; overlappen ze niet, dan krijg je een reparatiemelding.
  - *Daglengte voor de planten* (uren) bepaalt hoe lang de verlichting aan blijft, vanaf het dagbegin uit de integratie-opties.
  - Uitvinkbaar per kast (*Klimaat sturen op de grenswaarden van de planten*).
- **Zitten er dieren in**, dan zijn de planten voedsel: alleen het klimaat van de dieren telt. Zo kan een plant naar een kweekbak verhuizen om opgegeten te worden.
- **Werkscherm:** de planten met hun toestand uit Plant Monitor (in orde of probleem, wanneer laatst water) en knoppen *Water gegeven, Bemest, Gesnoeid, Geoogst, Verpot, Plaag, Gezaaid, Notitie*. Tik een plant aan of uit om de handeling alleen voor bepaalde planten te noteren.
- **Verzorging per plant (0.10):**
  - Onder de planten stel je per plant **Sproeien elke … dagen** en **Bemesten elke … dagen** in, bijvoorbeeld 1 dag voor kiemend gras.
  - Je krijgt dan een taak *Sproeien: Gras* in de takenlijst, de kalender en op het werkscherm.
  - De taak is afgehandeld zodra je *Water gegeven* (of *Bemest*) voor die plant noteert, of als je hem afvinkt. Afvinken zet de handeling ook in het plantendagboek.
  - Het aandringen en het scanbewijs gelden ook voor deze taken.
  - Is er nog nooit gesproeid, dan staat de taak op vandaag.
- **Plantendagboek:** handelingen staan in een eigen tabel (database v4, automatische migratie met reservekopie `arthropoda.db.bak-v3`). Bij elke handeling vuurt de gebeurtenis `arthropoda_plant_entry`.
- Grenswaarden worden via het entiteitenregister gevonden, dus hernoemde entiteiten blijven werken.

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

## Kasten, NFC en QR-codes (fase 7)

> Bij de eerste start na de update wordt de database uitgebreid naar versie 3. Er wordt alleen iets toegevoegd, en vooraf komt er een reservekopie (`arthropoda.db.bak-v2`).

**Kasten** (tab *Kasten*): per terrarium, faunabox, kweekbak, formicarium, … leg je vast:
- code en naam;
- type, afmetingen (de inhoud wordt berekend), materiaal, ventilatie en plaats;
- aankoop en prijs;
- status (in gebruik, leeg, onderhoud).

**Bewoners** wijs je toe in het kastformulier of in *Wijzigen* van een dier. Een verhuizing komt automatisch in het dagboek.

**Klimaat per kast:**
- Koppel sensoren en toestellen aan de kast (bv. de sensoren van je Raspberry Pi Pico W, zodra ze als entiteiten in HA staan via ESPHome of MQTT). Ze gelden dan voor alle bewoners.
- Gedeelde toestellen worden geregeld op de overlap van de caresheets, zoals in fase 2.
- De eigen instellingen van een dier blijven bewaard, maar worden niet gebruikt zolang het in een kast met klimaat zit.

**Taken per kast:**
- Schoonmaken en substraat vervangen worden één taak per kast, in plaats van één per bewoner. Het interval is het kortste uit de caresheets van de bewoners.
- Voor de **uitrusting** (UV-lamp, verwarmingskabel, filter, vernevelaar, …) geef je een vervang- of reinigingsinterval op. Je krijgt een taak *Onderhoud uitrusting* wanneer het zover is.

**Grootte-check:** staat in de caresheet `enclosure: {min_size_cm: [lengte, breedte, hoogte]}`, dan waarschuwt de integratie als een bewoner in een te kleine kast zit.

**Werkscherm** (`/arthropoda?enclosure=CODE`), gemaakt voor je gsm:
- de bewoners met foto (tik om ze aan of uit te vinken);
- grote knoppen: *Gevoederd, Gesproeid, Schoongemaakt, Water, Voedselplant, Substraat, Notitie, Foto, Meer…*;
- de taken van vandaag om af te vinken;
- het klimaat en de laatste handelingen.

Alles komt meteen in het dagboek.

**NFC-tags** (aanbevolen: waterdichte NTAG215/216-stickers):
1. Schrijf een tag met de HA-app: *Instellingen → Companion-app → NFC-tags → Tag schrijven*.
2. Klik in het paneel bij de kast op **📶 NFC-tag** en scan de tag één keer.
3. Voortaan: scan de tag. Op Android opent de HA-app meteen het werkscherm. Geef de app daarvoor de toestemming *Weergeven over andere apps*. Op iOS tik je op de melding.

Een link met *NFC Tools* schrijven (`homeassistant://navigate/arthropoda?enclosure=CODE`) kan ook. Android toont dan eerst de link, waarop je moet tikken. De werkwijze met de HA-app is daarom handiger, en levert ook betrouwbaarder scanbewijs.
Bij elke scan vuurt ook de gebeurtenis `arthropoda_enclosure_scanned`, voor eigen automatiseringen.

**QR-etiketten:** *Kasten → 🖨 Etiketten afdrukken* maakt een A4-vel met per kast een QR-code, de code, de naam en de soorten. Je kiest uit 3×8 (63,5 × 38,1 mm), 2×7 (99,1 × 38,1 mm) of 3×7 (70 × 42,3 mm). De QR-code opent de HA-app rechtstreeks op het werkscherm. Gebruik waterbestendige vinylstickers of lamineer de etiketten.

**Verzorgingsronde:**
1. Klik op *Kasten → 🔁 Ronde starten* en scan daarna kast na kast.
2. Het werkscherm toont hoeveel kasten je al bezocht hebt.
3. Met **Ronde afronden** zie je wat er gedaan is, en welke kasten nog open taken hebben die je nog niet bezocht.

**Lege kasten:** filter in de tab *Kasten* op *Leeg*, bv. wanneer er nakomelingen te verdelen zijn.

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

**Via de Marketplace (Home Assistant 2026.11 en nieuwer, aanbevolen):** Instellingen → Marketplace → *Add from link* → `Entomobiel/arthropoda-keeper` (koppel je GitHub-account als daarom gevraagd wordt) → installeren → HA herstarten. Updates verschijnen daarna onder Instellingen → Updates.

**Via HACS (oudere Home Assistant):** HACS → ⋮ → *Aangepaste repositories* → URL van deze repo, type *Integratie* → installeren → HA herstarten.

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
