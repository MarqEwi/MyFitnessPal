# MyFitnessPal aus Claude Code heraus lesen und beschreiben

Dieses Repo enthält alles, was auf dem Windows-Rechner nötig ist, um das
MyFitnessPal-Tagebuch (Konto `MarqEwi`) aus Claude Code heraus zu lesen und zu
beschreiben:

| Was | Wo |
| --- | --- |
| Auswahl des MCP-Servers, Endpunkte, bekannte Fehler | [`docs/mfp-tools.md`](docs/mfp-tools.md) |
| Schritt-für-Schritt-Einrichtung unter Windows inkl. Cookie | [`docs/setup-windows.md`](docs/setup-windows.md) |
| PowerShell-Skript, das die Einrichtung ausführt und prüft | [`scripts/setup-mfp-mcp.ps1`](scripts/setup-mfp-mcp.ps1) |
| Lese-/Schreib-Smoke-Test (Tagebuch, Banane, eigenes Lebensmittel) | [`scripts/mfp_smoke_test.py`](scripts/mfp_smoke_test.py) |
| Claude-Code-Skill `/mahlzeit` | [`skills/mahlzeit/SKILL.md`](skills/mahlzeit/SKILL.md) |

## Risiken in drei Sätzen

1. MyFitnessPal hat keine öffentliche API; jede Lösung spricht die internen
   Endpunkte des Web-Clients an, was laut den
   [MFP-Nutzungsbedingungen](https://www.myfitnesspal.com/terms-of-service)
   (automatisierter Zugriff, Scraping) untersagt ist.
2. MFP kann das Konto deshalb sperren oder die Session ungültig machen; bei
   normalem Nutzungsumfang (ein paar Aufrufe pro Tag von einer privaten IP)
   sind bisher keine Sperrungen dokumentiert, aber es gibt keine Garantie.
3. Jede Änderung an der MFP-Webseite (Cloudflare, NextAuth, HTML der
   Suchseite) kann Lesen oder Schreiben von heute auf morgen kaputtmachen;
   das ist bei einem der beiden Kandidaten bereits passiert (siehe
   `docs/mfp-tools.md`).

**Entscheidung, die noch aussteht:** Hauptkonto oder Zweitkonto? Ein
Zweitkonto schützt die eigene Historie vor Sperrung und Fehlbuchungen, hat aber
keine Ziele, Historie und Lieblingslebensmittel. Die Einrichtung ist für beide
Varianten identisch, nur das Cookie stammt aus dem jeweils eingeloggten Konto.

## Kurzfassung der Einrichtung

```powershell
# im Repo-Ordner, PowerShell
.\scripts\setup-mfp-mcp.ps1
```

Das Skript prüft Python und uv, installiert `mfp-mcp`, fragt das Session-Cookie
ab, registriert den Server in Claude Code (User-Scope), kopiert die Skill nach
`%USERPROFILE%\.claude\skills\mahlzeit\` und startet anschließend den
Lese-Smoke-Test. Details und Fehlerbehebung in `docs/setup-windows.md`.
