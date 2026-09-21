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

## Stand STEVENAS (21.09.2026)

In Betrieb seit 21.09.2026, eingerichtet vom Master PC (MASTERPC-MARC).

```
/volume1/Grundlagen/MyFitnessPal/
├── sync/    755  docker-compose.yml, Dockerfile, keepalive.sh, mfp_session.py,
│                 bootstrap.py, .env (600), .env.bak-20260921 (600)
├── keys/    700  cookies.json (600, UID 1001) – die lebende Session
└── daten/   755  SQLite-Cache
```

Container `mfp-server` und `mfp-keepalive`, Compose-Projekt **`mfp`**, Port **8484**
(`http://192.168.2.101:8484/mcp`), Image 351 MB, RAM 92 MB bzw. 2,6 MB.

**Die `.env` enthält kein Token mehr.** Nach dem ersten Login wurde `MFP_COOKIE` entfernt;
die Session lebt in `keys/cookies.json` und wird vom Keepalive alle 10 Minuten angefasst.
Übrig bleibt nur `MFP_ALLOWED_HOSTS`.

### Abweichungen der NAS-Kopie gegenüber diesem Ordner

Auf der NAS liegt alles flach in `sync/`, deshalb dort:

| Datei | Repo-Fassung | NAS-Fassung |
|---|---|---|
| `docker-compose.yml` | `context: ../../..`, `dockerfile: nas/mfp/Dockerfile` | `context: .`, `dockerfile: Dockerfile` |
| `Dockerfile` | `COPY scripts/mfp_session.py …` | `COPY mfp_session.py …` |

### Zwei Stolpersteine bei der Erstinbetriebnahme

1. **`cookies.json` wurde nicht geschrieben.** `refresh_and_persist()` speichert einen lebenden
   Cookie-Satz aus `MFP_COOKIE` nicht, wenn `cookies.json` noch leer ist – dann ist der
   Umgebungssatz selbst `sets[0]`, und die Bedingung `cookies is not sets[0]` greift nicht.
   Der Keepalive fand deshalb „keine Cookies vorhanden". Einmalig gelöst mit `bootstrap.py`
   (prüft das Token und schreibt es nach `cookies.json`). Die Datei bleibt für künftige
   Neuaufsetzungen im `sync/`-Ordner liegen.
2. **LAN-Zugriff schlug mit `421 Invalid Host header` fehl.** Das MCP-SDK lässt per
   DNS-Rebinding-Schutz nur `127.0.0.1`, `localhost` und `[::1]` als Host-Header zu.
   Gelöst über `MFP_ALLOWED_HOSTS=192.168.2.101:*,stevenas:*`, das die Vorgabe **ergänzt**
   statt sie abzuschalten – ein fremder Host-Header wird weiterhin mit 421 abgewiesen.

### Projektname

Die Compose setzt `name: mfp`. Ohne das leitet Compose den Projektnamen vom Ordner ab, und der
heißt hier wie bei `/volume1/Grundlagen/training/sync` schlicht `sync`. Beide Projekte wären
dann dieselbe Einheit: `docker compose down` im MyFitnessPal-Ordner würde `training-sync`
mit stoppen, `--remove-orphans` ihn löschen.

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
