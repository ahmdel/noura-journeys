#!/usr/bin/env python3
"""Build prices.json without API keys.

Hotel totals are a dynamic estimate for 2 adults / 1 room / 3 nights:
season, weekday, booking lead time, and the three daily refresh slots.
A key-free ECB FX quote from Frankfurter is mixed in when available so
each run can move with a real market signal.
"""

from __future__ import annotations

import json
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

# Typical double-room nightly rate in EUR (2 guests, city center, 3-star/4-star floor).
NIGHTLY_EUR = {
    "paris": 198,
    "rome": 176,
    "berlin": 128,
    "barcelona": 154,
    "amsterdam": 168,
    "venice": 186,
    "stockholm": 172,
    "prague": 112,
    "vienna": 148,
    "hamburg": 122,
    "cologne": 118,
    "brussels": 136,
    "madrid": 142,
    "porto": 108,
    "lisbon": 124,
    "athens": 118,
    "budapest": 104,
    "krakow": 92,
    "malaga": 110,
    "granada": 102,
    "hannover": 96,
}

TOUR_ESTIMATE = {
    "paris": 85,
    "rome": 70,
    "berlin": 55,
    "barcelona": 65,
    "amsterdam": 70,
    "venice": 75,
    "stockholm": 80,
    "prague": 45,
    "vienna": 65,
    "hamburg": 50,
    "cologne": 48,
    "brussels": 55,
    "madrid": 60,
    "porto": 40,
    "lisbon": 50,
    "athens": 45,
    "budapest": 40,
    "krakow": 35,
    "malaga": 40,
    "granada": 42,
    "hannover": 38,
}

SEASON = {
    1: 0.84,
    2: 0.82,
    3: 0.92,
    4: 1.02,
    5: 1.08,
    6: 1.16,
    7: 1.22,
    8: 1.20,
    9: 1.06,
    10: 0.94,
    11: 0.88,
    12: 1.10,
}

TRANSFER_ESTIMATE = 40
NIGHTS = 3
FX_URLS = (
    "https://api.frankfurter.app/latest?from=EUR&to=USD",
    "https://open.er-api.com/v6/latest/EUR",
)


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


def fetch_eur_usd() -> tuple[float | None, str]:
    for url in FX_URLS:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "noura-price-bot/1.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode())
            if "rates" in data and "USD" in data["rates"]:
                return float(data["rates"]["USD"]), url
        except Exception as exc:
            print(f"fx skip {url}: {exc}")
    return None, "none"


def slot_factor(now: datetime) -> tuple[float, str]:
    hour = now.hour
    if hour < 8:
        return 0.985, "morning"
    if hour < 16:
        return 1.0, "midday"
    return 1.028, "evening"


def weekday_factor(start: date) -> float:
    if start.weekday() in (1, 2):
        return 0.91
    if start.weekday() in (0, 3):
        return 0.96
    return 1.07


def lead_factor(today: date, start: date) -> float:
    days = (start - today).days
    if days <= 7:
        return 1.08
    if days <= 21:
        return 1.03
    if days <= 45:
        return 1.0
    return 0.97


def fx_factor(eur_usd: float | None) -> float:
    if eur_usd is None:
        return 1.0
    return max(0.94, min(1.06, 1 + (eur_usd - 1.08) * 0.12))


def hotel_total(city_id: str, start: date, today: date, now: datetime, eur_usd: float | None) -> int:
    slot, _ = slot_factor(now)
    raw = (
        NIGHTLY_EUR[city_id]
        * NIGHTS
        * SEASON[start.month]
        * weekday_factor(start)
        * lead_factor(today, start)
        * slot
        * fx_factor(eur_usd)
    )
    jitter = ((start.toordinal() + now.hour + len(city_id) * 7) % 17) - 8
    return max(180, round(raw + jitter))


def main() -> int:
    today = date.today()
    now = datetime.now(timezone.utc)
    eur_usd, fx_source = fetch_eur_usd()
    slot, slot_name = slot_factor(now)

    cities = {}
    for city_id, city_code in CITIES.items():
        months = []
        for offset in range(3):
            month_index = today.month - 1 + offset
            month_date = date(today.year + month_index // 12, month_index % 12 + 1, 1)
            starts = cheap_starts(today, month_date.year, month_date.month)
            if not starts:
                continue
            start = starts[0]
            end = start + timedelta(days=NIGHTS)
            hotel_min = hotel_total(city_id, start, today, now, eur_usd)
            tour = TOUR_ESTIMATE[city_id]
            months.append(
                {
                    "offset": offset,
                    "checkIn": start.isoformat(),
                    "checkOut": end.isoformat(),
                    "hotelMin": hotel_min,
                    "hotelName": "اتاق دوتخته مرکز شهر",
                    "tourEstimate": tour,
                    "transferEstimate": TRANSFER_ESTIMATE,
                    "total2p": hotel_min + tour + TRANSFER_ESTIMATE,
                }
            )
        cities[city_id] = {"iata": city_code, "months": months}

    payload = {
        "updatedAt": now.isoformat(),
        "source": "dynamic-formula",
        "fxSource": fx_source,
        "eurUsd": eur_usd,
        "refreshSlot": slot_name,
        "slotFactor": slot,
        "currency": "EUR",
        "people": 2,
        "nights": NIGHTS,
        "cities": cities,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    print(f"wrote {OUT} slot={slot_name} eurUsd={eur_usd}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
