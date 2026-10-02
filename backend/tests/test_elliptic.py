import csv
from pathlib import Path

import pytest
from sqlalchemy import select

from app.db import SessionLocal
from app.elliptic import (CAPABILITIES, TX_FEATURE_HEADERS,
                          WALLET_FEATURE_HEADERS, import_elliptic)
from app.models import (BlockchainDataset, BlockchainReferenceLabel,
                        BlockchainWalletScore, User)


def write_csv(path: Path, headers, rows):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader(); writer.writerows(rows)


def official_schema_fixture(root: Path, missing_wallet_label=False):
    wallet_rows=[]
    for address in ["WA", "WB", "WC", "WD"]:
        row={key:"0" for key in WALLET_FEATURE_HEADERS}; row.update({"address":address,"Time step":"1"}); wallet_rows.append(row)
    tx_rows=[]
    for tx_id in ["T1", "T2"]:
        row={key:"0" for key in TX_FEATURE_HEADERS}; row.update({"txId":tx_id,"Time step":"1","total_BTC":"2.5"}); tx_rows.append(row)
    write_csv(root/"wallets_features.csv",WALLET_FEATURE_HEADERS,wallet_rows)
    labels=[{"address":x,"class":"3"} for x in ["WA","WB","WC","WD"]]
    if missing_wallet_label: labels=labels[:-1]
    write_csv(root/"wallets_classes.csv",["address","class"],labels)
    write_csv(root/"AddrAddr_edgelist.csv",["input_address","output_address"],[{"input_address":"WA","output_address":"WB"}])
    write_csv(root/"AddrTx_edgelist.csv",["input_address","txId"],[{"input_address":x,"txId":"T1"} for x in ["WA","WB","WC"]])
    write_csv(root/"TxAddr_edgelist.csv",["txId","output_address"],[{"txId":"T1","output_address":"WD"},{"txId":"T2","output_address":"WA"}])
    write_csv(root/"txs_features.csv",TX_FEATURE_HEADERS,tx_rows)
    write_csv(root/"txs_classes.csv",["txId","class"],[{"txId":"T1","class":"1"},{"txId":"T2","class":"2"}])
    write_csv(root/"txs_edgelist.csv",["txId1","txId2"],[{"txId1":"T1","txId2":"T2"}])


def import_fixture(tmp_path):
    official_schema_fixture(tmp_path); db=SessionLocal(); user=db.scalar(select(User).where(User.email=="sup@test.local"))
    dataset=import_elliptic(db,tmp_path,user.workspace_id,user.id,max_transactions=2)
    return db,dataset


def test_schema_validation_and_missing_reference_are_atomic(tmp_path):
    official_schema_fixture(tmp_path,missing_wallet_label=True); db=SessionLocal(); user=db.scalar(select(User).where(User.email=="sup@test.local"))
    with pytest.raises(ValueError,match="Missing class references"):
        import_elliptic(db,tmp_path,user.workspace_id,user.id,max_transactions=2)
    assert db.scalar(select(BlockchainDataset)) is None
    write_csv(tmp_path/"wallets_classes.csv",["wrong"],[{"wrong":"x"}])
    with pytest.raises(ValueError,match="expected columns"):
        import_elliptic(db,tmp_path,user.workspace_id,user.id,max_transactions=2)
    db.close()


def test_idempotency_label_separation_subset_capabilities_and_graph(client,auth,tmp_path):
    db,dataset=import_fixture(tmp_path); first_id=dataset.id
    user=db.scalar(select(User).where(User.email=="sup@test.local")); again=import_elliptic(db,tmp_path,user.workspace_id,user.id,max_transactions=2)
    assert again.id==first_id and db.query(BlockchainDataset).count()==1
    original={x.address:x.score for x in db.scalars(select(BlockchainWalletScore).where(BlockchainWalletScore.dataset_id==first_id))}
    label=db.scalar(select(BlockchainReferenceLabel).where(BlockchainReferenceLabel.dataset_id==first_id,BlockchainReferenceLabel.node_type=="wallet")); label.label_code=1; label.label_name="illicit"; db.commit()
    assert {x.address:x.score for x in db.scalars(select(BlockchainWalletScore).where(BlockchainWalletScore.dataset_id==first_id))}==original
    assert CAPABILITIES["structural_graph"]["available"] is True
    assert CAPABILITIES["rapid_forwarding_detector"]["available"] is False
    db.close()
    summary=client.get(f"/api/blockchain-datasets/{first_id}/summary"); assert summary.status_code==200 and "bounded subset" in summary.json()["notice"]
    network=client.get(f"/api/blockchain-datasets/{first_id}/network?wallet=WA&hops=2").json()
    assert {x["node_type"] for x in network["nodes"]}=={"wallet","transaction"}
    assert {x["relationship_type"] for x in network["edges"]}>={"ADDR_TX","TX_ADDR"}
    assert all("amount" not in edge for edge in network["edges"])
    evaluation=client.get(f"/api/blockchain-datasets/{first_id}/evaluation").json()
    assert evaluation["unknown_labels_excluded"]>=1 and "never detector inputs" in evaluation["methodology"]
