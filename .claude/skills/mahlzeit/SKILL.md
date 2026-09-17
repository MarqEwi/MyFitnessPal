---
name: mahlzeit
description: Mahlzeit per Text erfassen, Kalorien und Makros über die MyFitnessPal-Datenbank berechnen und nach Freigabe ins MFP-Tagebuch (MCP-Server "myfitnesspal") schreiben. Aufruf z. B. "/mahlzeit Mittag: 200 g Hähnchenbrust, 150 g gekochter Reis, 100 g Brokkoli, 1 EL Olivenöl".
---

# /mahlzeit – Mahlzeit erfassen und in MyFitnessPal eintragen

Eingabe: `$ARGUMENTS` (Freitext, deutsch, metrische Einheiten).
Konto: MyFitnessPal-Benutzer `MarqEwi`. Werkzeuge: MCP-Server `myfitnesspal`
(`fitness_search_food`, `fitness_log_food`, `fitness_get_day`,
`fitness_delete_food`). Der Server läuft in der Cloud-Sitzung (Cookie aus
`MFP_COOKIE`) genauso wie auf dem PC; die Skill verhält sich überall gleich.
Einträge erscheinen im Tagebuch als „Marke - Name, Menge Einheit", z. B.
„Obst - Banane, 120.0 gram".

Antworte auf Deutsch, knapp, mit Tabellen. Schreibe **nie** ins Tagebuch,
bevor der Benutzer die berechnete Tabelle freigegeben hat.

## Mahlzeiten-Zuordnung

`fitness_log_food` adressiert Mahlzeiten über die **Position** im Konto, nicht
über den Namen: `breakfast` = 1. Mahlzeit, `lunch` = 2., `dinner` = 3.,
`snacks` = 4. Die tatsächlichen Namen liefert `fitness_get_day` in der
Reihenfolge des Kontos.

| Nutzer sagt | `meal`-Parameter | Name im Konto (bestätigt 2026-09-17) |
| --- | --- | --- |
| Frühstück, morgens | `breakfast` | breakfast |
| Mittag, Mittagessen | `lunch` | lunch |
| Abend, Abendessen | `dinner` | dinner |
| Snack, Snacks, Zwischenmahlzeit | `snacks` | snacks |

Das Konto benutzt die englischen Standardnamen. Deshalb darf `meal` auch bei
`fitness_delete_food` mitgegeben werden, der Namensfilter passt.

Fehlt die Mahlzeit im Text, aus der lokalen Uhrzeit ableiten und im Ergebnis
nennen: bis 10:30 Frühstück, 10:30 bis 14:30 Mittag, 14:30 bis 17:30 Snack,
ab 17:30 Abend.

## Ernährungsplan (plan.json)

Der Benutzer fährt ein aggressives Defizit mit festem Eiweißziel und will die
Tagesziele **erreichen, nicht unterschreiten**. Werte stehen in `plan.json`:

| Tagestyp | kcal | Eiweiß | KH | Fett |
| --- | --- | --- | --- | --- |
| Trainingstag | 2180 | 216 g | 194 g | 60 g |
| Ruhetag | 1803 | 216 g | 129 g | 47 g |

Tagestyp erkennen: „Trainingstag", „nach dem Training", „Training heute" ⇒
`training`; „Ruhetag", „trainingsfrei" ⇒ `rest`. Steht nichts im Text und
`training_days` in `plan.json` ist leer, **Ruhetag annehmen und das in einem
Halbsatz sagen** („ich rechne mit Ruhetag, sag Trainingstag, falls nicht").

## Ablauf

### 1. Parsen

- Mahlzeit erkennen (siehe Tabelle) und Datum (Standard heute; „gestern" und
  `YYYY-MM-DD` akzeptieren).
- Zutaten mit Menge und Einheit auflisten. Einheiten in Gramm bzw. Milliliter
  normalisieren: 1 EL Öl = 10 g, 1 TL Öl = 5 g, 1 EL flüssig = 15 ml, 1 TL
  flüssig = 5 ml, 1 Scheibe Brot = 45 g, 1 Ei (M) = 55 g, 1 Tasse = 250 ml.
  Umrechnungen im Ergebnis ausweisen.
- Fehlt bei einer Zutat die Menge, **nicht raten**: einmal gesammelt für alle
  betroffenen Zutaten nach der Menge fragen und dabei eine übliche Portion als
  Vorschlag nennen („Hähnchenbrust: 150 g?"). Erst nach Antwort weiter.

### 2. Zuordnen

Für jede Zutat `fitness_search_food(query, limit=5, with_macros=true)`.
Suchbegriff zuerst deutsch und generisch („Hähnchenbrust roh"), bei
schwachen Treffern englisch („chicken breast raw").

Auswahlregeln, in dieser Reihenfolge:

1. `verified == true` bevorzugen.
2. `serving` muss in Gramm oder Millilitern sein („100 g", „1 g", „100 ml"),
   sonst lässt sich die Menge nicht exakt loggen. Treffer mit Portionen wie
   „1 medium" oder „1 cup" nur nehmen, wenn nichts anderes passt, und dann
   die angenommene Grammzahl nennen.
3. Nährwerte plausibel gegen Referenzwerte (z. B. Hähnchenbrust roh ≈ 110 kcal
   / 100 g, gekochter Reis ≈ 130 kcal / 100 g, Olivenöl ≈ 900 kcal / 100 g).
   Ausreißer verwerfen.
4. Ist genau ein Treffer nach 1–3 plausibel: direkt nehmen. Sonst die besten
   drei mit kcal / 100 g, Eiweiß, KH, Fett, Marke und Verifizierung zeigen und
   den Benutzer wählen lassen.

Merken pro Zutat: `food_id`, `weight_id`, Portionsgröße aus `serving`,
Nährwerte je Portion.

Findet sich für ein Markenprodukt kein passender Treffer und der Benutzer
nennt die Etikett-Werte je 100 g, kann ein eigenes Lebensmittel angelegt
werden (nur nach Rückfrage, das MCP kann das nicht):

```
uv run --python 3.12 --with mfp-mcp==0.3.0 python scripts/mfp_food.py create --name "<Name>" --brand "<Marke>" --kcal <n> --protein <g> --carbs <g> --fat <g>
```

Danach erneut `fitness_search_food` mit dem Namen; erscheint es dort nicht,
mit dem nächstbesten Datenbank-Treffer loggen und den Benutzer darauf
hinweisen, dass das eigene Lebensmittel in der MFP-App unter „Meine
Lebensmittel" wählbar ist.

### 3. Berechnen

`quantity = Menge in g / Portionsgröße in g` (bei „100 g" also 200 g ⇒ 2.0;
bei „1 g" ⇒ 200). Nährwerte je Zutat = Werte je Portion × `quantity`.

Tabelle zeigen:

| Zutat (MFP-Treffer) | Menge | kcal | Eiweiß g | KH g | Fett g |
| --- | --- | --- | --- | --- | --- |
| … | … | … | … | … | … |
| **Summe** | | | | | |

Darunter: Mahlzeit, Datum, offene Annahmen (Umrechnungen, unverifizierte
Treffer). Dann fragen: „So in MyFitnessPal unter <Mahlzeit> für <Datum>
eintragen? (ja / Nummer ändern / abbrechen)".

### 4. Eintragen (nur nach „ja")

Pro Zutat `fitness_log_food(query=<Anzeigename>, meal=<Position>,
quantity=<berechnet>, date=<Datum>, food_id=<id>, weight_id=<id>)`.
Immer `food_id` und `weight_id` mitgeben, damit nicht der Top-Treffer der
Suche, sondern der gewählte Eintrag geloggt wird.

Schlägt ein Eintrag fehl: Fehler nennen, restliche Zutaten trotzdem loggen,
am Ende auflisten, was fehlt.

### 5. Prüfen und berichten

`fitness_get_day(date)` aufrufen und bestätigen, dass alle Zutaten in der
richtigen Mahlzeit stehen. Dann die Ziele holen (der MCP-Server kennt nur das
kcal-Ziel; das Skript liest Makro-Ziele und Mahlzeit-Budgets):

```
uv run --python 3.12 --with mfp-mcp==0.3.0 python scripts/mfp_goals.py --date <Datum> --plan <training|rest>
```

Ausgeben:

- geloggte Einträge mit kcal,
- Tabelle Tagesstand: gegessen / Ziel / Rest für kcal, Eiweiß, KH, Fett
  (Zucker und Natrium nur, wenn der Benutzer danach fragt),
- Mahlzeit-Budget der gerade geloggten Mahlzeit (z. B. „Frühstück 465 / 541 kcal"),
- ein Satz Einordnung, wenn ein Makro-Rest auffällig ist (z. B. viel Eiweiß
  offen, Fett fast aufgebraucht),
- Abweichung zwischen berechneter Tabelle und MFP-Summe, falls > 5 %.

Auch ohne Mahlzeit nutzbar: „Wie stehe ich heute?" ⇒ nur `mfp_goals.py`
ausführen und die Tabelle zeigen.

### 6. Lücke schließen („Was fehlt mir noch?", oder automatisch nach Abend/Snack)

Das Ziel des Benutzers ist, die Tageswerte zu **erreichen**. Nach der
Abendmahlzeit, bei einem Snack nach 17 Uhr oder auf Nachfrage:

1. Rest für kcal, Eiweiß, KH, Fett aus `mfp_goals.py` nehmen.
2. Zwei bis drei konkrete Vorschläge machen, die die Lücke schließen, mit
   Menge und kcal/Eiweiß, priorisiert nach dem größten offenen Makro. Bei
   viel offenem Eiweiß und wenig offenem Fett: Magerquark, Skyr, Hähnchenbrust,
   Thunfisch im eigenen Saft, Eiklar, Whey. Bei offenen KH: Reis, Kartoffeln,
   Haferflocken, Obst. Bei offenem Fett: Nüsse, Olivenöl, Eier, Lachs.
3. Werte für die Vorschläge aus `fitness_search_food` holen (kein Raten),
   Vorschläge so bemessen, dass der Tag innerhalb ±100 kcal des Ziels landet
   und Eiweiß erreicht ist.
4. Wählt der Benutzer einen Vorschlag, läuft er als normale Mahlzeit durch
   Schritt 3 bis 5.

Beispielausgabe: „Offen: 620 kcal, 78 g Eiweiß, 40 g KH, 9 g Fett. Vorschlag:
500 g Magerquark (335 kcal, 60 g E) + 1 Banane 120 g (107 kcal, 25 g KH)
⇒ Rest 178 kcal, 17 g E. Oder: 250 g Hähnchenbrust …"

## Korrektur und Rückgängig

- „/mahlzeit rückgängig" oder „lösch die letzte Mahlzeit": Einträge der
  letzten Buchung per `fitness_delete_food(query=<Name>, date=<Datum>)`
  entfernen, `meal` mitgeben, um Duplikate in anderen Mahlzeiten zu schonen.
  Bei „matches multiple" den genaueren Namen aus der Fehlermeldung nehmen.
- Mengenänderung: `fitness_delete_food` + `fitness_log_food`, nicht
  `fitness_modify_food` (nicht atomar).

## Fehlerbilder

| Meldung | Bedeutung, Aktion |
| --- | --- |
| `session expired or not connected` | Cookie abgelaufen (≈ 30 Tage). Benutzer bitten: in Chrome einloggen, Cookie kopieren, `uvx --python 3.12 mfp-mcp auth`. Nichts weiter versuchen. |
| `403` / Cloudflare | `MFP_IMPERSONATE=chrome124` in der MCP-Konfiguration setzen, VPN aus. |
| Suche liefert 0 Treffer für alles | MFP hat die Suchseite geändert; auf `docs/mfp-tools.md` im Repo `MarqEwi/MyFitnessPal` verweisen, nichts loggen. |
| `couldn't read your MyFitnessPal profile` | `MFP_USERNAME=MarqEwi` fehlt in der Server-Konfiguration. |

## Schutzregeln (Hauptkonto)

- Pro Aufruf höchstens eine Mahlzeit schreiben; nie mehrere Tage in einer
  Schleife.
- Einen fehlgeschlagenen `fitness_log_food`-Aufruf nicht automatisch
  wiederholen; erst nachlesen (`fitness_get_day`), ob der Eintrag trotz Fehler
  angekommen ist, damit nichts doppelt gebucht wird.
- Löschen nur für Einträge, die in dieser Sitzung selbst angelegt wurden oder
  die der Benutzer ausdrücklich benennt.
