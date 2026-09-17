#!/usr/bin/env python3
"""Tagesziele (kcal, Makros, Ballaststoffe, Zucker, Natrium, Mahlzeit-Budgets)
und Tagesstand aus MyFitnessPal: gegessen, Ziel, Rest.

    uv run --python 3.12 --with mfp-mcp==0.3.0 python scripts/mfp_goals.py [--date YYYY-MM-DD] [--json]

Quellen: Tagebuchseite (Summen) und https://api.myfitnesspal.com/v2/nutrient-goals
(Ziele je Wochentag, inkl. Ziel pro Mahlzeit). Cookie aus MFP_COOKIE oder cookies.json.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import date

logging.getLogger("myfitnesspal").setLevel(logging.ERROR)  # bekannte 500-Warnung des Profil-Endpunkts

try:
    from myfitnesspal_mcp import diary, mfp_client
except ImportError:
    sys.exit("mfp-mcp fehlt. Aufruf über: uv run --python 3.12 --with mfp-mcp==0.3.0 python scripts/mfp_goals.py")

ROWS = [  # (Anzeige, Einheit, Schlüssel in Tagebuch-Summen, Schlüssel im v2-Ziel)
    ("Kalorien", "kcal", "calories", "energy"),
    ("Eiweiß", "g", "protein", "protein"),
    ("Kohlenhydrate", "g", "carbohydrates", "carbohydrates"),
    ("Fett", "g", "fat", "fat"),
    ("Ballaststoffe", "g", "fiber", "fiber"),
    ("Zucker", "g", "sugar", "sugar"),
    ("Natrium", "mg", "sodium", "sodium"),
]
MEALS = ["breakfast", "lunch", "dinner", "snacks"]


def num(v):
    if isinstance(v, dict):
        v = v.get("value")
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def goals_for(client, day: date) -> dict:
    """Ziel für den Wochentag von `day`, sonst Standardziel."""
    r = client.session.get(
        "https://api.myfitnesspal.com/v2/nutrient-goals",
        headers=diary.api_headers(client, {"Accept": "application/json"}),
    )
    r.raise_for_status()
    items = r.json().get("items") or []
    if not items:
        return {}
    item = items[0]
    weekday = day.strftime("%A").lower()
    for g in item.get("daily_goals") or []:
        if g.get("day_of_week") == weekday and g.get("group_id") != item.get("default_group_id"):
            return g
    return item.get("default_goal") or {}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--date", help="YYYY-MM-DD (Standard: heute)")
    ap.add_argument("--json", action="store_true", help="maschinenlesbar")
    args = ap.parse_args()
    day = date.fromisoformat(args.date) if args.date else date.today()

    try:
        client = mfp_client.get_client()
    except Exception as exc:  # noqa: BLE001
        print(f"FEHLER Login: {exc}")
        return 1

    mfp_day = client.get_date(day)
    totals = dict(mfp_day.totals)
    goal = goals_for(client, day)
    if not goal:  # Fallback: Zielzeile der Tagebuchseite
        goal = {k: v for k, v in dict(mfp_day.goals or {}).items()}
        goal["energy"] = goal.pop("calories", None)

    out = {"day": day.isoformat(), "rows": [], "meals": []}
    for label, unit, tkey, gkey in ROWS:
        g = num(goal.get(gkey))
        if g is None:
            continue
        eaten = num(totals.get(tkey))
        out["rows"].append({"name": label, "unit": unit, "eaten": eaten, "goal": g,
                            "remaining": None if eaten is None else round(g - eaten, 1)})

    meal_goals = {m.get("meal_index"): num(m.get("energy")) for m in goal.get("meal_goals") or []}
    for idx, meal in enumerate(mfp_day.meals):
        kcal = num(meal.totals.get("calories")) or 0.0
        out["meals"].append({"meal": MEALS[idx] if idx < len(MEALS) else meal.name, "eaten": kcal,
                             "goal": meal_goals.get(idx)})

    if args.json:
        print(json.dumps(out, ensure_ascii=False, indent=1))
        return 0

    print(f"Tagesstand {day.isoformat()}")
    print(f"{'':15}{'gegessen':>10}{'Ziel':>10}{'Rest':>10}")
    for r in out["rows"]:
        eaten = "-" if r["eaten"] is None else f"{r['eaten']:.0f}"
        rest = "-" if r["remaining"] is None else f"{r['remaining']:.0f}"
        print(f"{r['name']:15}{eaten:>10}{r['goal']:>10.0f}{rest:>10}  {r['unit']}")
    print("\nMahlzeit-Budgets (kcal)")
    for m in out["meals"]:
        g = "-" if m["goal"] is None else f"{m['goal']:.0f}"
        print(f"  {m['meal']:10}{m['eaten']:>8.0f} / {g}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
