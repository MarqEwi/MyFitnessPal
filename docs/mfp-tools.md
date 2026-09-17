# MFP-Werkzeuge: Auswahl, Endpunkte, bekannte Fehler

Stand der Recherche: 2026-09-16. Alle Angaben stammen aus den Repos, PyPI und
den GitHub-Issues der beiden Kandidaten; Alle Tests aus Schritt 1 und 2 sind gegen das Konto `MarqEwi` bestanden (siehe Abschnitt 6).

## 1. Vergleich der Kandidaten

| Kriterium | `mfp-mcp` (PyPI, Mason-Levyy/myfitnesspal-mcp) | AdamWalt/myfitnesspal-mcp-python |
| --- | --- | --- |
| Letzter Commit | 2026-07-26 (Release 0.3.0 am 2026-07-27) | 2026-08-11 |
| Auf PyPI | ja, `mfp-mcp` 0.3.0 | nein (Installation nur aus dem Quelltext; der Paketname `mfp-mcp` in seiner pyproject kollidiert mit dem PyPI-Paket von Mason-Levyy) |
| Offene Issues | 0 (keine Issues, weder offen noch geschlossen) | 5 offene, darunter **#13 „Authentication fails with 403 on all methods" (Windows 11, 2026-08-05, ohne Antwort)** und **#22 „mfp_search_food returns count: 0 for all queries" (2026-08-26, ohne Antwort)** |
| Cloudflare-Umgehung | `curl_cffi` mit Chrome-TLS-Fingerprint; nur das NextAuth-Cookie nötig | Standard-Session von `python-myfitnesspal` (cloudscraper); genau das bekommt laut Issue #13 unter Windows 403 |
| Cookie-Beschaffung unter Windows | manuelles Einfügen per `mfp-mcp auth` (funktioniert überall), optional Auto-Refresh per Playwright | Auto-Discovery nur macOS (Keychain); unter Windows Fallback `browser_cookie3`, das seit Chrome 127 (App-Bound Encryption) die Chrome-Cookies nicht mehr entschlüsseln kann („Unable to get key for cookie decryption", Issue #13) |
| Tagebuch schreiben | `/food/add` (Legacy-Formular, `food_id` + `weight_id` aus der Web-Suche) | `POST https://api.myfitnesspal.com/v2/diary` (JSON) |
| Eigenes Lebensmittel anlegen | **nicht enthalten** | `POST /api/services/foods` (Web-BFF), Listen und Löschen ebenfalls |
| Tests ohne Konto | 62 Tests, lokal grün (`uv run pytest`, 2026-09-16) | 3 Testdateien (Serving, Custom-Food, Fasting) |
| Werkzeuge | 12 (`fitness_*`) | 20 (`mfp_*`) |

**Entscheidung: `mfp-mcp` 0.3.0 von Mason-Levyy.** Begründung:

- Er ist der einzige der beiden, dessen Auth-Weg unter Windows + Chrome
  nachweislich funktionieren kann: Cookie manuell einfügen, Transport mit
  echtem Chrome-Fingerprint. Beim Kandidaten AdamWalt sind genau die beiden
  Punkte aus der Aufgabenstellung (Login broken, Suche liefert nichts) als
  unbeantwortete Issues offen, und unter Windows ist der Chrome-Cookie-Weg
  technisch tot.
- Er ist auf PyPI veröffentlicht, wird per `uvx mfp-mcp` ohne venv gestartet
  und hat keine offenen Fehlerberichte.
- Nachteil: kein Werkzeug zum Anlegen eigener Lebensmittel (Schritt 2.5).
  Dafür liegt in `scripts/mfp_smoke_test.py --custom-food` ein Versuch über
  die Web-BFF-Endpunkte bei, die AdamWalt am 2026-07-26 verifiziert hat (siehe
  Abschnitt 4).

Installation und Start wurden am 2026-09-16 in einer Linux-Umgebung geprüft:
`uvx --python 3.12 mfp-mcp --help` läuft in 2,5 s, `claude mcp add --scope user myfitnesspal
-- uvx mfp-mcp` registriert den Server, ein MCP-Client über stdio sieht alle
12 Werkzeuge, und ohne Cookie antwortet `fitness_get_day` mit einer klaren
Meldung („session expired or not connected"). Live-Aufrufe gegen MFP brauchen
das Cookie aus dem Windows-Chrome und wurden daher noch nicht ausgeführt.

## 2. Werkzeuge von `mfp-mcp`

| Werkzeug | Zweck | Anmerkungen für die Skill |
| --- | --- | --- |
| `fitness_get_day(date)` | Tagessummen, Einträge pro Mahlzeit, Tagesnotiz | Einträge tragen den Mahlzeitnamen so, wie MFP ihn auf der Tagebuchseite zeigt (erstes Wort, Großschreibung). Eintragsname = „Marke - Name, Menge Einheit", z. B. „Obst - Banane, 120.0 gram". Erste Nutzung holt bis zu 30 Tage nach, ein Request pro Tag. |
| `fitness_search_food(query, limit, with_macros)` | Kandidaten mit Marke, kcal, Eiweiß/KH/Fett, Portion, `verified`, `food_id`, `weight_id` | `serving` ist die **erste** Portionsgröße des Eintrags, `weight_id` gehört zu genau dieser Portion. Andere Portionsgrößen sind über das MCP nicht wählbar. |
| `fitness_log_food(query, meal, quantity, date, food_id, weight_id)` | Eintrag ins echte Tagebuch | `quantity` = Anzahl der Portion aus `serving`. 120 g bei Portion „100 g" ⇒ `quantity=1.2`. `meal` ist eine **Position**: breakfast=0, lunch=1, dinner=2, snacks=3, unabhängig vom Namen im Konto. |
| `fitness_delete_food(query, meal, date)` | Eintrag per Namens-Match löschen | `meal` wird hier gegen den **angezeigten Namen** (kleingeschrieben, erstes Wort) gefiltert. Im Konto `MarqEwi` heißen die Mahlzeiten breakfast, lunch, dinner, snacks, der Filter passt also. Bei Mehrdeutigkeit listet der Fehler die Kandidaten. |
| `fitness_modify_food` | Löschen + neu anlegen | Nicht atomar: schlägt das Anlegen fehl, ist der alte Eintrag bereits weg. |
| `fitness_log_weight`, `fitness_get_exercise`, `fitness_get_note`, `fitness_log_note`, `fitness_log_feel`, `fitness_get_trends`, `fitness_bulk_export` | Gewicht, Training, Notizen, Trends, Export | Nicht Teil der Skill. |

## 3. Endpunkte, die der Server benutzt

| Aktion | Endpunkt | Auth |
| --- | --- | --- |
| Tagebuch lesen | `GET https://www.myfitnesspal.com/food/diary/<user>?date=YYYY-MM-DD` (HTML) | Cookie `__Secure-next-auth.session-token`, Bearer-Token wird daraus per `/user/auth_token` bezogen |
| Suche | `GET https://www.myfitnesspal.com/food/search?search=<q>&page=1` (HTML, liefert `data-original-id`, `data-weight-ids`, CSRF-Meta) | dito |
| Nährwerte eines Treffers | `GET https://api.myfitnesspal.com/v2/food/<external_id>` | Bearer + `mfp-client-id: mfp-main-js` |
| Eintrag anlegen | `POST https://www.myfitnesspal.com/food/add` (Formular: `food_entry[food_id]`, `food_entry[weight_id]`, `food_entry[quantity]`, `food_entry[meal_id]`, `food_entry[date]`) | Bearer + `X-CSRF-Token` von der Suchseite |
| Eintrag löschen | `POST https://www.myfitnesspal.com/food/remove/<food_entry_id>` (`_method=delete`, `authenticity_token`) | CSRF-Token der Tagebuchseite |
| Tagesnotiz | `GET/POST https://www.myfitnesspal.com/food/note` | dito |
| Gewicht | `POST https://api.myfitnesspal.com/v2/measurements` | Bearer |

## 4. Eigenes Lebensmittel anlegen (nicht in `mfp-mcp`)

`python-myfitnesspal` 2.1.2 bringt `Client.set_new_food()` mit, das den
Legacy-Weg `GET /food/submit` → `POST /food/duplicate` → `GET /food/new` →
`POST /food/new` nachbildet. Ob dieser Weg 2026 noch funktioniert, ist
unbekannt (AdamWalt berichtet, dass der ebenfalls legacy `/food/diary/<user>/add`
inzwischen 404 liefert).

AdamWalt hat am 2026-07-26 stattdessen die Endpunkte des heutigen Web-Clients
verifiziert; am 2026-09-17 mit dem Konto `MarqEwi` bestätigt. `scripts/mfp_food.py`
(`list`, `create`, `delete`) und `scripts/mfp_smoke_test.py --custom-food`
benutzen genau diese:

| Schritt | Endpunkt |
| --- | --- |
| CSRF | `GET https://www.myfitnesspal.com/api/auth/csrf` → `{csrfToken}` |
| Anlegen | `POST https://www.myfitnesspal.com/api/services/foods`, Header `x-csrf-token`, Body `{"item": {description, brand_name, public:false, type:"food", country_code, nutritional_contents:{energy:{unit:"calories",value}, protein, carbohydrates, fat, ...}, serving_sizes:[{value:100, unit:"g", nutrition_multiplier:1, ...}]}}` |
| Eigene Lebensmittel listen | `GET https://www.myfitnesspal.com/api/services/users/foods/mine?search=` |
| Löschen | `DELETE https://www.myfitnesspal.com/api/services/foods/<id>` mit `x-csrf-token` |

Stolperfalle laut AdamWalt: `country_code` entscheidet, ob MFP den
Kohlenhydratwert als Netto (EU, Ballaststoffe kommen dazu) oder Brutto (US)
interpretiert. Für deutsche Etiketten `country_code="DE"` und Netto-KH senden.

## 5. Session-Cookie

- Name: `__Secure-next-auth.session-token`, Domain `.myfitnesspal.com`.
- Gültigkeit: etwa 30 Tage ab letztem Login; jede Nutzung im Browser
  verlängert die Browser-Session, das kopierte Token läuft aber zum
  ursprünglichen Ablaufdatum aus.
- Ablage in der Cloud: Umgebungsvariable `MFP_COOKIE` der Claude-Code-Umgebung,
  von `.mcp.json` an den Server durchgereicht (siehe `docs/setup-cloud.md`).
- Ablage auf dem PC durch `mfp-mcp auth`: `%LOCALAPPDATA%\myfitnesspal-mcp\myfitnesspal-mcp\cookies.json`
  (platformdirs). Das Setup-Skript beschränkt die Datei per `icacls` auf den
  eigenen Benutzer, weil `chmod 600` unter Windows wirkungslos ist.
- Abgelaufen: Werkzeuge antworten mit „session expired or not connected".
  Dann erneut in Chrome einloggen, Cookie kopieren, `uvx --python 3.12 mfp-mcp auth`
  ausführen. Alternativ `uvx --from 'mfp-mcp[autorefresh]' mfp-mcp auth`, dann
  rotiert ein headless Chromium das Token selbst.

## 6. Teststatus und Fehlerprotokoll

Hier werden die Ergebnisse von `scripts/mfp_smoke_test.py` eingetragen.
Bei Fehlern: Datum, Endpunkt, HTTP-Status, Meldung.

| Datum | Test | Ergebnis | Endpunkt / Fehler |
| --- | --- | --- | --- |
| 2026-09-16 | Installation, `claude mcp add`, Tool-Liste über stdio | OK (Linux-Container, ohne Cookie) | – |
| 2026-09-16 | 62 Unit-Tests von `mfp-mcp` | OK | – |
| 2026-09-16 | Setup auf Windows-PC: Python 3.12 via uv, Cookie aus Chrome, `claude mcp add`, Status Connected | OK | Hürden: Execution Policy, fehlende Schreibrechte auf `C:\Users\Marc`, Claude-CLI nicht installiert; alle behoben, siehe `docs/setup-windows.md` |
| 2026-09-16 | Login mit Session-Cookie (Schritt 1.4) | OK | Benutzer `MarqEwi` |
| 2026-09-16 | Tagebuch heute und gestern lesen (Schritt 1.5) | OK | – |
| 2026-09-16 | Suche „Banane" (Schritt 2.1) | OK, 8 Treffer | Treffer 1: „Banane [Obst]", 100 g, 89 kcal, verifiziert, `food_id=2716704125`, `weight_id=3133739836` |
| 2026-09-16 | Banane 120 g unter Snacks eintragen (Schritt 2.2) | OK | `POST /food/add`, Treffer 1 × 1.2 Portionen, `food_id=2716704125` |
| 2026-09-16 | Eintrag im Tagebuch sichtbar (Schritt 2.3) | OK | Anzeige „Obst - Banane, 120.0 gram: 107 kcal" in Mahlzeit `snacks` |
| 2026-09-16 | Eintrag löschen und Löschung bestätigen (Schritt 2.4) | OK | `POST /food/remove/<id>`, erneutes Lesen zeigt keinen Eintrag mehr |
| 2026-09-17 | Lesetest erneut, Mahlzeitnamen ausgelesen | OK | Namen: breakfast, lunch, dinner, snacks; Tagesziel 1803 kcal. Warnung „Unable to fetch user metadata, status 500" ist bekannt und durch `MFP_USERNAME` abgefangen |
| 2026-09-17 | Eigenes Lebensmittel „TEST Claude" anlegen (2.5) | OK | `POST /api/services/foods` → HTTP 200, id 124276794449013 |
| 2026-09-17 | In „Meine Lebensmittel" sichtbar (2.5) | OK | `GET /api/services/users/foods/mine?search=TEST Claude` → 1 Treffer |
| 2026-09-17 | Eigenes Lebensmittel löschen (2.5) | OK | `DELETE /api/services/foods/124276794449013` → HTTP 204 |
| 2026-09-17 | Ende-zu-Ende aus der Cloud-Sitzung über die MCP-Werkzeuge: `fitness_get_day`, `fitness_search_food` („Skyr Milbona"), `fitness_log_food` (300 g Frühstück), Gegenprüfung | OK | Eintrag „Generic Skyr Milbona - Skyr Milbona , 300 gram", 186 kcal, E 33 g, KH 12 g, F 1 g (MFP rundet 0,6 g auf 1 g); Cloudflare hat die Cloud-IP nicht blockiert |

Bekannte Fehlerbilder aus den Issues, zur Einordnung eigener Fehler:

- **403 auf allen Endpunkten** (AdamWalt #13): Cloudflare lehnt den
  TLS-Fingerprint ab. Bei `mfp-mcp`: `MFP_IMPERSONATE=chrome124` setzen;
  Rechenzentrums-IPs (VPN) werden deutlich öfter geblockt als private.
- **Suche liefert 0 Treffer** (AdamWalt #22): MFP hat das HTML der
  Suchseite geändert. `mfp-mcp` parst dieselbe Seite über
  `a[data-original-id][data-weight-ids]`; liefert `fitness_search_food` leer,
  ist das der wahrscheinlichste Grund. Dann Issue bei Mason-Levyy eröffnen.
- **„couldn't read your MyFitnessPal profile"**: MFPs Profil-Endpunkt liefert
  500 für Konten mit E-Mail-Login. Abhilfe: `MFP_USERNAME=MarqEwi` als
  Umgebungsvariable oder beim `auth`-Dialog angeben.
- **Chrome-Cookie kann nicht automatisch gelesen werden**: erwartet unter
  Windows (App-Bound Encryption). Manuell kopieren, siehe `docs/setup-windows.md`.
