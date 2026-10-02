from pathlib import Path
import json,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from app.demo import demo_csvs
root=Path(__file__).resolve().parents[1]/'samples';root.mkdir(exist_ok=True);tx,acct,labels=demo_csvs();(root/'synthetic-transactions.csv').write_bytes(tx);(root/'synthetic-accounts.csv').write_bytes(acct);(root/'ground_truth.json').write_text(json.dumps(labels,indent=2));print(f'Wrote deterministic synthetic demo to {root}')

