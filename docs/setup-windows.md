# Einrichtung unter Windows (Chrome, Claude Code)

Voraussetzungen: Windows 10/11, Chrome mit aktivem Login auf
myfitnesspal.com, Claude Code CLI (`claude --version`), PowerShell.

Das Skript `scripts\setup-mfp-mcp.ps1` führt die Schritte 1 bis 5 aus und
prüft jeden einzeln. Die manuelle Variante steht hier zum Nachvollziehen.

## Schritt 0: PowerShell vorbereiten

- PowerShell **ohne** Administratorrechte öffnen (Startmenü → „PowerShell").
  Ein Admin-Fenster startet in `C:\WINDOWS\system32`; dort gehört das Repo
  nicht hin.
- Windows blockiert lokale `.ps1`-Skripte standardmäßig („Ausführung von
  Skripts auf diesem System deaktiviert"). Einmalig für den eigenen Benutzer
  freigeben:

  ```powershell
  Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
  ```

  Wer das nicht dauerhaft will, startet das Skript stattdessen so:

  ```powershell
  powershell -ExecutionPolicy Bypass -File .\scripts\setup-mfp-mcp.ps1
  ```

- Repo in einen eigenen Arbeitsordner klonen. `C:\dev` ist bewusst
  außerhalb des Benutzerprofils: Dort blockiert der „Überwachte
  Ordnerzugriff" von Windows Defender (Ransomware-Schutz) `git.exe` gern mit
  `could not create work tree dir ... Permission denied`.

  ```powershell
  New-Item -ItemType Directory -Force C:\dev | Out-Null
  cd C:\dev
  git clone https://github.com/MarqEwi/MyFitnessPal
  cd MyFitnessPal
  git checkout claude/festive-mccarthy-x1f2gt
  ```

  Kommt der Fehler auch dort: Windows-Sicherheit → Viren- & Bedrohungsschutz
  → Ransomware-Schutz → Überwachter Ordnerzugriff → Blockierungsverlauf
  prüfen und `git.exe` zulassen.

## Schritt 1: Python 3.10+ und uv prüfen

```powershell
py -3 --version        # oder: python --version  → 3.10 bis 3.13 sind ok
uv --version
```

Fehlt uv:

```powershell
winget install --id astral-sh.uv -e
# oder ohne winget:
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Danach ein neues PowerShell-Fenster öffnen, damit `uv` im PATH ist.
uv bringt bei Bedarf selbst ein passendes Python mit; ein separat installiertes
Python ist nicht zwingend.

Prüfung: `uvx mfp-mcp --help` zeigt die Optionen `serve` und `auth`.

## Schritt 2: Session-Cookie aus Chrome kopieren

`mfp-mcp` zieht das Cookie **nicht** automatisch aus Chrome (unter Windows ist
das seit Chrome 127 auch für andere Tools nicht mehr möglich). Deshalb:

1. In Chrome auf <https://www.myfitnesspal.com> einloggen und das Tagebuch
   einmal öffnen.
2. `F12` drücken → Reiter **Application** (deutsch: **Anwendung**) →
   links **Storage → Cookies → https://www.myfitnesspal.com**.
3. Die Zeile `__Secure-next-auth.session-token` anklicken. Der Wert steht in
   der Spalte *Value*; alternativ unten im Feld *Cookie Value* markieren und
   mit `Strg+C` kopieren. Der Wert ist eine lange Zeichenkette ohne
   Leerzeichen, oft beginnend mit `eyJ`.
4. Terminal:

   ```powershell
   uvx mfp-mcp auth
   ```

   Den Wert bei „Paste cookie" einfügen (Eingabe bleibt unsichtbar), Enter.
   Fragt das Tool nach dem Benutzernamen, `MarqEwi` eingeben (nicht die
   E-Mail).

5. Erwartete Ausgabe: `Connected as MarqEwi. Cookies saved to ...cookies.json`.

**Fehlerbilder:**

| Meldung | Ursache und Abhilfe |
| --- | --- |
| `Those cookies didn't authenticate ... 403` | Cloudflare blockt. Erst `$env:MFP_IMPERSONATE="chrome124"` setzen und erneut `uvx mfp-mcp auth`; VPN ausschalten. |
| `couldn't read your MyFitnessPal profile` | Beim Dialog den Benutzernamen eingeben oder dauerhaft `MFP_USERNAME=MarqEwi` setzen. |
| `No cookie received` | Der Wert wurde nicht eingefügt; Rechtsklick ins Fenster fügt in PowerShell ein. |

**Sicherheit des Cookies:** Das Cookie entspricht dem vollen Konto-Zugang.
Es liegt nach `auth` unter
`%LOCALAPPDATA%\myfitnesspal-mcp\myfitnesspal-mcp\cookies.json`. Das
Setup-Skript setzt darauf `icacls <datei> /inheritance:r /grant:r "$env:USERNAME:(R,W)"`,
damit nur der eigene Benutzer lesen darf. Niemals in `.env`, Repo-Dateien oder
Chat-Verläufe kopieren; `.gitignore` in diesem Repo schließt `cookies.json`,
`token.txt` und `.env` aus.

**Gültigkeit:** ungefähr 30 Tage. Läuft die Session ab, melden die Werkzeuge
„session expired or not connected". Dann Schritt 2 wiederholen (in Chrome
eingeloggt bleiben, neues Cookie kopieren, `uvx mfp-mcp auth`).
Wer das nicht manuell machen will:

```powershell
uvx --from "mfp-mcp[autorefresh]" playwright install chromium
uvx --from "mfp-mcp[autorefresh]" mfp-mcp auth
```

und in Schritt 3 den Server als `uvx --from "mfp-mcp[autorefresh]" mfp-mcp`
registrieren. Dann rotiert ein headless Chromium-Profil das Token selbst.

## Schritt 3: MCP-Server in Claude Code registrieren (User-Scope)

```powershell
claude mcp add --scope user myfitnesspal -- uvx mfp-mcp
claude mcp get myfitnesspal      # Status: Connected
```

Wer `MFP_USERNAME` oder `MFP_IMPERSONATE` braucht:

```powershell
claude mcp add --scope user myfitnesspal -e MFP_USERNAME=MarqEwi -e MFP_IMPERSONATE=chrome124 -- uvx mfp-mcp
```

Entfernen: `claude mcp remove myfitnesspal -s user`.

## Schritt 4: Skill installieren

```powershell
New-Item -ItemType Directory -Force "$env:USERPROFILE\.claude\skills\mahlzeit" | Out-Null
Copy-Item skills\mahlzeit\SKILL.md "$env:USERPROFILE\.claude\skills\mahlzeit\SKILL.md" -Force
```

In einer neuen Claude-Code-Sitzung ist `/mahlzeit` dann verfügbar.

## Schritt 5: Lesend testen (Aufgabe Schritt 1.5)

Variante A, im Terminal ohne Claude:

```powershell
uv run --with mfp-mcp==0.3.0 python scripts\mfp_smoke_test.py
```

zeigt Tagebuch heute und gestern mit Einträgen pro Mahlzeit, Tagessummen
(kcal, Eiweiß, KH, Fett) und die **tatsächlichen Mahlzeitnamen** des Kontos.
Diese Namen in `skills/mahlzeit/SKILL.md` (Abschnitt „Mahlzeiten-Zuordnung")
eintragen und die Skill erneut kopieren.

Variante B, in Claude Code:

```
Zeig mir mein MFP-Tagebuch von heute und gestern, Einträge pro Mahlzeit
und Tages-Summen für Kalorien, Eiweiß, Kohlenhydrate, Fett.
```

Claude ruft `fitness_get_day` zweimal auf.

## Schritt 6: Schreibend testen (Aufgabe Schritt 2)

```powershell
uv run --with mfp-mcp==0.3.0 python scripts\mfp_smoke_test.py --write
```

Das Skript sucht „Banane", zeigt die Treffer mit Portionsgrößen, fragt vor
dem Schreiben nach Bestätigung, trägt 120 g unter der vierten Mahlzeit
(Snacks) für heute ein, liest das Tagebuch erneut, zeigt den Eintrag, löscht
ihn wieder und bestätigt die Löschung.

Anlegen und Löschen eines eigenen Lebensmittels („TEST Claude", 100 g,
100 kcal, 10 g Eiweiß, 10 g KH, 2 g Fett):

```powershell
uv run --with mfp-mcp==0.3.0 python scripts\mfp_smoke_test.py --custom-food
```

Dieser Teil ist nicht durch den MCP-Server abgedeckt und benutzt die
Web-Endpunkte aus `docs/mfp-tools.md`, Abschnitt 4. Schlägt er fehl, die
Ausgabe (Endpunkt + HTTP-Status) in `docs/mfp-tools.md`, Abschnitt 6
eintragen.

Mit `--yes` entfällt die Rückfrage, mit `--date YYYY-MM-DD` lässt sich der
Testtag ändern.
