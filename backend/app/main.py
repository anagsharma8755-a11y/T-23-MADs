import csv, io, json, secrets, tempfile, shutil, html
from datetime import datetime, timedelta, timezone
from pathlib import Path
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, Response, Request, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, HTMLResponse
from pydantic import BaseModel, Field
from sqlalchemy import select, func, or_, delete
from sqlalchemy.orm import Session
from .config import settings
from .db import get_db, SessionLocal, engine, Base
from .models import *
from .auth import hash_password, verify_password, create_session, clear_session, current_user, require_csrf, supervisor, digest
from .ingest import validate_transactions, validate_accounts
from .detection import analyze, score_findings, DEFAULTS
from .demo import demo_csvs
from .graph_store import graph_store
from .elliptic import import_elliptic, evaluation as elliptic_evaluation, FILES as ELLIPTIC_FILES

app=FastAPI(title="MADs API",version="1.0.0",description="Workspace-scoped, explainable transaction-network investigation API")
app.add_middleware(CORSMiddleware,allow_origins=[x.strip() for x in settings.cors_origins.split(",")],allow_credentials=True,allow_methods=["*"],allow_headers=["*"])

class LoginBody(BaseModel): email:str; password:str
class RegisterBody(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    workspace_name: str = Field(min_length=2, max_length=120)
    email: str = Field(min_length=3, max_length=255, pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
    password: str = Field(min_length=10, max_length=128)
class DecisionBody(BaseModel): status:str; note:str|None=None
class SettingsBody(BaseModel): config:dict
class UserBody(BaseModel): email:str; name:str; password:str; role:str="analyst"

def audit(db,user,action,target_type,target_id,details=None): db.add(AuditEvent(workspace_id=user.workspace_id,user_id=user.id,action=action,target_type=target_type,target_id=str(target_id),details=details or {}))
def scoped_dataset(db,id,user):
    obj=db.scalar(select(Dataset).where(Dataset.id==id,Dataset.workspace_id==user.workspace_id))
    if not obj: raise HTTPException(404,"Dataset not found")
    return obj
def scoped_run(db,id,user):
    obj=db.scalar(select(AnalysisRun).join(Dataset).where(AnalysisRun.id==id,Dataset.workspace_id==user.workspace_id))
    if not obj: raise HTTPException(404,"Analysis run not found")
    return obj
def scoped_blockchain_dataset(db,id,user):
    obj=db.scalar(select(BlockchainDataset).where(BlockchainDataset.id==id,BlockchainDataset.workspace_id==user.workspace_id))
    if not obj: raise HTTPException(404,"Blockchain dataset not found")
    return obj
def latest_settings(db,user):
    row=db.scalar(select(DetectionSettings).where(DetectionSettings.workspace_id==user.workspace_id).order_by(DetectionSettings.version.desc()))
    if not row:
        row=DetectionSettings(workspace_id=user.workspace_id,version=1,config=DEFAULTS,created_by=user.id); db.add(row); db.commit(); db.refresh(row)
    return row

@app.exception_handler(ValueError)
async def value_error(_,exc): return __import__("fastapi").responses.JSONResponse(status_code=422,content={"detail":str(exc)})
@app.get("/health")
def health(): return {"status":"ok"}
@app.get("/ready")
def ready(db:Session=Depends(get_db)):
    db.execute(select(1)); neo4j="disabled"
    if graph_store.enabled:
        try: neo4j="ready" if graph_store.verify() else "unavailable"
        except Exception: neo4j="unavailable"
    return {"status":"ready","neo4j":neo4j}

@app.post("/api/auth/login")
def login(body:LoginBody,request:Request,response:Response,db:Session=Depends(get_db)):
    key=f"{request.client.host if request.client else 'unknown'}:{body.email.lower()}"; cutoff=datetime.now(timezone.utc)-timedelta(minutes=15)
    attempts=db.scalar(select(func.count()).select_from(LoginAttempt).where(LoginAttempt.key==key,LoginAttempt.success==False,LoginAttempt.attempted_at>=cutoff)) or 0
    if attempts>=5: raise HTTPException(429,"Too many login attempts. Try again later.")
    user=db.scalar(select(User).where(User.email==body.email.lower()))
    ok=bool(user and user.active and verify_password(body.password,user.password_hash)); db.add(LoginAttempt(key=key,success=ok)); db.commit()
    if not ok: raise HTTPException(401,"Invalid email or password")
    create_session(db,user,response); audit(db,user,"auth.login","user",user.id); db.commit()
    return {"id":user.id,"email":user.email,"name":user.name,"role":user.role,"workspace_id":user.workspace_id}
@app.post("/api/auth/register", status_code=201)
def register(body:RegisterBody,response:Response,db:Session=Depends(get_db)):
    email=body.email.lower()
    if db.scalar(select(User).where(User.email==email)):
        raise HTTPException(409,"An account with this email already exists")
    if not any(c.isupper() for c in body.password) or not any(c.islower() for c in body.password) or not any(c.isdigit() for c in body.password):
        raise HTTPException(422,"Password must include upper-case, lower-case, and numeric characters")
    workspace=Workspace(name=body.workspace_name.strip()); db.add(workspace); db.flush()
    user=User(workspace_id=workspace.id,email=email,name=body.name.strip(),password_hash=hash_password(body.password),role="supervisor")
    db.add(user); db.flush()
    db.add(DetectionSettings(workspace_id=workspace.id,version=1,config=DEFAULTS,created_by=user.id))
    db.flush(); audit(db,user,"auth.register","user",user.id,{"workspace_id":workspace.id})
    create_session(db,user,response)
    return {"id":user.id,"email":user.email,"name":user.name,"role":user.role,"workspace_id":user.workspace_id}
@app.post("/api/auth/logout")
def logout(request:Request,response:Response,user:User=Depends(require_csrf),db:Session=Depends(get_db)): audit(db,user,"auth.logout","user",user.id); clear_session(db,request,response); db.commit(); return {"ok":True}
@app.get("/api/auth/me")
def me(user:User=Depends(current_user)): return {"id":user.id,"email":user.email,"name":user.name,"role":user.role,"workspace_id":user.workspace_id}

@app.post("/api/uploads/preview")
async def preview(file:UploadFile=File(...),user:User=Depends(require_csrf)):
    raw=await file.read(settings.max_upload_bytes+1)
    if len(raw)>settings.max_upload_bytes: raise HTTPException(413,"File exceeds upload size limit")
    rows,errors=validate_transactions(raw,settings.max_upload_rows)
    return {"valid":not errors,"row_count":len(rows),"errors":errors[:100],"preview":[{**r,"amount":str(r["amount"]),"timestamp":r["timestamp"].isoformat()} for r in rows[:10]]}

async def import_dataset(name,tx_file,account_file,user,db):
    txraw=await tx_file.read(settings.max_upload_bytes+1)
    if len(txraw)>settings.max_upload_bytes: raise HTTPException(413,"Transaction file exceeds size limit")
    txs,errors=validate_transactions(txraw,settings.max_upload_rows); accounts=[]; aerrors=[]
    if account_file:
        araw=await account_file.read(settings.max_upload_bytes+1); accounts,aerrors=validate_accounts(araw,settings.max_upload_rows)
    if errors or aerrors: raise HTTPException(422,{"transaction_errors":errors[:100],"account_errors":aerrors[:100]})
    dataset=Dataset(workspace_id=user.workspace_id,name=name.strip() or tx_file.filename,filename=tx_file.filename,account_filename=account_file.filename if account_file else None,transaction_count=len(txs),uploaded_by=user.id,import_status="completed")
    try:
        db.add(dataset); db.flush(); ids=set()
        for r in txs:
            db.add(Transaction(dataset_id=dataset.id,**{k:r.get(k) or None for k in ["transaction_id","timestamp","sender_account","receiver_account","amount","currency","sender_device_id","receiver_device_id","sender_ip","receiver_ip"]})); ids|={r["sender_account"],r["receiver_account"]}
        amap={a["account_id"]:a for a in accounts}; ids|=set(amap)
        for aid in sorted(ids):
            a=amap.get(aid,{})
            db.add(Account(dataset_id=dataset.id,account_id=aid,created_at=a.get("created_at"),opening_balance=a.get("opening_balance"),device_id=a.get("device_id") or None,ip_address=a.get("ip_address") or None,kyc_group_id=a.get("kyc_group_id") or None))
        dataset.account_count=len(ids); audit(db,user,"dataset.import","dataset",dataset.id,{"transactions":len(txs),"accounts":len(ids)}); db.commit(); db.refresh(dataset)
        if graph_store.enabled:
            try:
                graph_store.sync_dataset(dataset.id,user.workspace_id,db.scalars(select(Account).where(Account.dataset_id==dataset.id)).all(),db.scalars(select(Transaction).where(Transaction.dataset_id==dataset.id)).all())
                audit(db,user,"graph.sync","dataset",dataset.id,{"store":"neo4j"}); db.commit()
            except Exception as exc:
                audit(db,user,"graph.sync_failed","dataset",dataset.id,{"store":"neo4j","error":str(exc)[:300]}); db.commit()
        return dataset
    except Exception: db.rollback(); raise
@app.post("/api/datasets")
async def upload_dataset(name:str=Form(...),transactions:UploadFile=File(...),accounts:UploadFile|None=File(None),user:User=Depends(require_csrf),db:Session=Depends(get_db)):
    d=await import_dataset(name,transactions,accounts,user,db); return {"id":d.id,"name":d.name,"transaction_count":d.transaction_count,"account_count":d.account_count}
@app.get("/api/datasets")
def datasets(user:User=Depends(current_user),db:Session=Depends(get_db)): return [{"id":d.id,"name":d.name,"transaction_count":d.transaction_count,"account_count":d.account_count,"created_at":d.created_at} for d in db.scalars(select(Dataset).where(Dataset.workspace_id==user.workspace_id).order_by(Dataset.created_at.desc())).all()]
@app.get("/api/datasets/{dataset_id}/summary")
def summary(dataset_id:int,user:User=Depends(current_user),db:Session=Depends(get_db)):
    d=scoped_dataset(db,dataset_id,user); totals=db.execute(select(Transaction.currency,func.sum(Transaction.amount)).where(Transaction.dataset_id==d.id).group_by(Transaction.currency)).all(); run=db.scalar(select(AnalysisRun).where(AnalysisRun.dataset_id==d.id,AnalysisRun.status=="completed").order_by(AnalysisRun.id.desc())); scores=db.scalars(select(AccountScore).where(AccountScore.run_id==run.id)).all() if run else []; accts=db.scalars(select(Account).where(Account.dataset_id==d.id)).all()
    patterns=db.execute(select(Finding.detector,func.count(Finding.id)).where(Finding.run_id==run.id).group_by(Finding.detector)).all() if run else []
    activity=db.execute(select(func.date(Transaction.timestamp),func.count(Transaction.id)).where(Transaction.dataset_id==d.id).group_by(func.date(Transaction.timestamp)).order_by(func.date(Transaction.timestamp))).all()
    shared_available=any(a.created_at and (a.device_id or a.ip_address or a.kyc_group_id) for a in accts)
    availability={"rapid_fan":{"available":True},"circular":{"available":True},"pass_through":{"available":True},"shared_attribute":{"available":shared_available,"reason":None if shared_available else "Requires account creation dates plus device, IP, or synthetic KYC metadata."}}
    return {"dataset":{"id":d.id,"name":d.name,"transaction_count":d.transaction_count,"account_count":d.account_count},"run_id":run.id if run else None,"flagged_accounts":len(scores),"high_risk":sum(s.severity=="High" for s in scores),"awaiting_review":sum(s.review_status in ("unreviewed","under_review") for s in scores),"confirmed":sum(s.review_status=="confirmed_suspicious" for s in scores),"cleared":sum(s.review_status=="cleared" for s in scores),"totals":[{"currency":c,"amount":float(a)} for c,a in totals],"activity":[{"date":str(day),"count":count} for day,count in activity],"patterns":[{"name":detector.replace("_"," ").title(),"value":count} for detector,count in patterns],"detector_availability":availability}

def execute_analysis(run_id:int):
    db=SessionLocal()
    try:
        run=db.get(AnalysisRun,run_id)
        if not run:return
        run.status="running"; run.progress=10; db.query(Finding).filter(Finding.run_id==run_id).delete(); db.query(AccountScore).filter(AccountScore.run_id==run_id).delete(); db.commit()
        txs=db.scalars(select(Transaction).where(Transaction.dataset_id==run.dataset_id)).all(); accts=db.scalars(select(Account).where(Account.dataset_id==run.dataset_id)).all(); cfg=db.get(DetectionSettings,run.settings_id).config
        found=analyze(txs,accts,cfg); run.progress=65; db.commit(); objs=[]
        for f in found: obj=Finding(run_id=run.id,**f); db.add(obj); objs.append(obj)
        db.flush(); scored=score_findings(found)
        for account,data in scored.items(): db.add(AccountScore(run_id=run.id,account_id=account,score=data["score"],severity=data["severity"],breakdown=data["breakdown"],finding_ids=[objs[i].id for i in data["finding_indexes"]]))
        run.status="completed"; run.progress=100; run.completed_at=datetime.now(timezone.utc); db.commit()
    except Exception as e:
        db.rollback(); run=db.get(AnalysisRun,run_id)
        if run: run.status="failed"; run.error=str(e); db.commit()
    finally: db.close()
@app.post("/api/datasets/{dataset_id}/analyses")
def start_analysis(dataset_id:int,background:BackgroundTasks,user:User=Depends(require_csrf),db:Session=Depends(get_db)):
    d=scoped_dataset(db,dataset_id,user); cfg=latest_settings(db,user); run=AnalysisRun(dataset_id=d.id,settings_id=cfg.id,status="queued",progress=0,created_by=user.id); db.add(run); db.flush(); audit(db,user,"analysis.start","analysis_run",run.id,{"dataset_id":d.id,"settings_version":cfg.version}); db.commit(); background.add_task(execute_analysis,run.id); return {"job_id":run.id,"status":"queued"}
@app.post("/api/analyses/{run_id}/retry")
def retry(run_id:int,background:BackgroundTasks,user:User=Depends(require_csrf),db:Session=Depends(get_db)):
    run=scoped_run(db,run_id,user); run.status="queued"; run.error=None; run.progress=0; db.commit(); background.add_task(execute_analysis,run.id); return {"job_id":run.id,"status":"queued"}
@app.get("/api/analyses/{run_id}")
def analysis_status(run_id:int,user:User=Depends(current_user),db:Session=Depends(get_db)):
    r=scoped_run(db,run_id,user); s=db.get(DetectionSettings,r.settings_id); return {"id":r.id,"dataset_id":r.dataset_id,"status":r.status,"progress":r.progress,"error":r.error,"settings_version":s.version,"created_at":r.created_at,"completed_at":r.completed_at}

@app.get("/api/analyses/{run_id}/scores")
def scores(run_id:int,q:str="",severity:str|None=None,status:str|None=None,sort:str="score",order:str="desc",page:int=1,page_size:int=50,user:User=Depends(current_user),db:Session=Depends(get_db)):
    scoped_run(db,run_id,user); stmt=select(AccountScore).where(AccountScore.run_id==run_id)
    if q: stmt=stmt.where(AccountScore.account_id.contains(q))
    if severity: stmt=stmt.where(AccountScore.severity==severity)
    if status: stmt=stmt.where(AccountScore.review_status==status)
    col={"score":AccountScore.score,"account_id":AccountScore.account_id,"severity":AccountScore.severity}.get(sort,AccountScore.score); stmt=stmt.order_by(col.desc() if order=="desc" else col.asc()); total=db.scalar(select(func.count()).select_from(stmt.subquery())); rows=db.scalars(stmt.offset((page-1)*page_size).limit(min(page_size,100))).all()
    return {"items":[{"id":x.id,"account_id":x.account_id,"score":x.score,"severity":x.severity,"breakdown":x.breakdown,"finding_ids":x.finding_ids,"review_status":x.review_status} for x in rows],"total":total,"page":page}
@app.get("/api/analyses/{run_id}/accounts/{account_id}")
def account_detail(run_id:int,account_id:str,user:User=Depends(current_user),db:Session=Depends(get_db)):
    scoped_run(db,run_id,user); score=db.scalar(select(AccountScore).where(AccountScore.run_id==run_id,AccountScore.account_id==account_id))
    if not score: raise HTTPException(404,"Flagged account not found")
    fs=db.scalars(select(Finding).where(Finding.run_id==run_id)).all(); wanted=[f for f in fs if f.id in score.finding_ids]
    tids={t for f in wanted for t in f.transaction_ids}; run=db.get(AnalysisRun,run_id); txs=db.scalars(select(Transaction).where(Transaction.dataset_id==run.dataset_id,Transaction.transaction_id.in_(tids))).all() if tids else []
    decisions=db.scalars(select(Decision).where(Decision.score_id==score.id).order_by(Decision.created_at.desc())).all()
    return {"score":{"id":score.id,"account_id":score.account_id,"score":score.score,"severity":score.severity,"breakdown":score.breakdown,"review_status":score.review_status},"findings":[{"id":f.id,"detector":f.detector,"detector_version":f.detector_version,"reason":f.reason,"limitations":f.limitations,"evidence":f.evidence,"transaction_ids":f.transaction_ids,"account_ids":f.account_ids,"currency":f.currency} for f in wanted],"transactions":[{"transaction_id":t.transaction_id,"timestamp":t.timestamp,"sender_account":t.sender_account,"receiver_account":t.receiver_account,"amount":float(t.amount),"currency":t.currency} for t in txs],"decisions":[{"status":d.status,"note":d.note,"user_id":d.user_id,"created_at":d.created_at} for d in decisions],"notice":"Risk is a prioritization score, not a calibrated probability of fraud."}
@app.post("/api/analyses/{run_id}/accounts/{account_id}/decision")
def decide(run_id:int,account_id:str,body:DecisionBody,user:User=Depends(require_csrf),db:Session=Depends(get_db)):
    scoped_run(db,run_id,user); allowed={x.value for x in ReviewStatus}
    if body.status not in allowed: raise HTTPException(422,"Invalid review status")
    if body.status in {"confirmed_suspicious","cleared"} and not (body.note and body.note.strip()): raise HTTPException(422,"A note is required when confirming or clearing")
    score=db.scalar(select(AccountScore).where(AccountScore.run_id==run_id,AccountScore.account_id==account_id))
    if not score: raise HTTPException(404,"Flagged account not found")
    score.review_status=body.status; d=Decision(score_id=score.id,status=body.status,note=body.note,user_id=user.id); db.add(d); audit(db,user,"decision.change","account_score",score.id,{"account_id":account_id,"status":body.status}); db.commit(); return {"ok":True,"status":body.status}

@app.get("/api/datasets/{dataset_id}/network")
def network(dataset_id:int,account_id:str,run_id:int|None=None,hops:int=1,node_limit:int=100,edge_limit:int=250,start:str|None=None,end:str|None=None,user:User=Depends(current_user),db:Session=Depends(get_db)):
    d=scoped_dataset(db,dataset_id,user); hops=max(1,min(hops,2)); node_limit=min(max(node_limit,1),200); edge_limit=min(max(edge_limit,1),500); graph_result=None
    if graph_store.enabled:
        try: graph_result=graph_store.neighborhood(d.id,account_id,hops,node_limit,edge_limit,start,end)
        except Exception: graph_result=None
    nodes={n["id"] for n in graph_result["nodes"]} if graph_result else {account_id}; chosen=[]; chosen_ids=set(); truncated=graph_result["truncated"] if graph_result else False
    if not graph_result:
        alltx=db.scalars(select(Transaction).where(Transaction.dataset_id==d.id).order_by(Transaction.timestamp)).all()
        for _ in range(hops):
            frontier=set(nodes)
            for t in alltx:
                if start and t.timestamp<datetime.fromisoformat(start.replace("Z","+00:00")): continue
                if end and t.timestamp>datetime.fromisoformat(end.replace("Z","+00:00")): continue
                if t.sender_account in frontier or t.receiver_account in frontier:
                    if t.id in chosen_ids: continue
                    if len(chosen)>=edge_limit or len(nodes|{t.sender_account,t.receiver_account})>node_limit: truncated=True; continue
                    chosen.append(t); chosen_ids.add(t.id); nodes|={t.sender_account,t.receiver_account}
    risks={}
    if run_id:
        scoped_run(db,run_id,user); risks={s.account_id:{"score":s.score,"severity":s.severity} for s in db.scalars(select(AccountScore).where(AccountScore.run_id==run_id,AccountScore.account_id.in_(nodes))).all()}
    if graph_result: grouped=graph_result["edges"]
    else:
        grouped={}
        for t in chosen:
            k=(t.sender_account,t.receiver_account,t.currency); g=grouped.setdefault(k,{"source":k[0],"target":k[1],"currency":k[2],"count":0,"total":0,"transactions":[]}); g["count"]+=1; g["total"]+=float(t.amount); g["transactions"].append({"id":t.transaction_id,"amount":float(t.amount),"timestamp":t.timestamp.isoformat()})
        grouped=list(grouped.values())
    return {"nodes":[{"id":n,**risks.get(n,{"score":0,"severity":"Unflagged"})} for n in nodes],"edges":grouped,"truncated":truncated,"source":"neo4j" if graph_result else "relational_fallback"}

def safe_cell(v):
    s=str(v if v is not None else ""); return "'"+s if s.startswith(("=","+","-","@")) else s
@app.get("/api/analyses/{run_id}/export")
def export(run_id:int,format:str="csv",user:User=Depends(current_user),db:Session=Depends(get_db)):
    scoped_run(db,run_id,user); scores_=db.scalars(select(AccountScore).where(AccountScore.run_id==run_id)).all(); findings=db.scalars(select(Finding).where(Finding.run_id==run_id)).all(); data=[]
    for s in scores_:
        related=[f for f in findings if f.id in s.finding_ids]; data.append({"account_id":s.account_id,"risk_score":s.score,"severity":s.severity,"review_status":s.review_status,"reasons":" | ".join(f.reason for f in related),"supporting_transactions":" | ".join(t for f in related for t in f.transaction_ids)})
    if format=="json": return data
    out=io.StringIO(); w=csv.DictWriter(out,fieldnames=list(data[0].keys()) if data else ["account_id","risk_score","severity","review_status","reasons","supporting_transactions"]); w.writeheader(); w.writerows([{k:safe_cell(v) for k,v in r.items()} for r in data]); return StreamingResponse(iter([out.getvalue()]),media_type="text/csv",headers={"Content-Disposition":f"attachment; filename=muletrace-run-{run_id}.csv"})
@app.get("/api/analyses/{run_id}/report/{account_id}",response_class=HTMLResponse)
def report(run_id:int,account_id:str,user:User=Depends(current_user),db:Session=Depends(get_db)):
    detail=account_detail(run_id,account_id,user,db); run=db.get(AnalysisRun,run_id); dataset=db.get(Dataset,run.dataset_id); cfg=db.get(DetectionSettings,run.settings_id); reasons="".join(f"<li><b>{f['detector']}</b>: {f['reason']}<br><small>{'; '.join(f['limitations'])}</small></li>" for f in detail["findings"]); txrows="".join(f"<tr><td>{t['transaction_id']}</td><td>{t['timestamp']}</td><td>{t['sender_account']}</td><td>{t['receiver_account']}</td><td>{t['currency']} {t['amount']:,.2f}</td></tr>" for t in detail["transactions"]); notes="".join(f"<li>{x['status']}: {x['note'] or '—'} ({x['created_at']})</li>" for x in detail["decisions"])
    return f"""<!doctype html><title>MADs Investigation Report</title><style>body{{font:15px Arial;max-width:900px;margin:40px auto;color:#142033}}h1{{color:#087f79}}table{{border-collapse:collapse;width:100%}}td,th{{padding:8px;border:1px solid #ccd}}small{{color:#596579}}@media print{{button{{display:none}}}}</style><button onclick='print()'>Print / save PDF</button><h1>MADs investigation report</h1><p>Dataset: <b>{dataset.name}</b> (#{dataset.id}) · Analysis run #{run.id} · Settings v{cfg.version}</p><h2>{account_id} — {detail['score']['score']}/100 ({detail['score']['severity']})</h2><p>Breakdown: {json.dumps(detail['score']['breakdown'])}. This score prioritizes review and is not a fraud probability.</p><h3>Findings</h3><ul>{reasons}</ul><h3>Supporting transactions</h3><table><tr><th>ID</th><th>Time</th><th>Sender</th><th>Receiver</th><th>Amount</th></tr>{txrows}</table><h3>Analyst decisions</h3><ul>{notes or '<li>No decisions recorded.</li>'}</ul><p><b>Data limitation:</b> Findings cover only imported records; balances and identity cannot be inferred beyond supplied metadata.</p>"""

@app.get("/api/settings")
def get_settings(user:User=Depends(current_user),db:Session=Depends(get_db)):
    s=latest_settings(db,user); return {"id":s.id,"version":s.version,"config":s.config,"created_at":s.created_at}
@app.post("/api/settings")
def save_settings(body:SettingsBody,user:User=Depends(supervisor),db:Session=Depends(get_db)):
    old=latest_settings(db,user); merged={**DEFAULTS,**body.config}; row=DetectionSettings(workspace_id=user.workspace_id,version=old.version+1,config=merged,created_by=user.id); db.add(row); db.flush(); audit(db,user,"settings.create","detection_settings",row.id,{"version":row.version}); db.commit(); return {"id":row.id,"version":row.version,"config":row.config}
@app.get("/api/audit")
def audit_history(page:int=1,user:User=Depends(current_user),db:Session=Depends(get_db)):
    rows=db.scalars(select(AuditEvent).where(AuditEvent.workspace_id==user.workspace_id).order_by(AuditEvent.created_at.desc()).offset((page-1)*50).limit(50)).all(); return [{"id":x.id,"action":x.action,"target_type":x.target_type,"target_id":x.target_id,"details":x.details,"user_id":x.user_id,"created_at":x.created_at} for x in rows]
@app.post("/api/users")
def create_user(body:UserBody,user:User=Depends(supervisor),db:Session=Depends(get_db)):
    if body.role not in {"analyst","supervisor"}: raise HTTPException(422,"Invalid role")
    if db.scalar(select(User).where(User.email==body.email.lower())): raise HTTPException(409,"Email already exists")
    row=User(workspace_id=user.workspace_id,email=body.email.lower(),name=body.name,password_hash=hash_password(body.password),role=body.role); db.add(row); db.flush(); audit(db,user,"user.create","user",row.id,{"role":row.role}); db.commit(); return {"id":row.id}
@app.get("/api/samples/{kind}")
def sample(kind:str):
    tx,acct,_=demo_csvs(); data=tx if kind=="transactions" else acct if kind=="accounts" else None
    if data is None: raise HTTPException(404,"Sample not found")
    return StreamingResponse(iter([data]),media_type="text/csv",headers={"Content-Disposition":f"attachment; filename=synthetic-{kind}.csv"})
@app.post("/api/demo/load")
async def load_demo(user:User=Depends(require_csrf),db:Session=Depends(get_db)):
    if not settings.demo_mode: raise HTTPException(404,"Demo mode is disabled")
    tx,acct,labels=demo_csvs()
    class F:
        def __init__(self,name,data): self.filename=name; self.data=data
        async def read(self,*_): return self.data
    d=await import_dataset("Synthetic MADs demo",F("synthetic-transactions.csv",tx),F("synthetic-accounts.csv",acct),user,db); audit(db,user,"demo.load","dataset",d.id,{"ground_truth":labels}); db.commit(); return {"id":d.id,"name":d.name,"ground_truth":labels}

@app.get("/api/demo/evaluation/{run_id}")
def demo_evaluation(run_id:int,user:User=Depends(current_user),db:Session=Depends(get_db)):
    if not settings.demo_mode: raise HTTPException(404,"Demo mode is disabled")
    run=scoped_run(db,run_id,user); dataset=db.get(Dataset,run.dataset_id)
    if dataset.filename!="synthetic-transactions.csv": raise HTTPException(422,"Evaluation is available only for the deterministic synthetic dataset")
    _,_,truth=demo_csvs(); findings=db.scalars(select(Finding).where(Finding.run_id==run.id)).all(); result={}
    for detector,expected_list in truth.items():
        expected=set(expected_list); detected={a for f in findings if f.detector==detector for a in f.account_ids}; tp=expected&detected; fp=detected-expected; fn=expected-detected
        result[detector]={"true_positives":sorted(tp),"false_positives":sorted(fp),"false_negatives":sorted(fn),"precision":round(len(tp)/len(detected),3) if detected else 0,"recall":round(len(tp)/len(expected),3) if expected else 0}
    return {"scope":"synthetic dataset only","run_id":run.id,"evaluation":result,"note":"Ground truth is scenario-level and stored separately from detector input. Counterparty accounts included in a finding may count as false positives in this strict account-level view."}

# Elliptic++ is a separate blockchain domain. Wallets and transaction nodes are
# never written into the bank-account tables above.
@app.post("/api/blockchain-datasets/import")
async def upload_elliptic(
    name:str=Form("Elliptic++ laptop demo"), max_transactions:int=Form(500),
    wallets_features:UploadFile=File(...), wallets_classes:UploadFile=File(...),
    AddrAddr_edgelist:UploadFile=File(...), AddrTx_edgelist:UploadFile=File(...),
    TxAddr_edgelist:UploadFile=File(...), txs_features:UploadFile=File(...),
    txs_classes:UploadFile=File(...), txs_edgelist:UploadFile=File(...),
    user:User=Depends(supervisor), db:Session=Depends(get_db),
):
    uploads={
        "wallets_features.csv":wallets_features,"wallets_classes.csv":wallets_classes,
        "AddrAddr_edgelist.csv":AddrAddr_edgelist,"AddrTx_edgelist.csv":AddrTx_edgelist,
        "TxAddr_edgelist.csv":TxAddr_edgelist,"txs_features.csv":txs_features,
        "txs_classes.csv":txs_classes,"txs_edgelist.csv":txs_edgelist,
    }
    temp=Path(tempfile.mkdtemp(prefix="muletrace-elliptic-"))
    total=0
    try:
        for official_name,upload in uploads.items():
            target=temp/official_name
            with target.open("wb") as handle:
                while chunk:=await upload.read(1024*1024):
                    total+=len(chunk)
                    if total>settings.max_blockchain_upload_bytes:
                        raise HTTPException(413,"Elliptic++ upload exceeds configured total size limit")
                    handle.write(chunk)
        dataset=import_elliptic(db,temp,user.workspace_id,user.id,name,max_transactions)
        audit(db,user,"elliptic.import","blockchain_dataset",dataset.id,{"wallets":dataset.wallet_count,"transactions":dataset.transaction_node_count,"relationships":dataset.relationship_count}); db.commit()
        if graph_store.enabled:
            try:
                graph_store.sync_blockchain_dataset(dataset.id,user.workspace_id,db.scalars(select(BlockchainWallet).where(BlockchainWallet.dataset_id==dataset.id)).all(),db.scalars(select(BlockchainTransactionNode).where(BlockchainTransactionNode.dataset_id==dataset.id)).all(),db.scalars(select(BlockchainRelationship).where(BlockchainRelationship.dataset_id==dataset.id)).all())
                audit(db,user,"elliptic.graph_sync","blockchain_dataset",dataset.id,{"store":"neo4j"}); db.commit()
            except Exception as exc:
                audit(db,user,"elliptic.graph_sync_failed","blockchain_dataset",dataset.id,{"store":"neo4j","error":str(exc)[:300]}); db.commit()
        return {"id":dataset.id,"name":dataset.name,"wallet_count":dataset.wallet_count,"transaction_node_count":dataset.transaction_node_count,"relationship_count":dataset.relationship_count}
    finally:
        shutil.rmtree(temp,ignore_errors=True)

@app.get("/api/blockchain-datasets")
def blockchain_datasets(user:User=Depends(current_user),db:Session=Depends(get_db)):
    rows=db.scalars(select(BlockchainDataset).where(BlockchainDataset.workspace_id==user.workspace_id).order_by(BlockchainDataset.imported_at.desc())).all()
    return [{"id":d.id,"name":d.name,"wallet_count":d.wallet_count,"transaction_node_count":d.transaction_node_count,"relationship_count":d.relationship_count,"imported_at":d.imported_at,"subset_method":d.subset_method} for d in rows]

@app.get("/api/blockchain-datasets/{dataset_id}/summary")
def blockchain_summary(dataset_id:int,user:User=Depends(current_user),db:Session=Depends(get_db)):
    d=scoped_blockchain_dataset(db,dataset_id,user)
    scores=db.scalars(select(BlockchainWalletScore).where(BlockchainWalletScore.dataset_id==d.id)).all()
    labels=dict(db.execute(select(BlockchainReferenceLabel.label_name,func.count()).where(BlockchainReferenceLabel.dataset_id==d.id).group_by(BlockchainReferenceLabel.label_name)).all())
    return {"dataset":{"id":d.id,"name":d.name,"wallet_count":d.wallet_count,"transaction_node_count":d.transaction_node_count,"relationship_count":d.relationship_count,"source_url":d.source_url,"schema_version":d.schema_version,"subset_method":d.subset_method,"source_files":d.source_files,"imported_at":d.imported_at},"capabilities":d.capabilities,"scores":{"flagged":sum(s.score>=40 for s in scores),"high":sum(s.severity=="High" for s in scores),"reviewed":sum(s.review_status not in ("unreviewed","under_review") for s in scores)},"reference_labels":labels,"notice":"Historical Bitcoin data — Elliptic++. Counts and findings describe the imported bounded subset, not the complete dataset."}

@app.get("/api/blockchain-datasets/{dataset_id}/wallets")
def blockchain_wallets(dataset_id:int,q:str="",page:int=1,page_size:int=50,user:User=Depends(current_user),db:Session=Depends(get_db)):
    d=scoped_blockchain_dataset(db,dataset_id,user); page_size=min(max(page_size,1),100)
    stmt=select(BlockchainWalletScore).where(BlockchainWalletScore.dataset_id==d.id)
    if q: stmt=stmt.where(BlockchainWalletScore.address.contains(q))
    total=db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows=db.scalars(stmt.order_by(BlockchainWalletScore.score.desc(),BlockchainWalletScore.address).offset((max(page,1)-1)*page_size).limit(page_size)).all()
    return {"items":[{"id":x.id,"address":x.address,"score":x.score,"severity":x.severity,"review_status":x.review_status,"reasons":x.reasons} for x in rows],"total":total,"page":max(page,1)}

@app.get("/api/blockchain-datasets/{dataset_id}/wallets/{address}")
def blockchain_wallet_detail(dataset_id:int,address:str,user:User=Depends(current_user),db:Session=Depends(get_db)):
    d=scoped_blockchain_dataset(db,dataset_id,user)
    wallet=db.scalar(select(BlockchainWallet).where(BlockchainWallet.dataset_id==d.id,BlockchainWallet.address==address)); score=db.scalar(select(BlockchainWalletScore).where(BlockchainWalletScore.dataset_id==d.id,BlockchainWalletScore.address==address))
    if not wallet or not score: raise HTTPException(404,"Wallet not found")
    label=db.scalar(select(BlockchainReferenceLabel).where(BlockchainReferenceLabel.dataset_id==d.id,BlockchainReferenceLabel.node_type=="wallet",BlockchainReferenceLabel.node_id==address))
    observations=db.scalars(select(BlockchainNodeFeature).where(BlockchainNodeFeature.dataset_id==d.id,BlockchainNodeFeature.node_type=="wallet",BlockchainNodeFeature.node_id==address).order_by(BlockchainNodeFeature.time_step)).all()
    decisions=db.scalars(select(BlockchainDecision).where(BlockchainDecision.score_id==score.id).order_by(BlockchainDecision.created_at.desc())).all()
    return {"wallet":{"address":address,"first_time_step":wallet.time_step,"feature_observations":len(observations),"features":wallet.features},"score":{"id":score.id,"score":score.score,"severity":score.severity,"breakdown":score.breakdown,"reasons":score.reasons,"evidence":score.evidence,"review_status":score.review_status},"reference_label":{"code":label.label_code,"name":label.label_name} if label else None,"reference_label_notice":"Dataset reference label; not a MADs prediction and never used as a detector input.","decisions":[{"status":x.status,"note":x.note,"user_id":x.user_id,"created_at":x.created_at} for x in decisions]}

@app.get("/api/blockchain-datasets/{dataset_id}/network")
def blockchain_network(dataset_id:int,wallet:str,hops:int=1,node_limit:int=120,edge_limit:int=300,user:User=Depends(current_user),db:Session=Depends(get_db)):
    d=scoped_blockchain_dataset(db,dataset_id,user); hops=min(max(hops,1),3); node_limit=min(max(node_limit,2),300); edge_limit=min(max(edge_limit,1),800)
    if not db.scalar(select(BlockchainWallet.id).where(BlockchainWallet.dataset_id==d.id,BlockchainWallet.address==wallet)): raise HTTPException(404,"Wallet not found")
    if graph_store.enabled:
        try:
            result=graph_store.blockchain_neighborhood(d.id,wallet,hops,node_limit,edge_limit)
            if result:
                wallet_scores={s.address:s for s in db.scalars(select(BlockchainWalletScore).where(BlockchainWalletScore.dataset_id==d.id,BlockchainWalletScore.address.in_([n["id"] for n in result["nodes"] if n["node_type"]=="wallet"]))).all()}
                for node in result["nodes"]:
                    score=wallet_scores.get(node["id"])
                    node.update({"score":score.score if score else None,"severity":score.severity if score else None})
                result["notice"]="Official directed relationships only; no pairwise transfers or edge amounts were inferred."
                return result
        except Exception:
            pass
    all_edges=db.scalars(select(BlockchainRelationship).where(BlockchainRelationship.dataset_id==d.id)).all(); nodes={("wallet",wallet)}; chosen=[]; truncated=False
    for _ in range(hops):
        frontier=set(nodes)
        for edge in all_edges:
            s=(edge.source_type,edge.source_id); t=(edge.target_type,edge.target_id)
            if s in frontier or t in frontier:
                if len(chosen)>=edge_limit or len(nodes|{s,t})>node_limit: truncated=True; continue
                if edge not in chosen: chosen.append(edge)
                nodes|={s,t}
    wallet_scores={s.address:s for s in db.scalars(select(BlockchainWalletScore).where(BlockchainWalletScore.dataset_id==d.id,BlockchainWalletScore.address.in_([n[1] for n in nodes if n[0]=="wallet"]))).all()}
    tx_steps={t.tx_id:t.time_step for t in db.scalars(select(BlockchainTransactionNode).where(BlockchainTransactionNode.dataset_id==d.id,BlockchainTransactionNode.tx_id.in_([n[1] for n in nodes if n[0]=="transaction"]))).all()}
    return {"nodes":[{"id":node_id,"node_type":node_type,"score":wallet_scores[node_id].score if node_type=="wallet" and node_id in wallet_scores else None,"severity":wallet_scores[node_id].severity if node_type=="wallet" and node_id in wallet_scores else None,"time_step":tx_steps.get(node_id)} for node_type,node_id in nodes],"edges":[{"id":e.id,"source":e.source_id,"target":e.target_id,"relationship_type":e.relationship_type,"source_type":e.source_type,"target_type":e.target_type} for e in chosen],"truncated":truncated,"notice":"Official directed relationships only; no pairwise transfers or edge amounts were inferred."}

@app.post("/api/blockchain-datasets/{dataset_id}/wallets/{address}/decision")
def blockchain_decide(dataset_id:int,address:str,body:DecisionBody,user:User=Depends(require_csrf),db:Session=Depends(get_db)):
    d=scoped_blockchain_dataset(db,dataset_id,user); allowed={x.value for x in ReviewStatus}
    if body.status not in allowed: raise HTTPException(422,"Invalid review status")
    if body.status in {"confirmed_suspicious","cleared"} and not (body.note and body.note.strip()): raise HTTPException(422,"A note is required when confirming or clearing")
    score=db.scalar(select(BlockchainWalletScore).where(BlockchainWalletScore.dataset_id==d.id,BlockchainWalletScore.address==address))
    if not score: raise HTTPException(404,"Wallet not found")
    score.review_status=body.status; db.add(BlockchainDecision(score_id=score.id,status=body.status,note=body.note,user_id=user.id)); audit(db,user,"elliptic.decision","blockchain_wallet_score",score.id,{"address":address,"status":body.status}); db.commit(); return {"ok":True,"status":body.status}

@app.get("/api/blockchain-datasets/{dataset_id}/evaluation")
def blockchain_evaluation(dataset_id:int,user:User=Depends(current_user),db:Session=Depends(get_db)):
    d=scoped_blockchain_dataset(db,dataset_id,user); return elliptic_evaluation(db,d.id)

@app.get("/api/blockchain-datasets/{dataset_id}/export")
def blockchain_export(dataset_id:int,user:User=Depends(current_user),db:Session=Depends(get_db)):
    d=scoped_blockchain_dataset(db,dataset_id,user); scores=db.scalars(select(BlockchainWalletScore).where(BlockchainWalletScore.dataset_id==d.id).order_by(BlockchainWalletScore.score.desc())).all(); labels={x.node_id:x for x in db.scalars(select(BlockchainReferenceLabel).where(BlockchainReferenceLabel.dataset_id==d.id,BlockchainReferenceLabel.node_type=="wallet")).all()}
    out=io.StringIO(); fields=["wallet_address","automated_structural_score","severity","analyst_status","reference_label","reference_label_code","reasons","evaluation_warning"]; writer=csv.DictWriter(out,fieldnames=fields); writer.writeheader()
    for score in scores:
        label=labels.get(score.address); writer.writerow({"wallet_address":safe_cell(score.address),"automated_structural_score":score.score,"severity":score.severity,"analyst_status":score.review_status,"reference_label":label.label_name if label else "","reference_label_code":label.label_code if label else "","reasons":safe_cell(" | ".join(score.reasons)),"evaluation_warning":"Reference label is not a MADs prediction and was not used as detector input."})
    return StreamingResponse(iter([out.getvalue()]),media_type="text/csv",headers={"Content-Disposition":f"attachment; filename=elliptic-subset-{d.id}-wallets.csv"})

@app.get("/api/blockchain-datasets/{dataset_id}/report/{address}",response_class=HTMLResponse)
def blockchain_report(dataset_id:int,address:str,user:User=Depends(current_user),db:Session=Depends(get_db)):
    d=scoped_blockchain_dataset(db,dataset_id,user); detail=blockchain_wallet_detail(dataset_id,address,user,db); score=detail["score"]; label=detail["reference_label"]; reasons="".join(f"<li>{html.escape(r)}</li>" for r in score["reasons"]) or "<li>No structural threshold crossed.</li>"; decisions="".join(f"<li>{html.escape(x['status'])}: {html.escape(x['note'] or '—')}</li>" for x in detail["decisions"]) or "<li>No decisions recorded.</li>"
    return f"""<!doctype html><title>MADs Elliptic++ report</title><style>body{{font:15px Arial;max-width:900px;margin:40px auto;color:#142033}}h1{{color:#7350bb}}.notice{{background:#f1ebff;padding:16px;border-radius:12px}}@media print{{button{{display:none}}}}</style><button onclick='print()'>Print / save PDF</button><h1>Historical Bitcoin data — Elliptic++</h1><p class='notice'>Bounded real-data subset. Wallet addresses are not bank accounts. Time steps are ordinal, not dates.</p><p>Dataset: <b>{html.escape(d.name)}</b> · {html.escape(d.subset_method)}</p><h2>Wallet {html.escape(address)}</h2><p>MADs structural score: <b>{score['score']}/100</b> ({score['severity']}) · Analyst status: {html.escape(score['review_status'])}</p><h3>Structural evidence</h3><ul>{reasons}</ul><h3>Dataset reference label — not a prediction</h3><p>{html.escape(label['name'] if label else 'unavailable')} ({label['code'] if label else '—'}). This label was not used as a detector input.</p><h3>Analyst decisions</h3><ul>{decisions}</ul><p><b>Capability limits:</b> No exact timestamps, edge-level amounts, balances, device IDs, IPs, or KYC attributes are present.</p>"""

@app.on_event("startup")
def recover_jobs():
    Base.metadata.create_all(engine); db=SessionLocal()
    try:
        for r in db.scalars(select(AnalysisRun).where(AnalysisRun.status.in_(["queued","running"]))).all(): r.status="failed"; r.error="Interrupted by restart; safe retry is available."
        db.commit()
    finally: db.close()

