# azshipsales

Streamlit app to parse Amazon India **last 30 days** customer shipment CSVs, aggregate sales by **Merchant SKU** and destination **city/state**, and persist rolling totals in JSON.

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
