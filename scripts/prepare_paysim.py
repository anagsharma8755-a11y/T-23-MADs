"""Download PaySim and convert a bounded slice into MuleTrace CSV inputs.

PaySim is a public, research-grade synthetic mobile-money dataset calibrated
from real transaction patterns. The generated files remain CSV end-to-end.
"""

from __future__ import annotations

import argparse
import csv
import io
import urllib.request
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path


SOURCE_URL = "https://huggingface.co/datasets/LordNR/AMLGraphX-Paysim/resolve/main/paysim.zip?download=true"


def prepare(output_dir: Path, rows: int, archive: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    if not archive.exists():
        print(f"Downloading PaySim from {SOURCE_URL}")
        urllib.request.urlretrieve(SOURCE_URL, archive)

    transactions_path = output_dir / "paysim-transactions.csv"
    labels_path = output_dir / "paysim-source-labels.csv"
    base = datetime(2024, 1, 1, tzinfo=timezone.utc)

    with zipfile.ZipFile(archive) as bundle:
        with bundle.open("paysim.csv") as raw:
            reader = csv.DictReader(io.TextIOWrapper(raw, encoding="utf-8"))
            legitimate: list[tuple[int, dict[str, str]]] = []
            fraudulent: list[tuple[int, dict[str, str]]] = []
            for index, row in enumerate(reader, start=1):
                if float(row["amount"]) <= 0:
                    continue
                if row["isFraud"] == "1": fraudulent.append((index, row))
                elif len(legitimate) < rows: legitimate.append((index, row))
            selected = sorted((fraudulent + legitimate[:max(rows - len(fraudulent), 0)])[:rows], key=lambda item: item[0])
            with transactions_path.open("w", newline="", encoding="utf-8") as tx_file, labels_path.open("w", newline="", encoding="utf-8") as label_file:
                tx_writer = csv.DictWriter(tx_file, fieldnames=["transaction_id", "timestamp", "sender_account", "receiver_account", "amount", "currency"])
                label_writer = csv.DictWriter(label_file, fieldnames=["transaction_id", "source_type", "source_is_fraud", "source_is_flagged_fraud"])
                tx_writer.writeheader(); label_writer.writeheader()
                count = 0
                for index, row in selected:
                    transaction_id = f"PAYSIM-{index:07d}"
                    timestamp = base + timedelta(hours=max(int(row["step"]) - 1, 0), seconds=index % 3600)
                    tx_writer.writerow({
                        "transaction_id": transaction_id,
                        "timestamp": timestamp.isoformat().replace("+00:00", "Z"),
                        "sender_account": row["nameOrig"],
                        "receiver_account": row["nameDest"],
                        "amount": row["amount"],
                        "currency": "INR",
                    })
                    label_writer.writerow({
                        "transaction_id": transaction_id,
                        "source_type": row["type"],
                        "source_is_fraud": row["isFraud"],
                        "source_is_flagged_fraud": row["isFlaggedFraud"],
                    })
                    count += 1
    print(f"Wrote {count:,} PaySim transactions ({len(fraudulent):,} source-labelled fraud rows) to {transactions_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--rows", type=int, default=15000)
    parser.add_argument("--output-dir", type=Path, default=Path("samples"))
    parser.add_argument("--archive", type=Path, default=Path("samples/paysim-source.zip"))
    args = parser.parse_args()
    prepare(args.output_dir, args.rows, args.archive)
