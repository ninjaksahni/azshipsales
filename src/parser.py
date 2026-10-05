from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO, StringIO
from typing import BinaryIO, TextIO, Union

import pandas as pd

REQUIRED_COLUMNS = [
    "Customer Shipment Date",
    "Merchant SKU",
    "FNSKU",
    "ASIN",
    "FC",
    "Quantity",
    "Amazon Order Id",
    "Currency",
    "Product Amount",
    "Shipping Amount",
    "Gift Amount",
    "Shipment To City",
    "Shipment To State",
    "Shipment To Postal Code",
]


@dataclass(frozen=True)
class ShipmentRow:
    order_id: str
    merchant_sku: str
    quantity: int
    product_amount: float
    city: str
    state: str
    shipment_date: str  # YYYY-MM-DD (local date from Customer Shipment Date)

    @property
    def dedup_key(self) -> str:
        return f"{self.order_id}|{self.merchant_sku}"


@dataclass
class ParseResult:
    rows: list[ShipmentRow]
    rows_read: int
    rows_skipped_zero_amount: int


def _normalize_text(value: object) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    return str(value).strip().upper()


def parse_shipment_csv(source: Union[str, bytes, TextIO, BinaryIO]) -> ParseResult:
    if isinstance(source, bytes):
        df = pd.read_csv(BytesIO(source))
    elif isinstance(source, str):
        df = pd.read_csv(StringIO(source))
    else:
        df = pd.read_csv(source)

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(missing)}")

    rows_read = len(df)
    rows: list[ShipmentRow] = []
    skipped_zero = 0

    for _, row in df.iterrows():
        amount = pd.to_numeric(row["Product Amount"], errors="coerce")
        if pd.isna(amount) or float(amount) == 0.0:
            skipped_zero += 1
            continue

        qty = int(pd.to_numeric(row["Quantity"], errors="coerce") or 0)
        if qty <= 0:
            skipped_zero += 1
            continue

        order_id = str(row["Amazon Order Id"]).strip()
        sku = str(row["Merchant SKU"]).strip()
        if not order_id or not sku:
            skipped_zero += 1
            continue

        ts = pd.to_datetime(row["Customer Shipment Date"], errors="coerce")
        shipment_date = ""
        if not pd.isna(ts):
            shipment_date = ts.date().isoformat()

        rows.append(
            ShipmentRow(
                order_id=order_id,
                merchant_sku=sku,
                quantity=qty,
                product_amount=float(amount),
                city=_normalize_text(row["Shipment To City"]),
                state=_normalize_text(row["Shipment To State"]),
                shipment_date=shipment_date,
            )
        )

    return ParseResult(
        rows=rows,
        rows_read=rows_read,
        rows_skipped_zero_amount=skipped_zero,
    )
