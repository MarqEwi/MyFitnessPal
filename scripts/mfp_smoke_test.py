#!/usr/bin/env python3
"""Lese-/Schreib-Smoke-Test gegen MyFitnessPal über die Bibliotheken von mfp-mcp.

Aufruf (Windows, PowerShell, im Repo-Ordner):

    uv run --with mfp-mcp==0.3.0 python scripts\\mfp_smoke_test.py             # nur lesen
    uv run --with mfp-mcp==0.3.0 python scripts\\mfp_smoke_test.py --write     # Banane 120 g rein und wieder raus
    uv run --with mfp-mcp==0.3.0 python scripts\\mfp_smoke_test.py --custom-food

Das Cookie kommt aus MFP_COOKIE oder aus der Datei, die `uvx mfp-mcp auth`
geschrieben hat. Jeder Schritt meldet OK oder FEHLER mit Endpunkt und
HTTP-Status, damit das Ergebnis in docs/mfp-tools.md übernommen werden kann.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, timedelta

try:
    from myfitnesspal_mcp import auth, config, diary, mfp_client
except ImportError:
    sys.exit(
        "mfp-mcp fehlt. Aufruf über: uv run --with mfp-mcp==0.3.0 python scripts/mfp_smoke_test.py"
    )

WEB = "https://www.myfitnesspal.com"
SNACK_MEAL = "snacks"  # mfp-mcp: Position 3 (0=breakfast, 1=lunch, 2=dinner, 3=snacks)
TEST_FOOD = {
    "description": "TEST Claude",
    "calories": 100,
    "protein": 10,
    "carbs": 10,
    "fat": 2,
    "serving_amount": 100,
    "serving_unit": "g",
}

RESULTS: list[tuple[str, str, str]] = []


def report(test: str, ok: bool, detail: str = "") -> None:
    status = "OK" if ok else "FEHLER"
    RESULTS.append((test, status, detail))
    print(f"[{status}] {test}" + (f" - {detail}" if detail else ""))


def num(value) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def show_day(client, day: date) -> object:
    mfp_day = client.get_date(day)
    print(f"\n=== Tagebuch {day.isoformat()} ===")
    for meal in mfp_day.meals:
        print(f"  {meal.name}:")
        if not meal.entries:
            print("    (leer)")
        for entry in meal.entries:
            t = entry.totals
            print(
                f"    - {entry.name}: {num(t.get('calories')):.0f} kcal, "
                f"E {num(t.get('protein')):.1f} g, KH {num(t.get('carbohydrates')):.1f} g, "
                f"F {num(t.get('fat')):.1f} g"
            )
    t = mfp_day.totals
    print(
        f"  Summe: {num(t.get('calories')):.0f} kcal, E {num(t.get('protein')):.1f} g, "
        f"KH {num(t.get('carbohydrates')):.1f} g, F {num(t.get('fat')):.1f} g"
    )
    goal = (mfp_day.goals or {}).get("calories")
    if goal:
        print(f"  Ziel: {num(goal):.0f} kcal")
    return mfp_day


def step_connect():
    print("== Schritt 1: Verbindung ==")
    if not auth.load_cookies():
        report("Cookie vorhanden", False, f"weder MFP_COOKIE noch {config.cookies_path()}")
        sys.exit(1)
    try:
        client = mfp_client.get_client()
    except Exception as exc:  # noqa: BLE001
        report("Login mit Session-Cookie", False, str(exc))
        sys.exit(1)
    report("Login mit Session-Cookie", True, f"Benutzer {client.effective_username}")
    return client


def step_read(client, today: date):
    print("\n== Schritt 1.5: Tagebuch lesen ==")
    names = None
    for day in (today, today - timedelta(days=1)):
        try:
            mfp_day = show_day(client, day)
            names = [m.name for m in mfp_day.meals]
            report(f"Tagebuch {day.isoformat()} lesen", True)
        except Exception as exc:  # noqa: BLE001
            report(f"Tagebuch {day.isoformat()} lesen", False, f"GET {WEB}/food/diary/...: {exc}")
    if names:
        print(f"\nMahlzeiten-Namen im Konto (Reihenfolge = meal_id 0..{len(names) - 1}): {names}")
        print("-> in skills/mahlzeit/SKILL.md, Abschnitt 'Mahlzeiten-Zuordnung' eintragen.")


def gram_candidate(candidates: list[dict], grams: float) -> tuple[dict, float] | None:
    """Erster Treffer, dessen erste Portion in g angegeben ist, plus Portionsanzahl."""
    for c in candidates:
        serving = (c.get("serving") or "").strip().lower()
        parts = serving.split()
        if len(parts) == 2 and parts[1] in ("g", "gram", "grams", "gramm"):
            try:
                per = float(parts[0].replace(",", "."))
            except ValueError:
                continue
            if per > 0:
                return c, round(grams / per, 3)
    return None


def step_search(client, query: str = "Banane") -> list[dict]:
    print(f"\n== Schritt 2.1: Suche '{query}' ==")
    try:
        candidates = diary.search_food(client, query, limit=8, with_macros=True)
    except Exception as exc:  # noqa: BLE001
        report("Suche", False, f"GET {WEB}/food/search: {exc}")
        return []
    if not candidates:
        report("Suche", False, "0 Treffer (HTML der Suchseite geändert? vgl. docs/mfp-tools.md)")
        return []
    for i, c in enumerate(candidates, 1):
        v = "verifiziert" if c.get("verified") else "unverifiziert"
        print(
            f"  {i}. {c['name']} [{c.get('brand') or '-'}] Portion {c.get('serving') or '?'}: "
            f"{num(c.get('calories')):.0f} kcal, E {num(c.get('protein')):.1f}, "
            f"KH {num(c.get('carbs')):.1f}, F {num(c.get('fat')):.1f} ({v}) "
            f"food_id={c['food_id']} weight_id={c['weight_id']}"
        )
    report("Suche", True, f"{len(candidates)} Treffer")
    return candidates


def confirm(prompt: str, assume_yes: bool) -> bool:
    if assume_yes:
        return True
    return input(f"{prompt} [j/N] ").strip().lower() in ("j", "ja", "y", "yes")


def step_write(client, today: date, candidates: list[dict], assume_yes: bool) -> None:
    print("\n== Schritt 2.2-2.4: Banane 120 g unter Snacks eintragen und wieder löschen ==")
    pick = gram_candidate(candidates, 120)
    if not pick:
        report("Gramm-basierten Treffer finden", False, "kein Treffer mit Portion in g; anderes Suchwort probieren (z. B. 'Banane roh')")
        return
    cand, qty = pick
    print(f"  Wähle: {cand['name']} ({cand.get('serving')}) x {qty} = 120 g")
    if not confirm("Eintrag jetzt ins echte Tagebuch schreiben?", assume_yes):
        report("Eintrag schreiben", False, "vom Benutzer abgebrochen")
        return
    try:
        res = diary.push_food(
            client, today, SNACK_MEAL, cand["name"], qty,
            food_id=cand["food_id"], weight_id=cand["weight_id"],
        )
        report("Eintrag schreiben", True, f"POST {WEB}/food/add -> {res}")
    except Exception as exc:  # noqa: BLE001
        report("Eintrag schreiben", False, f"POST {WEB}/food/add: {exc}")
        return

    mfp_day = show_day(client, today)
    found = [e for m in mfp_day.meals for e in m.entries if "banan" in e.name.lower()]
    if found:
        e = found[-1]
        report("Eintrag im Tagebuch sichtbar", True, f"{e.name}: {num(e.totals.get('calories')):.0f} kcal")
    else:
        report("Eintrag im Tagebuch sichtbar", False, "kein Eintrag mit 'Banan' gefunden")
        return

    try:
        # meal=None: Filter über den angezeigten Mahlzeitnamen funktioniert nur bei englischen Namen
        res = diary.delete_food(client, today, cand["name"], None)
        report("Eintrag löschen", True, f"POST {WEB}/food/remove/<id> -> {res}")
    except Exception as exc:  # noqa: BLE001
        report("Eintrag löschen", False, f"POST {WEB}/food/remove/<id>: {exc}")
        return
    mfp_day = client.get_date(today)
    still = [e for m in mfp_day.meals for e in m.entries if e.name == found[-1].name]
    report("Löschung bestätigt", not still, "" if not still else "Eintrag ist noch da")


def _csrf(client) -> str | None:
    r = client.session.get(f"{WEB}/api/auth/csrf", headers={"Accept": "application/json"})
    if r.status_code == 200:
        return r.json().get("csrfToken")
    print(f"  GET /api/auth/csrf -> HTTP {r.status_code}")
    return None


def step_custom_food(client, assume_yes: bool) -> None:
    print("\n== Schritt 2.5: eigenes Lebensmittel 'TEST Claude' anlegen und löschen ==")
    print("  (nicht Teil von mfp-mcp; Endpunkte des MFP-Web-Clients, siehe docs/mfp-tools.md Abschnitt 4)")
    if not confirm("Lebensmittel jetzt anlegen?", assume_yes):
        report("Eigenes Lebensmittel anlegen", False, "vom Benutzer abgebrochen")
        return
    csrf = _csrf(client)
    hdr = {"Accept": "application/json", "Content-Type": "application/json"}
    if csrf:
        hdr["x-csrf-token"] = csrf
    item = {
        "description": TEST_FOOD["description"],
        "brand_name": "Generic",
        "public": False,
        "type": "food",
        "country_code": "DE",
        "nutritional_contents": {
            "energy": {"unit": "calories", "value": TEST_FOOD["calories"]},
            "grams": 1,
            "protein": TEST_FOOD["protein"],
            "carbohydrates": TEST_FOOD["carbs"],
            "fat": TEST_FOOD["fat"],
        },
        "serving_sizes": [
            {"value": TEST_FOOD["serving_amount"], "unit": TEST_FOOD["serving_unit"],
             "nutrition_multiplier": 1, "gram_weight": 1, "fraction": False, "index": 0},
            {"value": 1, "unit": f"container ({TEST_FOOD['serving_amount']} {TEST_FOOD['serving_unit']} ea.)",
             "nutrition_multiplier": 1, "gram_weight": 1, "fraction": False, "index": 1},
        ],
    }
    r = client.session.post(f"{WEB}/api/services/foods", headers=hdr, data=json.dumps({"item": item}))
    if r.status_code not in (200, 201):
        report("Eigenes Lebensmittel anlegen", False, f"POST {WEB}/api/services/foods -> HTTP {r.status_code}: {r.text[:200]}")
        return
    new_id = None
    try:
        body = r.json()
        new_id = (body[0] if isinstance(body, list) else (body.get("item") or body)).get("id")
    except Exception:  # noqa: BLE001
        pass
    report("Eigenes Lebensmittel anlegen", True, f"HTTP {r.status_code}, id={new_id}")

    r = client.session.get(f"{WEB}/api/services/users/foods/mine", params={"search": "TEST Claude"},
                           headers={"Accept": "application/json"})
    if r.status_code == 200:
        mine = [f for f in (r.json() or []) if "TEST Claude" in str(f.get("description", ""))]
        report("In eigenen Lebensmitteln sichtbar", bool(mine), f"{len(mine)} Treffer")
        if mine and not new_id:
            new_id = mine[0].get("id")
    else:
        report("In eigenen Lebensmitteln sichtbar", False, f"GET /api/services/users/foods/mine -> HTTP {r.status_code}")

    if not new_id:
        report("Eigenes Lebensmittel löschen", False, "keine id bekannt; bitte in MFP unter 'Meine Lebensmittel' manuell löschen")
        return
    dh = {"Accept": "application/json"}
    if csrf:
        dh["x-csrf-token"] = csrf
    r = client.session.delete(f"{WEB}/api/services/foods/{new_id}", headers=dh)
    report("Eigenes Lebensmittel löschen", r.status_code in (200, 204),
           f"DELETE {WEB}/api/services/foods/{new_id} -> HTTP {r.status_code}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--write", action="store_true", help="Banane 120 g unter Snacks eintragen, prüfen, löschen")
    ap.add_argument("--custom-food", action="store_true", help="eigenes Lebensmittel 'TEST Claude' anlegen und löschen")
    ap.add_argument("--yes", action="store_true", help="keine Rückfragen vor Schreibvorgängen")
    ap.add_argument("--date", help="Testtag YYYY-MM-DD (Standard: heute)")
    ap.add_argument("--query", default="Banane", help="Suchbegriff für Schritt 2.1")
    args = ap.parse_args()
    today = date.fromisoformat(args.date) if args.date else date.today()

    client = step_connect()
    step_read(client, today)
    candidates = step_search(client, args.query)
    if args.write:
        step_write(client, today, candidates, args.yes)
    if args.custom_food:
        step_custom_food(client, args.yes)

    print("\n== Zusammenfassung (für docs/mfp-tools.md, Abschnitt 6) ==")
    print(f"| Datum | Test | Ergebnis | Endpunkt / Fehler |")
    for test, status, detail in RESULTS:
        print(f"| {today.isoformat()} | {test} | {status} | {detail.replace('|', '/')} |")
    return 0 if all(s == "OK" for _, s, _ in RESULTS) else 2


if __name__ == "__main__":
    sys.exit(main())
