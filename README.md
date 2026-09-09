# Noura Journeys

Live: https://noura-journeys.web.app

City pages from the app:

- https://noura-journeys.web.app/city/paris
- https://noura-journeys.web.app/city/rome
- … one path per city id

## Price updates (no Amadeus key)

`scripts/update_prices.py` writes `prices.json` with a dynamic formula (season, weekday, lead time, morning/midday/evening slot). If reachable, it also mixes in a key-free EUR/USD quote from Frankfurter.

GitHub Action runs at 08:00, 16:00 and 00:00 Tehran (`30 4,12,20 * * *` UTC). No Amadeus secrets are required.

Optional: `FIREBASE_TOKEN` so the Action redeploys Firebase after each update.
