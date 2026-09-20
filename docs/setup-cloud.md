# Einrichtung für Handy und Cloud (ohne PC)

Ziel: `/mahlzeit` funktioniert in jeder Claude-Code-Sitzung, die aus diesem
Repo gestartet wird, auch vom Handy aus, und unabhängig davon, ob der PC an
ist. Dafür läuft der MCP-Server in der Cloud-Umgebung von Claude Code und
bekommt das Session-Cookie aus einer Umgebungsvariable.

Entscheidung des Kontoinhabers (2026-09-16): Das Cookie des Hauptkontos darf
in der Cloud-Umgebung hinterlegt werden; das Risiko (Zugang zum MFP-Konto
liegt bei Anthropic im Umgebungs-Speicher) ist bewusst akzeptiert.

## Was das Repo bereits mitbringt

| Datei | Zweck |
| --- | --- |
| `.mcp.json` | Registriert den MCP-Server `myfitnesspal` für jede Sitzung in diesem Repo (Cloud und PC). Das Cookie kommt aus `MFP_COOKIE`, der Benutzername ist fest `MarqEwi`. |
| `.claude/skills/mahlzeit/SKILL.md` | Die Skill `/mahlzeit`, als Projekt-Skill in jeder Sitzung verfügbar. |

Geprüft am 2026-09-16: Cloudflare lässt Anfragen aus der Cloud-Umgebung
durch (Startseite 200, geschützte Seiten leiten ohne Challenge zum Login um).

## Einmalig: Cookie in der Cloud-Umgebung hinterlegen

1. Am PC in Chrome ein **Inkognito-Fenster** öffnen (`Strg+Umschalt+N`),
   dort bei myfitnesspal.com einloggen. `F12` → **Application** →
   **Cookies** → `https://www.myfitnesspal.com` → Wert von
   `__Secure-next-auth.session-token` kopieren. Danach das Inkognito-Fenster
   **schließen, nicht ausloggen**. Grund: Ein Token aus dem normalen Chrome
   stirbt, sobald Chrome oder die App die Session rotieren (beobachtet nach
   1 Stunde bzw. 2 Tagen); die Inkognito-Session rotiert niemand.
2. Im Browser <https://claude.ai/code> öffnen. Direkt **über dem
   Eingabefeld** steht eine Schaltfläche mit Wolken-Symbol und dem Namen der
   aktuellen Umgebung, meist **Default**. Darauf klicken. Im aufklappenden
   Menü unter **Cloud** mit der Maus über die Umgebung fahren; rechts
   erscheint ein **Zahnrad**. Darauf klicken, es öffnet sich der Dialog
   „Update cloud environment". (Es gibt keine eigene Einstellungsseite und
   keine URL dafür; nur dieser Weg.)
3. Im Dialog unter **Environment variables** eintragen:

   ```
   MFP_COOKIE=<der kopierte Wert>
   ```

   Speichern. Die Variable gilt für alle **neuen** Sitzungen dieser Umgebung;
   laufende Sitzungen bekommen sie nicht mehr. Der Hinweis im Dialog, dass
   jeder Nutzer der Umgebung die Werte lesen kann, betrifft bei einem
   persönlichen Konto nur einen selbst.

   Doku: <https://code.claude.com/docs/en/cloud-environments#configure-your-environment>

4. Neue Sitzung im Repo `MarqEwi/MyFitnessPal` starten und testen:

   ```
   Zeig mir mein MFP-Tagebuch von heute mit Tagessummen.
   ```

   Beim ersten Werkzeugaufruf fragt Claude Code, ob der Projekt-MCP-Server
   aus `.mcp.json` benutzt werden darf; einmal erlauben.

## Vom Handy aus

Claude-App öffnen → **Code** → Repo `MyFitnessPal` → neue Sitzung → tippen
oder diktieren:

```
/mahlzeit Abend: 200 g Lachs, 150 g Kartoffeln, 1 EL Butter
```

Die Skill zeigt die Tabelle mit kcal und Makros, fragt „So eintragen?" und
schreibt erst nach „ja" ins Tagebuch. Auch ohne `/mahlzeit` geht es, z. B.
„Was habe ich gestern gegessen?" oder „Lösch den Lachs von heute Abend".

## Wenn die Session abläuft (etwa alle 30 Tage)

Die Werkzeuge antworten dann mit „session expired or not connected". Dann:
neues Cookie wie oben kopieren, in den Umgebungs-Einstellungen den Wert von
`MFP_COOKIE` ersetzen, neue Sitzung starten. Auf dem PC zusätzlich einmal
`uvx --python 3.12 mfp-mcp auth` ausführen, damit der lokale Stand ebenfalls
frisch ist.

## PC und Cloud nebeneinander

Auf dem PC gibt es den Server zweimal: einmal im User-Scope (aus dem
Setup-Skript, mit lokal gespeichertem Cookie) und einmal über `.mcp.json`,
sobald Claude im Repo-Ordner gestartet wird. Beide heißen `myfitnesspal`;
im Repo-Ordner gewinnt `.mcp.json`. Ist `MFP_COOKIE` auf dem PC nicht
gesetzt, bleibt die Variable leer und `mfp-mcp` nimmt automatisch das lokal
gespeicherte Cookie aus `cookies.json`. Es ist also nichts weiter zu tun.
