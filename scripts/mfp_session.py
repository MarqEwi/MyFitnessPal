#!/usr/bin/env python3
"""Selbstverlängernde MyFitnessPal-Session für mfp-mcp.

Befund (2026-09-20): Das Cookie `__Secure-next-auth.session-token` ist ein
NextAuth-JWE mit 30 Tagen Laufzeit, aber der darin verpackte Zugang läuft nach
wenigen Stunden ab; Tagebuch-Aufrufe scheitern dann mit 302/403. Ein Aufruf von
`GET https://www.myfitnesspal.com/api/auth/session` mit dem alten Cookie liefert
ein frisches Cookie (Set-Cookie, wieder 30 Tage). Genau das macht dieses Skript:

    python scripts/mfp_session.py refresh   # Token verlängern und speichern
    python scripts/mfp_session.py serve     # verlängern, dann mfp-mcp starten (stdio);
                                            # bei Auth-Fehlern im Betrieb erneut verlängern
    python scripts/mfp_session.py serve --http --host 0.0.0.0 --port 8484   # HTTP-Modus (NAS)
    python scripts/mfp_session.py status    # lebt die Session?

Quelle des Start-Tokens (erste Fundstelle gewinnt): Datei cookies.json von
`mfp-mcp auth` (wird von diesem Skript aktuell gehalten), sonst MFP_COOKIE aus
der Umgebung. Jedes verlängerte Token wird nach cookies.json geschrieben
(nur Besitzer lesbar). Aufruf immer per
`uv run --python 3.12 --with mfp-mcp==0.3.0 python scripts/mfp_session.py …`.
"""

from __future__ import annotations

import logging
import os
import sys
import time

os.environ.setdefault("MFP_USERNAME", "MarqEwi")
logging.getLogger("myfitnesspal").setLevel(logging.ERROR)

try:
    from curl_cffi import requests as cffi_requests
    from myfitnesspal_mcp import auth, config, mfp_client
except ImportError:
    sys.exit("mfp-mcp fehlt. Aufruf: uv run --python 3.12 --with mfp-mcp==0.3.0 python scripts/mfp_session.py …")

SESSION_URL = "https://www.myfitnesspal.com/api/auth/session"
CHECK_URL = "https://www.myfitnesspal.com/user/auth_token?refresh=true"
log = logging.getLogger("mfp_session")


REFRESH_COOKIE = "refresh-token-data"


def current_cookies() -> dict[str, str]:
    """Kompletter Cookie-Satz: cookies.json zuerst (dort landet jede
    Verlängerung), sonst MFP_COOKIE (voller Cookie-Header oder nur Token)."""
    saved = auth._read_saved().get("cookies") or {}
    if saved.get(auth.SESSION_COOKIE):
        return dict(saved)
    env = config.cookie_env()
    return auth.parse_cookie_input(env) if env else {}


def _session_with(cookies: dict[str, str]) -> cffi_requests.Session:
    s = cffi_requests.Session(impersonate=config.impersonate())
    for name, value in cookies.items():
        s.cookies.set(name, value, domain=".myfitnesspal.com")
    return s


def _jar_to_dict(s: cffi_requests.Session, base: dict[str, str]) -> dict[str, str]:
    merged = dict(base)
    for c in s.cookies.jar:
        if c.value is not None and c.value != "delete":
            merged[c.name] = c.value
    return merged


def cookies_alive(cookies: dict[str, str]) -> bool:
    """Prüft über denselben Weg wie der Server (python-myfitnesspal-Client mit
    Bearer-Token-Abruf). Ein roher GET auf /user/auth_token antwortet auch bei
    gültiger Session mit 302 und taugt nicht als Prüfung."""
    try:
        mfp_client.build_client(cookies)
        return True
    except Exception:  # noqa: BLE001
        return False


def refresh_cookies(cookies: dict[str, str]) -> dict[str, str] | None:
    """Verlängert die Session über /api/auth/session mit dem vollen Cookie-Satz
    (Session-Token + refresh-token-data) und prüft, dass das Ergebnis wirklich
    nutzbar ist. Ohne refresh-token-data liefert MFP zwar ein neues Session-
    Token, aber ohne inneren Zugang (Tagebuch antwortet 302); das gilt als Fehler."""
    s = _session_with(cookies)
    r = s.get(SESSION_URL, allow_redirects=False, timeout=30)
    if r.status_code != 200 or '"user"' not in r.text:
        log.warning("api/auth/session antwortete %s (Session abgelaufen)", r.status_code)
        return None
    new = _jar_to_dict(s, cookies)
    if not cookies_alive(new):
        log.warning("Verlängerung ohne Wirkung: Tagebuch weiterhin gesperrt (fehlt %s?)", REFRESH_COOKIE)
        return None
    return new


def persist(cookies: dict[str, str]) -> None:
    auth.save_cookies(cookies, username=os.environ.get("MFP_USERNAME"))
    os.environ["MFP_COOKIE"] = "; ".join(f"{k}={v}" for k, v in cookies.items())  # mfp-mcp liest die Umgebung vor der Datei
    mfp_client.reset()


def candidate_cookie_sets() -> list[dict[str, str]]:
    """Alle bekannten Cookie-Sätze, zuerst cookies.json, dann MFP_COOKIE (falls
    abweichend). Die Umgebung kann ein neueres Login enthalten als die Datei."""
    sets = []
    saved = auth._read_saved().get("cookies") or {}
    if saved.get(auth.SESSION_COOKIE):
        sets.append(dict(saved))
    env = config.cookie_env()
    if env:
        parsed = auth.parse_cookie_input(env)
        if parsed.get(auth.SESSION_COOKIE) and all(parsed.get(auth.SESSION_COOKIE) != s.get(auth.SESSION_COOKIE) for s in sets):
            sets.append(parsed)
    return sets


def refresh_and_persist(reason: str = "") -> bool:
    sets = candidate_cookie_sets()
    if not sets:
        log.error("keine Cookies: weder cookies.json noch MFP_COOKIE")
        return False
    for cookies in sets:
        if cookies_alive(cookies):
            if cookies is not sets[0]:
                persist(cookies)  # Umgebung hatte das lebende Login: übernehmen
            return True
    for cookies in sets:
        new = refresh_cookies(cookies)
        if new:
            persist(new)
            log.info("Session verlängert%s", f" ({reason})" if reason else "")
            return True
    log.error("Verlängerung fehlgeschlagen%s: alle bekannten Sessions abgelaufen (MFP-Session stirbt nach ca. 30 min ohne Aufruf)", f" ({reason})" if reason else "")
    return False


def cmd_status() -> int:
    cookies = current_cookies()
    if not cookies:
        print("FEHLER: keine Cookies vorhanden"); return 1
    print(f"Cookies vorhanden: {sorted(cookies)}")
    print(f"{REFRESH_COOKIE}: {'vorhanden' if cookies.get(REFRESH_COOKIE) else 'FEHLT (Verlängerung nicht möglich, vollen Cookie-Header hinterlegen)'}")
    alive = cookies_alive(cookies)
    print("Tagebuch-Zugang:", "nutzbar" if alive else "abgelaufen")
    if not alive:
        new = refresh_cookies(cookies)
        print("Verlängerung über api/auth/session:", "OK" if new else "FEHLER (neuer Login im Browser nötig)")
        if new:
            persist(new); print("gespeichert")
    return 0


def cmd_refresh() -> int:
    ok = refresh_and_persist("manuell")
    print("OK: Session verlängert und gespeichert" if ok else "FEHLER: Verlängerung fehlgeschlagen, neues Cookie aus dem Browser nötig")
    return 0 if ok else 1


def cmd_serve() -> int:
    """Token verlängern, dann mfp-mcp starten. Der Server ruft bei Auth-Fehlern
    `refresh.refresh_session()` auf; das wird hier auf die HTTP-Verlängerung umgebogen."""
    from myfitnesspal_mcp import refresh as mfp_refresh

    refresh_and_persist("Start")

    def http_refresh_session() -> None:
        if not refresh_and_persist("Auth-Fehler im Betrieb"):
            time.sleep(2)
            refresh_and_persist("zweiter Versuch")
        mfp_client.reset()

    mfp_refresh.refresh_session = http_refresh_session
    mfp_refresh.available = lambda: True
    mfp_refresh.profile_seeded = lambda: True

    from myfitnesspal_mcp import cli
    # weitere Argumente (z. B. --http --host 0.0.0.0 --port 8484) an mfp-mcp durchreichen
    sys.argv = [sys.argv[0], "serve", *sys.argv[2:]]
    cli.main()
    return 0


def main() -> int:
    logging.basicConfig(level=logging.INFO, stream=sys.stderr, format="mfp_session: %(message)s")
    cmd = sys.argv[1] if len(sys.argv) > 1 else "serve"
    return {"status": cmd_status, "refresh": cmd_refresh, "serve": cmd_serve}.get(cmd, cmd_serve)()


if __name__ == "__main__":
    sys.exit(main())
