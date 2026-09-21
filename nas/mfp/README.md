# MyFitnessPal-MCP auf der NAS

Zweck: Ein immer laufender Ort für die MFP-Session. Der Server verlängert die
Session selbst (`scripts/mfp_session.py`), ein zweiter Container fasst sie alle
10 Minuten an, weil MFP-Sessions nach etwa 30 Minuten ohne Aufruf sterben
(Messungen in `docs/mfp-tools.md`, Abschnitt 4b). Einmal einloggen, dann
läuft es, bis MFP etwas Grundlegendes ändert.

Ressourcen: Image ca. 250 MB, RAM Server ca. 80 MB, Keepalive ca. 60 MB
(Limits 256 m / 128 m). Kein Port zwingend; 8484 nur für den LAN-Zugriff vom PC.

## Einrichtung (Kurzfassung, Details im NAS-Thread)

1. Ordner anlegen: `/volume1/Grundlagen/MyFitnessPal/{sync,keys,daten}`, Eigentümer `1001:10`,
   `keys` mit `chmod 700`.
2. Diesen Ordner (`nas/mfp/`) plus `scripts/mfp_session.py` nach `sync/` übertragen
   (Zeilenenden auf LF bereinigen, siehe NAS-Regeln).
3. `.env` aus `.env.example` mit dem Session-Token füllen.
4. `docker compose up -d --build`. Beim ersten Start übernimmt der Server das Token aus
   `MFP_COOKIE` nach `keys/cookies.json`. Danach `MFP_COOKIE` aus `.env` entfernen.
5. Prüfen: `docker compose logs mfp-keepalive` zeigt alle 10 min „Tagebuch-Zugang: nutzbar".

## Anbindung

- **PC (LAN):** `claude mcp add --scope user --transport http myfitnesspal http://192.168.2.101:8484/mcp`
  ersetzt die lokale Registrierung; kein Cookie mehr auf dem PC nötig.
- **Cloud/Handy:** Der Server hat keine eigene Zugangskontrolle und darf nicht direkt ins
  Internet. Weg dafür: Cloudflare Tunnel (`cloudflared`-Container, ausgehende Verbindung,
  kein Port-Forwarding) mit Cloudflare-Access-Service-Token; in `.mcp.json` dann
  `"type": "http", "url": "https://mfp.<deine-domain>/mcp", "headers": {"CF-Access-Client-Id": "${CF_ID}", "CF-Access-Client-Secret": "${CF_SECRET}"}`
  und die beiden Werte als Umgebungsvariablen der Claude-Cloud-Umgebung. Bis dahin hält
  der NAS-Keepalive auch das Token in `MFP_COOKIE` der Cloud am Leben, sofern es aus
  demselben Login stammt; nur die 30-Tage-Laufzeit des Cloud-Tokens bleibt.
