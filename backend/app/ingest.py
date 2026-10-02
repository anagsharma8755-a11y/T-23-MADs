import io
import pandas as pd
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from fastapi import HTTPException

TX_REQUIRED=["transaction_id","timestamp","sender_account","receiver_account","amount","currency"]
TX_OPTIONAL=["sender_device_id","receiver_device_id","sender_ip","receiver_ip"]
ACCT_REQUIRED=["account_id","created_at","opening_balance","device_id","ip_address","kyc_group_id"]

def parse_time(value: str, row: int, field="timestamp"):
    try:
        dt=datetime.fromisoformat(value.strip().replace("Z","+00:00"))
        if dt.tzinfo is None: raise ValueError("timezone required")
        return dt.astimezone(timezone.utc)
    except Exception: raise ValueError(f"row {row}: {field} must be an ISO-8601 timestamp with timezone")
def read_csv(raw: bytes, max_rows: int):
    try:
        frame=pd.read_csv(io.BytesIO(raw),dtype=str,keep_default_na=False,encoding="utf-8-sig",nrows=max_rows+1)
    except UnicodeDecodeError: raise HTTPException(422,"CSV must be UTF-8")
    except pd.errors.ParserError as exc: raise HTTPException(422,f"Malformed CSV: {exc}")
    if len(frame)>max_rows: raise HTTPException(413,f"CSV exceeds {max_rows} row limit")
    fields=[str(c).strip() for c in frame.columns]
    if len(fields)!=len(set(fields)): raise HTTPException(422,"CSV contains duplicate column names")
    frame.columns=fields
    rows=[(i,{str(k):(str(v).strip() if v is not None else "") for k,v in row.items()}) for i,row in enumerate(frame.to_dict(orient="records"),start=2)]
    return fields,rows
def validate_transactions(raw: bytes,max_rows=100000):
    fields,source=read_csv(raw,max_rows); errors=[]; result=[]; seen=set()
    missing=[c for c in TX_REQUIRED if c not in fields]
    if missing: return [],[{"row":1,"message":"Missing columns: "+", ".join(missing)}]
    for n,r in source:
        try:
            for f in TX_REQUIRED:
                if not r.get(f): raise ValueError(f"row {n}: {f} is required")
            if r["transaction_id"] in seen: raise ValueError(f"row {n}: duplicate transaction_id {r['transaction_id']}")
            seen.add(r["transaction_id"]); amount=Decimal(r["amount"])
            if not amount.is_finite() or amount<=0: raise ValueError(f"row {n}: amount must be a positive finite number")
            currency=r["currency"].upper()
            if len(currency)!=3 or not currency.isalpha(): raise ValueError(f"row {n}: currency must be a 3-letter code")
            result.append({**r,"amount":amount,"currency":currency,"timestamp":parse_time(r["timestamp"],n)})
        except (ValueError,InvalidOperation) as e: errors.append({"row":n,"message":str(e)})
    return result,errors
def validate_accounts(raw: bytes,max_rows=100000):
    fields,source=read_csv(raw,max_rows); errors=[]; result=[]; seen=set()
    missing=[c for c in ACCT_REQUIRED if c not in fields]
    if missing: return [],[{"row":1,"message":"Missing columns: "+", ".join(missing)}]
    for n,r in source:
        try:
            if not r["account_id"]: raise ValueError(f"row {n}: account_id is required")
            if r["account_id"] in seen: raise ValueError(f"row {n}: duplicate account_id {r['account_id']}")
            seen.add(r["account_id"])
            created=parse_time(r["created_at"],n,"created_at") if r["created_at"] else None
            opening=Decimal(r["opening_balance"]) if r["opening_balance"] else None
            result.append({**r,"created_at":created,"opening_balance":opening})
        except (ValueError,InvalidOperation) as e: errors.append({"row":n,"message":str(e)})
    return result,errors

