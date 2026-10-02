"""Prepare a compact, network-rich CSV from IBM's AML benchmark dataset."""

from __future__ import annotations

import argparse
import csv
import io
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path


SOURCE_URL = "https://huggingface.co/datasets/eexzzm/IBM-Transactions-for-Anti-Money-Laundering-HI-Small-Trans/resolve/main/HI-Small_Trans.csv.zip?download=true"
CURRENCIES = {
    "US Dollar": "USD", "Euro": "EUR", "UK Pound": "GBP", "Yen": "JPY",
    "Yuan": "CNY", "Australian Dollar": "AUD", "Canadian Dollar": "CAD",
    "Rupee": "INR", "Swiss Franc": "CHF", "Ruble": "RUB", "Bitcoin": "BTC",
}


def account(bank: str, value: str) -> str:
    return f"B{bank.strip()}-{value.strip()}"


def prepare(output_dir: Path, rows: int, archive: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    if not archive.exists():
        print(f"Downloading IBM AML benchmark from {SOURCE_URL}")
        urllib.request.urlretrieve(SOURCE_URL, archive)

    with zipfile.ZipFile(archive) as bundle:
        csv_name = next(name for name in bundle.namelist() if name.lower().endswith(".csv"))
        with bundle.open(csv_name) as raw:
            reader = csv.reader(io.TextIOWrapper(raw, encoding="utf-8-sig")); next(reader)
            laundering = [(i, row) for i, row in enumerate(reader, 1) if row[10] == "1" and float(row[7]) > 0]

        suspicious_accounts = {
            value
            for _, row in laundering
            for value in (account(row[1], row[2]), account(row[3], row[4]))
        }
        related: list[tuple[int, dict[str, str]]] = []
        with bundle.open(csv_name) as raw:
            reader = csv.reader(io.TextIOWrapper(raw, encoding="utf-8-sig")); next(reader)
            for i, row in enumerate(reader, 1):
                if len(related) >= max(rows - len(laundering), 0): break
                sender, receiver = account(row[1], row[2]), account(row[3], row[4])
                if row[10] == "0" and float(row[7]) > 0 and (sender in suspicious_accounts or receiver in suspicious_accounts):
                    related.append((i, row))

    selected = sorted((laundering + related)[:rows], key=lambda item: item[0])
    tx_path = output_dir / "ibm-aml-transactions.csv"
    labels_path = output_dir / "ibm-aml-source-labels.csv"
    with tx_path.open("w", newline="", encoding="utf-8") as tx_file, labels_path.open("w", newline="", encoding="utf-8") as labels_file:
        tx_writer = csv.DictWriter(tx_file, fieldnames=["transaction_id", "timestamp", "sender_account", "receiver_account", "amount", "currency"])
        label_writer = csv.DictWriter(labels_file, fieldnames=["transaction_id", "payment_format", "source_is_laundering"])
        tx_writer.writeheader(); label_writer.writeheader()
        for i, row in selected:
            transaction_id = f"IBMAML-{i:08d}"
            timestamp = datetime.strptime(row[0], "%Y/%m/%d %H:%M").replace(second=i % 60, tzinfo=timezone.utc)
            currency = CURRENCIES.get(row[8], "USD")
            tx_writer.writerow({
                "transaction_id": transaction_id,
                "timestamp": timestamp.isoformat().replace("+00:00", "Z"),
                "sender_account": account(row[1], row[2]),
                "receiver_account": account(row[3], row[4]),
                "amount": row[7],
                "currency": currency,
            })
            label_writer.writerow({"transaction_id": transaction_id, "payment_format": row[9], "source_is_laundering": row[10]})
    print(f"Wrote {len(selected):,} transactions, including {len(laundering):,} source-labelled laundering rows, to {tx_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--rows", type=int, default=15000)
    parser.add_argument("--output-dir", type=Path, default=Path("samples"))
    parser.add_argument("--archive", type=Path, default=Path("samples/ibm-aml-source.zip"))
    args = parser.parse_args()
    prepare(args.output_dir, args.rows, args.archive)
