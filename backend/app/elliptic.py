"""Elliptic++ importer and structural analysis.

Reference labels are deliberately read only after graph-derived scores are built.
No transaction is flattened into wallet-to-wallet transfers and no edge value is
inferred from node-level aggregate features.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import (
    BlockchainDataset, BlockchainDecision, BlockchainNodeFeature,
    BlockchainReferenceLabel, BlockchainRelationship, BlockchainTransactionNode,
    BlockchainWallet, BlockchainWalletScore,
)

SOURCE_URL = "https://github.com/git-disl/EllipticPlusPlus"
SCHEMA_VERSION = "elliptic++-official-v1"
FILES = {
    "wallet_features": "wallets_features.csv",
    "wallet_labels": "wallets_classes.csv",
    "address_address": "AddrAddr_edgelist.csv",
    "address_transaction": "AddrTx_edgelist.csv",
    "transaction_address": "TxAddr_edgelist.csv",
    "transaction_features": "txs_features.csv",
    "transaction_labels": "txs_classes.csv",
    "transaction_transaction": "txs_edgelist.csv",
}
EXACT_HEADERS = {
    "wallet_labels": ["address", "class"],
    "address_address": ["input_address", "output_address"],
    "address_transaction": ["input_address", "txId"],
    "transaction_address": ["txId", "output_address"],
    "transaction_labels": ["txId", "class"],
    "transaction_transaction": ["txId1", "txId2"],
}
WALLET_FEATURE_HEADERS = [
    "address", "Time step", "num_txs_as_sender", "num_txs_as receiver",
    "first_block_appeared_in", "last_block_appeared_in", "lifetime_in_blocks",
    "total_txs", "first_sent_block", "first_received_block",
    "num_timesteps_appeared_in", "btc_transacted_total", "btc_transacted_min",
    "btc_transacted_max", "btc_transacted_mean", "btc_transacted_median",
    "btc_sent_total", "btc_sent_min", "btc_sent_max", "btc_sent_mean",
    "btc_sent_median", "btc_received_total", "btc_received_min",
    "btc_received_max", "btc_received_mean", "btc_received_median",
    "fees_total", "fees_min", "fees_max", "fees_mean", "fees_median",
    "fees_as_share_total", "fees_as_share_min", "fees_as_share_max",
    "fees_as_share_mean", "fees_as_share_median", "blocks_btwn_txs_total",
    "blocks_btwn_txs_min", "blocks_btwn_txs_max", "blocks_btwn_txs_mean",
    "blocks_btwn_txs_median", "blocks_btwn_input_txs_total",
    "blocks_btwn_input_txs_min", "blocks_btwn_input_txs_max",
    "blocks_btwn_input_txs_mean", "blocks_btwn_input_txs_median",
    "blocks_btwn_output_txs_total", "blocks_btwn_output_txs_min",
    "blocks_btwn_output_txs_max", "blocks_btwn_output_txs_mean",
    "blocks_btwn_output_txs_median", "num_addr_transacted_multiple",
    "transacted_w_address_total", "transacted_w_address_min",
    "transacted_w_address_max", "transacted_w_address_mean",
    "transacted_w_address_median",
]
TX_AUGMENTED = [
    "in_txs_degree", "out_txs_degree", "total_BTC", "fees", "size",
    "num_input_addresses", "num_output_addresses", "in_BTC_min", "in_BTC_max",
    "in_BTC_mean", "in_BTC_median", "in_BTC_total", "out_BTC_min",
    "out_BTC_max", "out_BTC_mean", "out_BTC_median", "out_BTC_total",
]
TX_FEATURE_HEADERS = (["txId", "Time step"] +
                      [f"Local_feature_{i}" for i in range(1, 94)] +
                      [f"Aggregate_feature_{i}" for i in range(1, 73)] + TX_AUGMENTED)
LABEL_NAMES = {1: "illicit", 2: "licit", 3: "unknown"}

CAPABILITIES = {
    "structural_graph": {"available": True, "reason": "Directed wallet, transaction, and money-flow relationships are supplied."},
    "ordinal_time_steps": {"available": True, "reason": "The dataset supplies time steps 1–49."},
    "exact_timestamps": {"available": False, "reason": "Only ordinal time steps are supplied; they are not calendar timestamps."},
    "transaction_level_btc": {"available": True, "reason": "Documented node-level BTC aggregate features are supplied."},
    "edge_transfer_amounts": {"available": False, "reason": "No documented value allocation is supplied for individual graph edges."},
    "balances": {"available": False, "reason": "Wallet balances are not supplied."},
    "device_ids": {"available": False, "reason": "Device identifiers are not supplied."},
    "ip_addresses": {"available": False, "reason": "IP addresses are not supplied."},
    "kyc_attributes": {"available": False, "reason": "KYC attributes are not supplied."},
    "rapid_forwarding_detector": {"available": False, "reason": "Exact timestamps are required."},
    "forwarded_value_ratio_detector": {"available": False, "reason": "Documented per-edge monetary allocation is required."},
    "shared_attribute_detector": {"available": False, "reason": "Actual device, IP, or KYC attributes are required."},
}


def _resolve_files(root: Path) -> dict[str, Path]:
    found: dict[str, Path] = {}
    for key, name in FILES.items():
        matches = list(root.rglob(name))
        if len(matches) != 1:
            raise ValueError(f"Expected exactly one {name} below {root}; found {len(matches)}")
        found[key] = matches[0]
    return found


def _header(path: Path) -> list[str]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return next(csv.reader(handle), [])


def _validate_headers(paths: dict[str, Path]) -> None:
    for key, expected in EXACT_HEADERS.items():
        actual = _header(paths[key])
        if actual != expected:
            raise ValueError(f"{paths[key].name}: expected columns {expected}, got {actual}")
    wf = _header(paths["wallet_features"])
    if wf != WALLET_FEATURE_HEADERS:
        missing = sorted(set(WALLET_FEATURE_HEADERS) - set(wf))
        extra = sorted(set(wf) - set(WALLET_FEATURE_HEADERS))
        raise ValueError(f"wallets_features.csv schema mismatch; missing={missing}, extra={extra}, columns={len(wf)}")
    tf = _header(paths["transaction_features"])
    if tf != TX_FEATURE_HEADERS:
        missing = sorted(set(TX_FEATURE_HEADERS) - set(tf))
        extra = sorted(set(tf) - set(TX_FEATURE_HEADERS))
        raise ValueError(f"txs_features.csv schema mismatch; missing={missing}, extra={extra}, columns={len(tf)}")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _rows(path: Path):
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        yield from csv.DictReader(handle)


def _number(value: str):
    value = value.strip()
    if not value:
        return None
    try:
        result = float(value) if any(ch in value.lower() for ch in (".", "e")) else int(value)
        return result if not isinstance(result, float) or math.isfinite(result) else None
    except ValueError:
        return value


def _features(row: dict[str, str], identifier: str) -> dict:
    return {key: _number(value) for key, value in row.items() if key not in {identifier, "Time step"}}


def _label(value: str) -> tuple[int, str]:
    try:
        code = int(value)
    except ValueError as exc:
        raise ValueError(f"Invalid Elliptic++ class value {value!r}") from exc
    if code not in LABEL_NAMES:
        raise ValueError(f"Unsupported Elliptic++ class code {code}")
    return code, LABEL_NAMES[code]


def _score_wallets(dataset_id: int, wallet_ids: set[str], relationships: list[dict]) -> list[BlockchainWalletScore]:
    inbound, outbound, incident_txs = Counter(), Counter(), defaultdict(set)
    for edge in relationships:
        source, target, kind = edge["source_id"], edge["target_id"], edge["relationship_type"]
        if edge["source_type"] == "wallet":
            outbound[source] += 1
            if edge["target_type"] == "transaction": incident_txs[source].add(target)
        if edge["target_type"] == "wallet":
            inbound[target] += 1
            if edge["source_type"] == "transaction": incident_txs[target].add(source)
        # ADDR_ADDR is an official aggregate relation, not a fabricated transfer.
        if kind == "ADDR_ADDR":
            pass
    scores = []
    for address in sorted(wallet_ids):
        fan_in, fan_out = inbound[address], outbound[address]
        breakdown, reasons, score = {}, [], 0
        if fan_in >= 3:
            contribution = min(35, 20 + (fan_in - 3) * 3); score += contribution
            breakdown["structural_fan_in"] = contribution
            reasons.append(f"Appears as the target of {fan_in} official directed relationships in this subset.")
        if fan_out >= 3:
            contribution = min(35, 20 + (fan_out - 3) * 3); score += contribution
            breakdown["structural_fan_out"] = contribution
            reasons.append(f"Appears as the source of {fan_out} official directed relationships in this subset.")
        if fan_in >= 2 and fan_out >= 2:
            score += 20; breakdown["connected_path"] = 20
            reasons.append("Connects multiple inbound and outbound graph paths.")
        score = min(score, 100)
        severity = "High" if score >= 70 else "Medium" if score >= 40 else "Low"
        scores.append(BlockchainWalletScore(
            dataset_id=dataset_id, address=address, score=score, severity=severity,
            breakdown=breakdown, reasons=reasons,
            evidence={"incoming_relationships": fan_in, "outgoing_relationships": fan_out,
                      "incident_transactions": len(incident_txs[address]),
                      "enabled_detectors": ["structural_fan_in", "structural_fan_out", "connected_path"],
                      "disabled_detectors": ["rapid_forwarding", "forwarded_value_ratio", "shared_device_ip_kyc"]},
        ))
    return scores


def import_elliptic(
    db: Session, source_dir: str | Path, workspace_id: int, imported_by: int,
    name: str = "Elliptic++ laptop demo", max_transactions: int = 500,
) -> BlockchainDataset:
    """Import a label-blind bounded subset from the official downloaded CSV files."""
    if max_transactions < 1 or max_transactions > 25_000:
        raise ValueError("max_transactions must be between 1 and 25,000")
    paths = _resolve_files(Path(source_dir))
    _validate_headers(paths)
    manifest = {key: {"filename": path.name, "bytes": path.stat().st_size, "sha256": _sha256(path)} for key, path in paths.items()}
    subset_method = (f"Label-blind first {max_transactions} transaction feature records in official file order; "
                     "all official address→transaction and transaction→address relationships incident to selected "
                     "transactions; address→address and transaction→transaction relationships retained only when "
                     "both endpoints are selected. No relationships or values are fabricated.")
    fingerprint = hashlib.sha256(json.dumps({"files": manifest, "subset_method": subset_method}, sort_keys=True).encode()).hexdigest()
    existing = db.scalar(select(BlockchainDataset).where(
        BlockchainDataset.workspace_id == workspace_id, BlockchainDataset.manifest_hash == fingerprint))
    if existing:
        return existing

    selected_txs: dict[str, dict] = {}
    for row in _rows(paths["transaction_features"]):
        tx_id = row["txId"].strip()
        if not tx_id or tx_id in selected_txs:
            raise ValueError(f"Duplicate or empty txId in txs_features.csv: {tx_id!r}")
        selected_txs[tx_id] = row
        if len(selected_txs) >= max_transactions:
            break
    if len(selected_txs) < max_transactions:
        raise ValueError(f"Requested {max_transactions} transactions but only {len(selected_txs)} were available")

    wallet_ids: set[str] = set()
    relationships: list[dict] = []
    seen_edges: set[tuple] = set()

    def add_edge(kind: str, source_type: str, source_id: str, target_type: str, target_id: str):
        key = (kind, source_id, target_id)
        if key not in seen_edges:
            seen_edges.add(key)
            relationships.append({"relationship_type": kind, "source_type": source_type,
                                  "source_id": source_id, "target_type": target_type, "target_id": target_id})

    for row in _rows(paths["address_transaction"]):
        if row["txId"] in selected_txs:
            wallet_ids.add(row["input_address"]); add_edge("ADDR_TX", "wallet", row["input_address"], "transaction", row["txId"])
    for row in _rows(paths["transaction_address"]):
        if row["txId"] in selected_txs:
            wallet_ids.add(row["output_address"]); add_edge("TX_ADDR", "transaction", row["txId"], "wallet", row["output_address"])
    for row in _rows(paths["transaction_transaction"]):
        if row["txId1"] in selected_txs and row["txId2"] in selected_txs:
            add_edge("TX_TX", "transaction", row["txId1"], "transaction", row["txId2"])
    for row in _rows(paths["address_address"]):
        if row["input_address"] in wallet_ids and row["output_address"] in wallet_ids:
            add_edge("ADDR_ADDR", "wallet", row["input_address"], "wallet", row["output_address"])

    wallet_feature_rows: list[dict] = []
    wallet_feature_ids: set[str] = set()
    for row in _rows(paths["wallet_features"]):
        if row["address"] in wallet_ids:
            wallet_feature_rows.append(row); wallet_feature_ids.add(row["address"])
    missing_wallet_features = wallet_ids - wallet_feature_ids
    if missing_wallet_features:
        raise ValueError(f"Missing wallet feature references for {len(missing_wallet_features)} selected wallets; example={next(iter(missing_wallet_features))}")

    labels: list[dict] = []
    found_wallet_labels, found_tx_labels = set(), set()
    for node_type, key, path_key, wanted, found in (
        ("wallet", "address", "wallet_labels", wallet_ids, found_wallet_labels),
        ("transaction", "txId", "transaction_labels", set(selected_txs), found_tx_labels),
    ):
        for row in _rows(paths[path_key]):
            node_id = row[key]
            if node_id in wanted:
                code, label_name = _label(row["class"]); found.add(node_id)
                labels.append({"node_type": node_type, "node_id": node_id, "label_code": code, "label_name": label_name})
    if wallet_ids - found_wallet_labels or set(selected_txs) - found_tx_labels:
        raise ValueError(f"Missing class references: wallets={len(wallet_ids-found_wallet_labels)}, transactions={len(set(selected_txs)-found_tx_labels)}")

    dataset = BlockchainDataset(
        workspace_id=workspace_id, name=name, source_url=SOURCE_URL,
        schema_version=SCHEMA_VERSION, subset_method=subset_method,
        manifest_hash=fingerprint, source_files=manifest, capabilities=CAPABILITIES,
        wallet_count=len(wallet_ids), transaction_node_count=len(selected_txs),
        relationship_count=len(relationships), imported_by=imported_by,
    )
    try:
        db.add(dataset); db.flush()
        wallet_first_step: dict[str, int] = {}
        wallet_latest_features: dict[str, dict] = {}
        observation_counts: Counter = Counter()
        for row in wallet_feature_rows:
            step = int(row["Time step"]); address = row["address"]
            observation_index = observation_counts[(address, step)]
            observation_counts[(address, step)] += 1
            wallet_first_step[address] = min(step, wallet_first_step.get(address, step))
            wallet_latest_features[address] = _features(row, "address")
            db.add(BlockchainNodeFeature(dataset_id=dataset.id, node_type="wallet", node_id=address,
                                         time_step=step, observation_index=observation_index,
                                         features=_features(row, "address")))
        db.add_all([BlockchainWallet(dataset_id=dataset.id, address=address,
                                     time_step=wallet_first_step.get(address), features=wallet_latest_features.get(address, {}))
                    for address in sorted(wallet_ids)])
        for tx_id, row in selected_txs.items():
            step = int(row["Time step"]); features = _features(row, "txId")
            db.add(BlockchainTransactionNode(dataset_id=dataset.id, tx_id=tx_id, time_step=step, features=features))
            db.add(BlockchainNodeFeature(dataset_id=dataset.id, node_type="transaction", node_id=tx_id,
                                         time_step=step, observation_index=0, features=features))
        db.add_all([BlockchainRelationship(dataset_id=dataset.id, **edge) for edge in relationships])
        db.add_all([BlockchainReferenceLabel(dataset_id=dataset.id, **label) for label in labels])
        # This happens only after labels were collected and they are not passed into the scorer.
        db.add_all(_score_wallets(dataset.id, wallet_ids, relationships))
        db.commit(); db.refresh(dataset)
        return dataset
    except Exception:
        db.rollback()
        raise


def evaluation(db: Session, dataset_id: int, threshold: int = 40) -> dict:
    scores = {row.address: row.score for row in db.scalars(select(BlockchainWalletScore).where(BlockchainWalletScore.dataset_id == dataset_id))}
    labels = db.scalars(select(BlockchainReferenceLabel).where(
        BlockchainReferenceLabel.dataset_id == dataset_id,
        BlockchainReferenceLabel.node_type == "wallet",
        BlockchainReferenceLabel.label_code.in_([1, 2]),
    )).all()
    tp = fp = fn = tn = 0
    for label in labels:
        predicted = scores.get(label.node_id, 0) >= threshold
        actual = label.label_code == 1
        tp += predicted and actual; fp += predicted and not actual
        fn += (not predicted) and actual; tn += (not predicted) and (not actual)
    return {
        "threshold": threshold, "known_label_sample_count": len(labels),
        "unknown_labels_excluded": db.scalar(select(__import__("sqlalchemy").func.count()).select_from(BlockchainReferenceLabel).where(
            BlockchainReferenceLabel.dataset_id == dataset_id,
            BlockchainReferenceLabel.node_type == "wallet", BlockchainReferenceLabel.label_code == 3)) or 0,
        "true_positives": tp, "false_positives": fp, "false_negatives": fn, "true_negatives": tn,
        "precision": round(tp / (tp + fp), 4) if tp + fp else None,
        "recall": round(tp / (tp + fn), 4) if tp + fn else None,
        "scope": "Imported label-blind bounded subset; wallet reference labels 1 (illicit) and 2 (licit) only. Class 3 unknown is excluded.",
        "methodology": "Reference labels are joined only after graph-only scoring and are never detector inputs. This is evaluation, not model training.",
    }
