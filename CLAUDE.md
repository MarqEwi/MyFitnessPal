# Projekt-Hinweise für Claude

## Arbeitsordner auf dem Windows-PC

Neue Ordner und Klone auf dem PC des Benutzers immer unter
`E:\Users\Marc\Claude Projekte` anlegen. Dieses Repo liegt dort als
`E:\Users\Marc\Claude Projekte\MyFitnessPal`. Nie nach `C:\Users\Marc`,
`C:\dev` oder `C:\WINDOWS\system32` klonen.

## Konto und Sicherheit

- MyFitnessPal-Hauptkonto `MarqEwi`; Schreibvorgänge nur nach Freigabe,
  Testeinträge im selben Lauf wieder löschen (siehe README).
- Das Session-Cookie liegt auf dem PC (`cookies.json`) und als
  Umgebungsvariable `MFP_COOKIE` in der Cloud-Umgebung (vom Kontoinhaber so
  entschieden). Nie ins Repo oder in Chat-Nachrichten schreiben.
  `cookies.json`, `token.txt`, `.env` sind in `.gitignore`.

## Werkzeuge

- MCP-Server `mfp-mcp` 0.3.0 über `uvx --python 3.12 mfp-mcp` (Python 3.12
  wegen `lxml`): auf dem PC im User-Scope, in jeder Repo-Sitzung über
  `.mcp.json`, jeweils als `myfitnesspal`. Skill `/mahlzeit` liegt in
  `.claude/skills/mahlzeit/SKILL.md`.
- Makro-Ziele und Mahlzeit-Budgets liefert nur `scripts/mfp_goals.py`
  (Endpunkt `/v2/nutrient-goals`), der MCP-Server kennt nur das kcal-Ziel.
  Eigene Lebensmittel: `scripts/mfp_food.py`. Beide laufen per
  `uv run --python 3.12 --with mfp-mcp==0.3.0 python scripts/<name>.py`.
- Mahlzeiten im Konto heißen breakfast, lunch, dinner, snacks (englische
  Standardnamen, bestätigt 2026-09-17); Position und Name stimmen überein.
- Alle Befehle für Windows-PowerShell ohne Adminrechte formulieren.
