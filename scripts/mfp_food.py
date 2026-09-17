#!/usr/bin/env python3
"""Eigene Lebensmittel in MyFitnessPal anlegen, auflisten, löschen.

Nicht Teil des MCP-Servers; nutzt die Web-Endpunkte des MFP-Clients
(verifiziert am 2026-09-17, siehe docs/mfp-tools.md Abschnitt 4).
Cookie aus MFP_COOKIE (Cloud) oder cookies.json (PC, nach `mfp-mcp auth`).

    uv run --python 3.12 --with mfp-mcp==0.3.0 python scripts/mfp_food.py list [--search TEXT]
    uv run --python 3.12 --with mfp-mcp==0.3.0 python scripts/mfp_food.py create --name "Milbona Skyr Natur" --brand Lidl \
        --kcal 63 --protein 11 --carbs 4 --fat 0.2 [--fiber 0] [--sugar 4] [--serving 100 --unit g]
    uv run --python 3.12 --with mfp-mcp==0.3.0 python scripts/mfp_food.py delete --id 124276794449013

Nährwerte gelten je Portion (Standard 100 g). Kohlenhydrate wie auf dem
deutschen Etikett angeben (ohne Ballaststoffe); country_code=DE sorgt dafür,
dass MFP sie so interpretiert.
"""

from __future__ import annotations

import argparse
import json
import sys

import os

os.environ.setdefault("MFP_USERNAME", "MarqEwi")  # MFP-Profil-Endpunkt liefert 500; Name ist nicht geheim

try:
    from myfitnesspal_mcp import mfp_client
except ImportError:
    sys.exit("mfp-mcp fehlt. Aufruf über: uv run --python 3.12 --with mfp-mcp==0.3.0 python scripts/mfp_food.py ...")

WEB = "https://www.myfitnesspal.com"


def csrf(client) -> str | None:
    r = client.session.get(f"{WEB}/api/auth/csrf", headers={"Accept": "application/json"})
    return r.json().get("csrfToken") if r.status_code == 200 else None


def cmd_list(client, args) -> int:
    r = client.session.get(f"{WEB}/api/services/users/foods/mine", params={"search": args.search or ""},
                           headers={"Accept": "application/json"})
    if r.status_code != 200:
        print(f"FEHLER GET /api/services/users/foods/mine -> HTTP {r.status_code}")
        return 2
    foods = r.json() or []
    for f in foods:
        n = f.get("nutritional_contents", {})
        ss = (f.get("serving_sizes") or [{}])[0]
        print(f"- id={f.get('id')} {f.get('brand_name') or '-'} - {f.get('description')} "
              f"({ss.get('value')} {ss.get('unit')}): {n.get('energy', {}).get('value')} kcal, "
              f"E {n.get('protein')}, KH {n.get('carbohydrates')}, F {n.get('fat')}")
    print(f"{len(foods)} eigene Lebensmittel")
    return 0


def cmd_create(client, args) -> int:
    nutrition = {"energy": {"unit": "calories", "value": args.kcal}, "grams": 1,
                 "protein": args.protein, "carbohydrates": args.carbs, "fat": args.fat}
    for key in ("fiber", "sugar", "saturated_fat", "sodium"):
        v = getattr(args, key)
        if v is not None:
            nutrition[key] = v
    item = {
        "description": args.name,
        "brand_name": args.brand or "Generic",
        "public": False,
        "type": "food",
        "country_code": "DE",
        "nutritional_contents": nutrition,
        "serving_sizes": [
            {"value": args.serving, "unit": args.unit, "nutrition_multiplier": 1, "gram_weight": 1, "fraction": False, "index": 0},
            {"value": 1, "unit": f"container ({args.serving} {args.unit} ea.)", "nutrition_multiplier": 1, "gram_weight": 1, "fraction": False, "index": 1},
        ],
    }
    hdr = {"Accept": "application/json", "Content-Type": "application/json"}
    token = csrf(client)
    if token:
        hdr["x-csrf-token"] = token
    r = client.session.post(f"{WEB}/api/services/foods", headers=hdr, data=json.dumps({"item": item}))
    if r.status_code not in (200, 201):
        print(f"FEHLER POST /api/services/foods -> HTTP {r.status_code}: {r.text[:300]}")
        return 2
    body = r.json()
    new_id = (body[0] if isinstance(body, list) else (body.get("item") or body)).get("id")
    print(f"OK angelegt: id={new_id} '{args.name}' ({args.serving} {args.unit}): {args.kcal} kcal, "
          f"E {args.protein}, KH {args.carbs}, F {args.fat}")
    print("Hinweis: private Lebensmittel erscheinen in MFP unter 'Meine Lebensmittel'; "
          "in der Suche von fitness_search_food nur, wenn MFP sie dort einblendet.")
    return 0


def cmd_delete(client, args) -> int:
    hdr = {"Accept": "application/json"}
    token = csrf(client)
    if token:
        hdr["x-csrf-token"] = token
    r = client.session.delete(f"{WEB}/api/services/foods/{args.id}", headers=hdr)
    if r.status_code in (200, 204):
        print(f"OK gelöscht: id={args.id}")
        return 0
    print(f"FEHLER DELETE /api/services/foods/{args.id} -> HTTP {r.status_code}: {r.text[:300]}")
    return 2


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("list"); p.add_argument("--search", default="")
    p = sub.add_parser("create")
    p.add_argument("--name", required=True); p.add_argument("--brand", default="")
    p.add_argument("--kcal", type=float, required=True); p.add_argument("--protein", type=float, required=True)
    p.add_argument("--carbs", type=float, required=True); p.add_argument("--fat", type=float, required=True)
    p.add_argument("--fiber", type=float); p.add_argument("--sugar", type=float)
    p.add_argument("--saturated-fat", dest="saturated_fat", type=float); p.add_argument("--sodium", type=float)
    p.add_argument("--serving", type=float, default=100); p.add_argument("--unit", default="g")
    p = sub.add_parser("delete"); p.add_argument("--id", required=True)
    args = ap.parse_args()
    try:
        client = mfp_client.get_client()
    except Exception as exc:  # noqa: BLE001
        print(f"FEHLER Login: {exc}")
        return 1
    return {"list": cmd_list, "create": cmd_create, "delete": cmd_delete}[args.cmd](client, args)


if __name__ == "__main__":
    sys.exit(main())
