import argparse
from sqlalchemy import select
from .db import Base,engine,SessionLocal
from .models import Workspace,User,DetectionSettings,BlockchainWallet,BlockchainTransactionNode,BlockchainRelationship
from .auth import hash_password
from .detection import DEFAULTS
from .elliptic import import_elliptic
from .graph_store import graph_store

def main():
    p=argparse.ArgumentParser(); sub=p.add_subparsers(dest="cmd",required=True); b=sub.add_parser("bootstrap"); b.add_argument("--email",required=True); b.add_argument("--password",required=True); b.add_argument("--name",default="Lead Investigator"); b.add_argument("--workspace",default="MADs Lab")
    e=sub.add_parser("import-elliptic",help="Import a bounded subset from downloaded official Elliptic++ CSVs")
    e.add_argument("--source-dir",required=True); e.add_argument("--email",required=True)
    e.add_argument("--name",default="Elliptic++ laptop demo"); e.add_argument("--max-transactions",type=int,default=500)
    args=p.parse_args(); Base.metadata.create_all(engine); db=SessionLocal()
    if args.cmd=="bootstrap":
        if db.scalar(select(User).where(User.email==args.email.lower())): raise SystemExit("User already exists")
        ws=Workspace(name=args.workspace); db.add(ws); db.flush(); u=User(workspace_id=ws.id,email=args.email.lower(),name=args.name,password_hash=hash_password(args.password),role="supervisor"); db.add(u); db.flush(); db.add(DetectionSettings(workspace_id=ws.id,version=1,config=DEFAULTS,created_by=u.id)); db.commit(); print(f"Created supervisor {u.email} in workspace {ws.name}")
    elif args.cmd=="import-elliptic":
        u=db.scalar(select(User).where(User.email==args.email.lower()))
        if not u: raise SystemExit("User not found")
        if u.role!="supervisor": raise SystemExit("Elliptic++ imports require a supervisor")
        dataset=import_elliptic(db,args.source_dir,u.workspace_id,u.id,args.name,args.max_transactions)
        if graph_store.enabled:
            graph_store.sync_blockchain_dataset(dataset.id,u.workspace_id,db.scalars(select(BlockchainWallet).where(BlockchainWallet.dataset_id==dataset.id)).all(),db.scalars(select(BlockchainTransactionNode).where(BlockchainTransactionNode.dataset_id==dataset.id)).all(),db.scalars(select(BlockchainRelationship).where(BlockchainRelationship.dataset_id==dataset.id)).all())
        print(f"Elliptic++ dataset #{dataset.id}: {dataset.wallet_count} wallets, {dataset.transaction_node_count} transactions, {dataset.relationship_count} relationships")
if __name__=="__main__": main()
