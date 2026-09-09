#!/usr/bin/env python3
"""Fetch cheapest 2-adult hotel stay prices from Amadeus and write prices.json."""

from __future__ import annotations

import json
import os
import time
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "prices.json"

CITIES = {
    "paris": "PAR",
    "rome": "ROM",
    "berlin": "BER",
    "barcelona": "BCN",
    "amsterdam": "AMS",
    "venice": "VCE",
    "stockholm": "STO",
    "prague": "PRG",
    "vienna": "VIE",
    "hamburg": "HAM",
    "cologne": "CGN",
    "brussels": "BRU",
    "madrid": "MAD",
    "porto": "OPO",
    "lisbon": "LIS",
    "athens": "ATH",
    "budapest": "BUD",
    "krakow": "KRK",
    "malaga": "AGP",
    "granada": "GRX",
    "hannover": "HAJ",
}

TOUR_ESTIMATE = {
    "paris": 85, "rome": 70, "berlin": 55, "barcelona": 65, "amsterdam": 70,
    "venice": 75, "stockholm": 80, "prague": 45, "vienna": 65, "hamburg": 50,
    "cologne": 48, "brussels": 55, "madrid": 60, "porto": 40, "lisbon": 50,
    "athens": 45, "budapest": 40, "krakow": 35, "malaga": 40, "granada": 42,
    "hannover": 38,
}
TRANSFER_ESTIMATE = 40
NIGHTS = 3


def cheap_starts(today: date, year: int, month: int) -> list[date]:
    min_date = today + timedelta(days=3)
    last = (date(year + (month // 12), (month % 12) + 1, 1) - timedelta(days=1)).day
    preferred = []
    fallback = []
    for day in range(1, last + 1):
        start = date(year, month, day)
        if start < min_date:
            continue
        if start.weekday() in (1, 2):
            preferred.append(start)
        elif start.weekday() in (0, 3):
            fallback.append(start)
    return (preferred or fallback)[:2]


def amadeus_token() -> str:
    client_id = os.environ["AMADEUS_CLIENT_ID"]
    client_secret = os.environ["AMADEUS_CLIENT_SECRET"]
    hostname = os.environ.get("AMADEUS_HOSTNAME", "test")
    host = "https://test.api.amadeus.com" if hostname == "test" else "https://api.amadeus.com"
    data = urllib.parse.urlencode(
        {
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
        }
    ).encode()
    req = urllib.request.Request(
        f"{host}/v1/security/oauth2/token",
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        payload = json.loads(resp.read().decode())
    return payload["access_token"], host


def get_json(url: str, token: str):
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=45) as resp:
        return json.loads(resp.read().decode())


def hotel_ids(host: str, token: str, city_code: str) -> list[str]:
    url = (
        f"{host}/v1/reference-data/locations/hotels/by-city"
        f"?cityCode={city_code}&radius=5&radiusUnit=KM&hotelSource=ALL"
    )
    data = get_json(url, token)
    ids = [item["hotelId"] for item in data.get("data", []) if "hotelId" in item]
    return ids[:15]


def cheapest_offer(host: str, token: str, ids: list[str], check_in: date, check_out: date):
    if not ids:
        return None
    joined = ",".join(ids)
    url = (
        f"{host}/v3/shopping/hotel-offers?hotelIds={joined}"
        f"&adults=2&roomQuantity=1&checkInDate={check_in.isoformat()}"
        f"&checkOutDate={check_out.isoformat()}&currency=EUR&bestRateOnly=true"
    )
    try:
        data = get_json(url, token)
    except Exception:
        return None
    best = None
    for hotel in data.get("data", []):
        name = hotel.get("hotel", {}).get("name", "")
        for offer in hotel.get("offers", []):
            try:
                total = float(offer["price"]["total"])
            except (KeyError, TypeError, ValueError):
                continue
            if best is None or total < best["hotelMin"]:
                best = {"hotelMin": round(total), "hotelName": name}
    return best


def main() -> int:
    today = date.today()
    token, host = amadeus_token()
    cities = {}
    id_cache = {}
    for city_id, city_code in CITIES.items():
        try:
            id_cache[city_id] = hotel_ids(host, token, city_code)
            time.sleep(0.4)
        except Exception as exc:
            print(f"hotel list failed {city_id}: {exc}")
            id_cache[city_id] = []

        months = []
        for offset in range(3):
            month_date = date(today.year + ((today.month - 1 + offset) // 12), ((today.month - 1 + offset) % 12) + 1, 1)
            starts = cheap_starts(today, month_date.year, month_date.month)
            if not starts:
                continue
            start = starts[0]
            end = start + timedelta(days=NIGHTS)
            offer = None
            try:
                offer = cheapest_offer(host, token, id_cache[city_id], start, end)
                time.sleep(0.4)
            except Exception as exc:
                print(f"offer failed {city_id} {start}: {exc}")
            if not offer:
                continue
            tour = TOUR_ESTIMATE[city_id]
            total = offer["hotelMin"] + tour + TRANSFER_ESTIMATE
            months.append(
                {
                    "offset": offset,
                    "checkIn": start.isoformat(),
                    "checkOut": end.isoformat(),
                    "hotelMin": offer["hotelMin"],
                    "hotelName": offer["hotelName"],
                    "tourEstimate": tour,
                    "transferEstimate": TRANSFER_ESTIMATE,
                    "total2p": total,
                }
            )
        cities[city_id] = {"iata": city_code, "months": months}

    payload = {
        "updatedAt": datetime.now(timezone.utc).isoformat(),
        "source": "amadeus",
        "currency": "EUR",
        "people": 2,
        "nights": NIGHTS,
        "cities": cities,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
