# Noura Journeys

Live: https://noura-journeys.web.app

City pages from the app:

- https://noura-journeys.web.app/city/paris
- https://noura-journeys.web.app/city/rome
- … one path per city id

## What is needed for live prices 3x/day

1. GitHub login as [ahmdel](https://github.com/ahmdel/) (`gh auth login`) with `repo` and `workflow` scopes so this folder can be pushed to `https://github.com/ahmdel/noura-journeys`.
2. Free Amadeus keys from https://developers.amadeus.com — add GitHub Actions secrets:
   - `AMADEUS_CLIENT_ID`
   - `AMADEUS_CLIENT_SECRET`
   - `AMADEUS_HOSTNAME` = `production` for real market rates (`test` is sandbox data)
3. Optional: `FIREBASE_TOKEN` so the same Action redeploys Firebase after each price update.

Schedule: 08:00, 16:00 and 00:00 Tehran (`30 4,12,20 * * *` UTC).
