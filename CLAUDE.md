# Projekt-Hinweise für Claude

## Arbeitsordner auf dem Windows-PC

Neue Ordner und Klone auf dem PC des Benutzers immer unter
`E:\Users\Marc\Claude Projekte` anlegen. Dieses Repo liegt dort als
`E:\Users\Marc\Claude Projekte\MyFitnessPal`. Nie nach `C:\Users\Marc`,
`C:\dev` oder `C:\WINDOWS\system32` klonen.

## Konto und Sicherheit

- MyFitnessPal-Hauptkonto `MarqEwi`; Schreibvorgänge nur nach Freigabe,
  Testeinträge im selben Lauf wieder löschen (siehe README).
- Das Session-Cookie bleibt auf dem PC; nie in Chat, Repo oder Cloud-Sitzung
  einfügen. `cookies.json`, `token.txt`, `.env` sind in `.gitignore`.

## Werkzeuge

- MCP-Server `mfp-mcp` 0.3.0 über `uvx --python 3.12 mfp-mcp` (Python 3.12
  wegen `lxml`), registriert im User-Scope als `myfitnesspal`.
- Alle Befehle für Windows-PowerShell ohne Adminrechte formulieren.
