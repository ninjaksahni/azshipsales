# azshipsales

Streamlit app to see **where to fulfill each SKU** (city/market priority) and **what to stock in each city**, from Amazon India Shipment Sales CSV uploads. Rolling totals persist in JSON.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
streamlit run app.py
```

Upload shipment CSV exports from Seller Central. Re-uploading overlapping reports is safe: rows are deduplicated by **Amazon Order Id + Merchant SKU**. Rows with **Product Amount = 0** are excluded.

Aggregates are stored in `data/aggregates.json` (gitignored).

## Metrics

- **Top city / state per SKU**: ranked by **units shipped** (sum of `Quantity`); revenue is `Product Amount` in INR.
- City and state names are normalized to **uppercase** for consistent grouping.

## Map geocoding

The Maps tab looks up city coordinates via [Open-Meteo Geocoding](https://open-meteo.com/en/docs/geocoding-api) (free, no API key), with OpenStreetMap Nominatim as fallback. Results are cached in `data/geocode_cache.json`.

## Tests

```bash
python3 -m unittest discover -s tests -v
```
